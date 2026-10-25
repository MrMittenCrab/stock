"""Persistent semantic candidate map.

Vectors discover plausible equivalences; only independently reviewed pair judgments
authorize grouping. Gaussian scores are monotone in cosine similarity, NOT probabilities
of equivalence. No density algorithm or transitive vector grouping can merge claims.
"""
import hashlib
import math
import time

MODEL = 'BAAI/bge-small-en-v1.5'
# Change this explicitly when model weights, preprocessing or embedding code changes.
REVISION = 'aa8f8b060edb00e03bfdd08813a2949946c8ba55'
CONTRACT = 'fastembed-0.9-bge-small@'+REVISION+'-raw-text-512-cls-normalized-384-v3'
SIGMA = 0.65
BATCH = 32
STRUCTURED_CANDIDATE_LIMIT = 32
# A small, versioned unrelated reference set supplies an empirical noise baseline
# when an inventory has too few observations or a flat neighborhood. These are
# retrieval probes, not labeled investment relationships or calibration evidence.
NULL_REFERENCES = (
    'A recipe combines flour and water before baking bread.',
    'Migrating birds navigate using seasonal environmental cues.',
    'A municipal bond pays interest to its holders.',
    'Ocean currents transport heat across the planet.',
    'A retailer measures inventory turnover each quarter.',
    'A compiler translates source code into machine instructions.',
)
_MODEL = None
_MODEL_INITIALIZATION_SECONDS = 0.0


def schema(store):
    store.db.execute('''CREATE TABLE IF NOT EXISTS source_semantic_vectors (
        model TEXT NOT NULL, text_sha256 TEXT NOT NULL,
        dimensions INTEGER NOT NULL, vector BLOB NOT NULL,
        PRIMARY KEY(model,text_sha256))''')


def _model():
    global _MODEL, _MODEL_INITIALIZATION_SECONDS
    if _MODEL is None:
        started=time.monotonic()
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise ValueError(
                "Semantic map requires the local embedding backend: "
                "run .venv/bin/python -m pip install -e '.[semantic]' "
                "before rebuilding this large archive."
            ) from exc
        from .core import ROOT
        cache = ROOT / '.data' / 'embedding-models'
        cache.mkdir(parents=True, exist_ok=True)
        from huggingface_hub import snapshot_download
        path=snapshot_download('Qdrant/bge-small-en-v1.5-onnx-Q',revision=REVISION,
            cache_dir=str(cache),allow_patterns=['*.json','*.txt','model_optimized.onnx'])
        _MODEL = TextEmbedding(model_name=MODEL, cache_dir=str(cache),
            specific_model_path=path,threads=4,providers=['CPUExecutionProvider'])
        _MODEL_INITIALIZATION_SECONDS=time.monotonic()-started
    return _MODEL


def _normalized(values):
    import numpy as np
    vector = np.asarray(values, dtype=np.float32)
    if vector.shape != (384,) or not bool(np.isfinite(vector).all()):
        raise ValueError('Unexpected semantic embedding dimensions or nonfinite values')
    norm = float(np.linalg.norm(vector))
    if not math.isfinite(norm) or norm < 1e-8:
        raise ValueError('Empty or invalid semantic embedding')
    return vector / norm


