"""Efficiency must retain citation identity and the independent review gate."""
import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import Mock

from stock.evidence import candidates, resolve
from stock.editorial import review, validate_publication

DOC=dict(id=13,type='Presentation',title='CoreWeave',original='source.pdf',source_sha256='original',metadata_provenance=None)

def setup_claim(text='Revenue: $10 million\n\nPeriod: 2025'):
 from stock.evidence import candidates
 digest=hashlib.sha256(text.encode()).hexdigest();cs=candidates(text,DOC,digest,True)
 selection=dict(ids=[cs[0]['id']],representation='source_grounded_statement',text='Revenue was $10 million.',topics=['Financials'],category='Management',speaker=None,ambiguities=[])
 ps,errors=resolve([selection],cs,text,DOC,digest);assert not errors
 return text,digest,cs,ps

def supported(i=0):
 return dict(index=i,fidelity='supported',readability='clear',relevance='useful',warnings=[],reason='All material elements are explicitly cited.')

def test_compact_transport_keeps_exact_ids_text_roles_and_page():
 from stock.sort_transport import source_payload
 _,_,cs,_=setup_claim();cs[0].update(page=5,visual={'basis':'matched'})
 wire=source_payload(cs[0])
 assert wire['id']==cs[0]['id'] and wire['text']==cs[0]['text'] and wire['page']==5
 assert 'original_sha256' not in wire and 'start' not in wire and 'markdown_sha256' not in wire
 assert len(json.dumps(wire))<len(json.dumps(cs[0]))

def test_unchanged_accepted_review_is_not_repeated():
 _,_,_,ps=setup_claim();m=Mock();m.extract.return_value=[supported()]
 accepted,_=review(ps,m,'');validate_publication(accepted[0])
 again,rejected=review(copy.deepcopy(accepted),m,'')
 assert again==accepted and not rejected and m.extract.call_count==1


def test_pdf_preparation_cached_by_source_and_markdown(tmp_path,monkeypatch):
 from stock.core import Store
 from legacy_layout import attach
 p=tmp_path/'source.pdf';p.write_bytes(b'original')
 doc={**DOC,'original':str(p),'source_sha256':hashlib.sha256(b'original').hexdigest()}
 layout=[dict(page=1,width=100,height=100,blocks=[dict(text='Revenue: $10 million',bbox=[0,0,10,10])])]
 parse=Mock(return_value=layout);monkeypatch.setattr('legacy_layout.pdf_layout',parse)
 store=Store(tmp_path/'db');_,_,cs,_=setup_claim()
 attach(cs,doc,lambda _:None,store=store)
 fresh=copy.deepcopy(cs)
 for c in fresh:c.pop('page',None);c.pop('visual',None)
 assert attach(fresh,doc,lambda _:None,store=store)==layout
 assert fresh[0]['page']==1 and parse.call_count==1
 changed={**doc,'source_sha256':'other'}
 attach(fresh,changed,lambda _:None,store=store)
 assert parse.call_count==2






def test_status_reports_stage_elapsed_without_claiming_forward_progress(monkeypatch):
 import stock.sort_process as sp
 now=[10.];monkeypatch.setattr(sp.time,'monotonic',lambda:now[0])
 s=sp.Status();s('13 · CoreWeave · section 3/9 · semantic review');now[0]=14.
 line=s.line()
 assert line=='13 · 3/9 · Verify · 00:04'
 now[0]=15.;s('13 · CoreWeave · section 3/9 · citation recovery');now[0]=17.
 assert s.line()=='13 · 3/9 · Citations · 00:07'
 assert 'working' not in s.line()


def test_review_transport_sends_shared_source_once(monkeypatch):
 import stock.sort_process as process
 from stock.sort import Cursor
 from subprocess import CompletedProcess
 _,_,_,ps=setup_claim();p=ps[0];prompts=[]
 def run(command,**kwargs):
  prompts.append(command[-1]);return CompletedProcess(command,0,json.dumps({'type':'result','result':json.dumps({'reviews':[supported(),supported(1)]})}),'')
 monkeypatch.setattr(process,'run',run)
 cursor=Cursor.__new__(Cursor);cursor.command='replay'
 payload=[dict(index=i,text=p['text'],representation='source_grounded_statement',references=p['location']['references'],speaker=None,category='Management') for i in range(2)]
 cursor.extract(dict(candidates=[],text='',review=payload),'')
 assert prompts[0].count('Revenue: $10 million')==1
 assert cursor.metrics[0]['prompt_bytes']==len(prompts[0].encode())


