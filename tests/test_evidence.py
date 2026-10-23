import hashlib
import json
from pathlib import Path
from unittest.mock import Mock
import pytest
from stock.evidence import candidates,batches,resolve,extract,ProtocolError,AuthenticationError
from stock.core import Store
from stock.archive import import_document
from stock import sources
from stock.rebuild import rebuild

FIX=Path(__file__).parent/'fixtures/sort'

def doc(): return dict(id=13,type='Presentation',title='CoreWeave',original='source.pdf',source_sha256='original',metadata_provenance=None)
def digest(text):return hashlib.sha256(text.encode()).hexdigest()
def selection(cs,**kw):return dict(ids=[c['id'] for c in cs],topics=['Market'],category='Management',speaker=None,**kw)

def test_repeated_identity_exact_offsets():
 text='Demand exceeds supply.\n\nDemand exceeds supply.';d=doc();h=digest(text)
 cs=candidates(text,d,h)
 assert len(cs)==2 and cs[0]['id']!=cs[1]['id']
 assert candidates(text,d,h)==cs
 for c in cs:assert text[c['start']:c['end']]==c['text']
 ps,errors=resolve([selection(cs)],cs,text,d,h)
 assert not errors and len(ps)==1
 assert all(p['location']['markdown_sha256']==h for p in ps)

def test_overlap_duplicate_distinct_claims():
 text='Pricing remains stable.\n\nCapacity is constrained.\n\nDebt costs increased.';d=doc();h=digest(text);cs=candidates(text,d,h)
 ps,errors=resolve([selection(cs[:2]),selection(cs[1:]),selection(cs[:2])],cs,text,d,h)
 assert len(ps)==1 and not errors
 assert ps[0]["text"]==text
 ps,errors=resolve([{'text':'invented'},selection(cs[:1])],cs,text,d,h)
 assert len(ps)==1 and len(errors)==1

@pytest.mark.parametrize('did',[1,4,6,12,13])
def test_real_markdown_candidates(did):
 text=(FIX/f'document-{did}.md').read_text();d=doc();d['type']='Transcript' if did in (1,12) else 'Filing'
 cs=candidates(text,d,digest(text))
 assert cs
 for a,b in zip(cs,cs[1:]):assert a['end']<=b['start']
 assert all(text[c['start']:c['end']]==c['text'] for c in cs)
 assert not any(c['text'].startswith('|') for c in cs)
 assert all(len(json.dumps(b))<30000 for b in batches(cs))
 if did in (1,12):
  named=[c for c in cs if c['speaker']]
  assert named and all(c['speaker'] in ('Michael Intrator','Nitin Agrawal') for c in named)

def test_turns_roles_unknown_and_page_heading():
 text='## PEOPLE\n\nAlice Smith\n\nChief Executive Officer\n\nJane Brown\n\nAnalyst, Bank\n\n## Alice Smith\n\nMargins improved.\n\n# Page 2\n\nCapacity expanded.\n\nJane Brown\n\nAnalyst, Bank Q\n\nWhy did costs rise?\n\n### Unverified Participant\n\nThank you.'
 d={**doc(),'type':'Transcript'};cs=candidates(text,d,digest(text))
 assert [c['speaker'] for c in cs]==['Alice Smith','Alice Smith','Jane Brown',None]
 bad=selection(cs[:1]);bad['speaker']='Jane Brown'
 assert resolve([bad],cs,text,d,digest(text))[1]

@pytest.fixture
def staged(tmp_path,monkeypatch):
 import stock.archive as archive
 monkeypatch.setattr(archive,'ROOT',tmp_path)
 p=tmp_path/'source.md';p.write_text('# Investor Presentation\n\nDemand exceeds capacity and pricing remains stable.\n\nCapital costs have declined due to contracted revenue.')
 store=Store(tmp_path/'db');d=import_document(store,'CRWV.US',p);sources.schema(store)
 class Model:
  def __init__(self):self.calls=0
  def extract(self,u,ctx):self.calls+=1;return [selection(u['candidates'][:1])]
 return store,d,Model()

