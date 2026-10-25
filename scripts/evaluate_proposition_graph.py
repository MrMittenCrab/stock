"""Real local-model evaluation; all writes target disposable databases.

Default: labeled financial cases plus committed CoreWeave excerpts. --inventory
also reads the published CoreWeave inventory through SQLite mode=ro and evaluates
13 incoming fixture claims against it, without publishing or re-extracting.
"""
import argparse
import hashlib
import json
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from stock import semantic_map,relationships,sources
from stock.core import Store,DB

# Hand-labeled challenge examples, not a representative calibration sample.
CASES=[
 ('equivalent','CoreWeave serves customers.','CoreWeave provides services to clients.','EQUIVALENT'),
 ('mutual','CoreWeave revenue was $5 billion in 2025.','In 2025 CoreWeave generated $5 billion of revenue.','EQUIVALENT'),
 ('containment','CoreWeave serves customers and operates data centers.','CoreWeave serves customers.','ENTAILS'),
 ('theme','CoreWeave operates data centers.','CoreWeave purchases GPUs.','RELATED'),
 ('contradiction','CoreWeave revenue increased in 2025.','CoreWeave revenue decreased in 2025.','CONTRADICTS'),
 ('period','CoreWeave revenue increased in 2025.','CoreWeave revenue increased in 2026.','UNRESOLVED'),
 ('forecast','CoreWeave revenue is $5 billion.','CoreWeave forecasts revenue of $5 billion.','UNRESOLVED'),
 ('capacity','CoreWeave has 850 MW active power.','CoreWeave has 850 MW contracted power.','UNRESOLVED'),
 ('scope','CoreWeave revenue increased in Europe.','CoreWeave revenue increased globally.','UNRESOLVED'),
 ('definition','CoreWeave backlog is $5 billion.','CoreWeave revenue is $5 billion.','UNRESOLVED'),
 ('qualification','CoreWeave demand exceeds capacity.','CoreWeave demand exceeds capacity except in Europe.','UNRESOLVED'),
 ('issuer','CoreWeave revenue increased in 2025.','Microsoft revenue increased in 2025.','UNRESOLVED'),
 ('numeric','CoreWeave revenue was $5 billion in 2025.','CoreWeave revenue was $6 billion in 2025.','UNRESOLVED'),
 ('containment_explicit','CoreWeave provides cloud services and employs engineers.','CoreWeave provides cloud services.','ENTAILS'),
 ('contradiction_scoped','CoreWeave revenue increased globally in 2025.','CoreWeave revenue decreased globally in 2025.','CONTRADICTS'),
 ('uncertain','CoreWeave may expand.','CoreWeave intends to expand.','UNRESOLVED'),
]


def labeled(store):
    rows=[]
    for i,(_,a,b,_) in enumerate(CASES):
        rows.extend([dict(id=f'{i}a',text=a),dict(id=f'{i}b',text=b)])
    selected,stats=semantic_map.candidate_pairs(store,rows,{r['id'] for r in rows})
    results=[]
    for i,(label,a,b,gold) in enumerate(CASES):
        left=dict(text=a,category='Management',speaker=None,location={})
        right=dict(text=b,category='Management',speaker=None,location={})
        r=relationships.judge(store,left,right,'label:'+str(i)+'a','label:'+str(i)+'b')
        results.append(dict(case=label,gold=gold,predicted=r['kind'],direction=r['direction'],
            retrieved=tuple(sorted((f'{i}a',f'{i}b'))) in selected,scores=r['scores'],safeguards=r['safeguards']))
    material=[r for r in results if r['gold'] in ('EQUIVALENT','ENTAILS','CONTRADICTS')]
    standalone_asserted=[r for r in results if r['predicted'] in ('EQUIVALENT','ENTAILS','CONTRADICTS')]
    asserted=[r for r in standalone_asserted if r['retrieved']]
    return dict(standalone_asserted_relationship_count=len(standalone_asserted),
        standalone_asserted_relationship_precision=sum(r['predicted']==r['gold'] for r in standalone_asserted)/len(standalone_asserted) if standalone_asserted else None,
        provenance='Hand-labeled synthetic challenge cases; real pinned model outputs; not calibration',
        cases=results,candidate_material_recall=sum(r['retrieved'] for r in material)/len(material),
        asserted_relationship_count=len(asserted),material_gold_count=len(material),
        asserted_relationship_precision=sum(r['predicted']==r['gold'] for r in asserted)/len(asserted) if asserted else None,
        correct_classifications=sum(r['predicted']==r['gold'] for r in results),total=len(results),
        candidate_metrics=stats)


