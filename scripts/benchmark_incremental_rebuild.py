"""Offline workload replay on a disposable SQLite backup; never calls Cursor.

Synthetic negative answers measure coverage/batching, not semantic correctness.
The focused semantic fixtures test the actual grouping/complete-link behavior.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3
import tempfile
import time

from stock import insights, sources
from stock.archive import documents
from stock.core import DB, Store
from stock.evidence import extract


class NoModel:
    def extract(self,*args):
        raise AssertionError('Extraction/review checkpoint miss; live calls prohibited')


class Replay:
    def __init__(self):
        self.pairs=set();self.requests=0;self.characters=0

    def extract(self,unit,context):
        pairs=unit['semantic_pairs'];self.requests+=1
        self.characters+=len(insights.packed(insights.comparison_payload(pairs)))
        self.pairs.update(tuple(sorted((p['left']['id'],p['right']['id']))) for p in pairs)
        return [dict(pair=p['id'],equivalent=False,relation='different',
            dimensions_agree=False,information_preserved=False,
            reason='Synthetic offline replay: no semantic conclusion.',differences=['Offline fixture.']) for p in pairs]


def benchmark(database=DB):
    directory=Path(tempfile.mkdtemp(prefix='stock-incremental-'))
    original=sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro',uri=True)
    copy=sqlite3.connect(directory/'stock.sqlite3');original.backup(copy);copy.close();original.close()
    store=Store(directory/'stock.sqlite3')
    doc=next(d for d in documents(store,'CRWV.US') if d['id']==13)
    candidate=store.db.execute('SELECT id,markdown,manifest,quality_status FROM archive_evidence_versions WHERE document_id=13 ORDER BY id DESC LIMIT 1').fetchone()
    if candidate:doc.update(evidence_version=candidate[0],markdown=candidate[1],evidence=candidate[2],quality_status=candidate[3])
    artifacts=store.db.execute('SELECT id,checksum FROM knowledge_artifacts WHERE document_id=13 ORDER BY id').fetchall()
    start=time.monotonic();proposed,verify=extract(store,doc,NoModel(),lambda _:None);verify()
    extraction_seconds=time.monotonic()-start
    assert artifacts==store.db.execute('SELECT id,checksum FROM knowledge_artifacts WHERE document_id=13 ORDER BY id').fetchall()
    old=sources.passages(store,'CRWV.US')
    incoming=[dict(p,id=sources.passage_id(doc,p),document_id=13) for p in proposed]
    incoming_ids={p['id'] for p in incoming}
    rows=[p for p in old if p['document_id']!=13]+incoming
    lookup={p['id']:p for p in rows}
    docs={d['id']:{k:d.get(k) for k in ('id','title','type','publisher','period','publication_date','source_sha256','metadata_provenance')} for d in documents(store,'CRWV.US')}
    fps={p['id']:insights.passage_fingerprint(p,docs[p['document_id']]) for p in rows}
    counts=Counter();pending=[]
    cache={k:json.loads(v) for k,v in store.db.execute('SELECT fingerprint,payload FROM source_semantic_cache WHERE contract=?',(insights.CONTRACT,))}
    for a,b in insights.retrieve(rows):
        category=('unchanged_unchanged','new_existing','new_new')[int(a in incoming_ids)+int(b in incoming_ids)]
        counts[category]+=1
        key=insights.digest([insights.CONTRACT,*sorted((fps[a],fps[b]))])
        pair=dict(id=key,left=insights.evidence_payload(lookup[a],docs[lookup[a]['document_id']]),right=insights.evidence_payload(lookup[b],docs[lookup[b]['document_id']]))
        if key in cache:counts[category+'_cached']+=1
        elif len(insights.packed(insights.comparison_payload([pair])))>14000:counts[category+'_oversized_unreviewed']+=1
        else:pending.append((category,pair))
    batches=[];chunk=[]
    for item in pending:
        if chunk and len(insights.packed(insights.comparison_payload([p for _,p in chunk]+[item[1]])))>14000:
            batches.append(chunk);chunk=[]
        chunk.append(item)
    if chunk:batches.append(chunk)
    counts['remaining_model_batches']=len(batches)
    counts['remaining_batches_touching_replacement']=sum(any(c!='unchanged_unchanged' for c,_ in batch) for batch in batches)
    replay=Replay();start=time.monotonic()
    proposal=insights.stage(store,'CRWV.US',replay,lambda _:None,new_document=(doc,proposed))
    seconds=time.monotonic()-start
    required={tuple(sorted((a['id'],b['id']))) for a in incoming for b in rows if a['id']!=b['id']}
    reused=set()
    for pair in required-replay.pairs:
        key=insights.digest([insights.CONTRACT,*sorted(fps[i] for i in pair)])
        assert key in cache and insights.valid_cached_decision(cache[key])
        reused.add(pair)
    assert replay.pairs|reused==required
    assert all(set(pair)&incoming_ids for pair in replay.pairs)
    start=time.monotonic();resumed=insights.stage(store,'CRWV.US',NoModel(),lambda _:None,new_document=(doc,proposed))
    resume_seconds=time.monotonic()-start
    from stock.rebuild import rebuild
    assert rebuild(store,'CRWV.US','13',NoModel,lambda _:None)
    assert insights.head(store,'CRWV.US') and len(sources.passages(store,'CRWV.US'))==len(rows)
    assert {p['id'] for p in sources.passages(store,'CRWV.US')}==set(lookup)
    assert sum(len(e['members']) for e in insights.entries(store,'CRWV.US',document_id=13))==len(proposed)
    report=dict(disposable_database=str(directory/'stock.sqlite3'),offline_only=True,
        before=dict(counts),cache_entries=len(cache),valid_cache_entries=sum(insights.valid_cached_decision(r) for r in cache.values()),
        active_heads_before=proposal['parent'],verified_propositions=len(proposed),
        source_references=sum(len(p['location']['references']) for p in proposed),
        unique_source_anchors=len({r['source_id'] for p in proposed for r in p['location']['references']}),
        extraction_review_model_requests=0,extraction_review_seconds=extraction_seconds,
        checkpoint_artifacts_unchanged=len(artifacts),
        after=dict(candidate_pairs=len(required),new_new=len(incoming)*(len(incoming)-1)//2,
            new_existing=len(incoming)*(len(rows)-len(incoming)),unchanged_unchanged_model_pairs=0,
            cache_hits=proposal['cached_decisions']-proposal['historical_cached_decisions'],
            historical_cache_hits=proposal['historical_cached_decisions'],model_batches=proposal['model_requests'],
            serialized_characters=replay.characters,offline_seconds=seconds,
            resume_seconds=resume_seconds,resume_requests=resumed['model_requests'],
            historical_retrieval_backlog=proposal['historical_backlog_pairs']),
        automatic_publication_on_copy=True,production_publication=False,
        limitation='Synthetic replay measures workload and completeness of pair coverage, not semantic accuracy or live latency.')
    store.db.close()
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--database',type=Path,default=DB)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();report=benchmark(args.database)
    text=json.dumps(report,indent=2)
    if args.output:args.output.write_text(text+'\n')
    print(text)
