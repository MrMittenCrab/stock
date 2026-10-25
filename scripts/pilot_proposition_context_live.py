#!/usr/bin/env python3
"""Optional authenticated disposable pilot, capped at two existing transport requests."""
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stock import evidence, proposition_context as pc
from stock.core import Store
from stock.sort import Cursor
from stock.sort_process import DeferredCursor
from stock.sort_budget import Budget
from stock.archive import filehash


def run():
    fixture=Path(__file__).resolve().parents[1]/'tests/fixtures/proposition-context/microsoft-fy25q4-excerpt.md'
    report=dict(kind='authenticated Cursor observation, single source, no human adjudication',request_budget=2,production_activation=False,source_sha256=filehash(fixture))
    with tempfile.TemporaryDirectory(prefix='stock-context-live-') as tmp:
        copied=Path(tmp)/'microsoft.md';copied.write_bytes(fixture.read_bytes())
        store=Store(Path(tmp)/'disposable.db')
        doc=dict(id=203,title='Disposable Microsoft release excerpt',type='Filing',ticker='MSFT.US',publisher=None,period=None,metadata_provenance=None,original=str(copied),markdown=str(copied),source_sha256=filehash(copied))
        model=DeferredCursor(Cursor);model.contextualize=True;model.disposable_context=True
        def factory():
            cursor=Cursor();cursor.contextualize=True;cursor.disposable_context=True
            return cursor
        model.factory=factory
        events=[]
        class Progress:
            def __call__(self,message):pass
            def log_event(self,event):events.append(event)
        progress=Progress()
        with Budget(document_seconds=260,command_seconds=280,requests=2,request_seconds=120) as budget:
            budget.use_document(doc['id'])
            try:
                passages,verify=evidence.extract(store,doc,model,progress);verify()
                report['records']=[p['proposition_context'] for p in passages]
                report['counts']=dict(Counter(r['context_status'] for r in report['records']))
                before=budget.documents[doc['id']][1]
                again,_=evidence.extract(store,doc,model,progress)
                report['resume_requests']=budget.documents[doc['id']][1]-before
                assert again==passages
            except Exception as exc:
                report['error']=dict(type=type(exc).__name__,reason=str(exc))
            report['requests']=budget.documents[doc['id']][1]
        report['events']=events
        report['metrics']=[json.loads(row[0]) for row in store.db.execute('select payload from source_model_calls')]
        # Retain all diagnostic inputs/outputs and exact context records, not the database.
        report['artifacts']=[dict(id=r[0],contract=r[1],operation=r[2],payload=json.loads(r[3]),checksum=r[4]) for r in store.db.execute('select id,contract,operation,payload,checksum from knowledge_artifacts')]
    return report


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: pilot_proposition_context_live.py OUTPUT.json')
    Path(sys.argv[1]).write_text(json.dumps(run(),indent=2,ensure_ascii=False)+'\n')
