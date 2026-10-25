"""Product contracts for document-level knowledge construction."""
import json
import pytest
from stock.core import Store
from stock.archive import import_document
from stock import evidence, sources

@pytest.fixture
def research(tmp_path,monkeypatch):
 monkeypatch.setattr('stock.archive.ROOT',tmp_path)
 p=tmp_path/'input.md';p.write_text("# Investor Presentation FY'25 Results\n\nRevenue: $5.1B, up 168% YoY.\n\nBacklog: $66.8 billion.\n\nBacklog is subject to delivery and service availability.")
 s=Store(tmp_path/'copy.db');d=import_document(s,'CRWV.US',p)
 return s,d

class Recorded:
 supports_distillation=True
 def __init__(self):self.calls=[];self.interrupt=False
 def extract(self,u,c):
  self.calls.append(u)
  if 'review' in u:
   if self.interrupt:raise KeyboardInterrupt
   return [dict(index=i,fidelity='supported',readability='clear',relevance='useful',warnings=[],reason='All facts, period and qualifications are in selected references.') for i,_ in enumerate(u['review'])]
  assert 'distill' not in u
  cs=u['candidates']
  return [dict(ids=[a['id'] for a in cs if 'Revenue:' in a['text'] or 'FY' in a['text']],representation='source_grounded_statement',text='CoreWeave reported FY2025 revenue of $5.1 billion, up 168% year over year.',topics=['Financials'],category='Management',speaker=None,ambiguities=[])]

def test_document_generation_and_verification_two_calls(research):
 s,d=research;m=Recorded()
 ps,verify=evidence.extract(s,d,m,lambda _:None)
 assert len(ps)==1 and 'FY2025' in ps[0]['text']
 assert len(m.calls)==2 and 'review' in m.calls[1]
 for r in ps[0]['location']['references']:
  assert r['text']==open(d['markdown'] or d['original']).read()[r['start']:r['end']]
 verify();before=len(m.calls)
 assert evidence.extract(s,d,m,lambda _:None)[0]==ps
 assert len(m.calls)==before
 assert s.db.execute('select count(*) from knowledge_propositions').fetchone()[0]==1
 assert s.db.execute('select count(*) from knowledge_supports').fetchone()[0]>=2

def test_interruption_keeps_generation_without_publication(research):
 s,d=research;m=Recorded();m.interrupt=True
 with pytest.raises(KeyboardInterrupt):evidence.extract(s,d,m,lambda _:None)
 assert not sources.completed(s,d['id'])
 m.interrupt=False;ps,_=evidence.extract(s,d,m,lambda _:None)
 assert ps and len([u for u in m.calls if 'review' not in u])==1

def test_legacy_partitions_do_not_control_new_requests(research):
 s,d=research;evidence.schema(s)
 with s.db:
  for i in range(9):s.db.execute('insert into source_work_v3 values(?,?,?,?)',(d['id'],'historical',i,json.dumps({'complete':True})))
 m=Recorded();ps,_=evidence.extract(s,d,m,lambda _:None)
 assert ps and len(m.calls)==2
 assert s.db.execute('select count(*) from source_work_v3').fetchone()[0]==9

def test_rejections_never_open_review_pager(research):
 s,d=research
 class Status:
  def __call__(self,m):pass
  def review(self,m):raise AssertionError('routine review output')
  review_all=review
 class Bad(Recorded):
  def extract(self,u,c):
   out=super().extract(u,c)
   if 'review' not in u:
    out[0]['text']='Revenue was $999 billion.'
   return out
 ps,_=evidence.extract(s,d,Bad(),Status())
 assert not ps

@pytest.mark.parametrize('source,claim,valid',[
 ("FY'25 Revenue: $5.1B, up 168% YoY.",'FY2025 revenue was $5.1 billion, up 168%.',True),
 ('Revenue: $5,100 million.','Revenue was $5.1 billion.',True),
 ('Loss: $(606)M.','Loss was negative $606 million.',True),
 ('Margin: 60%.','Margin was 60 basis points.',False),
 ('Revenue: $5.1B.','Revenue was $51 billion.',False),
 ('Revenue: €5.1B.','Revenue was $5.1 billion.',False),
 ('FY2024 revenue: $5.1B.','FY2025 revenue was $5.1 billion.',False),
 ('Power: 3.1GW.','Power was 3,100 MW.',True),
])
def test_notation(source,claim,valid):
 from stock.quantities import unsupported
 assert (not unsupported(claim,source))==valid


def test_ambiguous_relationship_cannot_pass_without_original_layout(research,monkeypatch):
 s,d=research
 from pathlib import Path
 Path(d['original']).write_text('# Investor Presentation\n\nRevenue EBITDA\n\n$5.1B $3.1B')
 import hashlib
 d['source_sha256']=hashlib.sha256(Path(d['original']).read_bytes()).hexdigest()
 class Confident(Recorded):
  def extract(self,u,c):
   if 'review' in u:return super().extract(u,c)
   return [dict(ids=[a['id'] for a in u['candidates'] if not a.get('context_only')],representation='source_grounded_statement',text='Revenue was $5.1 billion.',topics=['Financials'],category='Management',speaker=None,ambiguities=[])]
 ps,_=evidence.extract(s,d,Confident(),lambda _:None)
 assert not ps


