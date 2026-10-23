"""Isolated validation. Never publishes into the production database.

Default: offline strategic inventory. --live-document ID: authenticated extraction only,
using a SQLite backup in a fresh .data directory; detailed output is opt-in.
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


def summary(document,count,seconds):
 elapsed=int(seconds)
 return f'{document} · Verified · {count} statements · {elapsed//60}:{elapsed%60:02d}'


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--live-document',type=int);parser.add_argument('--resume',type=Path);parser.add_argument('--request-seconds',type=float,default=120);parser.add_argument('--show-statements',action='store_true');args=parser.parse_args()
 if args.live_document is None:
  import subprocess
  command=[sys.executable,str(ROOT/'scripts/evaluate_strategic_commentary.py')]
  if args.show_statements:command.append('--show-statements')
  return subprocess.call(command)
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
 first_call=store.db.execute('SELECT COALESCE(MAX(id),0) FROM source_model_calls').fetchone()[0] if store.db.execute("SELECT 1 FROM sqlite_master WHERE name='source_model_calls'").fetchone() else 0
 started=time.monotonic();model=DeferredCursor(Cursor)
 try:
  with Budget(requests=6,document_seconds=720,command_seconds=900,request_seconds=args.request_seconds) as budget:
   budget.use_document(args.live_document)
   with Status() as status:
    passages,verify=extract(store,docs[0],model,status);verify()
  report=dict(document=args.live_document,wall_seconds=time.monotonic()-started,
      passages=passages,metrics=[json.loads(r[0]) for r in store.db.execute('SELECT payload FROM source_model_calls WHERE document_id=? AND id>? ORDER BY id',(args.live_document,first_call))],publication=False)
  (directory/'result.json').write_text(json.dumps(report,indent=2))
  print(summary(args.live_document,len(passages),report['wall_seconds']))
  if args.show_statements:
   for p in passages:print(p['text'])
  print('Report · '+str((directory/'result.json').relative_to(ROOT)))
 except Exception as exc:
  (directory/'failure.json').write_text(json.dumps(dict(error=type(exc).__name__,reason=str(exc),wall_seconds=time.monotonic()-started)))
  print(f'Paused · {type(exc).__name__} · {exc}\nRetained · {directory}')
  return 1
 finally:store.db.close()
 return 0

if __name__=='__main__':raise SystemExit(main())
