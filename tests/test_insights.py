"""Semantic judgments are replayed; no authenticated service or production writes."""
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
   location=dict(start=len(text),end=2*len(text),section='Demand',verification='Exact archived Markdown text'),
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


def test_paraphrase_cross_document_reversible_and_cached(library):
 s,docs,add=library
 a=add('Demand exceeds available capacity.')
 b=add('Customer demand is outpacing our available supply.',1)
 before=s.db.execute('SELECT * FROM source_passages').fetchall()
 m=Replay();proposal=insights.stage(s,'CRWV.US',m,lambda _:None)
 assert proposal['passage_count']==2 and len(proposal['groups'])==1
 assert len(m.calls)==1 and len(insights.entries(s,'CRWV.US'))==2
 assert insights.stage(s,'CRWV.US',m,lambda _:None)['groups']==proposal['groups']
 assert len(m.calls)==1
 insights.activate(s,proposal['id'])
 rows=insights.entries(s,'CRWV.US');assert len(rows)==1
 assert {p['id'] for p in rows[0]['members']}=={a,b}
 assert rows[0]['text'] in {p['text'] for p in rows[0]['members']}
 assert 'repeated_assertion' in insights.review_text(proposal)
 insights.ungroup(s,'CRWV.US',rows[0]['id'])
 assert len(insights.entries(s,'CRWV.US'))==2
 assert s.db.execute('SELECT * FROM source_passages').fetchall()==before
 assert s.db.execute('SELECT count(*) FROM source_insight_revisions').fetchone()[0]>=2

@pytest.mark.parametrize('text',[
 'Inference demand is exceeding available capacity.',
 'Demand exceeds capacity in Europe.',
 'Demand is expected to exceed available capacity in 2026.',
 'Demand no longer exceeds available capacity.',
 'Demand exceeds available capacity, except for reserved instances.',
 'Demand exceeds available capacity as of March 2026.',
 'CoreWeave added 11 data centers in 2025.',
])
def test_material_differences_not_merged(library,text):
 s,_,add=library;add('Demand exceeds available capacity.');add(text,1)
 proposal=insights.stage(s,'CRWV.US',Replay(False),lambda _:None)
 assert len(proposal['groups'])==2
 insights.activate(s,proposal['id'])
 assert len(insights.entries(s,'CRWV.US'))==2


def test_filters_topics_and_member_edits_never_propagate(library):
 s,docs,add=library
 a=add('Demand exceeds available capacity.',topics=('Market',))
 b=add('Customer demand exceeds available capacity.',1,topics=('Operations',))
 p=insights.stage(s,'CRWV.US',Replay(),lambda _:None);insights.activate(s,p['id'])
 sources.set_topic(s,a,'Market',False)
 assert 'Market' not in insights.entries(s,'CRWV.US')[0]['topics']
 rows=insights.entries(s,'CRWV.US',document_id=docs[0]['id'])
 assert len(rows)==1 and rows[0]['topics']==set() and len(rows[0]['members'])==1
 assert not insights.entries(s,'CRWV.US',document_id=docs[0]['id'],topic='Operations')
 rows=insights.entries(s,'CRWV.US',topic='Operations')
 assert rows[0]['text']=='Customer demand exceeds available capacity.' and rows[0]['members'][0]['id']==b
 assert s.db.execute('SELECT * FROM source_overrides').fetchall()==[(a,'Market',0)]


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


def test_no_transitive_merge(library):
 s,_,add=library
 for text in ['Demand exceeds capacity.','Customer demand exceeds capacity.','Demand outpaces available capacity.']:add(text)
 class Nontransitive(Replay):
  def extract(self,u,c):
   return [decision(p,not ({p['left']['text'],p['right']['text']}=={'Demand exceeds capacity.','Demand outpaces available capacity.'})) for p in u['semantic_pairs']]
 p=insights.stage(s,'CRWV.US',Nontransitive(),lambda _:None)
 assert sorted(map(lambda g:len(g['members']),p['groups']))==[1,2]


