"""Offline graph publication, correction and keyboard regressions."""
import json
from pathlib import Path
import pytest
from stock import sources
from stock.core import Store
from stock.archive import import_document
from stock import insights

FIX=Path(__file__).parent/'fixtures/sort'

@pytest.fixture
def library(tmp_path,monkeypatch):
 monkeypatch.setattr('stock.archive.ROOT',tmp_path)
 s=Store(tmp_path/'db')
 docs=[]
 for i in range(2):
  f=tmp_path/f'doc{i}.md';f.write_text(f'# CoreWeave Investor Presentation {i}\n\nDemand exceeds available capacity.')
  docs.append(import_document(s,'CRWV.US',f))
 sources.schema(s)
 def add(text,doc=0,topics=('Market',),**kw):
  d=docs[doc];p=dict(text=text,topics=list(topics),category='Management',speaker=None,
   location=dict(attributes={'issuer':'CoreWeave','period':'2025','scope':'company'},start=len(text),end=2*len(text),section='Demand',verification='Exact archived Markdown text'),
   publication_date='2025-12-31',date_provenance={})
  p.update(kw)
  # Independent records with stable citation identity, including legacy records.
  import hashlib
  ident=hashlib.sha256(json.dumps([doc,text,kw],sort_keys=True).encode()).hexdigest()
  with s.db:
   s.db.execute('INSERT INTO source_passages VALUES(?,?,?,?,?,?,?,?)',(ident,d['id'],text,p['category'],p['speaker'],json.dumps(p['location']),p['publication_date'],json.dumps(p['date_provenance'])))
   s.db.executemany('INSERT INTO source_topics VALUES(?,?)',[(ident,t) for t in topics])
  return ident
 yield s,docs,add
 s.db.close()


def decision(pair,equivalent=True,relation='repeated_assertion',**kw):
 return dict(pair=pair['id'],equivalent=equivalent,relation=relation,
  dimensions_agree=equivalent,information_preserved=equivalent,
  reason='Same issuer capacity constraint at the same as-of; no added scope.' if equivalent else 'Material difference retained.',
  differences=[] if equivalent else ['Different period, scope, qualification or proposition.'],**kw)

class Replay:
 def __init__(self,equivalent=True):self.calls=[];self.equivalent=equivalent
 def extract(self,u,c):
  self.calls.append(u)
  return [decision(p,self.equivalent) for p in u['semantic_pairs']]


@pytest.fixture(autouse=True)
def local_graph_models(offline_semantics):
 return offline_semantics


def test_stale_activation_and_transaction_failure_leave_head_unchanged(library):
 s,_,add=library;a=add('Demand exceeds capacity.');add('Customer demand exceeds capacity.',1)
 p=insights.stage(s,'CRWV.US',Replay(),lambda _:None)
 sources.set_topic(s,a,'Capital',True)
 with pytest.raises(ValueError,match='changed'):insights.activate(s,p['id'])
 assert len(insights.entries(s,'CRWV.US'))==2
 p=insights.stage(s,'CRWV.US',Replay(),lambda _:None)
 s.db.execute("CREATE TRIGGER fail_head BEFORE INSERT ON source_insight_heads BEGIN SELECT RAISE(ABORT,'forced failure'); END")
 import sqlite3
 with pytest.raises(sqlite3.IntegrityError):insights.activate(s,p['id'])
 assert len(insights.entries(s,'CRWV.US'))==2

async def test_keyboard_group_members_filter_topics_and_ungroup(library,monkeypatch):
 from stock.sources_ui import SourcesApp
 s,docs,add=library
 a=add('Demand exceeds available capacity.')
 b=add('Customer demand exceeds available capacity.',1)
 p=insights.stage(s,'CRWV.US',Replay(),lambda _:None);insights.activate(s,p['id'])
 opened=[];monkeypatch.setattr('stock.sources_ui.open_file',lambda path:opened.append(path))
 app=SourcesApp('CRWV.US',s)
 async with app.run_test(size=(100,30)) as pilot:
  await pilot.press('right','space','n','o')
  assert len(app.visible())==1 and opened
  member=app.member(app.visible()[0]);assert member['document_id']==docs[1]['id']
  await pilot.press('t','space','t')
  assert s.db.execute('SELECT passage_id FROM source_overrides').fetchall()==[(b,)]
  # Topic filter now exposes only a; editing b did not remove a's membership.
  assert [m['id'] for m in app.visible()[0]['members']]==[a]
  await pilot.press('u')
  assert len(insights.entries(s,'CRWV.US'))==2
  await pilot.press('escape')

