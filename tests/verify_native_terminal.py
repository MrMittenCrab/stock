"""Real PTY capture, not a screenshot/theme simulation.

Run: .venv/bin/python tests/verify_native_terminal.py
Captures stay in ignored .data. Asserts ANSI defaults/no explicit color fills
while Price edits/scrolls, Archive expands, and Sources expands/edits/filters.
"""
import fcntl
import json
import os
from pathlib import Path
import pty
import re
import select
import struct
import subprocess
import sys
import termios
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def child(kind):
 from stock.core import Store
 from stock.archive import documents
 from stock.ui import PriceApp
 from stock.archive_ui import ArchiveApp
 from stock.sources_ui import SourcesApp
 store=Store(ROOT/'.data/native-terminal.sqlite3')
 if kind=='price':
  rows=[dict(timestamp=f'2026-08-{i:02}T00:00:00Z',close=str(100+i)) for i in range(1,22)]
  store.annotate('CRWV.US',rows[-1]['timestamp'],'Native background\n'+'Scrolling original text\n'*80)
  app=PriceApp('CRWV.US',{'currency':'USD'},rows,store,None,False)
 elif kind=='archive': app=ArchiveApp('CRWV.US',store)
 else: app=SourcesApp('CRWV.US',store)
 app.run(mouse=False)


def capture(kind,profile):
 master,slave=pty.openpty()
 fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',30,100,0,0))
 env={**os.environ,'TERM':'xterm-256color','COLORTERM':'truecolor','COLORFGBG':profile}
 env.pop('NO_COLOR',None)
 process=subprocess.Popen([sys.executable,__file__,'--child',kind],stdin=slave,stdout=slave,stderr=slave,cwd=ROOT,env=env)
 os.close(slave)
 result=bytearray();start=time.monotonic();sent=0
 if kind=='price': actions=[b'\x1b[B',b' ',b'\x1b[C',b'\x1b[6~',b'\x1b']
 elif kind=='archive': actions=[b' ',b'\x1b[B',b' ',b'\x1b[6~',b'\x1b']
 else: actions=[b'\x1b[C',b' ',b't',b'\x1b[B',b' ',b't',b'f',b'\x1b']
 while time.monotonic()-start<18:
  elapsed=time.monotonic()-start
  if sent<len(actions) and elapsed>1+sent*.4:
   os.write(master,actions[sent]);sent+=1
  ready,_,_=select.select([master],[],[],.05)
  if ready:
   try: data=os.read(master,65536)
   except OSError: break
   if not data: break
   result.extend(data)
   # Reply as a terminal with native light/dark colors to any OSC queries.
   for selector in (b'10',b'11'):
    if b'\x1b]'+selector+b';?' in data:
     light=profile=='0;15'
     white=(selector==b'11')==light
     rgb=b'ffff/ffff/ffff' if white else b'0000/0000/0000'
     os.write(master,b'\x1b]'+selector+b';rgb:'+rgb+b'\x1b\\')
  if process.poll() is not None: break
 if process.poll() is None: process.terminate()
 process.wait(timeout=5);os.close(master)
 output=bytes(result)
 path=ROOT/'.data'/f'native-{kind}-{profile.replace(";","-")}.ansi';path.write_bytes(output)
 assert b'Traceback' not in output,output[-3000:]
 assert b'STOCK' in output,output[-1000:]
 sgr=re.findall(rb'\x1b\[([0-9;:]*)m',output)
 # Forbid all explicit color assignments. Default 39/49 and reverse 7 survive.
 for code in sgr:
  numbers=[int(x) for x in re.split(rb'[;:]',code) if x]
  assert not any(n in (38,48) or 30<=n<=37 or 40<=n<=47 or 90<=n<=107 for n in numbers),(path,code)
 if kind=='price': assert any(7 in [int(x) for x in code.split(b';') if x] for code in sgr),'Caret/selection reverse video missing'
 if kind=='sources': assert b'[x]' in output and b'[ ]' in output,'Inline checklist was not exercised'
 print(f'{kind} {profile}: {len(output)} terminal bytes, native defaults only')


if __name__=='__main__':
 if len(sys.argv)>1: child(sys.argv[2])
 else:
  from stock.core import Store
  from stock import sources
  from stock.archive import documents
  source=Store()
  target=Store(ROOT/'.data/native-terminal.sqlite3')
  source.db.backup(target.db)
  sources.schema(target)
  fixture=ROOT/'.data/verified-sort-repair-evidence.json'
  if not fixture.exists(): fixture=ROOT/'.data/verified-sort-evidence.json'
  if not fixture.exists(): fixture=ROOT/'.data/real-sort-evidence.json'
  if not fixture.exists(): raise SystemExit('Run tests/verify_sort_real.py first to create a verified real evidence fixture')
  records=json.loads(fixture.read_text())
  for doc in documents(target,'CRWV.US'):
   rows=[p for p in records if p['document_id']==doc['id']]
   if rows: sources.publish(target,doc,rows,doc['source_sha256'])
  source.db.close();target.db.close()
  for profile in ('15;0','0;15'):
   for kind in ('price','archive','sources'): capture(kind,profile)