def test_missing_or_uncertain_judgments_cannot_merge(library):
 s,_,add=library;add('Demand exceeds capacity.');add('Customer demand exceeds capacity.',1)
 class Bad:
  def extract(self,u,c):return []
 with pytest.raises(ValueError):insights.stage(s,'CRWV.US',Bad(),lambda _:None)
 assert len(insights.entries(s,'CRWV.US'))==2


def test_bounded_candidate_work(library):
 s,_,add=library
 for i in range(120):add(f'CoreWeave demand exceeds capacity for customer {i}.')
 m=Replay(False);p=insights.stage(s,'CRWV.US',m,lambda _:None)
 assert p['comparison_count']<=120*insights.NEIGHBORS
 assert len(p['groups'])==120
 assert len(m.calls)<p['comparison_count']

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
  location=dict(start=i,end=i+1,section='Demand',verification='Exact archived Markdown text'),
  publication_date='2025-12-31',date_provenance={}) for i,t in enumerate([
   'Demand exceeds available capacity.','Customer demand exceeds available capacity.'])]
 p=insights.stage(s,'CRWV.US',Replay(),lambda _:None,new_document=(docs[1],new))
 assert sources.publish(s,docs[1],new,docs[1]['source_sha256'],insight_proposal=p)
 assert len(insights.entries(s,'CRWV.US'))==1
 assert insights.current(s,'CRWV.US')
 assert len(sources.passages(s,'CRWV.US'))==3
 assert not sources.publish(s,docs[1],new,docs[1]['source_sha256'],insight_proposal=p)


def test_independent_corroboration_is_audited_not_an_extra_insight(library):
 s,_,add=library
 add('Demand exceeds available capacity.')
 add('Customer demand exceeds available capacity.',1,category='Media')
 class Independent(Replay):
  def extract(self,u,c):return [decision(p,relation='independent_corroboration') for p in u['semantic_pairs']]
 p=insights.stage(s,'CRWV.US',Independent(),lambda _:None)
 assert len(p['groups'])==1 and p['groups'][0]['basis'][0]['relation']=='independent_corroboration'


def test_group_publish_failure_rolls_back_evidence_and_group_head(library):
 s,docs,_=library
 new=[dict(text=t,topics=['Market'],category='Management',speaker=None,location=dict(start=i,end=i+1),publication_date=None,date_provenance={}) for i,t in enumerate(['Demand exceeds capacity.','Customer demand exceeds capacity.'])]
 p=insights.stage(s,'CRWV.US',Replay(),lambda _:None,new_document=(docs[0],new))
 s.db.execute("CREATE TRIGGER fail_publish BEFORE INSERT ON source_insight_heads BEGIN SELECT RAISE(ABORT,'forced failure'); END")
 import sqlite3
 with pytest.raises(sqlite3.IntegrityError):sources.publish(s,docs[0],new,docs[0]['source_sha256'],insight_proposal=p)
 assert not sources.passages(s,'CRWV.US') and not sources.completed(s,docs[0]['id'])
 assert insights.head(s,'CRWV.US') is None


def test_identical_claim_and_exact_support_uses_no_model(library):
 s,_,add=library
 ref=dict(text='Demand exceeds available capacity.',start=0,end=34,markdown_sha256='unchanged',original_sha256='unchanged')
 for i in range(2):
  add(ref['text'],location=dict(start=i,end=i+1,references=[ref],section='Demand'))
 m=Replay();p=insights.stage(s,'CRWV.US',m,lambda _:None)
 assert len(p['groups'])==1 and not m.calls
 assert 'Deterministic' in p['groups'][0]['basis'][0]['reason']


def test_oversized_evidence_is_reviewed_without_truncation(library):
 s,_,add=library
 add('Demand exceeds capacity. '+('Material source qualification. '*1000))
 add('Customer demand exceeds capacity.',1)
 m=Replay(False);p=insights.stage(s,'CRWV.US',m,lambda _:None)
 assert len(p['groups'])==2 and len(m.calls)==1
 assert len(m.calls[0]['semantic_pairs'][0]['left']['text'])>28000 or len(m.calls[0]['semantic_pairs'][0]['right']['text'])>28000


