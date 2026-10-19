"""Local document recognition and hash-addressed archive registration."""
import hashlib
import json
import os
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path

from .core import ROOT, symbol

TYPES = ('Annual', 'Interim', 'Quarterly', 'Earnings', 'Filing', 'Release',
         'Presentation', 'Transcript', 'Letter', 'Research', 'Article', 'Other')


def schema(store):
    if store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='archive_imports'").fetchone():
        return
    store.db.executescript('''
    CREATE TABLE IF NOT EXISTS archive_documents (
      id INTEGER PRIMARY KEY, ticker TEXT NOT NULL, source_sha256 TEXT NOT NULL,
      original_filename TEXT NOT NULL, source_path TEXT NOT NULL,
      title TEXT NOT NULL, type TEXT NOT NULL, period TEXT, publisher TEXT,
      publication_date TEXT, date_evidence TEXT NOT NULL, source_metadata TEXT NOT NULL,
      imported_at REAL NOT NULL, sorted_at REAL,
      conversion_status TEXT NOT NULL, conversion_error TEXT, converter TEXT,
      UNIQUE(ticker, source_sha256));
    CREATE TABLE IF NOT EXISTS archive_files (
      id INTEGER PRIMARY KEY, document_id INTEGER NOT NULL REFERENCES archive_documents(id),
      role TEXT NOT NULL, path TEXT NOT NULL UNIQUE, sha256 TEXT NOT NULL,
      UNIQUE(document_id, role, path));
    CREATE TABLE IF NOT EXISTS archive_imports (
      document_id INTEGER NOT NULL REFERENCES archive_documents(id),
      source_path TEXT NOT NULL, original_filename TEXT NOT NULL, imported_at REAL NOT NULL,
      UNIQUE(document_id, source_path, original_filename));
    ''')


def filehash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def documents(store, ticker):
    schema(store)
    cursor=store.db.execute('SELECT * FROM archive_documents WHERE ticker=? ORDER BY publication_date IS NULL, publication_date, id', (symbol(ticker),))
    result=[]
    for row in cursor.fetchall():
        doc=dict(zip([col[0] for col in cursor.description],row))
        doc['files']=[dict(role=r[0],path=r[1],sha256=r[2]) for r in store.db.execute(
            'SELECT role,path,sha256 FROM archive_files WHERE document_id=? ORDER BY id',(doc['id'],))]
        doc['original']=next((f['path'] for f in doc['files'] if f['role']=='original'),None)
        doc['markdown']=next((f['path'] for f in doc['files'] if f['role']=='markdown'),None)
        if doc['original'] and Path(doc['original']).suffix.lower()=='.md':
            doc['markdown']=doc['original']
        result.append(doc)
    return result


# PDF engines live in local converter environments; do not install another engine.
def pdf_python():
    candidates=[os.environ.get('STOCK_PDF_PYTHON'),sys.executable,shutil.which('python3')]
    executable=shutil.which('pymupdf')
    if executable:
        with open(executable) as stream:
            first=stream.readline().strip()
        if first.startswith('#!'):
            candidates.append(first[2:])
    for candidate in dict.fromkeys(c for c in candidates if c):
        try:
            if subprocess.run([candidate,'-c','import pymupdf'],capture_output=True,timeout=15).returncode==0:
                return candidate
        except (OSError,subprocess.SubprocessError):
            continue
    raise ValueError('PDF reading requires local PyMuPDF; set STOCK_PDF_PYTHON to its Python interpreter')


def read_document(path):
    path=Path(path)
    if path.suffix.lower()=='.pdf':
        script='''import json,sys,pymupdf
with pymupdf.open(sys.argv[1]) as doc:
 print(json.dumps({"text":"\\n".join(page.get_text(sort=True) for page in doc),"metadata":doc.metadata}))
'''
        run=subprocess.run([pdf_python(),'-c',script,str(path)],capture_output=True,text=True,timeout=120)
        if run.returncode:
            raise ValueError('Cannot read PDF content (invalid, encrypted, or damaged PDF)')
        data=json.loads(run.stdout)
        return data['text'],data['metadata'] or {}
    if path.suffix.lower() not in ('.md','.txt'):
        raise ValueError('Supported archive files: PDF, Markdown (.md), and text (.txt)')
    return path.read_text(encoding='utf-8-sig'),{}


def parse_date(value):
    value=re.sub(r'(\d)(?:st|nd|rd|th)\b',r'\1',value.strip(),flags=re.I)
    value=re.sub(r'\s+',' ',value)
    for fmt in ('%Y-%m-%d','%Y/%m/%d','%d %B %Y','%d %b %Y','%B %d, %Y','%b %d, %Y','%B %d %Y','%b %d %Y','%Y年%m月%d日'):
        try: return datetime.strptime(value,fmt).date().isoformat()
        except ValueError: pass
    return None


