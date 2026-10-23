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
 chosen={**selection(cs), 'representation':'verbatim','text':None,'ambiguities':[]}
 def run(cmd,**kwargs):
  prompts.append(cmd[-1]);return Mock(returncode=0,stderr='',stdout=json.dumps({'type':'result','result':json.dumps({'selections':[chosen]})}))
 monkeypatch.setattr('stock.sort_process.run',run)
 assert c.extract(dict(candidates=cs,text=''),'CoreWeave')==[chosen]
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
 assert '\r13 · 0/0 · Prepare · 00:00' in output.getvalue()
 assert not any(word in output.getvalue() for word in ('child','stage','total','unknown'))
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
 assert len(ps)==1 and m.calls==3
 # Overlapping context can produce repeated selections; identical results are deduplicated.

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
 assert len(ps)==2 and len(calls)==2 and len(calls[1])==2
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

@pytest.mark.parametrize('text', ['**11**\n\nData Centers Added in 2025', 'Active Power Contracted Power\n\n**850MW+ 3.1GW+**', '**43**\n\nActive Data Centers'])
def test_layout_fragments_cannot_be_selected(text):
 cs=candidates(text,doc(),digest(text))
 ps,errors=resolve([selection(cs)],cs,text,doc(),digest(text))
 assert not ps and errors

@pytest.mark.parametrize('text', ['Demand exceeds supply.', '**Revenue:** $1.6 billion, up 110% YoY driven by demand.', '**Adjusted Net Loss:**\n\n$(284) million, compared to $(36) million in Q4\'24', 'We expect margins to decline.'])
def test_short_and_quantitative_claims_remain_selectable(text):
 cs=candidates(text,doc(),digest(text))
 assert resolve([selection(cs)],cs,text,doc(),digest(text))[0]

def test_review_all_passages(staged):
 from stock.rebuild import review_passages
 ps=[dict(text=f'Demand exceeds supply {i}.',topics=['Market'],location={'candidate_id':str(i)}) for i in range(8)]
 rendered=review_passages(ps)
 assert all(f'{i+1}/8' in rendered and p['text'] in rendered for i,p in enumerate(ps))
 assert 'verification' in rendered.lower() and 'relevance' in rendered.lower()

def test_checkpoint_contract_isolated_preserved(staged):
 s,d,m=staged
 from stock.evidence import schema
 schema(s)
 with s.db:s.db.execute('insert into source_work_v3 values(?,?,?,?)',(d['id'],digest(Path(d['original']).read_text()),0,json.dumps(dict(version=3,complete=True,accepted=[]))))
 assert extract(s,d,m,lambda _:None)[0]
 assert s.db.execute('select count(*) from source_work_v3').fetchone()[0]==2

def test_actual_eight_live_passages_and_readability():
 from stock.evidence import layout_errors,quality_flags
 frozen=json.loads((FIX/'document-13-live.json').read_text())
 text=(FIX/'document-13-live.md').read_text();h=digest(text)
 assert h==frozen['markdown_sha256']
 cs=candidates(text,doc(),h);lookup={c['id']:c for c in cs}
 assert len(frozen['passages'])==8
 for i,p in enumerate(frozen['passages']):
  loc=p['location'];assert text[loc['start']:loc['end']]==p['text']
  ids=loc.get('candidate_ids',[loc['candidate_id']]);group=[lookup[x] for x in ids]
  accepted,errors=resolve([selection(group)],cs,text,doc(),h)
  assert bool(errors)==(i<3)
  assert bool(accepted)==(i>=3)
  assert bool(layout_errors(p['text']))==(i<3)
 # The ambiguous power layout is a readability failure. Count tiles can be
 # interpreted, but do not offer commentary. Neither is measured by table count.
 assert all('|' not in p['text'] for p in frozen['passages'])
 assert quality_flags(frozen['passages'][1]['text'])

@pytest.mark.parametrize('text', ['**Capacity:**\n\n850MW', '# Capacity\n\n**43**\n\n# Demand\n\nDemand exceeds supply.'])
def test_label_boundary_never_invents_association(text):
 from stock.evidence import layout_errors
 cs=candidates(text,doc(),digest(text))
 assert all(text[c['start']:c['end']]==c['text'] for c in cs)
 if text.startswith('**Capacity:'):
  assert len(cs)==1 and not layout_errors(cs[0]['text'])
 else:
  assert layout_errors(cs[0]['text'])
  assert cs[-1]['text']=='Demand exceeds supply.'

def test_terminal_review_keyboard_pager_receives_all(monkeypatch):
 from stock.sort_process import Status
 import pydoc
 seen=[]
 monkeypatch.setattr('sys.stdout.isatty',lambda:True)
 monkeypatch.setattr('sys.stdin.isatty',lambda:True)
 monkeypatch.setattr(pydoc,'ttypager',seen.append)
 Status().review_all('All eight\nLast passage')
 assert len(seen)==1 and 'All eight\nLast passage' in seen[0] and 'b: back' in seen[0]

def test_paired_metrics_colon_does_not_establish_mapping():
 from stock.evidence import layout_errors
 assert layout_errors('**Active Power Contracted Power:**\n\n850MW+ 3.1GW+')
 assert not layout_errors('**Active Power:**\n\n850MW+')

@pytest.mark.parametrize('complete',[False,True])
def test_old_contract_never_resumes_even_same_hash(staged,complete):
 from stock.evidence import schema
 s,d,m=staged;schema(s)
 payload=dict(version=3,complete=complete,accepted=[],raw=[],rejected=[])
 with s.db:s.db.execute('insert into source_work_v3 values(?,?,?,?)',(d['id'],digest(Path(d['original']).read_text()),0,json.dumps(payload)))
 assert extract(s,d,m,lambda _:None)[0]
 assert json.loads(s.db.execute('select payload from source_work_v3 where markdown_hash=?',(digest(Path(d['original']).read_text()),)).fetchone()[0])==payload

def test_rejected_rebuild_on_database_copy_preserves_all_frozen_tables(staged,tmp_path):
 import sqlite3
 s,d,m=staged;ps,_=extract(s,d,m,lambda _:None);sources.publish(s,d,ps,d['source_sha256'])
 sources.set_topic(s,sources.passages(s,'CRWV.US')[0]['id'],'Capital',True)
 copied=Store(tmp_path/'copy.sqlite3');s.db.backup(copied.db)
 tables=('source_passages','source_topics','source_overrides','source_sorts','archive_documents')
 def snapshot(store):return {t:store.db.execute(f'SELECT * FROM {t} ORDER BY 1').fetchall() for t in tables}
 before=snapshot(s)
 assert not rebuild(copied,'CRWV.US',str(d['id']),lambda:m,lambda _:None,lambda:False)
 assert snapshot(copied)==before==snapshot(s)

def test_exclusion_report_handles_invalid_selection_shape(staged):
 s,d,m=staged;m.extract=lambda u,c:[dict(ids=7,topics=['Market'],category='Management',speaker=None)]
 log=[]
 assert extract(s,d,m,log.append)[0]==[]
 assert any('1 unresolved' in line for line in log)