def test_new_document_groups_publish_atomically_across_existing_evidence(library):
 s,docs,add=library;add('Demand exceeds available capacity.')
 new=[dict(text=t,topics=['Market'],category='Management',speaker=None,
  location=dict(attributes={'issuer':'CoreWeave','period':'2025','scope':'company'},start=i,end=i+1,section='Demand',verification='Exact archived Markdown text'),
  publication_date='2025-12-31',date_provenance={}) for i,t in enumerate([
   'Demand exceeds available capacity.','Customer demand exceeds available capacity.'])]
 p=insights.stage(s,'CRWV.US',Replay(),lambda _:None,new_document=(docs[1],new))
 assert sources.publish(s,docs[1],new,docs[1]['source_sha256'],insight_proposal=p)
 assert len(insights.entries(s,'CRWV.US'))==1
 assert insights.current(s,'CRWV.US')
 assert len(sources.passages(s,'CRWV.US'))==3
 assert not sources.publish(s,docs[1],new,docs[1]['source_sha256'],insight_proposal=p)

def test_group_publish_failure_rolls_back_evidence_and_group_head(library):
 s,docs,_=library
 new=[dict(text=t,topics=['Market'],category='Management',speaker=None,location=dict(attributes={'issuer':'CoreWeave','period':'2025','scope':'company'},start=i,end=i+1),publication_date=None,date_provenance={}) for i,t in enumerate(['Demand exceeds capacity.','Customer demand exceeds capacity.'])]
 p=insights.stage(s,'CRWV.US',Replay(),lambda _:None,new_document=(docs[0],new))
 s.db.execute("CREATE TRIGGER fail_publish BEFORE INSERT ON source_insight_heads BEGIN SELECT RAISE(ABORT,'forced failure'); END")
 import sqlite3
 with pytest.raises(sqlite3.IntegrityError):sources.publish(s,docs[0],new,docs[0]['source_sha256'],insight_proposal=p)
 assert not sources.passages(s,'CRWV.US') and not sources.completed(s,docs[0]['id'])
 assert insights.head(s,'CRWV.US') is None

async def test_topic_editor_remains_bound_to_explicit_member(library):
 from stock.sources_ui import SourcesApp
 s,_,add=library
 a=add('Demand exceeds available capacity.')
 b=add('Customer demand exceeds available capacity.',1)
 p=insights.stage(s,'CRWV.US',Replay(),lambda _:None);insights.activate(s,p['id'])
 app=SourcesApp('CRWV.US',s)
 async with app.run_test(size=(100,30)) as pilot:
  await pilot.press('right','n','t','space')
  assert app.editing==b
  assert '[ ] Market' in str(app.row_widgets[1].render())
  await pilot.press('space')
  assert app.editing==b and '[x] Market' in str(app.row_widgets[1].render())
  assert next(x for x in sources.passages(s,'CRWV.US') if x['id']==a)['topics']=={'Market'}
  await pilot.press('escape')

def test_rebuild_semantic_group_activation_rolls_back_on_failure(library,monkeypatch):
 from stock.rebuild import rebuild
 s,docs,add=library
 add('Demand exceeds available capacity.')
 add('Customer demand exceeds available capacity.',1)
 initial=insights.stage(s,'CRWV.US',Replay(),lambda _:None);insights.activate(s,initial['id'])
 before=s.db.execute('SELECT * FROM source_passages ORDER BY id').fetchall()
 new=[dict(text=t,topics=['Market'],category='Management',speaker=None,
  location=dict(attributes={'issuer':'CoreWeave','period':'2025','scope':'company'},start=i,end=i+1,candidate_id=f'new{i}'),publication_date=None,date_provenance={}) for i,t in enumerate(['Demand exceeds capacity.','Customer demand exceeds capacity.'])]
 monkeypatch.setattr('stock.rebuild.extract',lambda *args:(new,lambda:None))
 class Real(Replay):supports_distillation=True
 s.db.execute("CREATE TRIGGER fail_rebuild BEFORE UPDATE ON source_insight_heads BEGIN SELECT RAISE(ABORT,'forced failure'); END")
 import sqlite3
 with pytest.raises(sqlite3.IntegrityError):rebuild(s,'CRWV.US',str(docs[1]['id']),Real,lambda _:None,lambda:True)
 assert before==s.db.execute('SELECT * FROM source_passages ORDER BY id').fetchall()
 assert insights.head(s,'CRWV.US')==initial['id']

def test_rebuild_checks_other_document_snapshot_before_commit(library,monkeypatch):
 from stock.rebuild import rebuild
 from stock.evidence import IntegrityError
 s,docs,add=library
 a=add('Demand exceeds available capacity.')
 add('Customer demand exceeds available capacity.',1)
 new=[dict(text='Demand exceeds available capacity.',topics=['Market'],category='Management',speaker=None,
  location=dict(attributes={'issuer':'CoreWeave','period':'2025','scope':'company'},start=0,end=34,candidate_id='new'),publication_date=None,date_provenance={})]
 before=s.db.execute('SELECT * FROM source_passages ORDER BY id').fetchall()
 checks=[]
 def verify():
  checks.append(True)
  if len(checks)==2:sources.set_topic(s,a,'Capital',True)
 monkeypatch.setattr('stock.rebuild.extract',lambda *args:(new,verify))
 class Real(Replay):supports_distillation=True
 def approve():raise AssertionError('No keyboard approval')
 with pytest.raises(IntegrityError,match='changed'):rebuild(s,'CRWV.US',str(docs[1]['id']),Real,lambda _:None,approve)
 assert before==s.db.execute('SELECT * FROM source_passages ORDER BY id').fetchall()
 assert not insights.head(s,'CRWV.US')
 assert s.db.execute('SELECT * FROM source_overrides').fetchall()==[(a,'Capital',1)]