DATE_PATTERN=r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4}\b|\b[A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b|\d{4}年\d{1,2}月\d{1,2}日'


def identify(text, metadata):
    lines=[re.sub(r'^\s*#+\s*','',line).strip() for line in text.splitlines() if line.strip()]
    title=str(metadata.get('title') or '').strip() or (lines[0] if lines else 'Untitled')
    # Restrict type recognition to front matter/headings; a report's appendix or
    # references to prior reports must not determine its primary type.
    head='\n'.join(([title] if metadata.get('title') else [])+lines[:30])
    head=re.sub(r'(?i)(annual|interim|quarterly)\s*\n\s*(report|results)',r'\1 \2',head)
    rules=[('Transcript',r'\b(?:earnings |conference |results )?call transcript\b|\btranscript\b'),
           ('Letter',r'\bletter to (?:shareholders|investors)\b'),
           ('Research',r'\b(?:equity research|research report|research note)\b'),
           ('Annual',r'\bannual (?:report|results)\b|\bform\s+(?:10-k|20-f|40-f)\b|年報|年度報告'),
           ('Interim',r'\b(?:interim|half[- ]year) (?:report|results)\b|\bform\s+6-k\b(?=.*interim)|中期報告'),
           ('Quarterly',r'\bquarterly (?:report|results)\b|\bform\s+10-q\b|季度報告'),
           ('Presentation',r'\b(?:investor|results|earnings|corporate) presentation\b'),
           ('Earnings',r'\bearnings (?:release|results|announcement)\b'),
           ('Filing',r'\bform\s+(?:8-k|6-k|20-f|40-f|s-1|f-1|13f)\b|\bregulatory filing\b'),
           ('Release',r'\b(?:press|news) release\b'),('Article',r'\b(?:article|opinion|byline)\s*:')]
    matches=[(match.start(),index,kind) for index,(kind,pattern) in enumerate(rules)
             if (match:=re.search(pattern,head,re.I|re.S))]
    kind=min(matches)[2] if matches else None
    period=None
    match=re.search(r'\b(Q[1-4]|H[12]|FY)\s*[- ]?\s*(20\d{2})\b',head,re.I)
    if match: period=match[1].upper()+('-' if match[1].upper()!='FY' else '')+match[2]
    if period is None:
        reverse=re.search(r'\b(20\d{2})\s*[- ]?\s*(Q[1-4]|H[12])\b',head,re.I)
        if reverse: period=reverse[2].upper()+'-'+reverse[1]
    if period is None:
        # Only reporting-end dates, not publication dates, define a period.
        end=re.search(r'(?:year|months?|quarter|period)\s+ended\s+('+DATE_PATTERN+')',head,re.I)
        ending=parse_date(end[1]) if end else None
        if ending:
            year,month,_=map(int,ending.split('-'))
            if kind=='Annual': period=f'FY{year}'
        if not period and kind in ('Annual','Interim'):
            year_match=re.search(r'(?:annual|interim|half[- ]year) (?:report|results)\s*\n?\s*(20\d{2})|(20\d{2})\s*(?:annual|interim|half[- ]year) (?:report|results)',head,re.I)
            if year_match and kind=='Annual': period='FY'+next(g for g in year_match.groups() if g)
    evidence=[]
    for line in lines:
        # Explicit publication labels only. Creation/modification dates are not evidence.
        label=re.match(r'^(?:originally |first )?(?:published|publication date|issued|released|date of (?:publication|release))\s*(?:on\s+|[:：]\s*|\s+)(.+)$',line,re.I)
        if label:
            match=re.match('('+DATE_PATTERN+')',label[1])
            value=parse_date(match[0]) if match else None
            if value: evidence.append(dict(date=value,source='document text',quote=line))
    for key in ('publication_date','published','datePublished'):
        if metadata.get(key) and (value:=parse_date(str(metadata[key]))):
            evidence.append(dict(date=value,source='metadata',key=key,quote=str(metadata[key])))
    publisher=metadata.get('publisher') or None
    for line in lines[:30]:
        explicit=re.match(r'publisher\s*:\s*(.+)',line,re.I)
        if explicit: publisher=explicit[1];break
    if not publisher and lines and re.fullmatch(r'.+\b(?:Limited|Ltd\.?|Inc\.?|Corporation|Corp\.?)',lines[0],re.I):
        publisher=lines[0]
    # Prefer a report heading to a company name as its exact title.
    if not metadata.get('title'):
        heading=next((line for line in lines[:15] if re.search(r'(?:annual|interim|quarterly) (?:report|results)',line,re.I)),None)
        title=heading or title
    return dict(title=title,type=kind,period=period,publisher=publisher,
                date=min((e['date'] for e in evidence),default=None),date_evidence=evidence)


def clarify(info,interactive=None,read=input,output=None):
    if info['type']: return
    if interactive is None: interactive=sys.stdin.isatty()
    if not interactive:
        raise ValueError('Document type is uncertain; rerun in an interactive terminal to choose its type')
    output=output or sys.stdout
    options=('Annual','Interim','Quarterly','Other')
    while not info['type']:
        print('Type?  '+' · '.join(f'{i} {v}' for i,v in enumerate(options,1)),file=output,flush=True)
        try: answer=read('> ').strip()
        except EOFError as exc: raise ValueError('Classification cancelled; rerun in an interactive terminal') from exc
        picked=options[int(answer)-1] if answer.isdigit() and 1<=int(answer)<=len(options) else next((k for k in TYPES if k.lower()==answer.lower()),None)
        if picked=='Other' and options!=TYPES:
            options=TYPES
        elif picked:
            info['type']=picked


def sanitize(value):
    value=unicodedata.normalize('NFKC',value)
    value=re.sub(r'[^\w.-]+','-',value,flags=re.UNICODE).strip(' .-_')
    value=value[:90]
    while len(value.encode('utf-8'))>160: value=value[:-1]
    return value.rstrip('.-') or 'Untitled'


def basename(info):
    return f"{info['date'] or 'undated'}--{info['type'].lower()}--{sanitize(info['period'] or info['title'])}"


def run_converter(command, *, timeout):
    """Keep converter descendants from surviving cancellation or a timeout."""
    process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,text=True,start_new_session=True)
    try:
        stdout,stderr=process.communicate(timeout=timeout)
        return subprocess.CompletedProcess(command,process.returncode,stdout,stderr)
    except BaseException:
        try: os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError: pass
        process.communicate()
        raise


