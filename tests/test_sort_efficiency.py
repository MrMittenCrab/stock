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
 from stock.source_layout import attach
 p=tmp_path/'source.pdf';p.write_bytes(b'original')
 doc={**DOC,'original':str(p),'source_sha256':hashlib.sha256(b'original').hexdigest()}
 layout=[dict(page=1,width=100,height=100,blocks=[dict(text='Revenue: $10 million',bbox=[0,0,10,10])])]
 parse=Mock(return_value=layout);monkeypatch.setattr('stock.source_layout.pdf_layout',parse)
 store=Store(tmp_path/'db');_,_,cs,_=setup_claim()
 attach(cs,doc,lambda _:None,store=store)
 fresh=copy.deepcopy(cs)
 for c in fresh:c.pop('page',None);c.pop('visual',None)
 assert attach(fresh,doc,lambda _:None,store=store)==layout
 assert fresh[0]['page']==1 and parse.call_count==1
 changed={**doc,'source_sha256':'other'}
 attach(fresh,changed,lambda _:None,store=store)
 assert parse.call_count==2


def test_missing_citation_is_repaired_then_only_corrected_statement_reviewed():
 from stock.editorial import recover_citations
 text,digest,cs,ps=setup_claim()
 m=Mock();m.extract.return_value=[{**supported(),'fidelity':'unresolved','reason':'Missing cited period 2025.'}]
 _,failures=review(ps,m,'')
 class Repair:
  def __init__(self):self.calls=[]
  def extract(self,u,context):
   self.calls.append(u)
   if 'review' in u:return [supported()]
   assert 'Missing cited period' in context
   assert {c['id'] for c in u['candidates']}=={c['id'] for c in cs}
   return [dict(ids=[c['id'] for c in cs],representation='source_grounded_statement',text='Revenue was $10 million in 2025.',topics=['Financials'],category='Management',speaker=None,ambiguities=[])]
 repair=Repair()
 accepted,rejected=recover_citations(failures,cs,text,DOC,digest,repair,'',[])
 assert not rejected and len(accepted)==1 and len(repair.calls)==2
 assert len(repair.calls[1]['review'])==1
 validate_publication(accepted[0]);assert len(accepted[0]['location']['references'])==2


def test_unsupported_repair_has_bounded_attempts_and_audit():
 from stock.editorial import recover_citations
 text,digest,cs,ps=setup_claim()
 m=Mock();m.extract.return_value=[{**supported(),'fidelity':'unsupported','reason':'Invented causality.'}]
 _,failures=review(ps,m,'')
 repair=Mock();repair.extract.return_value=[]
 accepted,rejected=recover_citations(failures,cs,text,DOC,digest,repair,'',[])
 assert not accepted and rejected and repair.extract.call_count==1
 assert rejected[0]['repair']['attempts']==1 and rejected[0]['proposed']['text']==ps[0]['text']


def test_status_reports_stage_elapsed_without_claiming_forward_progress(monkeypatch):
 import stock.sort_process as sp
 now=[10.];monkeypatch.setattr(sp.time,'monotonic',lambda:now[0])
 s=sp.Status();s('13 · CoreWeave · section 3/9 · semantic review');now[0]=14.
 line=s.line()
 assert 'section 3/9' in line and 'stage 4s' in line and 'total 4s' in line and 'child idle' in line
 now[0]=15.;s('13 · CoreWeave · section 3/9 · citation recovery');now[0]=17.
 assert 'stage 2s' in s.line() and 'total 7s' in s.line()
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