def test_corrupt_artifact_fails_closed(research):
 s,d=research;m=Recorded();evidence.extract(s,d,m,lambda _:None)
 with s.db:s.db.execute("update knowledge_artifacts set payload='[]'")
 with pytest.raises(evidence.IntegrityError):evidence.extract(s,d,m,lambda _:None)


def test_operator_wait_excludes_nested_reading(monkeypatch):
 from stock.sort_budget import Budget,operator_wait
 now=[0.];monkeypatch.setattr('stock.sort_budget.time.monotonic',lambda:now[0])
 with Budget(document_seconds=10,command_seconds=20) as b:
  b.use_document(13)
  with operator_wait():
   now[0]=10
   with operator_wait():now[0]=30
  assert b.remaining()==10


def test_replacement_preserves_retired_publication_and_topics(research):
 s,d=research;m=Recorded();ps,_=evidence.extract(s,d,m,lambda _:None)
 sources.publish(s,d,ps,d['source_sha256']);old=sources.passages(s,'CRWV.US')[0]
 sources.set_topic(s,old['id'],'Capital',True)
 from stock.rebuild import rebuild
 assert rebuild(s,'CRWV.US',str(d['id']),lambda:m,lambda _:None,lambda:True)
 history=json.loads(s.db.execute('select payload from source_publication_history').fetchone()[0])
 assert history['passages'][0][0]==old['id']
 assert [old['id'],'Capital',1] in history['overrides']
 assert 'Capital' in sources.passages(s,'CRWV.US')[0]['topics']


def test_many_failed_claims_use_one_followup_batch(research):
 s,d=research
 class Model(Recorded):
  def extract(self,u,c):
   self.calls.append(u)
   if 'review' in u:
    return [dict(index=i,fidelity='unresolved',readability='clear',relevance='useful',warnings=[],reason='Missing cited period or qualification.') for i,_ in enumerate(u['review'])]
   if u.get('operation')=='resolve-uncertainty':return []
   return [dict(ids=[a['id']],representation='source_grounded_statement',text=a['text'],topics=['Financials'],category='Management',speaker=None,ambiguities=[]) for a in u['candidates'] if not a.get('context_only')]
 m=Model();ps,_=evidence.extract(s,d,m,lambda _:None)
 assert not ps
 assert len(m.calls)==3 and sum(u.get('operation')=='resolve-uncertainty' for u in m.calls)==1


def test_long_source_context_is_bounded_and_exact():
 from stock.knowledge import sections,CONTEXT
 from stock.sort_transport import source_payload
 from stock.insights import packed
 text=''.join(f'## Section {i}\n\n'+('Revenue is contracted with delivery obligations. '*300)+'\n\n' for i in range(20))
 cs=evidence.candidates(text,dict(id=4,type='Filing',original='source',source_sha256='sha'),'hash',True)
 work=sections(cs)
 assert len(work)>1
 assert [a['id'] for batch in work for a in batch]==[a['id'] for a in cs]
 assert all(sum(len(packed(source_payload(a))) for a in batch)<=CONTEXT for batch in work)
 assert all(a['text']==text[a['start']:a['end']] for batch in work for a in batch)

@pytest.mark.parametrize('source,claim',[
 ("Q1'25 revenue was $10 million.",'Q1 2025 revenue was $10 million.'),
 ('Revenue (in millions): $10. We operate 43 data centers.','We operate 43 data centers.'),
 ('Active power was 850 megawatts.','Active power was 850 MW.'),
])
def test_period_and_unit_scope_normalization(source,claim):
 from stock.quantities import unsupported
 assert not unsupported(claim,source)


def test_manual_split_transfers_changed_passage_identity(research):
 from stock import insights
 from stock.rebuild import rebuild
 s,d=research;m=Recorded();ps,_=evidence.extract(s,d,m,lambda _:None)
 sources.publish(s,d,ps,d['source_sha256']);old=sources.passages(s,'CRWV.US')[0]
 # Historical split edge to another supporting passage must never be forgotten.
 insights.schema(s)
 revision=insights.save_revision(s,dict(contract=insights.CONTRACT,ticker='CRWV.US',parent=None,
     groups=[],suppressed_pairs=[[old['id'],'other-member']],snapshot=insights.snapshot(s,'CRWV.US'),fingerprints={}))
 with s.db:s.db.execute('insert into source_insight_heads values(?,?)',('CRWV.US',revision['id']))
 with s.db:s.db.execute('delete from knowledge_artifacts')
 class Changed(Recorded):
  def extract(self,u,c):
   if 'semantic_pairs' in u:return []
   result=super().extract(u,c)
   if 'review' not in u:result[0]['text']='FY2025 revenue was $5.1 billion, up 168% year over year.'
   return result
 approve=[]
 assert rebuild(s,'CRWV.US',str(d['id']),Changed,lambda _:None,lambda:approve.append(True))
 assert not approve
 incoming=sources.passages(s,'CRWV.US')[0]
 active=insights.load(s,insights.head(s,'CRWV.US'))
 assert sorted((incoming['id'],'other-member')) in [list(pair) for pair in active['suppressed_pairs']]
 assert insights.head(s,'CRWV.US')!=revision['id']
 assert s.db.execute('SELECT count(*) FROM source_publication_history').fetchone()[0]==1