def vectors(store, rows, progress=lambda _:None, encoder=None):
    """Cache by exact text hash, independent of the source record's lifecycle.

    Hash/model version prevents stale text from using another passage's embedding.
    A failed encoding request cannot publish any partial semantic grouping.
    Completed vector batches remain reusable on resume.
    """
    import numpy as np
    from .sort_budget import check
    schema(store)
    unique = {}
    for p in rows:
        unique.setdefault(hashlib.sha256(p['text'].encode('utf-8')).hexdigest(),p['text'])
    cached = {}
    missing = []
    for key,text in sorted(unique.items()):
        check()
        row = store.db.execute(
            'SELECT dimensions,vector FROM source_semantic_vectors WHERE model=? AND text_sha256=?',
            (CONTRACT,key)).fetchone()
        if row:
            dim,buffer=row
            if dim != 384 or len(buffer) != 384*4:
                raise ValueError('Corrupt stored semantic vector')
            vector = _normalized(np.frombuffer(buffer,dtype='<f4'))
            cached[key] = vector
        else:
            missing.append((key,text))
    if missing:
        backend = encoder if encoder is not None else _model()
        for offset in range(0,len(missing),BATCH):
            check()
            batch=missing[offset:offset+BATCH]
            progress(f'Semantic map · Embed {min(offset+BATCH,len(missing))}/{len(missing)}')
            encoded=list(backend.embed([t for _,t in batch],batch_size=BATCH))
            if len(encoded)!=len(batch):
                raise ValueError('Embedding backend returned incomplete batch')
            with store.db:
                for (key,_),raw in zip(batch,encoded):
                    vector = _normalized(raw)
                    cached[key] = vector
                    store.db.execute(
                        'INSERT OR REPLACE INTO source_semantic_vectors VALUES(?,?,?,?)',
                        (CONTRACT,key,384,vector.astype('<f4').tobytes()))
    return {p['id']:cached[hashlib.sha256(p['text'].encode('utf-8')).hexdigest()] for p in rows},len(missing)