def test_repair_review_interruption_resumes_corrected_selection():
 from stock.editorial import recover_citations
 text,digest,cs,ps=setup_claim();m=Mock();m.extract.return_value=[{**supported(),'fidelity':'unresolved','reason':'Missing cited period 2025.'}]
 _,failures=review(ps,m,'');audit=[]
 class Repair:
  def __init__(self):self.calls=[];self.interrupt=True
  def extract(self,u,context):
   self.calls.append('review' if 'review' in u else 'repair')
   if 'review' in u:
    if self.interrupt:raise KeyboardInterrupt
    return [supported()]
   return [dict(ids=[c['id'] for c in cs],representation='source_grounded_statement',text='Revenue was $10 million in 2025.',topics=['Financials'],category='Management',speaker=None,ambiguities=[])]
 import pytest
 repair=Repair()
 with pytest.raises(KeyboardInterrupt):recover_citations(failures,cs,text,DOC,digest,repair,'',audit)
 repair.interrupt=False
 accepted,rejected=recover_citations(failures,cs,text,DOC,digest,repair,'',audit)
 assert accepted and not rejected and repair.calls==['repair','review','review']
 assert audit[0]['complete']


def test_interrupted_section_reuses_completed_statement_reviews(tmp_path,monkeypatch):
 from stock.core import Store
 from stock.archive import import_document
 from stock.evidence import extract
 monkeypatch.setattr('stock.archive.ROOT',tmp_path)
 source=tmp_path/'input.md';source.write_text('# Investor Presentation\n\nRevenue increased '+('Customer demand remains strong '*180)+'.\n\nCapacity expanded '+('Contracted demand remains strong '*180)+'.')
 store=Store(tmp_path/'db');doc=import_document(store,'CRWV.US',source)
 class Model:
  def __init__(self):self.calls=[];self.interrupt=True
  def extract(self,u,context):
   self.calls.append('review' if 'review' in u else 'selection')
   if 'review' in u:
    if self.interrupt and self.calls.count('review')==2:raise KeyboardInterrupt
    return [supported(i) for i in range(len(u['review']))]
   return [dict(ids=[c['id']],representation='verbatim',text=None,topics=['Market'],category='Management',speaker=None,ambiguities=[]) for c in u['candidates'] if not c.get('context_only')]
 import pytest
 model=Model()
 with pytest.raises(KeyboardInterrupt):extract(store,doc,model,lambda _:None)
 model.interrupt=False
 ps,_=extract(store,doc,model,lambda _:None)
 assert len(ps)==2 and model.calls==['selection','review','review','review']
 assert extract(store,doc,model,lambda _:None)[0]==ps
 assert len(model.calls)==4


def test_compatible_checkpoint_adoption_preserves_original_audit(tmp_path,monkeypatch):
 from stock.core import Store
 from stock.archive import import_document
 from stock.evidence import extract,CONTRACT,PREVIOUS_CONTRACT
 monkeypatch.setattr('stock.archive.ROOT',tmp_path)
 path=tmp_path/'input.md';path.write_text('# Investor Presentation\n\nRevenue increased.')
 store=Store(tmp_path/'db');doc=import_document(store,'CRWV.US',path)
 class Model:
  def __init__(self):self.calls=0
  def extract(self,u,context):
   self.calls+=1
   if 'review' in u:return [supported()]
   return [dict(ids=[next(c['id'] for c in u['candidates'] if not c.get('context_only'))],representation='verbatim',text=None,topics=['Market'],category='Management',speaker=None,ambiguities=[])]
 model=Model();expected,_=extract(store,doc,model,lambda _:None)
 key,index,payload=store.db.execute('select markdown_hash,section_index,payload from source_work_v3').fetchone()
 old_key=key.replace(CONTRACT,PREVIOUS_CONTRACT).removesuffix(':compact')
 state=json.loads(payload);state['contract']=PREVIOUS_CONTRACT;old_payload=json.dumps(state)
 with store.db:
  store.db.execute('delete from source_work_v3')
  store.db.execute('insert into source_work_v3 values(?,?,?,?)',(doc['id'],old_key,index,old_payload))
 actual,_=extract(store,doc,model,lambda _:None)
 assert actual==expected and model.calls==2
 assert store.db.execute('select payload from source_work_v3 where markdown_hash=?',(old_key,)).fetchone()[0]==old_payload
 assert store.db.execute('select count(*) from source_work_v3').fetchone()[0]==2