def test_complete_document13_fits_one_analysis_request():
 from pathlib import Path
 from stock.knowledge import sections
 text=(Path(__file__).parent/'fixtures/sort/document-13-live.md').read_text()
 cs=evidence.candidates(text,dict(id=13,type='Presentation',original='source.pdf',source_sha256='hash'),'hash',True)
 assert len(sections(cs))==1


def test_topic_corrections_record_reversible_audit(research):
 s,d=research;ps,_=evidence.extract(s,d,Recorded(),lambda _:None)
 sources.publish(s,d,ps,d['source_sha256']);p=sources.passages(s,'CRWV.US')[0]
 sources.set_topic(s,p['id'],'Capital',True)
 sources.set_topic(s,p['id'],'Capital',False)
 rows=s.db.execute('select previous,present from source_correction_events order by id').fetchall()
 assert rows==[(None,1),(1,0)]

@pytest.mark.parametrize('body',[
 'Revenue EBITDA\n$5.1B $3.1B',
 'Revenue EBITDA\n\n$5.1B\n\n$3.1B',
 'Active and contracted energy\n\n850 MWh 900 MWh',
 '| | | Results |\n|---|---|---|\n| Revenue EBITDA | $5.1B | $3.1B |',
])
def test_confident_review_cannot_approve_flattened_relationship(research,body):
 from pathlib import Path
 import hashlib
 s,d=research;Path(d['original']).write_text('# Investor Presentation\n\n'+body)
 d['source_sha256']=hashlib.sha256(Path(d['original']).read_bytes()).hexdigest()
 class Confident(Recorded):
  def extract(self,u,c):
   if 'review' in u:return super().extract(u,c)
   return [dict(ids=[a['id'] for a in u['candidates'] if not a['text'].startswith('#')],representation='source_grounded_statement',text='Revenue was $5.1 billion.' if '$5.1' in body else 'Active energy was 850 MWh.',topics=['Financials'],category='Management',speaker=None,ambiguities=[])]
 ps,_=evidence.extract(s,d,Confident(),lambda _:None)
 assert not ps


def test_selective_layout_fetches_only_matching_page_and_reuses_cache(tmp_path,monkeypatch):
 from stock.source_layout import selective
 import hashlib
 from subprocess import CompletedProcess
 p=tmp_path/'source.pdf';p.write_bytes(b'original PDF fixture')
 d=dict(original=str(p),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
 s=Store(tmp_path/'db');calls=[]
 monkeypatch.setattr('stock.archive.pdf_python',lambda:'fixture-python')
 def run(command,**kwargs):
  calls.append(command)
  value=dict(page=int(command[-1]),width=100,height=100,blocks=[dict(text='Specific revenue label',bbox=[0,0,20,20])]) if command[-1]=='1' else ['Specific revenue label','Unrelated original page']
  return CompletedProcess(command,0,json.dumps(value),'')
 monkeypatch.setattr('stock.sort_process.run',run)
 atoms=[dict(id='exact-source-id',text='Specific revenue label')]
 first=selective(atoms,d,s)
 assert [p['page'] for p in first]==[1]
 assert first[0]['matched_source_ids']==['exact-source-id']
 assert len(calls)==2 and calls[-1][-1]=='1'
 assert selective(atoms,d,s)==first and len(calls)==2

@pytest.mark.parametrize('source',["Q1 FY2025 revenue was $5.1B.",'Revenue in the first quarter of 2025 was $5.1B.'])
def test_explicit_fiscal_and_spelled_quarter_equivalence(source):
 from stock.quantities import unsupported
 assert not unsupported('Q1 2025 revenue was $5.1 billion.',source)


def test_unrelated_layout_page_cannot_authorize_ambiguous_claim(research,monkeypatch):
 from pathlib import Path
 import hashlib
 s,d=research;Path(d['original']).write_text('# Investor Presentation\n\nRevenue EBITDA\n\n$5.1B $3.1B')
 d['source_sha256']=hashlib.sha256(Path(d['original']).read_bytes()).hexdigest()
 monkeypatch.setattr('stock.source_layout.selective',lambda *args:[dict(page=99,original_sha256=d['source_sha256'],matched_source_ids=['unrelated-anchor'],blocks=[])])
 class Confident(Recorded):
  def extract(self,u,c):
   if 'review' in u:return super().extract(u,c)
   return [dict(ids=[a['id'] for a in u['candidates'] if not a.get('context_only')],representation='source_grounded_statement',text='Revenue was $5.1 billion.',topics=['Financials'],category='Management',speaker=None,ambiguities=[])]
 assert evidence.extract(s,d,Confident(),lambda _:None)[0]==[]