def convert_pdf(source, destination):
    """Reuse pdfmd (Marker), then optional local pymupdf4llm. Never call an LLM."""
    errors=[]
    converter=shutil.which('pdfmd')
    if converter:
        with tempfile.TemporaryDirectory(prefix='stock-pdfmd-') as folder:
            bundle=Path(folder)/'converted.zip'
            try:
                run=run_converter([converter,str(source),'--zip-output',str(bundle)],timeout=600)
                if run.returncode: raise ValueError('pdfmd failed; check the local Marker installation')
                with zipfile.ZipFile(bundle) as zipped:
                    members=[m for m in zipped.infolist() if not m.is_dir()]
                    markdown=[m for m in members if m.filename.lower().endswith('.md')]
                    if len(markdown)!=1: raise ValueError('pdfmd must produce one Markdown document')
                    # All assets retain their relative locations under one per-document
                    # directory; the root Markdown references them there.
                    asset_dir=destination.parent/(destination.stem+'.assets')
                    if asset_dir.exists(): raise ValueError('Conversion assets already exist; no files overwritten')
                    body=zipped.read(markdown[0]).decode('utf-8')
                    base=Path(markdown[0].filename).parent
                    assets=[]
                    for member in members:
                        path=Path(member.filename)
                        if path.is_absolute() or '..' in path.parts: raise ValueError('Unsafe converter output path')
                        if member==markdown[0] or path.suffix.lower()=='.json': continue
                        try: relative=path.relative_to(base)
                        except ValueError: continue
                        assets.append((relative,zipped.read(member)))
                    if not body.strip(): raise ValueError('Converter produced empty Markdown')
                    if assets:
                        asset_dir.mkdir()
                        for relative,data in assets:
                            target=asset_dir/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
                            body=body.replace(str(relative),asset_dir.name+'/'+str(relative))
                    destination.write_text(body,encoding='utf-8')
                    return 'pdfmd / Marker'
            except (OSError,ValueError,subprocess.SubprocessError,zipfile.BadZipFile) as exc:
                errors.append(str(exc))
    try:
        engine=pdf_python()
        run=run_converter([engine,'-c','import pymupdf4llm,sys; print(pymupdf4llm.to_markdown(sys.argv[1],show_progress=False))',str(source)],timeout=300)
        if run.returncode==0 and run.stdout.strip():
            destination.write_text(run.stdout,encoding='utf-8');return 'pymupdf4llm'
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        errors.append(str(exc))
    raise ValueError('PDF conversion unavailable; configure pdfmd/Marker or local pymupdf4llm'+ (' ('+'; '.join(errors)+')' if errors else ''))


