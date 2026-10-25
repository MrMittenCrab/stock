"""Paired 0893253/current audit using immutable previously recorded raw scores.

All writes are to a disposable database. Original gold fixtures are unchanged;
source-grounded supplier disagreement is reported separately, never substituted.
"""
import argparse
from itertools import combinations
import json
from pathlib import Path
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from stock import relationships as rel, semantic_map
from stock.core import Store
from compare_financial_nli import baseline_module,summarize
from evaluate_semantic_quality import evaluate


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    prior=json.loads((ROOT/'docs/benchmarks/semantic-quality.json').read_text())
    old=baseline_module('relationships');old_map=baseline_module('semantic_map');started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='stock-correctness-') as directory:
        store=Store(Path(directory)/'audit.db');rel.schema(store)
        for name in ('coreweave','original_challenge','independent_heldout','disclosures_heldout'):
            for c in prior[name]['cases']:
                texts=c['texts'];raw=[c['scores'][key] for key in ('left_to_right','right_to_left')]
                store.db.execute('INSERT OR REPLACE INTO source_nli_cache VALUES(?,?,?)',
                    (rel._digest([rel.CONTRACT,*texts]),rel.CONTRACT,json.dumps(raw)))
        store.db.commit();reports={}
        def run(name,claims,cases):
            result=evaluate(store,name,claims,cases,old)
            rows=[dict(p,id=p['key'],location=dict(references=p.get('references',[])),speaker=None,category='Management') for p in claims]
            before_pairs,before_stats=old_map.candidate_pairs(store,rows,{p['id'] for p in rows})
            for c in result['cases']:c['retrieved_before']=tuple(sorted((c['left'],c['right']))) in before_pairs
            result['summary_before']=summarize(result['cases'],'before');result['summary_after']=summarize(result['cases'],'after')
            for policy in ('before','after'):
                field='retrieved_before' if policy=='before' else 'retrieved'
                end_to_end=[dict(c,**{policy:c[policy] if c[field] else dict(kind='UNRESOLVED')}) for c in result['cases']]
                result['end_to_end_'+policy]=summarize(end_to_end,policy)
            result['initial_retrieval_before']=dict(candidates=len(before_pairs),**{k:dict(gold=sum(c['gold']==k for c in result['cases']),retrieved=sum(c['gold']==k and c['retrieved_before'] for c in result['cases'])) for k in ('EQUIVALENT','ENTAILS','CONTRADICTS')})
            result['initial_retrieval_after']=dict(candidates=result['frontiers'][0]['candidates'],**result['frontiers'][0]['by_kind'])
            # The old taxonomy describes 4e01591, so do not republish it as a
            # diagnosis of 0893253. Exact before/after decisions remain auditable.
            for c in result['cases']:c.pop('failure_taxonomy_before',None)
            reports[name]=result
        fixture=json.loads((ROOT/'tests/fixtures/sort/semantic-coreweave.json').read_text())
        claims=fixture['claims'];cases=[(a['key'],b['key'],'EQUIVALENT' if a['group']==b['group'] else 'UNRESOLVED',a['key']+'/'+b['key']) for a,b in combinations(claims,2)]
        run('coreweave',claims,cases)
        from evaluate_proposition_graph import CASES
        for name,data in [('original_challenge',CASES),('independent_heldout',json.loads((ROOT/'tests/fixtures/financial-relationships-heldout.json').read_text())['cases'])]:
            claims=[];cases=[]
            for i,(label,a,b,gold) in enumerate(data):
                ka,kb=f'{i}a',f'{i}b';claims.extend([dict(key=ka,text=a),dict(key=kb,text=b)]);cases.append((ka,kb,gold,label))
            run(name,claims,cases)
        disclosures=json.loads((ROOT/'tests/fixtures/financial-disclosures-heldout.json').read_text());claims=[];cases=[]
        for i,(label,source,a,b,gold) in enumerate(disclosures['cases']):
            ka,kb=f'{i}a',f'{i}b';attrs=dict(issuer='Microsoft' if source=='microsoft' else 'Apple',period='2024',scope='issuer')
            claims.extend(dict(key=k,text=t,attributes=attrs,references=[disclosures['sources'][source]]) for k,t in ((ka,a),(kb,b)))
            cases.append((ka,kb,gold,label))
        run('disclosures_heldout',claims,cases)
        combined=[c for report in reports.values() for c in report['cases']]
        reports['combined']={policy:summarize(combined,policy) for policy in ('before','after')}
        reports['disputed_labels']=[dict(dataset='coreweave',case='suppliers-summary/suppliers-detail',original_gold='EQUIVALENT',adjudication='RELATED',
            automatic_kind=next(c['after']['kind'] for c in reports['coreweave']['cases'] if c['case']=='suppliers-summary/suppliers-detail'),
            reason='Supplier concentration is shared, but component availability disruption is not the same trigger as disruption at suppliers. The summary also explicitly covers capacity increases and platform/services components. Neither complete proposition safely entails the other without an added causal assumption. Same source anchors do not make two reconstructions equivalent.',
            evidence=[c for c in fixture['claims'] if c['key'].startswith('suppliers-')])]
        reports['disputed_labels'].append(dict(dataset='independent_heldout',case='mixed-modality',
            original_gold='UNRESOLVED',adjudication='ENTAILS',direction='right_to_left',
            reason='The longer claim repeats the entire actual-period assertion and appends a forecast conjunct. It entails the shorter actual assertion, while the reverse does not. Original labels and strict scores remain unchanged.'))
        reports.update(baseline_commit='0893253',policy=rel.POLICY,inference_contract=rel.CONTRACT,
            score_source='Previously committed exact original-text scores in semantic-quality.json; no new NLI needed for these observed fixtures.',
            elapsed_seconds=time.monotonic()-started,production_changed=False)
        args.output.write_text(json.dumps(reports,indent=2)+'\n')
        print(json.dumps({k:v for k,v in reports.items() if k in ('combined','elapsed_seconds')},indent=2))
        for name in ('coreweave','original_challenge','independent_heldout','disclosures_heldout'):
            print(name,json.dumps({k:reports[name][k] for k in ('summary_before','summary_after','initial_retrieval_before','initial_retrieval_after')}))
        store.db.close()

if __name__=='__main__':main()