def test_failed_cursor_attempt_retains_measured_cost(monkeypatch):
 import stock.sort_process as process
 from stock.sort import Cursor
 from stock.evidence import ProtocolError
 import pytest
 from subprocess import CompletedProcess
 monkeypatch.setattr(process,'run',lambda command,**kw:CompletedProcess(command,0,'broken',''))
 cursor=Cursor.__new__(Cursor);cursor.command='replay'
 with pytest.raises(ProtocolError):cursor.extract(dict(candidates=[],text=''),'')
 assert len(cursor.metrics)==1 and cursor.metrics[0]['outcome']=='failed'
 assert cursor.metrics[0]['response_chars']==6




def test_interrupted_section_reuses_completed_statement_reviews(tmp_path,monkeypatch):
 from stock.core import Store
 from stock.archive import import_document
 from stock.evidence import extract
 monkeypatch.setattr('stock.archive.ROOT',tmp_path)
 monkeypatch.setattr('stock.editorial.REVIEW_CONTEXT',1000)
 source=tmp_path/'input.md';source.write_text('# Investor Presentation\n\nRevenue increased '+('Customer demand remains strong '*20)+'.\n\nCapacity expanded '+('Contracted demand remains strong '*20)+'.')
 store=Store(tmp_path/'db');doc=import_document(store,'CRWV.US',source)
 class Model:
  def __init__(self):self.calls=[];self.interrupt=True;self.reviewed=set()
  def extract(self,u,context):
   self.calls.append('review' if 'review' in u else 'selection')
   if 'review' in u:
    if self.interrupt and self.calls.count('review')==2:raise KeyboardInterrupt
    identity=json.dumps(u['review'],sort_keys=True)
    assert identity not in self.reviewed
    self.reviewed.add(identity)
    return [supported(i) for i in range(len(u['review']))]
   return [dict(ids=[c['id']],representation='verbatim',text=None,topics=['Market'],category='Management',speaker=None,ambiguities=[]) for c in u['candidates'] if not c.get('context_only')]
 import pytest
 model=Model()
 with pytest.raises(KeyboardInterrupt):extract(store,doc,model,lambda _:None)
 model.interrupt=False
 ps,_=extract(store,doc,model,lambda _:None)
 assert len(ps)==2 and model.calls.count('selection')==1
 before=list(model.calls)
 assert extract(store,doc,model,lambda _:None)[0]==ps
 assert model.calls==before




def test_terminal_width_keeps_document_section_stage_and_timers():
 from stock.sort_process import Status
 s=Status();s('13 · CoreWeave Q4-2025 Earnings Presentation · section 3/9 · semantic review')
 line=s.line(width=80)
 assert len(line)<=79
 for term in ('13','3/9','Verify','00:'):assert term in line
 assert not any(word in line for word in ('child','stage','total','unknown'))


def test_duplicate_selections_do_not_duplicate_review_work():
 _,_,_,ps=setup_claim();m=Mock();m.extract.return_value=[supported()]
 accepted,rejected=review([ps[0],copy.deepcopy(ps[0])],m,'')
 assert not rejected and len(accepted)==1
 assert len(m.extract.call_args.args[0]['review'])==1


def test_cursor_timeout_is_not_a_schema_retry(monkeypatch):
 import pytest
 import subprocess
 import stock.sort_process as process
 from stock.sort import Cursor
 from stock.evidence import ProtocolError
 command=Mock(side_effect=subprocess.TimeoutExpired('agent',600))
 monkeypatch.setattr(process,'run',command)
 cursor=Cursor.__new__(Cursor);cursor.command='replay'
 with pytest.raises(ValueError) as error:cursor.extract(dict(candidates=[],text=''),'')
 assert not isinstance(error.value,ProtocolError)
 assert command.call_count==1 and cursor.metrics[0]['outcome']=='failed'


