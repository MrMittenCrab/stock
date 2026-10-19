"""Opt-in real CoreWeave regression; operates on a copied database and archive.

Run: .venv/bin/python tests/verify_archive_metadata_real.py
Requires the four originals and metadata JSON in ~/Downloads, plus the existing
local archive and production PDF converter. Does not enrich the live archive.
"""
import sqlite3,shutil,json,builtins
from pathlib import Path
from stock import archive
from stock.core import Store,ROOT
folder=ROOT/'.data/metadata-real-verification'
folder.mkdir(exist_ok=True)
s=Store(folder/'archive.sqlite3')
source=sqlite3.connect(ROOT/'.data/stock.sqlite3');source.backup(s.db);source.close()
archive.schema(s)
old=ROOT/'Research';new=folder/'Research'
if new.exists(): shutil.rmtree(new)
shutil.copytree(old,new)
with s.db:
 for ident,path in s.db.execute('SELECT id,path FROM archive_files').fetchall():
  s.db.execute('UPDATE archive_files SET path=? WHERE id=?',(str(new/Path(path).relative_to(old)),ident))
originals=Path.home()/'Downloads/CoreWeave_Test'
pre={d['id']:(d['source_sha256'],d['conversion_status']) for d in archive.documents(s,'CRWV.US')}
# Existing three PDFs and conversions are copied, including the transcript assets.
presentation=archive.import_document(s,'CRWV.US',originals/'CoreWeave-1Q26-Earnings-Presentation.pdf',root=new,interactive=False)
print('Presentation conversion:',presentation['conversion_status'],presentation['conversion_error'],flush=True)
assert presentation['conversion_status']=='converted'
builtins.input=lambda prompt: (print(prompt+'j',flush=True) or 'j')
metadata=Path.home()/'Downloads/CoreWeave_Archive_Metadata.json'
count=archive.import_metadata(s,'CRWV.US',metadata,interactive=True)
assert 0<=count<=4
print('Enriched:',count,flush=True)
docs=archive.documents(s,'CRWV.US');assert len(docs)==4
for d in docs:
 assert d['source_sha256']==archive.filehash(originals/d['original_filename'])
 assert all(archive.filehash(f['path'])==f['sha256'] for f in d['files'])
 if d['id'] in pre: assert (d['source_sha256'],d['conversion_status'])==pre[d['id']]
 meta=json.loads(d['structured_metadata'])
 if d['type']=='Transcript': assert d['publication_date'] is None and meta['event_date']=='2026-05-07'
 print(d['id'],d['original_filename'],Path(d['original']).name,d['publication_date'],{k:v for k,v in meta.items() if k.endswith('_date')},flush=True)
 assert Path(d['markdown']).is_file()
 text=Path(d['markdown']).read_text()
 for f in d['files']:
  if f['role']=='asset': assert Path(f['path']).parent.name in text or Path(f['path']).parent.parent.name in text
before=s.db.total_changes
assert archive.import_metadata(s,'CRWV.US',metadata,interactive=False)==0
assert before==s.db.total_changes
assert s.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
assert s.db.execute('PRAGMA foreign_key_check').fetchall()==[]
print('PASS: four real originals, existing IDs/hashes/conversions, asset references, date semantics, idempotency, SQLite integrity',flush=True)