def inventory(store):
    # No Store is ever opened on production; connection is explicitly read-only.
    conn=sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True)
    conn.row_factory=sqlite3.Row
    rows=[dict(r) for r in conn.execute('''SELECT p.id,p.text,p.category,p.speaker,p.location,p.document_id
        FROM source_passages p JOIN archive_documents d ON d.id=p.document_id WHERE d.ticker='CRWV.US' ''')]
    conn.close()
    for r in rows:r['location']=json.loads(r['location'])
    fixture=json.loads((ROOT/'tests/fixtures/sort/semantic-coreweave.json').read_text())
    new=[dict(id='incoming:'+c['key'],text=c['text'],category='Management',speaker=None,location={}) for c in fixture['claims']]
    all_rows=rows+new;lookup={r['id']:r for r in all_rows};incoming={r['id'] for r in new}
    selected,metrics=semantic_map.candidate_pairs(store,all_rows,incoming)
    start=time.monotonic();edges=[]
    for a,b in sorted(selected):
        fps=[hashlib.sha256(json.dumps(lookup[m],sort_keys=True).encode()).hexdigest() for m in (a,b)]
        edges.append(relationships.judge(store,lookup[a],lookup[b],*fps))
    elapsed=time.monotonic()-start
    reused=[]
    for a,b in sorted(selected):
        fps=[hashlib.sha256(json.dumps(lookup[m],sort_keys=True).encode()).hexdigest() for m in (a,b)]
        reused.append(relationships.judge(store,lookup[a],lookup[b],*fps))
    _,resume=semantic_map.candidate_pairs(store,all_rows,incoming)
    from collections import Counter
    return dict(provenance='Published CoreWeave inventory, SQLite read-only; incoming committed source excerpts; no new gold labels',
        metrics=metrics,outcomes=dict(Counter(e['kind'] for e in edges)),
        local_nli_inference_count=sum(e['inference_count'] for e in edges),nli_wall_seconds=elapsed,
        resume_inference_count=sum(e['inference_count'] for e in reused),resume_metrics=resume,
        final_precision=None,production_changed=False,cursor_deduplication_requests=0)


def excerpts(directory):
    # Existing fixture loader now stages real local graph evidence rather than
    # replaying Cursor equivalence judgments.
    import runpy
    return runpy.run_path(str(ROOT/'scripts/verify_semantic_insights.py'))['replay'](directory)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--inventory',action='store_true')
    parser.add_argument('--output',type=Path);args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='stock-graph-eval-') as directory:
        s=Store(Path(directory)/'local.db');start=time.monotonic()
        report=dict(embedding_model=semantic_map.CONTRACT,inference_model=relationships.CONTRACT,
            policy=relationships.POLICY,labeled=labeled(s),excerpts=excerpts(Path(directory)/'excerpts'))
        if args.inventory:report['inventory']=inventory(s)
        report.update(total_seconds=time.monotonic()-start,
            nli_initialization_seconds=getattr(relationships._BACKEND,'initialization_seconds',None),
            nli_model_execution_seconds=getattr(relationships._BACKEND,'inference_seconds',None),
            cursor_deduplication_requests=0,production_changed=False)
        s.db.close()
    text=json.dumps(report,indent=2)
    if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text+'\n')
    print(text)

if __name__=='__main__':main()
