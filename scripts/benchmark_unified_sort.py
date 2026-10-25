"""Complete offline Sort replay against identical committed CoreWeave excerpts.
Extraction/source verification are recorded; current semantic models execute locally.
No production database, archive conversion or production publication.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]


def _worker(implementation,directory):
 sys.path.insert(0,str(implementation))
 from stock import archive,sources,insights
 from stock.core import Store
 from stock.sort import Cursor,sort_document
 import stock.sort_process as process
 import stock.sort as sort
 from stock.evidence import extract
 import stock.source_layout as layout
 if hasattr(layout,'selective'):
  def recorded_layout(atoms,doc,store):
   if doc['id']!=13:return []
   page=json.loads((ROOT/'tests/fixtures/sort/document-13-power-layout.json').read_text())
   normalized=layout.normalized
   body=normalized(''.join(b['text'] for b in page['blocks']))
   matched=[a['id'] for a in atoms if len(normalized(a['text']))>=12 and normalized(a['text']) in body]
   return [{**page,'original_sha256':doc['source_sha256'],'matched_source_ids':matched}]
  layout.selective=recorded_layout
 from stock.editorial import validate_publication
 fix=ROOT/'tests/fixtures/sort'
 data=json.loads((fix/'semantic-coreweave.json').read_text())
 directory=Path(directory)
 store=Store(directory/'db');archive.schema(store);sources.schema(store)
 judgments={tuple(r['keys']):{k:v for k,v in r.items() if k!='keys'} for r in data['judgments']}
 keys={c['text']:c['key'] for c in data['claims']}
 docs=[];claims_by_doc={};sent=set();metrics=[]
 for did in sorted({c['document'] for c in data['claims']}):
  meta=json.loads((fix/f'document-{did}.json').read_text())
  path=fix/f'document-{did}.md';sha=hashlib.sha256(path.read_bytes()).hexdigest()
  # Both implementations see identical canonical paths/IDs/hashes; only DBs differ.
  store.db.execute("""INSERT INTO archive_documents(id,ticker,source_sha256,original_filename,source_path,title,type,period,publisher,publication_date,date_evidence,source_metadata,imported_at,conversion_status)
    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(did,'CRWV.US',sha,meta['source'],str(path),meta['source'],meta['type'],'2025' if did in (12,13) else '2026' if did==1 else '2023','CoreWeave',None,'{}','{}',0,'converted'))
  store.db.execute('INSERT INTO archive_files(document_id,role,path,sha256) VALUES(?,?,?,?)',(did,'original',str(path),sha))
  claims_by_doc[did]=[c for c in data['claims'] if c['document']==did]
 store.db.commit();docs=archive.documents(store,'CRWV.US')
 class Recorded(Cursor):
  supports_distillation=True
  def __init__(self):self.current_doc=None;self.record_metrics=None
  def extract(self,u,context):
   if 'semantic_pairs' in u:
    result=[dict(pair=p['id'],**judgments[tuple(sorted([keys[p['left']['text']],keys[p['right']['text']]]))]) for p in u['semantic_pairs']]
    key='judgments'
   elif 'distill' in u:
    result=[dict(ids=[c['id']],topics=['Operations'],reason='Recorded material source support for fixture insight.') for c in u['distill'] if any(int(c['id'].rsplit(':',2)[1])<r['end'] and int(c['id'].rsplit(':',2)[2])>r['start'] for claim in claims_by_doc[self.current_doc] for r in claim['references'])]
    key='insights'
   elif 'review' in u:
    result=[dict(index=i,fidelity='supported',readability='clear',relevance='useful',warnings=[],reason='Hand-recorded supported fixture; exact original references retained.') for i,_ in enumerate(u['review'])]
    key='reviews'
   else:
    result=[];primary=set(u.get('primary_ids',[]))
    for c in claims_by_doc[self.current_doc]:
     if c['key'] in sent:continue
     refs=c['references'];atoms=[a for a in u['candidates'] if not a.get('context_only') and any(a['start']<r['end'] and a['end']>r['start'] for r in refs)]
     if not atoms or not any(a['id'] in primary for a in atoms):continue
     # Each original reference must be covered; never infer missing context.
     if any(not any(a['start']<=r['start'] for a in atoms) or not any(a['end']>=r['end'] for a in atoms) for r in refs):continue
     if hasattr(layout,'selective') and __import__('re').search(r'Q[1-4] 20[0-9]{2}',c['text']):
      atoms=sorted(atoms+[a for a in u['candidates'] if a.get('context_only') and 'Earnings Call' in a['text']],key=lambda a:a['start'])
     speaker=next((a.get('speaker') for a in atoms if a.get('speaker')),None)
     result.append(dict(ids=[a['id'] for a in atoms],representation='source_grounded_statement',text=c['text'],topics=[c['topic']],category='Management',speaker=speaker,ambiguities=[]))
     sent.add(c['key'])
    key='selections'
   def transport(command,**kwargs):
    stage=u.get('operation','review' if 'review' in u else 'reconstruction')
    if stage=='semantic-grouping':
     stage='cross-document grouping' if any(p['left']['document']['id']!=p['right']['document']['id'] for p in u['semantic_pairs']) else 'within-document grouping'
    metrics.append(dict(stage=stage,document=self.current_doc,prompt_chars=len(command[-1]),usage=None))
    return subprocess.CompletedProcess(command,0,json.dumps(dict(type='result',result=json.dumps({key:result}))), '')
   old=process.run;process.run=transport
   try:
    self.command='recorded';return super().extract(u,context)
   finally:process.run=old
 model=Recorded();started=time.perf_counter()
 for doc in docs:
  model.current_doc=doc['id'];sort_document(store,doc,model,lambda _:None)
 # Prior interface requires a separate cross-document semantic stage.
 if not hasattr(insights,'current') or not insights.current(store,'CRWV.US'):
  p=insights.stage(store,'CRWV.US',model,lambda _:None);insights.activate(store,p['id'])
 cold=time.perf_counter()-started;first=len(metrics)
 before=store.db.execute('SELECT * FROM source_passages ORDER BY id').fetchall()
 def cache_counts():
  tables={row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
  return {table:store.db.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in ('source_nli_cache','source_semantic_vectors','source_candidate_scores') if table in tables}
 cached_before_resume=cache_counts()
 started=time.perf_counter()
 for doc in docs:sort_document(store,doc,model,lambda _:None)
 if not hasattr(insights,'current') or not insights.current(store,'CRWV.US'):
  p=insights.stage(store,'CRWV.US',model,lambda _:None)
 resumed=time.perf_counter()-started
 assert cache_counts()==cached_before_resume,'Completed resume changed semantic caches'
 from stock import relationships as local_nli
 local_cost=dict(raw_cached_pairs=cached_before_resume.get('source_nli_cache'),
     nli_execution_seconds=getattr(local_nli._BACKEND,'inference_seconds',None),
     nli_initialization_seconds=getattr(local_nli._BACKEND,'initialization_seconds',None),
     cache_counts=cached_before_resume,resume_added_cache_rows=0)
 ps=sources.passages(store,'CRWV.US')
 for p in ps:validate_publication(p)
 assert before==store.db.execute('SELECT * FROM source_passages ORDER BY id').fetchall()
 assert {p['text'] for p in ps}==set(keys),'A recorded material insight was lost'
 entries=insights.entries(store,'CRWV.US')
 gold={c['text']:c['group'] for c in data['claims']}
 # Recall is measured rather than asserted: conservative local policy can retain
 # extra formulations. Never disguise those misses as cost improvements.
 missed_merges=len(entries)-len(set(gold.values()))
 assert all(len({gold[p['text']] for p in entry['members']})==1 for entry in entries),'Materially distinct propositions merged'
 counts={}
 for m in metrics[:first]:
  v=counts.setdefault(m['stage'],dict(requests=0,prompt_characters=0));v['requests']+=1;v['prompt_characters']+=m['prompt_chars']
 anchors=sorted((p['text'],[(r['text'],r['start'],r['end'],r['markdown_sha256']) for r in p['location']['references']]) for p in ps)
 counts.setdefault('citation recovery',dict(requests=0,prompt_characters=0))
 by_document={str(did):dict(requests=sum(m['document']==did for m in metrics[:first]),prompt_characters=sum(m['prompt_chars'] for m in metrics[:first] if m['document']==did)) for did in claims_by_doc}
 from itertools import combinations
 revision=insights.load(store,insights.head(store,'CRWV.US'))
 edges={tuple(sorted((e['left'],e['right']))):e for e in revision.get('relationships',[])}
 positives=[(a,b) for a,b in combinations(ps,2) if gold[a['text']]==gold[b['text']]]
 pair_trace=[dict(texts=[a['text'],b['text']],retrieved=tuple(sorted((a['id'],b['id']))) in edges,
     relationship=edges.get(tuple(sorted((a['id'],b['id']))),{})) for a,b in positives]
 return dict(local_inference_cost=local_cost,labeled_equivalent_pairs=pair_trace,graph_metrics=revision.get('semantic_map'),missed_merges=missed_merges,cursor_deduplication_requests=sum(m['stage'] in ('within-document grouping','cross-document grouping') for m in metrics[:first]),by_document=by_document,stages=counts,requests=first,prompt_characters=sum(m['prompt_chars'] for m in metrics[:first]),cold_local_seconds=cold,resumed_local_seconds=resumed,resume_requests=len(metrics)-first,evidence=len(ps),insights=len(insights.entries(store,'CRWV.US')),exact_citations=sum(len(p['location']['references']) for p in ps),anchors=anchors,missing_fixture_claims=sorted(set(keys)-{p['text'] for p in ps}),live_latency=None,actual_tokens=None)

def worker(implementation,directory):
 # Tests may invoke the replay in-process; recorded layout must not escape it.
 sys.path.insert(0,str(implementation))
 import stock.source_layout as layout
 original=getattr(layout,'selective',None)
 try:return _worker(implementation,directory)
 finally:
  if original is not None:layout.selective=original


if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--worker');parser.add_argument('--directory');parser.add_argument('--baseline',default='a076578');args=parser.parse_args()
 if args.worker:print(json.dumps(worker(Path(args.worker),args.directory)));sys.exit()
 base=ROOT/'.data';base.mkdir(exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='unified-replay-',dir=base) as temp:
  temp=Path(temp);prior=temp/'baseline';prior.mkdir()
  archive_file=temp/'baseline.tar'
  with archive_file.open('wb') as out:subprocess.run(['git','archive',args.baseline],cwd=ROOT,stdout=out,check=True)
  with tarfile.open(archive_file) as tar:tar.extractall(prior,filter='data')
  # Reuse pretrained artifacts; baseline and current have the same pinned model.
  (prior/'.data').mkdir(exist_ok=True)
  (prior/'.data/embedding-models').symlink_to(ROOT/'.data/embedding-models',target_is_directory=True)
  reports={}
  for name,implementation in [('before',prior),('after',ROOT)]:
   directory=temp/name;directory.mkdir()
   result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',str(implementation),'--directory',str(directory)],capture_output=True,text=True,check=True)
   reports[name]=json.loads(result.stdout)
  after=dict(reports['after']['anchors'])
  assert all(set(map(tuple,refs))<=set(map(tuple,after[text])) for text,refs in reports['before']['anchors']),'Existing exact support lost'
  for report in reports.values():del report['anchors']
  reports.update(baseline=args.baseline,provenance='Hand-recorded fixture decisions replayed through actual prompt transport and publication gates. Local wall times exclude live model service. No production writes.',authenticated_requests=0)
  print(json.dumps(reports,indent=2))
