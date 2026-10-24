import subprocess
import sys
import time
import pytest
from stock.sort_budget import Budget,BudgetExceeded
from stock.sort_process import DeferredCursor,run,Status


def test_defaults_and_invalid_values():
 with Budget() as b:
  assert b.document_seconds==720 and b.requests==12 and b.request_seconds==120
  assert 1199<b.remaining()<=1200
 for kwargs in [dict(requests=0),dict(command_seconds=-1),dict(document_seconds=0),dict(request_seconds=0)]:
  with pytest.raises(ValueError):Budget(**kwargs)


def test_document_and_command_deadlines_never_restart(monkeypatch):
 now=[0.];monkeypatch.setattr('stock.sort_budget.time.monotonic',lambda:now[0])
 with Budget(document_seconds=10,command_seconds=15) as b:
  b.use_document(13);now[0]=5;b.use_document(14)
  assert b.remaining()==10
  b.use_document(13);assert b.remaining()==5
  now[0]=10
  with pytest.raises(BudgetExceeded):b.check()
  b.use_document(14);now[0]=15
  with pytest.raises(BudgetExceeded):b.check()


def test_request_retries_share_deadline_and_count(monkeypatch):
 now=[0.];monkeypatch.setattr('stock.sort_budget.time.monotonic',lambda:now[0])
 with Budget(request_seconds=4,requests=3) as b:
  b.use_document(13);b.request('same');now[0]=3
  b.request('same');assert b.timeout(120)==1
  now[0]=4
  with pytest.raises(BudgetExceeded,match='Request timeout'):b.request('same')
  with pytest.raises(BudgetExceeded,match='Request limit'):b.request('different')


def test_child_timeout_cancels_process_group():
 import stock.sort_process as process
 started=time.monotonic()
 with Budget(command_seconds=.2,document_seconds=.2) as b:
  b.use_document(13)
  with pytest.raises(BudgetExceeded):
   run([sys.executable,'-c','import time; time.sleep(30)'],text=True,timeout=120)
 assert time.monotonic()-started<4
 assert process.ACTIVE_PROCESS is None


def test_status_is_silent_outside_review_and_logs(tmp_path,monkeypatch,capsys):
 monkeypatch.setattr('stock.core.ROOT',tmp_path)
 with Status() as status:
  status('13 · CoreWeave · section 2/4 · semantic review')
  status('Verbose diagnostic retained only in log')
  assert capsys.readouterr().out==''
  status.review('CRWV.US · Done · 12 insights · 18 sources · 07:16')
 assert 'Verbose diagnostic' in status.log_path.read_text()
 assert capsys.readouterr().out=='CRWV.US · Done · 12 insights · 18 sources · 07:16\n'


def test_cancelled_review_keeps_selection_and_resumes_without_repeating(tmp_path,monkeypatch):
 from stock.core import Store
 from stock.archive import import_document
 from stock.sort import sort_stock
 from stock import sources,insights
 monkeypatch.setattr('stock.archive.ROOT',tmp_path)
 p=tmp_path/'source.md';p.write_text('# Investor Presentation\n\nActive power: 850MW.')
 store=Store(tmp_path/'db');doc=import_document(store,'CRWV.US',p)
 class Recorded:
  supports_distillation=True
  def __init__(self):self.calls=[]
  def extract(self,u,context):
   if 'distill' in u:
    self.calls.append('distill')
    return [dict(ids=[c['id']],topics=['Operations'],reason='Material power metric.') for c in u['distill'] if 'Active power:' in c['text']]
   if 'review' in u:
    self.calls.append('review')
    return [dict(index=i,fidelity='supported',readability='clear',relevance='useful',warnings=[],reason='Exact power and unit.') for i,_ in enumerate(u['review'])]
   self.calls.append('reconstruct')
   return [dict(ids=[c['id']],representation='source_grounded_statement',text='CoreWeave reported active power of 850MW.',topics=['Operations'],category='Management',speaker=None,ambiguities=[]) for c in u['candidates'] if 'Active power:' in c['text']]
 model=Recorded()
 class Factory:
  supports_distillation=True
  def __new__(cls):return model
 monkeypatch.setattr('stock.sort.Cursor',Factory)
 with Budget(requests=1):
  with pytest.raises(BudgetExceeded,match='Request limit'):sort_stock(store,'CRWV.US',lambda _:None)
 assert not sources.completed(store,doc['id']) and not sources.passages(store,'CRWV.US')
 assert model.calls==['reconstruct']
 assert store.db.execute('SELECT count(*) FROM knowledge_artifacts').fetchone()[0]>0
 with Budget():assert sort_stock(store,'CRWV.US',lambda _:None)
 assert model.calls==['reconstruct','review'] and insights.current(store,'CRWV.US')
 count=store.db.execute('SELECT count(*) FROM source_insight_revisions').fetchone()[0]
 with Budget():assert sort_stock(store,'CRWV.US',lambda _:None)
 assert model.calls==['reconstruct','review']
 assert store.db.execute('SELECT count(*) FROM source_insight_revisions').fetchone()[0]==count


