"""Paired policy experiment, exhaustive labeled classification, independent frontier.

All model/cache writes are to a disposable DB. The baseline policy is loaded from
commit 4e01591. Both policies consume identical original-text raw NLI predictions;
no threshold/model tuning, no production connection, no remote model requests.
"""
import argparse
from collections import Counter
from itertools import combinations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import types

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from stock import relationships as rel, semantic_map, proposition_graph
from stock.core import Store


def baseline():
    module=types.ModuleType('stock._baseline_relationships')
    exec(compile(subprocess.check_output(['git','show','4e01591:stock/relationships.py'],cwd=ROOT),'<baseline>','exec'),module.__dict__)
    return module


def metrics(rows,policy,retrieved_only=False):
    selected=[r for r in rows if r['retrieved'] or not retrieved_only]
    result={'evaluated':len(selected),'unresolved':sum(r[policy]['kind']=='UNRESOLVED' for r in selected)}
    for kind in ('EQUIVALENT','ENTAILS','CONTRADICTS'):
        gold=sum(r['gold']==kind for r in rows)
        predicted=[r for r in selected if r[policy]['kind']==kind]
        tp=sum(r['gold']==kind and (kind!='ENTAILS' or r[policy]['direction']=='left_to_right') for r in predicted)
        result[kind]=dict(gold=gold,predicted=len(predicted),correct=tp,
            recall=tp/gold if gold else None,precision=tp/len(predicted) if predicted else None)
    result['false_merges']=sum(r['gold']!='EQUIVALENT' and r[policy]['kind']=='EQUIVALENT' for r in selected)
    result['missed_merges']=result['EQUIVALENT']['gold']-result['EQUIVALENT']['correct']
    return result


def taxonomy(row):
    """Positive-only failure audit; an absent negative pair is not a miss.

    Root causes can coexist. Model errors (<.5 gold probability) are separated
    from supportive scores failing the unchanged provisional confidence gate.
    Human-reviewed exceptions document where lexical attributes mislead.
    """
    if row['gold'] not in ('EQUIVALENT','ENTAILS','CONTRADICTS'):
        return None
    old=row['before'];scores=row['scores']
    failed=old['kind']!=row['gold'] or (row['gold']=='ENTAILS' and old['direction']!='left_to_right')
    audit={key:False for key in ('incorrect_embedding_retrieval','incorrect_nli_inference',
        'overly_restrictive_decision_thresholds','explicitly_conflicting_attributes',
        'missing_contextual_attributes','incorrectly_extracted_attributes','genuine_source_ambiguity',
        'overly_restrictive_attribute_veto')}
    audit['incorrect_embedding_retrieval']=not row['retrieved']
    if not failed:return dict(categories=audit,explanation='Baseline classification is correct; retrieval is assessed independently.')
    audit['missing_contextual_attributes']=any(x.startswith('unknown_') for x in old['safeguards'])
    audit['incorrectly_extracted_attributes']=row['gold']=='EQUIVALENT' and any(x in old['safeguards'] for x in
        ('numbers','period','named_entities','qualification','metric','modality_terms'))
    if row['gold']=='EQUIVALENT':
        support=min(x['entailment'] for x in scores.values())
    elif row['gold']=='ENTAILS':
        support=min(scores['left_to_right']['entailment'],scores['right_to_left']['neutral'])
    else:support=min(x['contradiction'] for x in scores.values())
    audit['incorrect_nli_inference']=support<.5
    audit['overly_restrictive_decision_thresholds']=.5<=support<.985
    label=row['case']
    explanation='See exact original texts, bidirectional scores, baseline vetoes and revised compatibility trace.'
    if label=='suppliers-summary/suppliers-detail':
        audit['genuine_source_ambiguity']=True
        explanation=('Same source wording, but the label is presentation equivalence: the summary explicitly asserts limited suppliers '
            'as well as a disruption risk; the detail compresses that premise. Issuer is deictic on one side. '
            'No invented period/scope or forced merge; both raw NLI directions fail.')
    if row['gold']=='ENTAILS' and any(x in old['safeguards'] for x in ('numbers','metric','scope')):
        audit['overly_restrictive_attribute_veto']=True
        explanation=('Extra premise detail is directional information, not evidence against entailment. '
            'Literal first-conjunct projection can resolve only exact clause containment with compatible source context; '
            'other directional cases remain subject to the original NLI thresholds.')
    # A positive label does not by itself establish the absence of disagreement.
    # These cases were manually reviewed: remaining vetoes are lexical differences,
    # absent context or extra premise content; no explicit material conflict was found.
    return dict(categories=audit,explanation=explanation,
        threshold_note='A threshold flag records supportive scores below the gate; it does not justify lowering it.')


