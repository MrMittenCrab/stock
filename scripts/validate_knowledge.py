"""Isolated validation. Never publishes into the production database.

Default: recorded benchmark. --live-document ID: authenticated extraction only,
using a SQLite backup in a fresh .data directory; prints readable accepted claims.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--live-document',type=int);parser.add_argument('--resume',type=Path);parser.add_argument('--request-seconds',type=float,default=120);args=parser.parse_args()
 if args.live_document is None:
  import subprocess
  return subprocess.call([sys.executable,str(ROOT/'scripts/benchmark_unified_sort.py')])
 from stock.core import Store,DB
 from stock.archive import documents
 from stock.evidence import extract
 from stock.sort import Cursor
 from stock.sort_process import DeferredCursor,Status
 from stock.sort_budget import Budget
 if args.resume:
  directory=args.resume.resolve()
  if directory.parent!=(ROOT/'.data').resolve() or not directory.name.startswith('knowledge-validation-') or not (directory/'copy.sqlite3').is_file():raise ValueError('Resume requires an existing isolated validation directory')
  store=Store(directory/'copy.sqlite3')
 else:
  directory=Path(tempfile.mkdtemp(prefix='knowledge-validation-',dir=ROOT/'.data'))
  source=sqlite3.connect(f'file:{DB}?mode=ro',uri=True)
  store=Store(directory/'copy.sqlite3');source.backup(store.db);source.close()
 docs=[d for d in documents(store,'CRWV.US') if d['id']==args.live_document]
 if len(docs)!=1:raise ValueError('Unknown CoreWeave document ID')
 started=time.monotonic();model=DeferredCursor(Cursor)
 try:
  with Budget(requests=6,document_seconds=720,command_seconds=900,request_seconds=args.request_seconds) as budget:
   budget.use_document(args.live_document)
   with Status() as status:
    passages,verify=extract(store,docs[0],model,status);verify()
  report=dict(document=args.live_document,wall_seconds=time.monotonic()-started,
      passages=passages,metrics=[json.loads(r[0]) for r in store.db.execute('SELECT payload FROM source_model_calls WHERE document_id=? ORDER BY id',(args.live_document,))],publication=False)
  (directory/'result.json').write_text(json.dumps(report,indent=2))
  print(f'{args.live_document} · Verified · {len(passages)} statements · {report["wall_seconds"]:.1f}s')
  for p in passages:print(p['text'])
  print('Report · '+str(directory/'result.json'))
 except Exception as exc:
  (directory/'failure.json').write_text(json.dumps(dict(error=type(exc).__name__,reason=str(exc),wall_seconds=time.monotonic()-started)))
  print(f'Paused · {type(exc).__name__} · {exc}\nRetained · {directory}')
  return 1
 finally:store.db.close()
 return 0

if __name__=='__main__':raise SystemExit(main())
