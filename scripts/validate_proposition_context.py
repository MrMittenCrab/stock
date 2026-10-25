#!/usr/bin/env python3
"""Phase 2.5 validation; all SQLite work is disposable. Freeze before opening cases."""
import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from stock import semantic_map as sm, relationships as rel
from stock.core import Store
OUT=ROOT/'docs/benchmarks/proposition-context-validation'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data):path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def freeze():
    from evaluate_proposition_graph import CASES
    fixture=ROOT/'tests/fixtures/sort/semantic-coreweave.json'
    claims=json.loads(fixture.read_text())['claims']
    datasets={
        'coreweave':([dict(id=c['key'],text=c['text']) for c in claims],
            [dict(left=a['key'],right=b['key'],kind='EQUIVALENT' if a['group']==b['group'] else 'UNRESOLVED') for a,b in combinations(claims,2)]),
        'development_challenge':([dict(id=f'{i}{side}',text=text) for i,(_,a,b,_) in enumerate(CASES) for side,text in [('a',a),('b',b)]],
            [dict(left=f'{i}a',right=f'{i}b',kind=k,name=n) for i,(n,a,b,k) in enumerate(CASES)])}
    protocol=dict(version=1,starting_commit='5740ed5',frontier=0,budgets=[10,25,50,100],
        ranking='default candidate set, descending persisted cosine, lexical IDs break ties; budget clips set; no frontier expansion',
        material_kinds=['EQUIVALENT','ENTAILS','CONTRADICTS'],
        labels='Existing authored development labels, not new human adjudication. Unlabeled pairs are unreviewed, never negatives.',
        comparison='Future views must use identical inventory, labels and budgets; default candidate workload reported separately.',
        acceptance='No arbitrary recall target; document missed positives and workload. Human semantic adjudication and mandatory integrity gates required before Phase 3.',
        embedding_contract=sm.CONTRACT,nli_contract=rel.CONTRACT,relationship_policy=rel.POLICY,
        sources={str(fixture.relative_to(ROOT)):sha(fixture),'scripts/evaluate_proposition_graph.py':sha(ROOT/'scripts/evaluate_proposition_graph.py')},
        datasets={n:dict(rows=r,labels=l) for n,(r,l) in datasets.items()},
        heldout_policy='No proposition-context heldout cases or review outcomes opened before baseline file and hash are written. Heldout once only, no tuning.')
    if (OUT/'raw-baseline.json').exists():raise SystemExit('Frozen baseline already exists; will not overwrite')
    OUT.mkdir(parents=True,exist_ok=True);write(OUT/'protocol.json',protocol)
    result=dict(protocol_sha256=sha(OUT/'protocol.json'),datasets={},production_changed=False,nli_calls=0,cursor_requests=0)
    with tempfile.TemporaryDirectory(prefix='stock-context-baseline-') as tmp:
        store=Store(Path(tmp)/'baseline.db')
        for name,(rows,labels) in datasets.items():
            start=time.monotonic();pairs,stats=sm.candidate_pairs(store,rows,{r['id'] for r in rows},frontier=0)
            scores=store.db.execute('select left_id,right_id,similarity from source_candidate_scores where run=? order by similarity desc,left_id,right_id',(stats['candidate_run'],)).fetchall()
            ranked=[(a,b) for a,b,_ in scores if (a,b) in pairs]
            def coverage(selected):
                return {k:dict(labeled=sum(c['kind']==k for c in labels),retrieved=sum(c['kind']==k and tuple(sorted((c['left'],c['right']))) in selected for c in labels)) for k in ('EQUIVALENT','ENTAILS','CONTRADICTS','RELATED','UNRESOLVED')}
            missed=[c for c in labels if c['kind'] in protocol['material_kinds'] and tuple(sorted((c['left'],c['right']))) not in pairs]
            _,resume=sm.candidate_pairs(store,rows,{r['id'] for r in rows},frontier=0)
            result['datasets'][name]=dict(inventory_size=len(rows),total_possible_pairs=len(rows)*(len(rows)-1)//2,default_candidate_pairs=len(pairs),coverage=coverage(pairs),missed_material=missed,
                matched_budgets=[dict(budget=b,reviewed=min(b,len(ranked)),coverage=coverage(set(ranked[:b]))) for b in protocol['budgets']],
                ranked_candidates=[dict(left=a,right=b,cosine=v) for a,b,v in scores if (a,b) in pairs],metrics=stats,resume_metrics=resume,elapsed_seconds=time.monotonic()-start)
        result['vector_cache_bytes']=store.db.execute('select sum(length(vector)) from source_semantic_vectors').fetchone()[0]
        store.db.close()
    write(OUT/'raw-baseline.json',result)
    (OUT/'raw-baseline.sha256').write_text(sha(OUT/'raw-baseline.json')+'  raw-baseline.json\n')
    print(json.dumps({n:{k:d[k] for k in ('inventory_size','total_possible_pairs','default_candidate_pairs','coverage','missed_material')} for n,d in result['datasets'].items()},indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['freeze']);args=parser.parse_args();freeze()