def test_terminal_width_keeps_document_section_stage_and_timers():
 from stock.sort_process import Status
 s=Status();s('13 · CoreWeave Q4-2025 Earnings Presentation · section 3/9 · semantic review')
 line=s.line(width=80)
 assert len(line)<=79
 for term in ('13','3/9','review','stage','total','child'):assert term in line


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
 from stock.source_layout import bounded_context
 blocks=[dict(text='Revenue',bbox=[0,10,20,20])]+[dict(text=f'Unrelated label {i}',bbox=[50,i*10,90,i*10+8]) for i in range(10)]+[dict(text='Note: excludes assets acquired under finance leases.',bbox=[0,70,80,75])]
 pages=[dict(page=1,width=100,height=100,blocks=blocks)]
 result=bounded_context([dict(text='Revenue',page=1)],pages)
 assert blocks[-1] in result[0]['blocks']
 assert all(b in blocks for b in result[0]['blocks'])


def test_corrupt_layout_cache_is_recomputed(tmp_path,monkeypatch):
 from stock.core import Store
 from stock.source_layout import attach
 p=tmp_path/'source.pdf';p.write_bytes(b'original');doc={**DOC,'original':str(p)}
 layout=[dict(page=1,width=100,height=100,blocks=[dict(text='Revenue: $10 million',bbox=[0,0,10,10])])]
 parse=Mock(return_value=layout);monkeypatch.setattr('stock.source_layout.pdf_layout',parse)
 store=Store(tmp_path/'db');_,_,cs,_=setup_claim();attach(cs,doc,lambda _:None,store=store)
 with store.db:store.db.execute("update cache set payload='invalid' where key=?",('sort-layout-v2:'+doc['source_sha256'],))
 assert attach(cs,doc,lambda _:None,store=store)==layout
 assert parse.call_count==2


def test_exhausted_repair_review_does_not_complete_unreviewed_work():
 from stock.editorial import recover_citations
 from stock.evidence import ProtocolError
 import pytest
 text,digest,cs,ps=setup_claim();m=Mock();m.extract.return_value=[{**supported(),'fidelity':'unresolved','reason':'Missing cited period 2025.'}]
 _,failures=review(ps,m,'');audit=[]
 class Repair:
  def __init__(self):self.calls=[];self.broken=True
  def extract(self,u,context):
   self.calls.append('review' if 'review' in u else 'repair')
   if 'review' in u:return [] if self.broken else [supported()]
   return [dict(ids=[c['id'] for c in cs],representation='source_grounded_statement',text='Revenue was $10 million in 2025.',topics=['Financials'],category='Management',speaker=None,ambiguities=[])]
 repair=Repair()
 with pytest.raises(ProtocolError):recover_citations(failures,cs,text,DOC,digest,repair,'',audit)
 assert not audit[0]['complete'] and 'accepted' not in audit[0]
 repair.broken=False
 accepted,rejected=recover_citations(failures,cs,text,DOC,digest,repair,'',audit)
 assert not rejected and accepted and repair.calls==['repair','review','review','review','review']
 validate_publication(accepted[0])


def test_repair_binds_reviewed_layout_to_publication_fingerprint():
 from stock.editorial import recover_citations
 text,digest,cs,ps=setup_claim();m=Mock();m.extract.return_value=[{**supported(),'fidelity':'unresolved','reason':'Missing cited period 2025.'}]
 _,failures=review(ps,m,'')
 layout=[dict(page=1,blocks=[dict(text='Period: 2025',bbox=[0,0,10,10])])]
 def context(passages):return json.dumps(dict(original_pdf_layout=layout))
 class Repair:
  def extract(self,u,c):
   if 'review' in u:return [supported()]
   return [dict(ids=[c['id'] for c in cs],representation='source_grounded_statement',text='Revenue was $10 million in 2025.',topics=['Financials'],category='Management',speaker=None,ambiguities=[])]
 accepted,rejected=recover_citations(failures,cs,text,DOC,digest,Repair(),context,[])
 assert not rejected and accepted[0]['location']['visual_context']==layout
 validate_publication(accepted[0])