def test_coreweave_recorded_excerpts_pipeline(tmp_path):
 import runpy
 module=runpy.run_path(str(Path(__file__).parents[1]/'scripts/verify_semantic_insights.py'))
 report=module['replay'](tmp_path)
 assert (report['passages'],report['distinct_insights'],report['retained_member_records'])==(13,9,13)
 assert report['false_merges']==report['missed_merges']==report['resume_requests']==0
 assert report['replayed_cursor_requests']==1

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
  location=dict(start=i,end=i+1,candidate_id=f'new{i}'),publication_date=None,date_provenance={}) for i,t in enumerate(['Demand exceeds capacity.','Customer demand exceeds capacity.'])]
 monkeypatch.setattr('stock.rebuild.extract',lambda *args:(new,lambda:None))
 class Real(Replay):supports_distillation=True
 s.db.execute("CREATE TRIGGER fail_rebuild BEFORE UPDATE ON source_insight_heads BEGIN SELECT RAISE(ABORT,'forced failure'); END")
 import sqlite3
 with pytest.raises(sqlite3.IntegrityError):rebuild(s,'CRWV.US',str(docs[1]['id']),Real,lambda _:None,lambda:True)
 assert before==s.db.execute('SELECT * FROM source_passages ORDER BY id').fetchall()
 assert insights.head(s,'CRWV.US')==initial['id']


def test_default_sort_groups_completed_evidence_and_is_idempotent(library,monkeypatch):
 from stock.sort import sort_stock
 s,docs,add=library
 a=add('Demand exceeds available capacity.')
 add('Customer demand exceeds available capacity.',1)
 for d in docs:
  s.db.execute('INSERT INTO source_sorts VALUES(?,?,?,4)',(d['id'],0,d['source_sha256']))
 s.db.commit()
 model=Replay();monkeypatch.setattr('stock.sort.Cursor',lambda:model)
 before=s.db.execute('SELECT * FROM source_passages ORDER BY id').fetchall()
 assert sort_stock(s,'CRWV.US',lambda _:None)
 active=insights.head(s,'CRWV.US');assert active and len(model.calls)==1
 revisions=s.db.execute('SELECT count(*) FROM source_insight_revisions').fetchone()[0]
 sources.set_topic(s,a,'Capital',True)
 assert sort_stock(s,'CRWV.US',lambda _:None)
 assert insights.head(s,'CRWV.US')==active and len(model.calls)==1
 assert s.db.execute('SELECT count(*) FROM source_insight_revisions').fetchone()[0]==revisions
 assert before==s.db.execute('SELECT * FROM source_passages ORDER BY id').fetchall()
 assert s.db.execute('SELECT * FROM source_overrides').fetchall()==[(a,'Capital',1)]
 insights.ungroup(s,'CRWV.US',insights.entries(s,'CRWV.US')[0]['id'])
 ungrouped=insights.head(s,'CRWV.US')
 assert sort_stock(s,'CRWV.US',lambda _:None)
 assert insights.head(s,'CRWV.US')==ungrouped and len(model.calls)==1


def test_review_only_groups_without_activation(library,monkeypatch):
 from stock.sort import sort_stock
 s,docs,add=library
 add('Demand exceeds available capacity.');add('Customer demand exceeds available capacity.',1)
 for d in docs:s.db.execute('INSERT INTO source_sorts VALUES(?,?,?,4)',(d['id'],0,d['source_sha256']))
 s.db.commit()
 model=Replay();monkeypatch.setattr('stock.sort.Cursor',lambda:model)
 output=[]
 assert sort_stock(s,'CRWV.US',output.append,review_only=True)
 assert insights.head(s,'CRWV.US') is None and len(model.calls)==1
 assert any('Proposed 1 distinct insights' in line for line in output)
 assert sort_stock(s,'CRWV.US',lambda _:None)
 assert len(model.calls)==1 and insights.head(s,'CRWV.US')