def test_protocol_retry_resume_and_legacy_isolation(staged):
 s,d,m=staged
 s.db.execute('INSERT INTO source_sort_sections VALUES(?,?,?,?)',(d['id'],'legacy',0,'{"complete":true}'));s.db.commit()
 original=m.extract
 def retry(u,c):
  if m.calls<1:m.calls+=1;raise ProtocolError('invalid escape')
  return original(u,c)
 m.extract=retry
 ps,_=extract(s,d,m,lambda _:None)
 assert len(ps)==1 and m.calls==2
 assert extract(s,d,m,lambda _:None)[0]==ps and m.calls==2
 assert s.db.execute('select count(*) from source_sort_sections').fetchone()[0]==1

def test_frozen_rebuild_rejection_approval_overrides(staged):
 s,d,m=staged;ps,_=extract(s,d,m,lambda _:None);sources.publish(s,d,ps,d['source_sha256'])
 old=sources.passages(s,'CRWV.US');sources.set_topic(s,old[0]['id'],'Capital',True)
 before=s.db.execute('select * from source_passages').fetchall()
 assert not rebuild(s,'CRWV.US',str(d['id']),lambda:m,lambda _:None,lambda:False)
 assert s.db.execute('select * from source_passages').fetchall()==before
 assert rebuild(s,'CRWV.US',str(d['id']),lambda:m,lambda _:None,lambda:True)
 assert 'Capital' in sources.passages(s,'CRWV.US')[0]['topics']
 from stock.sort import sort_document
 assert sort_document(s,d,Mock(side_effect=AssertionError)) is None


def test_auth_not_retried(staged):
 s,d,m=staged;m.extract=Mock(side_effect=AuthenticationError('rejected'))
 with pytest.raises(AuthenticationError):extract(s,d,m,lambda _:None)
 assert m.extract.call_count==1

def test_cursor_compact_contract_and_invalid_escape(monkeypatch):
 from stock.sort import Cursor
 c=Cursor.__new__(Cursor);c.command='agent'
 text='Investment claim.';cs=candidates(text,doc(),digest(text));prompts=[]
 def run(cmd,**kwargs):
  prompts.append(cmd[-1]);return Mock(returncode=0,stderr='',stdout=json.dumps({'type':'result','result':json.dumps({'selections':[selection(cs)]})}))
 monkeypatch.setattr('stock.sort_process.run',run)
 assert c.extract(dict(candidates=cs,text=''),'CoreWeave')==[selection(cs)]
 assert 'Never return quotations' in prompts[0]
 def broken(*a,**k):return Mock(returncode=0,stderr='',stdout=json.dumps({'type':'result','result':'{"selections":[{"text":"Q4\\{passages"}]}'}))
 monkeypatch.setattr('stock.sort_process.run',broken)
 with pytest.raises(ProtocolError,match='Invalid'):c.extract(dict(candidates=cs,text=''),'')

def test_rebuild_atomic_rollback_and_other_document(staged):
 s,d,m=staged;ps,_=extract(s,d,m,lambda _:None);sources.publish(s,d,ps,d['source_sha256'])
 before=s.db.execute('select * from source_passages').fetchall()
 s.db.execute("CREATE TRIGGER fail_rebuild BEFORE INSERT ON source_sorts BEGIN SELECT RAISE(ABORT,'interrupted'); END")
 import sqlite3
 with pytest.raises(sqlite3.Error):rebuild(s,'CRWV.US',str(d['id']),lambda:m,lambda _:None,lambda:True)
 assert s.db.execute('select * from source_passages').fetchall()==before
 assert sources.completed(s,d['id'])