def evaluate(store,name,claims,cases,old):
    rows=[dict(p,id=p['key'],location=dict(references=p.get('references',[])),speaker=None,category='Management') for p in claims]
    lookup={p['id']:p for p in rows};incoming=set(lookup)
    contextual={p['id']:rel.with_context(p,{'id':p.get('document')}) for p in rows}
    frontiers=[];selected=set()
    for frontier in (0,1,2,4):
        pairs,stats=semantic_map.candidate_pairs(store,rows,incoming,frontier=frontier)
        if frontier==0:selected=pairs;initial_stats=stats
        material=[c for c in cases if c[2] in ('EQUIVALENT','ENTAILS','CONTRADICTS')]
        frontiers.append(dict(frontier=frontier,candidates=len(pairs),
            material_gold=len(material),material_retrieved=sum(tuple(sorted(c[:2])) in pairs for c in material),
            by_kind={k:dict(gold=sum(c[2]==k for c in material),retrieved=sum(c[2]==k and tuple(sorted(c[:2])) in pairs for c in material)) for k in ('EQUIVALENT','ENTAILS','CONTRADICTS')},
            embedded=stats['embedded'],similarities=stats['similarity_calculations']))
    results=[];count=0
    for a,b,gold,label in cases:
        x=rel.judge(store,contextual[a],contextual[b],name+':'+a,name+':'+b)
        count+=x['inference_count']
        raw=x['scores'];before=old.decide(lookup[a],lookup[b],raw['left_to_right'],raw['right_to_left'])
        pair=tuple(sorted((a,b)))
        score=store.db.execute('SELECT similarity FROM source_candidate_scores WHERE run=? AND left_id=? AND right_id=?',
            (initial_stats['candidate_run'],*pair)).fetchone()
        candidate_trace=dict(similarity=score[0] if score else None,
            cutoffs={key:initial_stats['cutoffs'].get(key) for key in (a,b)})
        results.append(dict(candidate_trace=candidate_trace,case=label,left=a,right=b,texts=[lookup[a]['text'],lookup[b]['text']],gold=gold,
            retrieved=tuple(sorted((a,b))) in selected,scores=raw,before=before,after=x,
            baseline_attributes=[old.attributes(lookup[a]),old.attributes(lookup[b])],
            revised_attributes=[rel.attributes(contextual[a]),rel.attributes(contextual[b])]))
    for r in results:r['failure_taxonomy_before']=taxonomy(r)
    resumed=[rel.judge(store,contextual[a],contextual[b],name+':'+a,name+':'+b) for a,b,_,_ in cases]
    report=dict(cases=results,frontiers=frontiers,inference_count=count,resume_inference_count=sum(r['inference_count'] for r in resumed),
        before=metrics(results,'before'),after=metrics(results,'after'),
        retrieved_before=metrics(results,'before',True),retrieved_after=metrics(results,'after',True))
    if name=='coreweave':
        for policy in ('before','after'):
            edges=[dict(r[policy],left=r['left'],right=r['right']) for r in results if r['retrieved']]
            groups=proposition_graph.groups(rows,edges,set())
            report[policy]['presentation_groups']=len(groups)
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    old=baseline();started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='stock-semantic-quality-') as directory:
        store=Store(Path(directory)/'audit.db')
        fixture=json.loads((ROOT/'tests/fixtures/sort/semantic-coreweave.json').read_text())
        claims=fixture['claims'];cases=[(a['key'],b['key'],'EQUIVALENT' if a['group']==b['group'] else 'UNRESOLVED',a['key']+'/'+b['key']) for a,b in combinations(claims,2)]
        coreweave=evaluate(store,'coreweave',claims,cases,old)
        from evaluate_proposition_graph import CASES
        datasets=[('original_challenge',CASES),('independent_heldout',json.loads((ROOT/'tests/fixtures/financial-relationships-heldout.json').read_text())['cases'])]
        report=dict(coreweave=coreweave)
        for name,data in datasets:
            claims=[];cases=[]
            for i,(label,a,b,gold) in enumerate(data):
                ka,kb=f'{i}a',f'{i}b';claims.extend([dict(key=ka,text=a),dict(key=kb,text=b)])
                cases.append((ka,kb,gold,label))
            report[name]=evaluate(store,name,claims,cases,old)
        disclosures=json.loads((ROOT/'tests/fixtures/financial-disclosures-heldout.json').read_text())
        claims=[];cases=[]
        for i,(label,source,a,b,gold) in enumerate(disclosures['cases']):
            ka,kb=f'{i}a',f'{i}b'
            attrs=dict(issuer='Microsoft' if source=='microsoft' else 'Apple',period='2024',scope='issuer')
            for key,text in ((ka,a),(kb,b)):
                claims.append(dict(key=key,text=text,attributes=attrs,references=[disclosures['sources'][source]]))
            cases.append((ka,kb,gold,label))
        report['disclosures_heldout']=evaluate(store,'disclosures_heldout',claims,cases,old)
        report['disclosures_heldout']['provenance']=disclosures['provenance']
        report['disclosures_heldout']['sources']=disclosures['sources']
        store.db.close()
    report.update(baseline_commit='4e01591',policy=rel.POLICY,inference_contract=rel.CONTRACT,
        nli_initialization_seconds=rel._BACKEND.initialization_seconds,nli_execution_seconds=rel._BACKEND.inference_seconds,
        elapsed_seconds=time.monotonic()-started,production_changed=False,cursor_deduplication_requests=0,
        provenance='Exhaustive CoreWeave fixture pairs; original challenge; independent synthetic financial set; separate source-grounded Microsoft/Apple disclosure cases with counterfactual negatives. Same original-text raw NLI scores for both policies; no threshold or model changes. Small authored sets, not representative calibration; policy development has now observed their errors.')
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    for name in ('coreweave','original_challenge','independent_heldout','disclosures_heldout'):
        print(name,json.dumps({k:report[name][k] for k in ('before','after','retrieved_before','retrieved_after','frontiers','inference_count','resume_inference_count')},indent=2))

if __name__=='__main__':main()