def test_grouping_budget_preserves_cached_decisions_without_partial_activation(library,monkeypatch):
 monkeypatch.setattr(insights,'REQUEST_BUDGET',2500)
 from stock.sort_budget import Budget,BudgetExceeded
 from stock.sort_process import DeferredCursor
 s,_,add=library
 for i in range(15):add(f'Customer demand exceeds available capacity for separate region {i}.')
 m=Replay(False)
 with Budget(requests=1) as budget:
  budget.use_document('Insights')
  with pytest.raises(BudgetExceeded,match='Request limit'):
   insights.stage(s,'CRWV.US',DeferredCursor(lambda:m),lambda _:None)
 assert insights.head(s,'CRWV.US') is None
 cached=s.db.execute('SELECT count(*) FROM source_semantic_cache').fetchone()[0]
 assert cached>0 and len(m.calls)==1
 p=insights.stage(s,'CRWV.US',m,lambda _:None)
 assert p['cached_decisions']==cached
 insights.activate(s,p['id'])
 assert len(insights.entries(s,'CRWV.US'))==15


def test_rebuild_checks_other_document_snapshot_before_commit(library,monkeypatch):
 from stock.rebuild import rebuild
 from stock.evidence import IntegrityError
 s,docs,add=library
 a=add('Demand exceeds available capacity.')
 add('Customer demand exceeds available capacity.',1)
 new=[dict(text='Demand exceeds available capacity.',topics=['Market'],category='Management',speaker=None,
  location=dict(start=0,end=34,candidate_id='new'),publication_date=None,date_provenance={})]
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


def test_complete_recorded_sort_pipeline_retains_all_coreweave_insights(tmp_path):
 import runpy
 root=Path(__file__).parents[1]
 module=runpy.run_path(str(root/'scripts/benchmark_unified_sort.py'))
 report=module['worker'](root,tmp_path)
 assert (report['evidence'],report['insights'],report['exact_citations'])==(13,9,22)  # Includes the exact reporting-quarter header.
 assert not report['missing_fixture_claims'] and report['resume_requests']==0
 assert report['stages']['review']['requests']>0
 assert report['stages']['cross-document grouping']['requests']>0
 assert report['actual_tokens'] is report['live_latency'] is None


def test_historical_manual_split_survives_another_split_and_staging(library):
 s,_,add=library
 for text in ['Demand exceeds capacity.','Demand outpaces capacity.','Power capacity expanded.','Power capacity increased.']:add(text)
 class TwoGroups(Replay):
  def extract(self,u,c):
   return [decision(p,p['left']['text'].split()[0]==p['right']['text'].split()[0]) for p in u['semantic_pairs']]
 p=insights.stage(s,'CRWV.US',TwoGroups(),lambda _:None);insights.activate(s,p['id'])
 groups=insights.entries(s,'CRWV.US');assert len(groups)==2
 old=insights.ungroup(s,'CRWV.US',groups[0]['id'])
 # Emulate the actual historical payload written before suppression was persisted.
 old.pop('suppressed_pairs')
 with s.db:s.db.execute('UPDATE source_insight_revisions SET payload=? WHERE id=?',(insights.packed(old),old['id']))
 insights.ungroup(s,'CRWV.US',groups[1]['id'])
 assert len(insights.entries(s,'CRWV.US'))==4
 p=insights.stage(s,'CRWV.US',TwoGroups(),lambda _:None);insights.activate(s,p['id'])
 assert len(p['suppressed_pairs'])==2 and len(insights.entries(s,'CRWV.US'))==4


def test_incremental_replacement_exhaustive_pairs_without_historical_backlog(library):
 s,docs,add=library
 historical=[add(f'Historical evidence {i}.') for i in range(12)]
 add('Outgoing evidence.',1)
 new=[dict(text=t,topics=['Market'],category='Management',speaker=None,
  location=dict(start=i,end=i+1),publication_date=None,date_provenance={})
  for i,t in enumerate(['Unrelated wording alpha.','Other wording beta.'])]
 m=Replay(False)
 p=insights.stage(s,'CRWV.US',m,lambda _:None,new_document=(docs[1],new))
 pairs=[pair for call in m.calls for pair in call['semantic_pairs']]
 incoming={sources.passage_id(docs[1],x) for x in new}
 assert len(pairs)==25  # 2*12 + one incoming/incoming; even with no shared tokens.
 assert all(pair['left']['id'] in incoming or pair['right']['id'] in incoming for pair in pairs)
 assert p['grouping_scope']=='replacement'
 assert p['historical_backlog_pairs']>0
 assert p['comparison_count']==25