def test_pdf_interpreter_probe_uses_remaining_deadline(tmp_path,monkeypatch):
 from stock.archive import pdf_python
 # A disposable executable stalls during the import probe itself.
 probe=tmp_path/'python-probe'
 probe.write_text('#!'+sys.executable+'\nimport time\ntime.sleep(30)\n');probe.chmod(0o755)
 monkeypatch.setenv('STOCK_PDF_PYTHON',str(probe))
 started=time.monotonic()
 with Budget(command_seconds=.2):
  with pytest.raises(BudgetExceeded):pdf_python()
 assert time.monotonic()-started<4


def test_review_only_combines_pending_documents_without_publication(tmp_path,monkeypatch):
 from stock import sources,insights
 from stock.archive import import_document
 from stock.core import Store
 from stock.sort import sort_stock
 monkeypatch.setattr('stock.archive.ROOT',tmp_path)
 s=Store(tmp_path/'db');docs=[]
 for i in range(2):
  path=tmp_path/f'source{i}.md';path.write_text(f'# Investor Presentation {i}\n\nDemand exceeds capacity.')
  docs.append(import_document(s,'CRWV.US',path))
 class Model:
  supports_distillation=True
  def extract(self,u,c):
   if 'distill' in u:return [dict(ids=[a['id']],topics=['Market'],reason='Material capacity constraint.') for a in u['distill'] if 'Demand' in a['text']]
   if 'review' in u:return [dict(index=i,fidelity='supported',readability='clear',relevance='useful',warnings=[],reason='Exact demand and capacity.') for i,_ in enumerate(u['review'])]
   if 'semantic_pairs' in u:
    return [dict(pair=p['id'],equivalent=True,relation='repeated_assertion',dimensions_agree=True,information_preserved=True,reason='Identical period and scope in fixture.',differences=[]) for p in u['semantic_pairs']]
   return [dict(ids=[a['id']],representation='source_grounded_statement',text=a['text'],topics=['Market'],category='Management',speaker=None,ambiguities=[]) for a in u['candidates'] if 'Demand' in a['text']]
 monkeypatch.setattr('stock.sort.Cursor',Model)
 output=[]
 with Budget():assert sort_stock(s,'CRWV.US',output.append,review_only=True)
 assert any('Existing 2 passages · Proposed 1 distinct insights' in line for line in output)
 assert not sources.passages(s,'CRWV.US') and not insights.head(s,'CRWV.US')
 assert all(not sources.completed(s,d['id']) for d in docs)
 row=s.db.execute('SELECT id FROM source_insight_revisions').fetchone()
 with pytest.raises(ValueError,match='Preview'):insights.activate(s,row[0])


@pytest.mark.parametrize('review_only',[False,True])
def test_cli_explicit_rebuild_is_unattended(tmp_path,monkeypatch,review_only):
 from stock.cli import main
 from stock.core import Store
 seen=[]
 monkeypatch.setattr('stock.cli.Store',lambda:Store(tmp_path/'db'))
 monkeypatch.setattr('stock.core.ROOT',tmp_path)
 monkeypatch.setattr(sys,'argv',['stock','sort','CRWV.US','--rebuild','13']+(['--review-only'] if review_only else []))
 def forbidden(*args):raise AssertionError('No interactive input')
 monkeypatch.setattr('builtins.input',forbidden)
 def rebuild(store,ticker,reference,factory,progress,**kw):
  seen.append(kw['review_only']);return True
 monkeypatch.setattr('stock.rebuild.rebuild',rebuild)
 assert main()==0
 assert seen==[review_only]
