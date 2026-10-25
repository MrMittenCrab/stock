#!/usr/bin/env python3
"""One bounded authenticated validation; never opens production DB or activates heads."""
import copy
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stock import evidence, knowledge, proposition_context as pc
from stock.core import Store, DB
from stock.archive import filehash
from stock.sort import Cursor
from stock.sort_process import DeferredCursor
from stock.sort_budget import Budget
from validate_proposition_context import OUT, ROOT, write, sha

def run():
    output=OUT/'authenticated.json'
    if output.exists():raise SystemExit('Single attempt already captured; refusing another run')
    source=ROOT/'tests/fixtures/sort/document-12.md';text=source.read_text()
    # Exact source slices, including roster identity and original utterance; no invented source text.
    spans=[(0,text.index('Nitin Agrawal')), (text.index('#### Michael Intrator'),text.index('Good afternoon, everyone')), (text.index('On to execution.'),text.index('\n\n',text.index('On to execution.')))]
    snapshot='\n\n'.join(text[a:b] for a,b in spans)
    before=filehash(DB) if DB.exists() else None
    report=dict(kind='authenticated model observation; no human adjudication',request_limit=4,source=str(source.relative_to(ROOT)),source_sha256=sha(source),source_slices=[dict(start=a,end=b,text=text[a:b]) for a,b in spans],baseline_sha256=sha(OUT/'raw-baseline.json'),production_before_sha256=before)
    with tempfile.TemporaryDirectory(prefix='stock-context-auth-validation-') as tmp:
        path=Path(tmp)/'transcript.md';path.write_text(snapshot)
        store=Store(Path(tmp)/'disposable.db')
        doc=dict(id=251,type='Transcript',title='Disposable exact transcript slices',ticker='FIXTURE.US',publisher=None,period=None,metadata_provenance=None,original=str(path),markdown=str(path),source_sha256=sha(path))
        model=DeferredCursor(Cursor);model.contextualize=True;model.disposable_context=True
        calls=[]
        class Targeted:
            contextualize=True;disposable_context=True
            def __init__(self):self.cursor=Cursor()
            def extract(self,unit,context):
                self.cursor.contextualize=True;self.cursor.disposable_context=True
                self.cursor.record_metrics=self.record_metrics
                if 'review' not in unit:
                    context=json.dumps(dict(source_context=json.loads(context),validation_target='Select the context-dependent execution paragraph as verbatim (text null). Apply the existing context contract to resolve only necessary referents using supplied exact source IDs. Abstain if support is insufficient. Do not change the original quotation.'))
                calls.append(dict(unit=copy.deepcopy(unit),context=context))
                result=self.cursor.extract(unit,context);calls[-1]['output']=copy.deepcopy(result)
                return result
        model.factory=Targeted
        events=[]
        class Progress:
            def __call__(self,m):pass
            def log_event(self,e):events.append(e)
        with Budget(document_seconds=520,command_seconds=550,requests=4,request_seconds=120) as budget:
            budget.use_document(doc['id'])
            try:
                passages,verify=evidence.extract(store,doc,model,Progress());verify()
                report['passages']=passages
                count=budget.documents[doc['id']][1]
                resumed,_=evidence.extract(store,doc,model,Progress())
                report['resume_requests']=budget.documents[doc['id']][1]-count
                report['resume_equal']=passages==resumed
                bound={**doc,'markdown_sha256':sha(path)}
                report['manifest']=pc.association(store,bound,passages)
            except Exception as exc:report['error']=dict(type=type(exc).__name__,reason=str(exc))
            report['requests']=budget.documents[doc['id']][1]
        report.update(events=events,calls=calls,metrics=[json.loads(r[0]) for r in store.db.execute('select payload from source_model_calls')],
            artifacts=[dict(id=r[0],contract=r[1],operation=r[2],payload=json.loads(r[3]),checksum=r[4]) for r in store.db.execute('select id,contract,operation,payload,checksum from knowledge_artifacts')])
        store.db.close()
    report['production_after_sha256']=filehash(DB) if DB.exists() else None
    report['production_unchanged']=before==report['production_after_sha256']
    write(output,report);print(json.dumps({k:v for k,v in report.items() if k in ('requests','error','resume_requests','resume_equal','production_unchanged')}))
if __name__=='__main__':run()