def test_incremental_preserves_existing_group_and_complete_link(library):
 s,docs,add=library
 a=add('Demand exceeds capacity.');b=add('Customer demand exceeds capacity.')
 initial=insights.stage(s,'CRWV.US',Replay(),lambda _:None);insights.activate(s,initial['id'])
 new=[dict(text='Demand outpaces supply.',topics=['Market'],category='Management',speaker=None,
  location=dict(start=0,end=1),publication_date=None,date_provenance={})]
 class Partial(Replay):
  def extract(self,u,c):
   self.calls.append(u)
   return [decision(p,b not in (p['left']['id'],p['right']['id'])) for p in u['semantic_pairs']]
 m=Partial();p=insights.stage(s,'CRWV.US',m,lambda _:None,new_document=(docs[1],new))
 assert any(g['members']==initial['groups'][0]['members'] for g in p['groups'])
 assert sorted(len(g['members']) for g in p['groups'])==[1,2]
 assert len([x for call in m.calls for x in call['semantic_pairs']])==2


def test_rebuild_unattended_never_invokes_approval(library,monkeypatch):
 from stock.rebuild import rebuild
 s,docs,add=library;add('Old evidence.',1)
 new=[dict(text='Replacement evidence.',topics=['Market'],category='Management',speaker=None,
  location=dict(start=0,end=1,candidate_id='new'),publication_date=None,date_provenance={})]
 verified=[]
 monkeypatch.setattr('stock.rebuild.extract',lambda *args:(new,lambda:verified.append(True)))
 class Real(Replay):supports_distillation=True
 def forbidden():raise AssertionError('Must not request keyboard confirmation')
 assert rebuild(s,'CRWV.US',str(docs[1]['id']),Real,lambda _:None,forbidden)
 assert verified and insights.current(s,'CRWV.US')
 assert [p['text'] for p in sources.passages(s,'CRWV.US')]==['Replacement evidence.']


def test_legacy_unreviewed_negative_cache_is_not_a_judgment(library):
 s,docs,add=library
 a=add('Demand exceeds capacity.');b=add('Customer demand exceeds capacity.',1)
 p=insights.stage(s,'CRWV.US',Replay(False),lambda _:None)
 key=s.db.execute('SELECT fingerprint FROM source_semantic_cache').fetchone()[0]
 r=json.loads(s.db.execute('SELECT payload FROM source_semantic_cache').fetchone()[0])
 r['reason']='Full evidence exceeds comparison budget; uncertainty preserved as separate insights.'
 with s.db:s.db.execute('UPDATE source_semantic_cache SET payload=? WHERE fingerprint=?',(insights.packed(r),key))
 m=Replay();p=insights.stage(s,'CRWV.US',m,lambda _:None)
 assert len(m.calls)==1 and len(p['groups'])==1


def test_rebuild_transfers_manual_split_and_topic_by_unique_source_identity(library,monkeypatch):
 from stock.rebuild import rebuild
 s,docs,add=library
 a=add('Demand exceeds capacity.',location=dict(start=0,end=1),doc=1)
 b=add('Customer demand exceeds capacity.')
 p=insights.stage(s,'CRWV.US',Replay(),lambda _:None);insights.activate(s,p['id'])
 insights.ungroup(s,'CRWV.US',p['groups'][0]['id'])
 sources.set_topic(s,a,'Capital',True)
 new=[dict(text='Capacity falls short of demand.',topics=['Market'],category='Management',speaker=None,
  location=dict(start=0,end=1,candidate_id='replacement'),publication_date='2025-12-31',date_provenance={})]
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
  location=dict(start=999,end=1000),publication_date=None,date_provenance={})]
 monkeypatch.setattr('stock.rebuild.extract',lambda *args:(new,lambda:None))
 with pytest.raises(IntegrityError,match='manual corrections/splits'):
  rebuild(s,'CRWV.US',str(docs[1]['id']),lambda:None,lambda _:None)
 assert insights.head(s,'CRWV.US')==old_head
 assert s.db.execute('SELECT * FROM source_passages ORDER BY id').fetchall()==before


