"""Opt-in CoreWeave fixture checks plus ONE authenticated Cursor section extraction.

PYTHONPATH=. .venv/bin/python tests/verify_sort_real.py
Never publishes to the user's database or copies source content into Git.
"""
import hashlib
import json
from pathlib import Path
import tempfile
from stock.core import ROOT, Store
from stock.archive import documents, filehash
from stock.sort import Cursor, units, pdf_pages, validate, public_date
from stock import sources


def main():
 store=Store()
 docs=documents(store,'CRWV.US')
 kinds={d['type'] for d in docs}
 assert {'Annual','Quarterly','Filing','Presentation','Transcript'}<=kinds
 evidence=[]
 for doc in docs:
  assert filehash(doc['original'])==doc['source_sha256']
  pages=pdf_pages(doc['original'])
  assert pages
  if doc['markdown']:
   text=Path(doc['markdown']).read_text(encoding='utf-8-sig')
   work=list(units(text))
   assert ''.join(u['text'] for u in work)==text
   assert all(len(u['text'])<=18000 for u in work)
  else:
   assert doc['conversion_status']=='failed'
   assert any(u['page'] for i,text in enumerate(pages,1) for u in units(text,i))
  evidence.append(dict(document=doc['id'],pages=len(pages),public_date=public_date(doc)[0]))
 print(f'Verified {len(docs)} real CoreWeave archive files, bounded sections, PDF fallback and dates',flush=True)
 doc=next(d for d in docs if d['type']=='Transcript')
 text=Path(doc['markdown']).read_text(encoding='utf-8-sig')
 unit=next(units(text));context='Document title: '+doc['title']+'\nPublisher: '+(doc['publisher'] or 'Unknown')+'\nFront matter (untrusted):\n'+text[:6500]
 cursor=Cursor()
 cache=ROOT/'.data'/('verify-real-section-'+hashlib.sha256((unit['text']+context).encode()).hexdigest()+'.json')
 if cache.exists():
  raw=json.loads(cache.read_text());print('Reusing authenticated extraction fixture',flush=True)
 else:
  print('Extracting one real transcript section with authenticated Cursor',flush=True)
  raw=cursor.extract(unit,context)
  cache.write_text(json.dumps(raw,indent=2))
 assert raw
 pages=pdf_pages(doc['original'])
 rows=[validate(p,unit,context,doc,pages,'converted Markdown',doc['source_sha256']) for p in raw]
 assert any(p['category']=='Management' and p['speaker'] for p in rows)
 for p in rows:
  loc=p['location']
  if loc.get('segments'):
   for part in loc['segments']:
    assert pages[part['page']-1][part['start']:part['end']]==p['text'][part['text_start']:part['text_end']]
  else: assert pages[loc['page']-1][loc['start']:loc['end']]==p['text']
 (ROOT/'.data/verified-sort-evidence.json').write_text(json.dumps([dict(document_id=doc['id'],**p) for p in rows],indent=2))
 print(f'Validated {len(rows)} original passages with exact PDF page anchors and speaker evidence',flush=True)
 # Atomic publication/stability in a disposable database copied via SQLite backup.
 with tempfile.TemporaryDirectory(prefix='verify-sort-',dir=ROOT/'.data') as directory:
  trial=Store(Path(directory)/'stock.sqlite3')
  store.db.backup(trial.db)
  sources.schema(trial)
  assert sources.publish(trial,doc,rows,doc['source_sha256'])
  before=trial.db.execute('SELECT * FROM source_passages').fetchall()
  assert not sources.publish(trial,doc,[],doc['source_sha256'])
  assert before==trial.db.execute('SELECT * FROM source_passages').fetchall()
  for table in ('annotations','archive_documents','archive_files'):
   original=store.db.execute(f'SELECT * FROM {table} ORDER BY 1').fetchall()
   copied=trial.db.execute(f'SELECT * FROM {table} ORDER BY 1').fetchall()
   if table=='archive_documents':
    index=[r[1] for r in trial.db.execute('PRAGMA table_info(archive_documents)')].index('sorted_at')
    copied=[row[:index]+(old[index],)+row[index+1:] for old,row in zip(original,copied)]
   assert original==copied
  trial.db.close()
 store.db.close()
 print('Atomic publication, frozen repeat and preservation verified; user database unchanged')


if __name__=='__main__': main()
