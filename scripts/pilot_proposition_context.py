#!/usr/bin/env python3
"""Bounded disposable replay. Never opens production storage or invokes Cursor."""
import copy
import hashlib
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stock import evidence, knowledge, proposition_context as pc, sources
from stock.core import Store
from stock.insights import packed

FIXTURES=Path(__file__).resolve().parents[1]/'tests/fixtures'
PILOT=FIXTURES/'proposition-context'


class RecordedTransport:
    contextualize=True
    disposable_context=True
    def __init__(self,cases,reviews):self.cases=cases;self.reviews=reviews;self.calls=[];self.sizes=[]
    def extract(self,unit,context):
        self.calls.append(copy.deepcopy(unit))
        if 'review' in unit:
            by_text={c['original_text']:c for c in self.cases}
            result=[dict(index=i,**self.reviews[by_text[p['text']]['id']]) for i,p in enumerate(unit['review'])]
        else:
            available={a['id'] for a in unit['candidates']}
            result=[dict(selection_key=c['id'],ids=[r['source_id'] for r in c['references']],representation=c['representation'],text=c['original_text'],topics=['Operations'],category='Management',speaker=None,ambiguities=[],context=copy.deepcopy(c['proposal'])) for c in self.cases if set(r['source_id'] for r in c['references'])<=available]
        self.sizes.append(dict(operation='review' if 'review' in unit else 'extraction',input_chars=len(packed([unit,context])),context_input_chars=sum(len(packed({k:p[k] for k in ('context_proposal','context_references')})) for p in unit.get('review',[])),response_chars=len(packed(result)),context_response_chars=sum(len(packed(x.get('context',{}))) if 'review' not in unit else len(packed({k:x[k] for k in ('context_preservation','context_reason')})) for x in result)))
        return result


def run():
    fixture=json.loads((PILOT/'cases.json').read_text());reviews=json.loads((PILOT/'reviews.json').read_text())['reviews']
    report=dict(kind='deterministic recorded-response pipeline replay; no live Cursor or human accuracy measurement',total_cases=len(fixture['cases']),held_out=sum(c['heldout'] for c in fixture['cases']),source_versions={},requests=[],counts=Counter(),exact_citations_preserved=True,identities_preserved=True,production_activation=False,remote_cursor_requests=0,prompt_instruction_increment_chars=dict(extraction=len(pc.GENERATION_PROMPT),review=len(pc.REVIEW_PROMPT)))
    with tempfile.TemporaryDirectory(prefix='stock-context-pilot-') as tmp:
        store=Store(Path(tmp)/'disposable.db');knowledge.schema(store)
        for name,source in fixture['sources'].items():
            path=FIXTURES/source['path'];data=path.read_bytes();sha=hashlib.sha256(data).hexdigest()
            assert sha==source['sha256'],'Fixture hash changed'
            report['source_versions'][name]=sha
            copied=Path(tmp)/(name+'.md');copied.write_bytes(data);text=copied.read_text()
            doc=dict(id=source['id'],type=source['type'],title='Disposable source fixture',ticker='FIXTURE.US',publisher=None,period=None,metadata_provenance=None,source_sha256=sha,original=str(copied),markdown=str(copied))
            atoms=knowledge.prepare_atoms(text,doc,sha);lookup={a['id']:a for a in atoms}
            all_cases=[c for c in fixture['cases'] if c['source']==name]
            for case in all_cases:
                for ref in case['references']:
                    atom=lookup[ref['source_id']]
                    assert atom['start']==ref['start'] and atom['end']==ref['end'] and text[ref['start']:ref['end']]==ref['text']
            cases=[c for c in all_cases if not c['heldout']]
            initial=store.db.execute('select count(*) from knowledge_artifacts').fetchone()[0]
            model=RecordedTransport(cases,reviews)
            passages,verify=evidence.extract(store,doc,model,lambda _:None);verify()
            assert len(passages)==len(cases),(name,len(passages),len(cases))
            bound_doc={**{k:doc.get(k) for k in ('id','title','type','ticker','publisher','period','source_sha256','metadata_provenance')},'markdown_sha256':sha,'original':str(copied),'markdown':str(copied)}
            for p in passages:
                r=pc.read(store,p['context_record_id'],p,bound_doc)
                report['counts'][r['context_status']]+=1
                report['counts']['original_'+r['verification']['original_support']]+=1
                report['counts']['context_'+r['verification']['context_preservation']]+=1
                if pc.eligible(r):report['counts']['eligible']+=1
                else:assert r['standalone_text']==p['text'] and not r['resolutions']
                for ref in p['location']['references']:assert text[ref['start']:ref['end']]==ref['text']
                raw={k:v for k,v in p.items() if k not in ('proposition_context','context_record_id','context_proposal','context_references','selection_key')}
                assert sources.passage_id(doc,p)==sources.passage_id(doc,raw)
            manifest=pc.association(store,bound_doc,passages)
            assert len(pc.load(store,manifest)['output'])==len(passages)
            before=store.db.execute('select count(*) from knowledge_artifacts').fetchone()[0]
            previous=len(model.calls)
            resumed,_=evidence.extract(store,doc,model,lambda _:None)
            after=store.db.execute('select count(*) from knowledge_artifacts').fetchone()[0]
            assert resumed==passages and len(model.calls)==previous and before==after
            report['requests'].append(dict(source=name,extraction=sum('review' not in u for u in model.calls),review=sum('review' in u for u in model.calls),resume_requests=len(model.calls)-previous,new_artifacts=before-initial,reused_on_resume=before-initial,sizes=model.sizes))
            assert not sources.completed(store,doc['id'])
        report['total_selections']=sum(report['counts'][s] for s in ('unnecessary','resolved','unresolved'))
        report['total_proposals']=report['total_selections']
        report['counts']=dict(report['counts'])
        report['abstentions']=[dict(id=c['id'],reasons=c['proposal']['unresolved'] or [reviews[c['id']]['context_reason']]) for c in fixture['cases'] if not c['heldout'] and reviews[c['id']]['context_preservation']!='accepted']
        report['limitations']=['Review responses are deterministic test expectations, not empirical independent source-verification observations.','Standalone sufficiency, factual correctness, meaning preservation and fluency have no independent human scores.','No live Cursor requests; authenticated model access not tested.','Held-out cases are anchor-validated but not executed or used to tune prompts.','CoreWeave fixtures are repository replay evidence, not newly authenticated production disclosures.','No semantic pair labels, embeddings, NLI or production activation.']
    return report


if __name__=='__main__':
    report=run();output=packed(report)
    if len(sys.argv)>1:Path(sys.argv[1]).write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    else:print(output)