def test_incremental_budget_resume_then_atomic_publish(library,monkeypatch):
 from stock.sort_budget import Budget,BudgetExceeded
 from stock.sort_process import DeferredCursor
 s,docs,add=library
 for i in range(7):add(f'Demand for customer {i} exceeds capacity.')
 new=[dict(text='Customer demand exceeds capacity.',topics=['Market'],category='Management',speaker=None,
  location=dict(start=0,end=1),publication_date=None,date_provenance={})]
 monkeypatch.setattr(insights,'REQUEST_BUDGET',2500)
 m=Replay(False)
 with Budget(requests=1) as budget:
  budget.use_document(docs[1]['id'])
  with pytest.raises(BudgetExceeded):
   insights.stage(s,'CRWV.US',DeferredCursor(lambda:m),lambda _:None,new_document=(docs[1],new))
 assert not insights.head(s,'CRWV.US') and len(sources.passages(s,'CRWV.US'))==7
 done=s.db.execute('SELECT count(*) FROM source_semantic_cache').fetchone()[0]
 p=insights.stage(s,'CRWV.US',m,lambda _:None,new_document=(docs[1],new))
 assert p['cached_decisions']==done and p['comparison_count']==7
 assert sources.publish(s,docs[1],new,docs[1]['source_sha256'],insight_proposal=p)
 assert len(insights.entries(s,'CRWV.US',document_id=docs[1]['id']))==1


def test_archive_sort_can_reconsider_previously_separate_groups(library):
 s,_,add=library
 add('Demand exceeds capacity.');add('Customer demand exceeds capacity.',1)
 p=insights.stage(s,'CRWV.US',Replay(False),lambda _:None);insights.activate(s,p['id'])
 with s.db:s.db.execute('DELETE FROM source_semantic_cache')
 p=insights.stage(s,'CRWV.US',Replay(),lambda _:None)
 assert len(p['groups'])==1


def test_incremental_reuses_historical_cache_even_without_active_revision(library):
 s,docs,add=library
 a=add('Demand exceeds capacity.');b=add('Customer demand exceeds capacity.')
 staged=insights.stage(s,'CRWV.US',Replay(),lambda _:None)
 assert not insights.head(s,'CRWV.US')  # Completed decisions, interrupted activation.
 new=[dict(text='Another market observation.',topics=['Market'],category='Management',speaker=None,
  location=dict(start=0,end=1),publication_date=None,date_provenance={})]
 m=Replay(False);p=insights.stage(s,'CRWV.US',m,lambda _:None,new_document=(docs[1],new))
 assert any(set(g['members'])=={a,b} for g in p['groups'])
 assert all({q['left']['id'],q['right']['id']}!={a,b} for call in m.calls for q in call['semantic_pairs'])
 assert p['historical_cached_decisions']==1


def test_large_incremental_rebuild_uses_semantic_map_not_cartesian_product(library,monkeypatch):
 s,docs,add=library
 originals=[add(f'Operational update for separate customer {i}.') for i in range(80)]
 new=[dict(text='CoreWeave reported demand for GPUs.',
  topics=['Market'],category='Management',speaker=None,
  location=dict(start=0,end=35),publication_date=None,date_provenance={})]
 from stock import semantic_map
 called=[]
 def fake_candidates(store,rows,incoming,progress):
  called.append((len(rows),len(incoming)))
  new_id=next(iter(incoming))
  return {tuple(sorted((new_id,originals[0])))},dict(
   status='retrieval_only_not_verified_equivalence',scanned=80,proposed=1)
 monkeypatch.setattr(semantic_map,'candidate_pairs',fake_candidates)
 model=Replay(False)
 p=insights.stage(s,'CRWV.US',model,lambda _:None,new_document=(docs[1],new))
 assert called==[(81,1)]
 assert p['semantic_map']['scanned']==80
 assert p['comparison_count']<80  # lexical safety candidates may expand shortlist
 assert len(p['groups'])==81
 assert len(model.calls)>0