def import_document(store,ticker,source,*,root=None,interactive=None):
    ticker=symbol(ticker);source=Path(source).expanduser().resolve(strict=True)
    if not source.is_file(): raise ValueError('Import source must be a file')
    schema(store)
    digest=filehash(source)
    existing=next((d for d in documents(store,ticker) if d['source_sha256']==digest),None)
    if existing:
        with store.db:
            store.db.execute('INSERT OR IGNORE INTO archive_imports VALUES(?,?,?,?)',(existing['id'],str(source),source.name,time.time()))
        doc=existing
    else:
        text,metadata=read_document(source)
        info=identify(text,metadata);clarify(info,interactive)
        folder=Path(root or ROOT/'Research')/ticker/'Archive';folder.mkdir(parents=True,exist_ok=True)
        extension=source.suffix.lower();stem=basename(info)
        target=folder/(stem+extension)
        created=False
        # Serialize identity checks and exclusive allocation across concurrent imports.
        store.db.execute('BEGIN IMMEDIATE')
        try:
            existing=next((d for d in documents(store,ticker) if d['source_sha256']==digest),None)
            if existing:
                store.db.rollback()
                return import_document(store,ticker,source,root=root,interactive=interactive)
            suffix=0
            while True:
                candidate=stem if suffix==0 else stem+'--'+digest[:min(64,8+suffix-1)]
                target=folder/(candidate+extension)
                # Reserve the shared PDF/MD stem even when only one exists.
                if any(folder.glob(candidate+'.*')):
                    suffix+=1
                    if suffix>58: raise ValueError('Cannot allocate an archive filename without overwriting files')
                    continue
                try:
                    with target.open('xb') as output:
                        created=True
                        with source.open('rb') as original:
                            shutil.copyfileobj(original,output)
                    break
                except FileExistsError: suffix+=1
            if filehash(target)!=digest: raise ValueError('Source changed during import; retry')
            cursor=store.db.execute('''INSERT INTO archive_documents
                (ticker,source_sha256,original_filename,source_path,title,type,period,publisher,
                 publication_date,date_evidence,source_metadata,imported_at,conversion_status)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (ticker,digest,source.name,str(source),info['title'],info['type'],info['period'],info['publisher'],info['date'],json.dumps(info['date_evidence']),json.dumps(metadata),time.time(),'pending' if extension=='.pdf' else 'native' if extension=='.md' else 'not-applicable'))
            ident=cursor.lastrowid
            store.db.execute('INSERT INTO archive_files(document_id,role,path,sha256) VALUES(?,?,?,?)',(ident,'original',str(target),digest))
            store.db.execute('INSERT INTO archive_imports VALUES(?,?,?,?)',(ident,str(source),source.name,time.time()))
            store.db.commit()
        except BaseException:
            store.db.rollback()
            if created: target.unlink(missing_ok=True)
            raise
        doc=next(d for d in documents(store,ticker) if d['id']==ident)
    if Path(doc['original']).suffix.lower()=='.pdf' and doc['conversion_status']!='converted':
        _convert_registered(store,doc)
    return next(d for d in documents(store,ticker) if d['id']==doc['id'])


def _convert_registered(store,doc):
    original=Path(doc['original']);destination=original.with_suffix('.md')
    created=[]
    try:
        if not original.is_file() or filehash(original)!=doc['source_sha256']:
            raise ValueError('Archived original is missing or changed; restore it before retrying conversion')
        # Expensive conversion stays outside a database transaction. Concurrent
        # conversions stage independently; only one may publish the result.
        with tempfile.TemporaryDirectory(prefix='.stock-convert-',dir=original.parent) as folder:
            staged=Path(folder)/destination.name
            converter=convert_pdf(original,staged)
            if not staged.is_file() or not staged.stat().st_size: raise ValueError('Converter produced no Markdown')
            store.db.execute('BEGIN IMMEDIATE')
            status=store.db.execute('SELECT conversion_status FROM archive_documents WHERE id=?',(doc['id'],)).fetchone()[0]
            if status=='converted': store.db.rollback();return
            outputs=sorted(Path(folder).rglob('*'))
            for path in outputs:
                if path.is_dir(): continue
                target=original.parent/path.relative_to(folder)
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as stream:
                    created.append(target);stream.write(path.read_bytes())
                role='markdown' if path==staged else 'asset'
                store.db.execute('INSERT INTO archive_files(document_id,role,path,sha256) VALUES(?,?,?,?)',(doc['id'],role,str(target),filehash(target)))
            store.db.execute("UPDATE archive_documents SET conversion_status='converted',conversion_error=NULL,converter=? WHERE id=?",(converter,doc['id']))
            store.db.commit()
    except BaseException as exc:
        store.db.rollback()
        for path in reversed(created): path.unlink(missing_ok=True)
        with store.db:
            store.db.execute("UPDATE archive_documents SET conversion_status='failed',conversion_error=? WHERE id=? AND conversion_status!='converted'",(str(exc),doc['id']))
        if isinstance(exc,(KeyboardInterrupt,SystemExit)): raise
