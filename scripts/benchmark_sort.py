#!/usr/bin/env python3
"""Read-only archived-section replay. No authentication, Cursor process, or publication.

Run from the repository: .venv/bin/python scripts/benchmark_sort.py --baseline b3b311d
The baseline is extracted from Git into a temporary directory. Both workers use the
same archived document, exact selections and recorded independent review decisions.
Timings measure local processing only; replay has no model-time speedup meaning.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]


def worker(args):
    sys.path.insert(0,args.implementation)
    from stock.core import Store
    from stock.archive import documents
    from stock import evidence as ev
    from stock.editorial import validate_publication
    from stock.sort import Cursor
    import stock.sort_process as process
    source=sqlite3.connect(Path(args.database).resolve().as_uri()+'?mode=ro',uri=True)
    # documents() only reads an already current archive schema.
    class ReadOnly:db=source
    doc=next(d for d in documents(ReadOnly(),'CRWV.US') if d['id']==13)
    text=Path(doc['markdown']).read_bytes().decode('utf-8-sig')
    digest=hashlib.sha256(Path(doc['markdown']).read_bytes()).hexdigest()
    # Replay only completed, accepted historical evidence. Unresolved evidence
    # is covered separately by focused recovery/gate tests, never rubber-stamped.
    old_key=digest+':v4-editorial-1:'
    states=[json.loads(r[0]) for r in source.execute('SELECT payload FROM source_work_v3 WHERE document_id=13 AND markdown_hash LIKE ? ORDER BY section_index',(old_key+'%',))]
    if len(states)<2 or not all(s['complete'] for s in states[:2]):raise RuntimeError('Two completed archived sections are required')
    source.close()
    originals=ev.candidates(text,doc,digest,include_context=True)
    # Original batches included PDF-match metadata in their budget.
    from stock.source_layout import attach
    pages=attach(originals,doc,lambda _:None)
    legacy=getattr(ev,'legacy_batches',ev.batches)
    old_work=list(legacy(originals))
    primary=[c for b in old_work[:2] for c in b]
    end=originals.index(primary[-1])+5
    available={c['id'] for c in originals[:end]}
    recorded={}
    for state in states[:2]:
        for p in state['accepted']:
            loc=p['location'];refs=loc.get('references',[])
            if refs and {r['source_id'] for r in refs}<=available:
                validate_publication(p)
                recorded[p['text']]=p
    if not recorded:raise RuntimeError('Archived supported selections required')
    original_batches=ev.batches
    if hasattr(ev,'legacy_batches'):
        ev.batches=lambda atoms:list(original_batches([c for c in atoms if c['id'] in {a['id'] for a in primary}]))
    else:
        ev.batches=lambda atoms:[[next(c for c in atoms if c['id']==a['id']) for a in b] for b in old_work[:2]]
    import stock.source_layout as layout
    profile=dict(pdf_parse_seconds=0.,layout_prepare_seconds=0.,normalization_seconds=0.,normalization_calls=0)
    parse=layout.pdf_layout;prepare=layout.attach;normalize=layout.normalized
    def timed_parse(*a,**kw):
        start=time.perf_counter()
        try:return parse(*a,**kw)
        finally:profile['pdf_parse_seconds']+=time.perf_counter()-start
    def timed_prepare(*a,**kw):
        start=time.perf_counter()
        try:return prepare(*a,**kw)
        finally:profile['layout_prepare_seconds']+=time.perf_counter()-start
    def timed_normalize(*a,**kw):
        start=time.perf_counter()
        try:return normalize(*a,**kw)
        finally:
            profile['normalization_seconds']+=time.perf_counter()-start
            profile['normalization_calls']+=1
    layout.pdf_layout=timed_parse;layout.attach=timed_prepare;layout.normalized=timed_normalize
    local_run=process.run
    class Replay:
        def __init__(self):
            self.calls=[];self.cursor=Cursor.__new__(Cursor);self.cursor.command='REPLAY-NO-PROCESS'
        def extract(self,unit,context):
            self.unit=unit
            return self.cursor.extract(unit,context)
        def run(self,command,**kwargs):
            if command[0]!='REPLAY-NO-PROCESS':return local_run(command,**kwargs)
            u=self.unit;start=time.perf_counter()
            if 'review' in u:
                result={'reviews':[{k:v for k,v in recorded[p['text']]['location']['review'].items() if k in ('fidelity','readability','relevance','warnings','reason')} | {'index':i} for i,p in enumerate(u['review'])]}
            else:
                allowed={c['id'] for c in u['candidates']};primary=set(u.get('primary_ids',allowed));chosen=[]
                for p in recorded.values():
                    loc=p['location'];ids=[r['source_id'] for r in loc['references']]
                    if set(ids)<=allowed and ids[0] in primary:
                        chosen.append(dict(ids=ids,representation=loc['representation'],text=None if loc['representation']=='verbatim' else p['text'],topics=p['topics'],category=p['category'],speaker=p['speaker'],ambiguities=[]))
                result={'selections':chosen}
            response=json.dumps(dict(type='result',result=json.dumps(result)))
            self.calls.append(dict(stage='review' if 'review' in u else 'selection',prompt_chars=len(command[-1]),prompt_bytes=len(command[-1].encode()),response_chars=len(response),replay_seconds=time.perf_counter()-start))
            return subprocess.CompletedProcess(command,0,response,'')
    replay=Replay();process.run=replay.run
    with tempfile.TemporaryDirectory(prefix='sort-replay-',dir=ROOT/'.data') as temp:
        store=Store(Path(temp)/'staging.sqlite3')
        runs=[]
        for label in ('cold','resume'):
            for key in profile:profile[key]=0
            offset=len(replay.calls);start=time.perf_counter()
            passages,verify=ev.extract(store,doc,replay,lambda _:None);verify()
            elapsed=time.perf_counter()-start
            for p in passages:validate_publication(p)
            calls=replay.calls[offset:]
            runs.append(dict(**profile,run=label,cursor_calls=len(calls),selection_calls=sum(c['stage']=='selection' for c in calls),review_calls=sum(c['stage']=='review' for c in calls),prompt_chars=sum(c['prompt_chars'] for c in calls),response_chars=sum(c['response_chars'] for c in calls),local_wall_seconds=elapsed,replay_response_seconds=sum(c['replay_seconds'] for c in calls),model_processing_seconds=None,total_live_wall_seconds=None,calls=calls))
        quality=sorted((p['text'],[r['source_id'] for r in p['location']['references']],p['category'],p['speaker']) for p in passages)
        print(json.dumps(dict(runs=runs,quality=quality,accepted=len(passages),source_chars=len(text),primary_spans=len(primary),pdf_pages=len(pages)),ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',default='b3b311d')
    parser.add_argument('--database',default=str(ROOT/'.data/stock.sqlite3'))
    parser.add_argument('--output',default=str(ROOT/'.data/sort-efficiency/benchmark.json'))
    parser.add_argument('--worker',action='store_true');parser.add_argument('--implementation')
    args=parser.parse_args()
    if args.worker:return worker(args)
    with tempfile.TemporaryDirectory(prefix='stock-sort-baseline-',dir=ROOT/'.data') as temp:
        base=Path(temp);archive=base/'baseline.tar'
        subprocess.run(['git','archive','--output',str(archive),args.baseline,'stock'],cwd=ROOT,check=True)
        with tarfile.open(archive) as tar:tar.extractall(base,filter='data')
        results={}
        for name,implementation in [('old',base),('new',ROOT)]:
            run=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker','--implementation',str(implementation),'--database',args.database],capture_output=True,text=True,check=True)
            results[name]=json.loads(run.stdout)
        if results['old']['quality']!=results['new']['quality']:
            raise AssertionError('Replay changed accepted statements, citations or attribution')
        results['baseline_commit']=args.baseline
        results['same_quality']=True
        results['limitations']='No live model calls; local wall time includes real PDF extraction, matching, serialization and SQLite staging. Replay times cannot establish live model or end-to-end speedup. No tokenizer estimate is presented as actual usage.'
        output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(results,indent=2,ensure_ascii=False))
        for name in ('old','new'):
            print(name,results[name]['accepted'],'accepted;',json.dumps(results[name]['runs'],indent=2))
        print('Identical statements and exact citations. Report:',output)

if __name__=='__main__':main()