def test_status_timer_and_child_cancellation(monkeypatch):
 import io,time
 from stock.sort_process import Status,run
 import stock.sort_process as process
 output=io.StringIO();output.isatty=lambda:True
 monkeypatch.setattr(process.sys,'stdout',output)
 with Status() as status:
  status('13 · section 1 · Cursor');time.sleep(.6)
 assert '\r13 · section 1 · Cursor' in output.getvalue()
 assert 'working' in output.getvalue()
 p=Mock();p.communicate.side_effect=[KeyboardInterrupt,('','')];p.poll.return_value=None;p.pid=123
 monkeypatch.setattr(process.subprocess,'Popen',lambda *a,**k:p)
 kill=Mock();monkeypatch.setattr(process.os,'killpg',kill)
 with pytest.raises(KeyboardInterrupt):run(['agent'],text=True)
 kill.assert_called_once()

def test_interruption_preserves_completed_v3_section(staged,monkeypatch):
 s,d,m=staged
 import stock.evidence as ev
 original_batches=ev.batches
 monkeypatch.setattr(ev,'batches',lambda cs:iter([[c] for c in cs]))
 original=m.extract
 def interrupted(u,c):
  if m.calls:raise KeyboardInterrupt
  return original(u,c)
 m.extract=interrupted
 with pytest.raises(KeyboardInterrupt):extract(s,d,m,lambda _:None)
 assert s.db.execute('select count(*) from source_work_v3').fetchone()[0]==1
 m.extract=original
 ps,_=extract(s,d,m,lambda _:None)
 assert len(ps)==2 and m.calls==2

def test_continuation_is_coherent_and_raw_table_excluded():
 text='Our customers include AI enterprises. We\n\nbelieve demand is strong.'
 cs=candidates(text,doc(),digest(text))
 assert len(cs)==1 and cs[0]['text']==text
 broken=(FIX/'unreadable-table.md').read_text()
 assert candidates(broken,doc(),digest(broken))==[]

def test_targeted_retry_excludes_accepted_ids(staged):
 s,d,m=staged;calls=[]
 def model(u,c):
  calls.append(u['candidates'])
  if len(calls)==1:
   return [selection(u['candidates'][:1]),{**selection(u['candidates'][1:]),'category':'Executive'}]
  return [selection(u['candidates'])]
 m.extract=model
 ps,_=extract(s,d,m,lambda _:None)
 assert len(ps)==2 and len(calls)==2 and len(calls[1])==1
 assert calls[1][0]['id']!=calls[0][0]['id']

def test_unmatched_corrections_block_replacement(staged):
 s,d,m=staged;ps,_=extract(s,d,m,lambda _:None);sources.publish(s,d,ps,d['source_sha256'])
 ident=sources.passages(s,'CRWV.US')[0]['id'];sources.set_topic(s,ident,'Capital',True)
 # New staging selects a different claim; the old correction must never disappear.
 s.db.execute('delete from source_work_v3');s.db.commit()
 m.extract=lambda u,c:[selection(u['candidates'][1:])]
 approval=Mock(return_value=True)
 assert not rebuild(s,'CRWV.US',str(d['id']),lambda:m,lambda _:None,approval)
 approval.assert_not_called()
 assert sources.passages(s,'CRWV.US')[0]['id']==ident
 assert 'Capital' in sources.passages(s,'CRWV.US')[0]['topics']

def test_actual_checkpoint_failure_reproduction():
 from stock.sort import validate
 for case in json.loads((FIX/'checkpoint-failures.json').read_text()):
  if 'Overlapping' in case['error']:
   p=validate(case['candidate'],case['unit'],case['context'],case['document'],None,'archived Markdown','hash')
   assert any(max(p['location']['start'],loc['start'])<min(p['location']['end'],loc['end']) for loc in case['overlapping_locations'])
  else:
   with pytest.raises(ValueError,match='Ambiguous|current transcript turn'):
    validate(case['candidate'],case['unit'],case['context'],case['document'],None,'archived Markdown','hash')

def test_metric_label_stays_with_value():
 text=(FIX/'presentation-results.md').read_text()
 cs=candidates(text,doc(),digest(text))
 value=next(c for c in cs if '$898 million' in c['text'])
 assert 'Adjusted EBITDA:' in value['text']
 assert text[value['start']:value['end']]==value['text']

