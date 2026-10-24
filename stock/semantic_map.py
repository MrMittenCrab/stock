"""Persistent semantic candidate map.

Vectors discover plausible equivalences; only independently reviewed pair judgments
authorize grouping. Gaussian scores are monotone in cosine similarity, NOT probabilities
of equivalence. No density algorithm or transitive vector grouping can merge claims.
"""
import hashlib
import math
from pathlib import Path

MODEL = 'BAAI/bge-small-en-v1.5'
# Change this explicitly when model weights, preprocessing or embedding code changes.
CONTRACT = 'fastembed-bge-small-en-v1.5-384-v1'
SIGMA = 0.65
COSINE_FLOOR = 0.72
NEAREST = 24
BATCH = 32
_MODEL = None


def schema(store):
    store.db.execute('''CREATE TABLE IF NOT EXISTS source_semantic_vectors (
        model TEXT NOT NULL, text_sha256 TEXT NOT NULL,
        dimensions INTEGER NOT NULL, vector BLOB NOT NULL,
        PRIMARY KEY(model,text_sha256))''')


def _model():
    global _MODEL
    if _MODEL is None:
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise RuntimeError(
                "Semantic map requires the local embedding backend: "
                "run .venv/bin/python -m pip install -e '.[semantic]' "
                "before rebuilding this large archive."
            ) from exc
        from .core import ROOT
        cache = ROOT / '.data' / 'embedding-models'
        cache.mkdir(parents=True, exist_ok=True)
        _MODEL = TextEmbedding(model_name=MODEL, cache_dir=str(cache))
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


def candidate_pairs(store, rows, incoming, progress=lambda _:None, encoder=None):
    """Exact local cosine scan plus Gaussian-rank neighborhood discovery.

    Every historical passage receives a similarity score for each incoming passage.
    The retrieved set is an overinclusive screening candidate set, NOT a complete
    equivalence proof. Low-scoring pairs remain unresolved, never certified distinct.
    """
    import numpy as np
    from .sort_budget import check
    lookup = {p['id']:p for p in rows}
    new = sorted(incoming)
    old = sorted(set(lookup)-set(new))
    data,count = vectors(store,rows,progress,encoder)
    pairs=set()
    # Incoming/incoming require exhaustive direct verification.
    from itertools import combinations
    pairs.update(tuple(sorted(pair)) for pair in combinations(new,2))
    if old:
        matrix=np.stack([data[k] for k in old]).astype(np.float32)
        for key in new:
            check()
            similarity=matrix @ data[key]
            # Gaussian kernel is strictly increasing with cosine for unit vectors.
            # The explicit floor retains all dense neighbors, with a soft minimum
            # neighbor count for unexpectedly low-score paraphrases.
            gaussian=np.exp((similarity-1.0)/(SIGMA*SIGMA))
            top=min(NEAREST,len(old))
            ranked=np.argsort(-gaussian,kind='stable')
            chosen=set(int(i) for i in ranked[:top])
            chosen.update(int(i) for i in np.flatnonzero(similarity>=COSINE_FLOOR))
            pairs.update(tuple(sorted((key,old[i]))) for i in chosen)
    return pairs,dict(model=CONTRACT,embedded=count,scanned=len(new)*len(old),
                      new_new=len(new)*(len(new)-1)//2,proposed=len(pairs),
                      sigma=SIGMA,cosine_floor=COSINE_FLOOR,minimum_neighbors=NEAREST,
                      status='retrieval_only_not_verified_equivalence')