def candidate_pairs(store, rows, incoming, progress=lambda _:None, encoder=None, frontier=0):
    """Empirical upper-tail discovery; explicit refinement expands quantile bands.

    Every relevant pair is scored exactly once per inventory/text/model contract.
    Deferred scores persist independently of publication. No screened pair becomes
    a negative judgment. Initial robust upper-tail / neighborhood elbow is a
    workload heuristic, not a calibrated recall guarantee or equivalence gate.
    """
    import json
    import numpy as np
    from itertools import combinations
    from .sort_budget import check
    lookup={p['id']:p for p in rows}
    new=sorted(set(incoming));old=sorted(set(lookup)-set(new))
    if not set(new)<=set(lookup):raise ValueError('Unknown incoming proposition')
    if len(rows)<2 or not new:
        return set(),dict(model=CONTRACT,embedded=0,cached_embeddings=0,
            existing_propositions=len(old),new_propositions=len(new),total_propositions=len(rows),
            scanned=0,new_new_scanned=0,similarity_calculations=0,score_cache_hit=True,
            proposed=0,deferred=0,candidate_run=None,frontier=frontier,cutoffs={},
            minimum_neighbors=0,cursor_deduplication_requests=0,
            status='no_relevant_pairs',embedding_initialization_seconds=0.0,embedding_seconds=0.0)
    started=time.monotonic()
    initialized=_MODEL is not None
    data,count=vectors(store,rows,progress,encoder)
    embedding_seconds=time.monotonic()-started
    initialization_seconds=0.0 if initialized or encoder is not None or not count else _MODEL_INITIALIZATION_SECONDS
    store.db.executescript("""
        CREATE TABLE IF NOT EXISTS source_candidate_runs(
            id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS source_candidate_scores(
            run TEXT NOT NULL, left_id TEXT NOT NULL, right_id TEXT NOT NULL,
            similarity REAL NOT NULL, PRIMARY KEY(run,left_id,right_id));
    """)
    key=hashlib.sha256(json.dumps([CONTRACT,sorted((k,p['text']) for k,p in lookup.items()),new]).encode()).hexdigest()
    cached=store.db.execute('SELECT payload FROM source_candidate_runs WHERE id=?',(key,)).fetchone()
    score_hit=bool(cached)
    if not cached:
        scored=[]
        for a,b in combinations(new,2):
            check();scored.append((key,a,b,float(np.dot(data[a],data[b]))))
        if old:
            matrix=np.stack([data[k] for k in old]).astype(np.float32)
            for a in new:
                check()
                similarity=matrix @ data[a]
                scored.extend((key,*sorted((a,b)),float(v)) for b,v in zip(old,similarity))
        with store.db:
            store.db.executemany('INSERT OR REPLACE INTO source_candidate_scores VALUES(?,?,?,?)',scored)
            store.db.execute('INSERT INTO source_candidate_runs VALUES(?,?)',(key,json.dumps({'count':len(scored)})))
    scored=store.db.execute('SELECT left_id,right_id,similarity FROM source_candidate_scores WHERE run=? ORDER BY similarity DESC,left_id,right_id',(key,)).fetchall()
    neighborhoods={k:[] for k in new}
    for a,b,v in scored:
        for k in (a,b):
            if k in neighborhoods:neighborhoods[k].append(v)
    cutoffs={};null_data=None;null_embedded=0;null_comparisons=0
    for k,values in neighborhoods.items():
        if not values:continue
        arr=np.sort(np.asarray(values))
        median=float(np.median(arr));mad=float(np.median(np.abs(arr-median)))
        upper=arr[arr>=median]
        gaps=np.diff(upper)
        if len(gaps) and float(gaps.max())>1e-6:
            elbow=float(upper[int(np.argmax(gaps))+1])
        else:
            if null_data is None:
                probes=[dict(id='null:'+str(i),text=t) for i,t in enumerate(NULL_REFERENCES)]
                null_vectors,null_embedded=vectors(store,probes,progress,encoder)
                null_data=np.stack(list(null_vectors.values()))
            baseline=null_data @ data[k];null_comparisons+=len(baseline)
            elbow=float(baseline.max())
        initial=max(median+mad,elbow)
        # Expansion is driven by the empirical inventory distribution, not top-k.
        # Final explicit rounds can examine every deferred pair, even low similarity.
        if frontier:
            base=min(float(np.mean(arr<initial)),(len(arr)-.5)/len(arr))
            q=base**(2**min(frontier,20))
            cutoff=min(initial,float(np.quantile(arr,q)))
        else:cutoff=initial
        cutoffs[k]=cutoff
    pairs={(a,b) for a,b,v in scored if any(v>=cutoffs[k]-1e-7 for k in (a,b) if k in cutoffs)}
    # A separate bounded index surfaces possible contradictions even below the
    # embedding tail. It authorizes local verification only, never grouping.
    structured=structured_candidates(rows,set(new),scored)
    structured_added=len(structured-pairs)
    pairs |= structured
    return pairs,dict(model=CONTRACT,embedded=count,cached_embeddings=len({p['text'] for p in rows})-count,
        existing_propositions=len(old),new_propositions=len(new),total_propositions=len(rows),
        scanned=len(new)*len(old),new_new_scanned=len(new)*(len(new)-1)//2,
        similarity_calculations=0 if score_hit else len(scored),score_cache_hit=score_hit,
        proposed=len(pairs),deferred=len(scored)-len(pairs),candidate_run=key,
        frontier=frontier,cutoffs=cutoffs,minimum_neighbors=0,
        null_reference_comparisons=null_comparisons,null_reference_embeddings=null_embedded,
        discovery_policy='empirical-tail-plus-structured-v3',
        structured_candidates=len(structured),structured_added=structured_added,
        structured_candidate_limit=STRUCTURED_CANDIDATE_LIMIT,
        embedding_seconds=embedding_seconds,embedding_initialization_seconds=initialization_seconds,
        cursor_deduplication_requests=0,status='adaptive_candidates_not_verified_equivalence')


def structured_candidates(rows,incoming,scored):
    """Bounded matching-condition channel; scored order is deterministic.

    Enforce an endpoint budget for every incoming item, including edges chosen
    by a different incoming item. Embedding candidates have a separate budget.
    """
    from .semantic_attributes import contradiction_signature
    signatures={p['id']:contradiction_signature(p) for p in rows}
    index={}
    for ident,signature in signatures.items():
        if signature is not None:index.setdefault(signature,set()).add(ident)
    counts={ident:0 for ident in incoming}
    selected=set()
    for a,b,_ in scored:
        signature=signatures[a]
        if signature is None or b not in index[signature]:continue
        endpoints=[ident for ident in (a,b) if ident in incoming]
        if not endpoints or any(counts[k]>=STRUCTURED_CANDIDATE_LIMIT for k in endpoints):continue
        selected.add((a,b))
        for k in endpoints:counts[k]+=1
    return selected
