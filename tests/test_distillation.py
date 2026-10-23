import pytest
from stock import distillation
from stock.core import Store


def atom(i,text):return dict(id=str(i),text=text,section='Operations',turn=None)

class Model:
 def __init__(self):self.calls=[]
 def extract(self,u,c):
  self.calls.append(u)
  return [dict(ids=[x['id']],topics=['Operations'],reason='Specific material fact with incremental capacity information.') for x in u['distill'] if 'Thank you' not in x['text']]


def test_source_id_plan_empty_short_kpi_and_cached_resume(tmp_path):
 s=Store(tmp_path/'db');m=Model()
 atoms=[atom(0,'Thank you for attending.'),atom(1,'Active Data Centers: 43 as of December 31, 2025.')]
 result=distillation.plan(s,{'id':13,'title':'CoreWeave'},atoms,m,lambda _:None)
 assert result=={'1'} and len(m.calls)==1
 assert distillation.plan(s,{'id':13,'title':'CoreWeave'},atoms,m,lambda _:None)==result
 assert len(m.calls)==1
 assert not distillation.plan(s,{'id':13},atoms[:1],m,lambda _:None)


def test_plan_rejects_unknown_ids_and_never_silently_truncates(tmp_path):
 s=Store(tmp_path/'db')
 class Bad:
  def extract(self,u,c):return [dict(ids=['unknown'],topics=[],reason='material')]
 with pytest.raises(ValueError):distillation.plan(s,{'id':1},[atom(0,'Active power: 850MW+.')],Bad(),lambda _:None)
 # Large selections retain all material candidates, without a second selection quota.
 m=Model();atoms=[atom(i,f'Data center {i} has separately contracted power.') for i in range(220)]
 result=distillation.plan(s,{'id':1},atoms,m,lambda _:None)
 assert len(result)==220
 assert not any(u.get('selection_assessment') for u in m.calls)


def test_fresh_sort_distills_before_reconstruction_and_freezes(tmp_path,monkeypatch):
 from stock.archive import import_document
 from stock.sort import sort_document
 from stock import sources
 import json
 monkeypatch.setattr('stock.archive.ROOT',tmp_path)
 path=tmp_path/'source.md';path.write_text('# Investor Presentation\n\nActive power: 850MW.\n\nThank you for attending.')
 s=Store(tmp_path/'db');doc=import_document(s,'CRWV.US',path)
 class Full(Model):
  supports_distillation=True
  def extract(self,u,c):
   if 'distill' in u:return super().extract(u,c)
   self.calls.append(u)
   if 'review' in u:
    return [dict(index=i,fidelity='supported',readability='clear',relevance='useful',warnings=[],reason='Exact active power label and value.') for i,_ in enumerate(u['review'])]
   cs=[x for x in u['candidates'] if 'Active power:' in x['text']]
   return [dict(ids=[x['id']],representation='source_grounded_statement',text='CoreWeave reported active power of 850MW.',topics=['Operations'],category='Management',speaker=None,ambiguities=[]) for x in cs]
 m=Full();assert sort_document(s,doc,m,lambda _:None)==1
 assert len([u for u in m.calls if 'distill' in u])==1
 assert len(sources.passages(s,'CRWV.US'))==1
 states=[json.loads(r[0]) for r in s.db.execute('SELECT payload FROM source_work_v3')]
 assert all(state['document_plan'] for state in states)
 calls=len(m.calls);assert sort_document(s,doc,m,lambda _:None) is None
 assert len(m.calls)==calls

@pytest.mark.parametrize('operation,key', [('distill','insights'),('semantic_pairs','judgments')])
def test_cursor_new_protocols_keep_readonly_transport(monkeypatch,operation,key):
 from unittest.mock import Mock
 from stock.sort import Cursor
 import json
 captured=[]
 def run(cmd,**kwargs):
  captured.append(cmd[-1]);return Mock(returncode=0,stderr='',stdout=json.dumps(dict(type='result',result=json.dumps({key:[]}))))
 monkeypatch.setattr('stock.sort_process.run',run)
 cursor=Cursor.__new__(Cursor);cursor.command='agent'
 assert cursor.extract(dict(candidates=[],text='',**{operation:[]}),'{}')==[]
 assert 'UNTRUSTED DATA' in captured[0]
 assert cursor.metrics[-1]['outcome']=='ok'


def test_cross_batch_duplicate_ownership_keeps_at_least_one(tmp_path,monkeypatch):
 import json
 monkeypatch.setattr(distillation,'selection_batches',lambda xs:([x] for x in xs))
 s=Store(tmp_path/'db')
 class Symmetric:
  def extract(self,u,c):
   # A recorded failure mode: omit a primary when another equivalent span is
   # offered as context. Only already retained representatives may be offered.
   if u['selection_assessment'] and json.loads(c)['document_shortlist_context']:return []
   return [dict(ids=[u['distill'][0]['id']],topics=['Market'],reason='Material capacity constraint.')]
 result=distillation.plan(s,{'id':13},[atom(0,'Demand exceeds capacity.'),atom(1,'Customer demand outpaces capacity.')],Symmetric(),lambda _:None)
 assert result=={'0','1'}