def test_bounded_layout_retains_remote_qualifications_and_geometry():
 from legacy_layout import bounded_context
 blocks=[dict(text='Revenue',bbox=[0,10,20,20])]+[dict(text=f'Unrelated label {i}',bbox=[50,i*10,90,i*10+8]) for i in range(10)]+[dict(text='Note: excludes assets acquired under finance leases.',bbox=[0,70,80,75])]
 pages=[dict(page=1,width=100,height=100,blocks=blocks)]
 result=bounded_context([dict(text='Revenue',page=1)],pages)
 assert blocks[-1] in result[0]['blocks']
 assert all(b in blocks for b in result[0]['blocks'])


def test_corrupt_layout_cache_is_recomputed(tmp_path,monkeypatch):
 from stock.core import Store
 from legacy_layout import attach
 p=tmp_path/'source.pdf';p.write_bytes(b'original');doc={**DOC,'original':str(p)}
 layout=[dict(page=1,width=100,height=100,blocks=[dict(text='Revenue: $10 million',bbox=[0,0,10,10])])]
 parse=Mock(return_value=layout);monkeypatch.setattr('legacy_layout.pdf_layout',parse)
 store=Store(tmp_path/'db');_,_,cs,_=setup_claim();attach(cs,doc,lambda _:None,store=store)
 with store.db:store.db.execute("update cache set payload='invalid' where key=?",('sort-layout-v2:'+doc['source_sha256'],))
 assert attach(cs,doc,lambda _:None,store=store)==layout
 assert parse.call_count==2

def test_transport_compacts_json_without_changing_payload(monkeypatch):
 from stock.sort import Cursor
 import stock.sort_process as process
 from subprocess import CompletedProcess
 prompts=[]
 def run(command,**kwargs):
  prompts.append(command[-1]);return CompletedProcess(command,0,json.dumps({'type':'result','result':'{"selections":[]}'}),'')
 monkeypatch.setattr(process,'run',run)
 cursor=Cursor.__new__(Cursor);cursor.command='offline'
 body='Exact  spacing\n\nSecond line'
 anchors=candidates(body,DOC,hashlib.sha256(body.encode()).hexdigest(),True)
 cursor.extract(dict(candidates=anchors,text=''),{'document':{'title':'Exact title'}})
 assert '"document":{"title":"Exact title"}' in prompts[0]
 assert cursor.metrics[0]['prompt_sha256']==hashlib.sha256(prompts[0].encode()).hexdigest()
 assert cursor.metrics[0]['source_anchors']==len(anchors)
 payload=json.loads(prompts[0][prompts[0].index('{"context":'):])
 assert [s['text'] for s in payload['untrusted_section']]==[a['text'] for a in anchors]


def test_resume_preserves_budgets_and_quotes_document():
 from stock.cli import sort_resume_command
 import argparse,shlex
 args=argparse.Namespace(ticker='CRWV.US',rebuild='a b.md',review_only=False,document_seconds=1800.,command_seconds=2400.,cursor_requests=19,request_seconds=300.)
 words=shlex.split(sort_resume_command(args))
 assert words[:5]==['stock','sort','CRWV.US','--rebuild','a b.md']
 for flag,value in [('--document-seconds','1800.0'),('--command-seconds','2400.0'),('--cursor-requests','19'),('--request-seconds','300.0')]:
  assert words[words.index(flag)+1]==value

def test_timeout_records_partial_output_without_content():
 import sys,pytest
 from stock.sort_process import run
 from stock.sort_budget import Budget,BudgetExceeded
 with Budget(request_seconds=1):
  with pytest.raises(BudgetExceeded) as caught:
   run([sys.executable,'-c','import time; print("private-source",flush=True); time.sleep(5)'],text=True,timeout=.2)
 diagnostic=caught.value.process_diagnostics
 assert diagnostic['timed_out'] and diagnostic['stdout_bytes']==15
 assert diagnostic['effective_timeout_seconds']<=.2
 assert diagnostic['returncode'] is not None
 assert 'private-source' not in json.dumps(diagnostic)