def test_manual_ungroup_survives_incremental_new_evidence(library):
 s,_,add=library
 add('Demand exceeds available capacity.');add('Customer demand exceeds available capacity.',1)
 p=insights.stage(s,'CRWV.US',Replay(),lambda _:None);insights.activate(s,p['id'])
 insights.ungroup(s,'CRWV.US',insights.entries(s,'CRWV.US')[0]['id'])
 add('Different period: demand exceeds available capacity in 2026.')
 p=insights.stage(s,'CRWV.US',Replay(False),lambda _:None);insights.activate(s,p['id'])
 assert len(insights.entries(s,'CRWV.US'))==3
 assert any('Manual ungroup' in d['reason'] for d in p['differences'])

def test_rebuild_unattended_never_invokes_approval(library,monkeypatch):
 from stock.rebuild import rebuild
 s,docs,add=library;add('Old evidence.',1)
 new=[dict(text='Replacement evidence.',topics=['Market'],category='Management',speaker=None,
  location=dict(attributes={'issuer':'CoreWeave','period':'2025','scope':'company'},start=0,end=1,candidate_id='new'),publication_date=None,date_provenance={})]
 verified=[]
 monkeypatch.setattr('stock.rebuild.extract',lambda *args:(new,lambda:verified.append(True)))
 class Real(Replay):supports_distillation=True
 def forbidden():raise AssertionError('Must not request keyboard confirmation')
 assert rebuild(s,'CRWV.US',str(docs[1]['id']),Real,lambda _:None,forbidden)
 assert verified and insights.current(s,'CRWV.US')
 assert [p['text'] for p in sources.passages(s,'CRWV.US')]==['Replacement evidence.']

def test_rebuild_transfers_manual_split_and_topic_by_unique_source_identity(library,monkeypatch):
 from stock.rebuild import rebuild
 s,docs,add=library
 a=add('Demand exceeds capacity.',location=dict(attributes={'issuer':'CoreWeave','period':'2025','scope':'company'},start=0,end=1),doc=1)
 b=add('Customer demand exceeds capacity.')
 p=insights.stage(s,'CRWV.US',Replay(),lambda _:None);insights.activate(s,p['id'])
 insights.ungroup(s,'CRWV.US',p['groups'][0]['id'])
 sources.set_topic(s,a,'Capital',True)
 new=[dict(text='Capacity falls short of demand.',topics=['Market'],category='Management',speaker=None,
  location=dict(attributes={'issuer':'CoreWeave','period':'2025','scope':'company'},start=0,end=1,candidate_id='replacement'),publication_date='2025-12-31',date_provenance={})]
 monkeypatch.setattr('stock.rebuild.extract',lambda *args:(new,lambda:None))
 class Real(Replay):supports_distillation=True
 assert rebuild(s,'CRWV.US',str(docs[1]['id']),Real,lambda _:None)
 active=insights.load(s,insights.head(s,'CRWV.US'))
 incoming=sources.passage_id(docs[1],new[0])
 assert sorted((incoming,b)) in [list(pair) for pair in active['suppressed_pairs']]
 assert a not in active['fingerprints'] and incoming in active['fingerprints']
 assert len(insights.entries(s,'CRWV.US'))==2
 assert 'Capital' in next(p for p in sources.passages(s,'CRWV.US') if p['id']==incoming)['topics']
 assert s.db.execute('SELECT count(*) FROM source_publication_history').fetchone()[0]==1

def test_rebuild_unmatched_manual_split_blocks_before_grouping(library,monkeypatch):
 from stock.rebuild import rebuild
 from stock.evidence import IntegrityError
 s,docs,add=library
 add('Demand exceeds capacity.',doc=1);add('Customer demand exceeds capacity.')
 p=insights.stage(s,'CRWV.US',Replay(),lambda _:None);insights.activate(s,p['id'])
 insights.ungroup(s,'CRWV.US',p['groups'][0]['id'])
 before=s.db.execute('SELECT * FROM source_passages ORDER BY id').fetchall();old_head=insights.head(s,'CRWV.US')
 new=[dict(text='Changed source.',topics=['Market'],category='Management',speaker=None,
  location=dict(attributes={'issuer':'CoreWeave','period':'2025','scope':'company'},start=999,end=1000),publication_date=None,date_provenance={})]
 monkeypatch.setattr('stock.rebuild.extract',lambda *args:(new,lambda:None))
 with pytest.raises(IntegrityError,match='manual corrections/splits'):
  rebuild(s,'CRWV.US',str(docs[1]['id']),lambda:None,lambda _:None)
 assert insights.head(s,'CRWV.US')==old_head
 assert s.db.execute('SELECT * FROM source_passages ORDER BY id').fetchall()==before