def test_moderator_operator_and_unknown_identity():
 text='Alex Host\n\nModerator\n\nBob Operator\n\nOperator\n\n## Alex Host\n\nHow have credit conditions changed?\n\n## Bob Operator\n\nPress star one.\n\n## Unidentified Participant\n\nOur financing remains secured by customer contracts.'
 cs=candidates(text,{**doc(),'type':'Transcript'},digest(text))
 assert [c['speaker'] for c in cs]==['Alex Host',None]
 assert cs[0]['speaker_role']=='Moderator'
 assert not any('star one' in c['text'] for c in cs)

def test_checkpoint_integrity_failure(staged):
 from stock.evidence import IntegrityError
 s,d,m=staged;extract(s,d,m,lambda _:None)
 row=s.db.execute('select payload from source_work_v3').fetchone();payload=json.loads(row[0]);payload['accepted'][0]['text']='invented'
 with s.db:s.db.execute('update source_work_v3 set payload=?',(json.dumps(payload),))
 with pytest.raises(IntegrityError,match='anchor'):extract(s,d,m,lambda _:None)

def test_document_specific_rebuild_and_reset(staged,tmp_path):
 s,d,m=staged;ps,_=extract(s,d,m,lambda _:None);sources.publish(s,d,ps,d['source_sha256'])
 other=tmp_path/'other.md';other.write_text('# Investor Presentation\n\nCustomer concentration increases our risk exposure.')
 d2=import_document(s,'CRWV.US',other)
 cs=candidates(other.read_text(),d2,digest(other.read_text()))
 ps2,_=resolve([selection(cs)],cs,other.read_text(),d2,digest(other.read_text()))
 sources.publish(s,d2,ps2,d2['source_sha256'])
 before=s.db.execute('select * from source_passages where document_id=?',(d2['id'],)).fetchall()
 assert rebuild(s,'CRWV.US',str(d['id']),lambda:m,lambda _:None,lambda:True)
 assert s.db.execute('select * from source_passages where document_id=?',(d2['id'],)).fetchall()==before
 p=next(p for p in sources.passages(s,'CRWV.US') if p['document_id']==d['id'])
 sources.set_topic(s,p['id'],'Capital',True);calls=m.calls
 sources.reset(s,'CRWV.US',str(d['id']))
 assert m.calls==calls and 'Capital' not in next(p for p in sources.passages(s,'CRWV.US') if p['document_id']==d['id'])['topics']

def test_markdown_heading_without_blank_line_and_crlf():
 text='# Context\r\nDemand exceeds available capacity.\r\n\r\n## Pricing\r\nPricing remains stable.\r\n'
 cs=candidates(text,doc(),digest(text))
 assert len(cs)==2
 assert [c['section'] for c in cs]==['Context','Pricing']
 assert all(text[c['start']:c['end']]==c['text'] for c in cs)

def test_rebuild_lock(staged):
 import fcntl
 from stock.core import ROOT
 s,d,m=staged;dbpath=s.db.execute('PRAGMA database_list').fetchone()[2]
 directory=ROOT/'.data'/'sort-locks';directory.mkdir(exist_ok=True)
 name=hashlib.sha256(f'{dbpath}:{d["id"]}'.encode()).hexdigest()
 with (directory/name).open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  with pytest.raises(ValueError,match='already running'):rebuild(s,'CRWV.US',str(d['id']),lambda:m,lambda _:None,lambda:True)


def test_cursor_http_auth_failure_stops_document_calls(monkeypatch):
 from stock.sort import Cursor
 cursor=Cursor.__new__(Cursor);cursor.command='agent'
 run=Mock(return_value=Mock(returncode=1,stdout='',stderr='HTTP 401: token rejected'))
 monkeypatch.setattr('stock.sort_process.run',run)
 with pytest.raises(AuthenticationError):cursor.extract(dict(candidates=[],text=''),'')
 assert run.call_count==1
