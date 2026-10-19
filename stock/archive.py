"""Local document recognition and hash-addressed archive registration."""
import hashlib
import json
import os
import re
import signal
import ssl
import urllib.request
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
    columns={row[1] for row in store.db.execute('PRAGMA table_info(archive_documents)')}
    if {'metadata_provenance','sec_accession'} <= columns and store.db.execute("SELECT 1 FROM sqlite_master WHERE name='archive_imports'").fetchone():
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
    columns={row[1] for row in store.db.execute('PRAGMA table_info(archive_documents)')}
    for name,definition in (('metadata_provenance',"TEXT NOT NULL DEFAULT '{}'"),('sec_accession','TEXT')):
        if name not in columns:
            store.db.execute(f'ALTER TABLE archive_documents ADD COLUMN {name} {definition}')
    store.db.commit()


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
    lines=[re.sub(r'<[^>]+>|[*`]', '', line).strip() for line in lines]
    raw_title=str(metadata.get('title') or '').strip()
    accession_match=re.search(r'\b\d{10}-\d{2}-\d{6}\b',json.dumps(metadata)+'\n'+text[:4000])
    accession=accession_match[0] if accession_match else None
    useful_title=raw_title if raw_title and not re.fullmatch(r'\d{10}-\d{2}-\d{6}',raw_title) else None
    title=useful_title or (lines[0] if lines else 'Untitled')
    # Restrict type recognition to front matter/headings; a report's appendix or
    # references to prior reports must not determine its primary type.
    head='\n'.join(([title] if useful_title else [])+lines[:60])
    head=re.sub(r'(?i)(FORM\s+)(10|20|40|8|6)\s*[-‐‑–—]\s*([QKF])',r'\1\2-\3',head)
    head=re.sub(r'(?i)(annual|interim|quarterly)\s*\n\s*(report|results)',r'\1 \2',head)
    ordinals={'first':'1','second':'2','third':'3','fourth':'4'}
    head=re.sub(r'\b(first|second|third|fourth)\s+(?:fiscal\s+)?quarter\s+(?:of\s+)?(?:fiscal\s+)?(20\d{2})\b',
                lambda m:'Q'+ordinals[m[1].lower()]+' '+m[2],head,flags=re.I)
    rules=[('Transcript',r'\b(?:earnings |conference |results )?call transcript\b|\btranscript\b|\bearnings call\b(?=.*(?:participants|operator:))'),
           ('Letter',r'\bletter to (?:shareholders|investors)\b'),
           ('Research',r'\b(?:equity research|research report|research note)\b'),
           ('Annual',r'\bannual (?:report|results)\b|\bform\s+(?:10-k|20-f|40-f)\b|年報|年度報告|年度业绩|年度業績'),
           ('Interim',r'\b(?:interim|half[- ]year) (?:report|results)\b|\bform\s+6-k\b(?=.*interim)|中期報告|中期报告|中期業績|中期业绩'),
           ('Quarterly',r'\bquarterly (?:report|results)\b|\bform\s+10-q\b|季度報告|季度报告|季度業績|季度业绩'),
           ('Presentation',r'\b(?:investor|results|earnings|corporate) presentation\b'),
           ('Earnings',r'\bearnings (?:release|results|announcement)\b'),
           ('Filing',r'\bform\s+(?:8-k|6-k|20-f|40-f|s-1|f-1|13f)\b|\bregulatory filing\b'),
           ('Release',r'\b(?:press|news) release\b'),('Article',r'\b(?:article|opinion|byline)\s*:')]
    matches=[(match.start(),index,kind) for index,(kind,pattern) in enumerate(rules)
             if (match:=re.search(pattern,head,re.I|re.S))]
    kind=min(matches)[2] if matches else None
    period=None
    report_end=None
    inferred_period=False
    match=re.search(r'\b(Q[1-4]|H[12]|FY)\s*[- ]?\s*(20\d{2})\b',head,re.I)
    if match: period=match[1].upper()+('-' if match[1].upper()!='FY' else '')+match[2]
    if period is None:
        reverse=re.search(r'\b(20\d{2})\s*[- ]?\s*(Q[1-4]|H[12])\b',head,re.I)
        if reverse: period=reverse[2].upper()+'-'+reverse[1]
    if period is None:
        # Only reporting-end dates, not publication dates, define a period.
        end=re.search(r'(?:year|months?|quarter|period)\s+ended\s+('+DATE_PATTERN+')',head,re.I)
        ending=parse_date(end[1]) if end else None
        report_end=ending
        if ending:
            year,month,_=map(int,ending.split('-'))
            if kind=='Annual': period=f'FY{year}'
            elif kind=='Quarterly' and not re.search(r'\bfiscal quarter\b',head,re.I) and month in (3,6,9,12):
                period=f'Q{month//3}-{year}';inferred_period=True
            elif kind=='Interim' and month==6:
                period=f'H1-{year}';inferred_period=True
        if not period and kind in ('Annual','Interim'):
            year_match=re.search(r'(?:annual|interim|half[- ]year) (?:report|results)\s*\n?\s*(20\d{2})|(20\d{2})\s*(?:annual|interim|half[- ]year) (?:report|results)',head,re.I)
            if year_match and kind=='Annual': period='FY'+next(g for g in year_match.groups() if g)
    if report_end is None:
        end=re.search(r'(?:year|months?|quarter|period)\s+ended\s+('+DATE_PATTERN+')',head,re.I)
        report_end=parse_date(end[1]) if end else None
    if not report_end:
        chinese_end=re.search(r'截至('+DATE_PATTERN+r')止',head)
        report_end=parse_date(chinese_end[1]) if chinese_end else None
    if not period and kind=='Annual':
        chinese_year=re.search(r'(20\d{2})\s*年?\s*(?:年報|年度報告|年度报告)|(?:年報|年度報告|年度报告)\s*(20\d{2})',head)
        if chinese_year: period='FY'+next(g for g in chinese_year.groups() if g)
        elif report_end: period='FY'+report_end[:4]
    if not period and kind=='Interim' and report_end and report_end[5:7]=='06':
        period='H1-'+report_end[:4];inferred_period=True
    candidates=[]
    pattern=r'\b(?:(Q[1-4]|H[12]|FY)\s*[- ]?\s*(20\d{2})|(20\d{2})\s*[- ]?\s*(Q[1-4]|H[12]|FY))\b'
    for match in re.finditer(pattern,head,re.I):
        unit=(match[1] or match[4]).upper();year=match[2] or match[3]
        candidate=unit+('' if unit=='FY' else '-')+year
        if candidate not in candidates: candidates.append(candidate)
    if len(candidates)==1:
        period=candidates[0];inferred_period=False
    elif len(candidates)>1: period=None
    evidence=[]
    for line in lines[:60]:
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
    # A primary form heading is distinct from mentions inside other documents.
    form=re.search(r'^FORM\s+(10-[QK](?:/A)?|20-F|40-F|8-K|6-K)\b',head,re.I|re.M) if kind in ('Annual','Quarterly','Filing') else None
    # Prefer a report heading to a company name as its exact title.
    if not useful_title:
        if form: title='Form '+form[1].upper()
        heading=next((line for line in lines[:15] if re.search(r'(?:annual|interim|quarterly) (?:report|results)',line,re.I)),None)
        title=title if form else heading or title
    registrant=re.search(r'([^\n]+)\n?\s*\(Exact name of registrant',head,re.I)
    registrant=registrant[1].strip() if registrant else None
    if not publisher and registrant: publisher=registrant
    info=dict(title=title,type=kind,period=period,publisher=publisher,accession=accession,registrant=registrant,
              date=min((e['date'] for e in evidence),default=None),date_evidence=evidence,report_end=report_end,period_choices=candidates,sec_form=form[1].upper() if form else None)
    info['provenance']={key:{'source':'document text' if key!='date' else min(evidence,key=lambda e:e['date'])['source'], 'value':info[key]}
                        for key in ('type','period','publisher','date') if info[key]}
    if inferred_period and period:
        info['provenance']['period']={'source':'reporting-end candidate','value':period}
        if period not in candidates: candidates.append(period)
    if metadata.get('publisher') and publisher==metadata['publisher']:
        info['provenance']['publisher']={'source':'document metadata','value':publisher}
    if useful_title or title!= (lines[0] if lines else 'Untitled') or (lines and not re.search(r'SECURITIES AND EXCHANGE|UNITED STATES',title,re.I)):
        info['provenance']['title']={'source':'document metadata' if useful_title else 'document text','value':title}
    return info


def clarify(info,interactive=None,read=None,output=None):
    if interactive is None: interactive=sys.stdin.isatty()
    if not interactive:
        if info.get('provenance',{}).get('period',{}).get('source')=='reporting-end candidate':
            info['period']=None
            info['provenance'].pop('period')
        if not info['type']: raise ValueError('Document type is uncertain; rerun in an interactive terminal to choose its type')
        return
    read=read or input
    output=output or sys.stdout
    provenance=info.setdefault('provenance',{})
    for key,label in (('type','Type'),('period','Period'),('date','Date'),('title','Title'),('publisher','Publisher')):
        if key in provenance and provenance[key].get('source')!='reporting-end candidate': continue
        options=list(TYPES) if key=='type' else list(info.get(key+'_choices',[]))
        if options: options+=['Unknown','Enter']
        while True:
            hint=' · '.join(f'{i} {v}' for i,v in enumerate(options,1)) if options else ('YYYY-MM-DD · Enter Unknown' if key=='date' else 'Enter value · Enter Unknown')
            print(f'{label}?  {hint}',file=output,flush=True)
            try: answer=read('> ').strip()
            except EOFError as exc: raise ValueError('Classification cancelled; rerun in an interactive terminal') from exc
            if answer.isdigit() and 1<=int(answer)<=len(options): answer=options[int(answer)-1]
            if answer=='Enter':
                options=[];continue
            value=None if not answer or answer.lower()=='unknown' else answer
            if key=='type' and value:
                value=next((t for t in TYPES if t.lower()==value.lower()),None)
                if not value: continue
            if key=='date' and value:
                value=parse_date(value)
                if not value: continue
            info[key]=value or 'Unknown' if key in ('type','title') else value
            provenance[key]={'source':'user-supplied','value':info[key]}
            if key=='date': info['date_evidence']=[{'date':value,'source':'user-supplied'}] if value else []
            break


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
        prior=json.loads(existing['metadata_provenance'])
        keys=('type','period','date','title','publisher')
        complete=all(key in prior and (prior[key].get('source')=='user-supplied' or (existing['publication_date'] if key=='date' else existing[key])) for key in keys)
        doc=existing
        if not complete:
            text,metadata=read_document(Path(existing['original']))
            info=identify(text,metadata)
            resolve_sec(ticker,info,metadata)
            for key in keys:
                # Manual Unknown is also a deliberate correction.
                if prior.get(key,{}).get('source')=='user-supplied':
                    info[key]=existing['publication_date'] if key=='date' else existing[key]
                    info['provenance'][key]=prior[key]
                    if key=='date': info['date_evidence']=json.loads(existing['date_evidence'])
            clarify(info,interactive)
            changes={key:info[key] for key in keys if key in info['provenance'] and
                     (prior.get(key)!=info['provenance'][key] or info[key]!=(existing['publication_date'] if key=='date' else existing[key]))}
            if changes:
                doc=update_metadata(store,existing,changes,provenance=info['provenance'],
                                    date_evidence=info['date_evidence'],accession=info.get('accession'))
    else:
        text,metadata=read_document(source)
        info=identify(text,metadata)
        resolve_sec(ticker,info,metadata)
        clarify(info,interactive)
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
                 publication_date,date_evidence,source_metadata,imported_at,conversion_status,metadata_provenance,sec_accession)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (ticker,digest,source.name,str(source),info['title'],info['type'],info['period'],info['publisher'],info['date'],json.dumps(info['date_evidence']),json.dumps(metadata),time.time(),'pending' if extension=='.pdf' else 'native' if extension=='.md' else 'not-applicable',json.dumps(info['provenance']),info.get('accession')))
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


def sec_json(url):
    request=urllib.request.Request(url,headers={'User-Agent':os.environ.get('STOCK_SEC_USER_AGENT','StockArchive/0.1 (+https://github.com/MrMittenCrab/stock)'),'Accept':'application/json'})
    context=ssl.create_default_context()
    # python.org macOS builds can lack their optional bundled CA installation.
    # Load the OS CA bundle as well; verification always remains enabled.
    if not ssl.get_default_verify_paths().cafile and Path('/etc/ssl/cert.pem').is_file():
        context.load_verify_locations('/etc/ssl/cert.pem')
    with urllib.request.urlopen(request,timeout=8,context=context) as response:
        return json.load(response)


def resolve_sec(ticker,info,metadata):
    """Match primary filings, never assign a parent filing's date to an exhibit.

    An accession alone identifies a submission, not its individual documents.
    Require issuer, form and reporting end as well. Annual report booklets and
    transcripts are deliberately excluded from primary 10-K/10-Q matching.
    """
    if not ticker.endswith('.US') or not info.get('accession'): return
    form=info.get('sec_form')
    if not form or not re.fullmatch(r'(10-Q|10-K|20-F|40-F)(/A)?',form,re.I): return
    try:
        tickers=sec_json('https://www.sec.gov/files/company_tickers.json')
        issuer=next((v for v in tickers.values() if v['ticker']==ticker[:-3]),None)
        if not issuer: return
        url=f"https://data.sec.gov/submissions/CIK{int(issuer['cik_str']):010d}.json"
        submissions=sec_json(url)
        normalize=lambda name:re.sub(r'[^\w]','',name).casefold()
        names=[submissions.get('name','')]+[v['name'] for v in submissions.get('formerNames',[])]
        if info.get('registrant') and normalize(info['registrant']) not in {normalize(name) for name in names}:
            return
        tables=[submissions.get('filings',{}).get('recent',{})]
        accession=info['accession']
        for part in submissions.get('filings',{}).get('files',[]):
            if accession not in tables[0].get('accessionNumber',[]):
                tables.append(sec_json('https://data.sec.gov/submissions/'+part['name']))
                if accession in tables[-1].get('accessionNumber',[]): break
        for table in tables:
            for i,number in enumerate(table.get('accessionNumber',[])):
                if number!=accession: continue
                if table['form'][i].upper()!=form.upper(): return
                report=parse_date(table['reportDate'][i])
                if not report or report!=info.get('report_end'): return
                filed=parse_date(table['filingDate'][i])
                if not filed: return
                evidence={'date':filed,'source':'SEC submissions','url':url,'accession':accession,
                          'primary_document':table['primaryDocument'][i],'report_date':report}
                info['date_evidence'].append(evidence)
                info['date']=min(e['date'] for e in info['date_evidence'] if e.get('date'))
                info['publisher']=submissions['name']
                fiscal_end=str(submissions.get('fiscalYearEnd',''))
                if form.upper().startswith('10-Q') and re.fullmatch(r'\d{4}',fiscal_end) and (not info.get('period') or info['provenance'].get('period',{}).get('source')=='reporting-end candidate'):
                    month=int(report[5:7]);end_month=int(fiscal_end[:2])
                    if 1<=end_month<=12 and (month-end_month)%3==0:
                        quarter=((month-end_month-1)%12)//3+1
                        year=int(report[:4])+(month>end_month)
                        info['period']=f'Q{quarter}-{year}'
                        info['provenance']['period']={'source':'SEC fiscal calendar','value':info['period'],'url':url,'fiscal_year_end':fiscal_end}
                earliest=min(info['date_evidence'],key=lambda e:e['date'])
                info['provenance']['date']={**earliest,'value':info['date']}
                info['provenance']['publisher']={'source':'SEC submissions','value':info['publisher'],'url':url}
                return
    except (OSError,ValueError,KeyError,IndexError,TypeError):
        # Offline or ambiguous matches remain unresolved and go through CLI clarification.
        return


def update_metadata(store,doc,changes,*,provenance=None,date_evidence=None,accession=None):
    """Update in place, preserving document/file IDs and source identity.

    Stage a complete replacement bundle before changing registered paths. Publish
    exclusively, commit SQLite, then remove old files. On failure remove only the
    files we created; originals and registered hashes remain intact.
    """
    allowed={'type','period','date','title','publisher'}
    if set(changes)-allowed: raise ValueError('Unsupported metadata field')
    info={k:doc['publication_date'] if k=='date' else doc[k] for k in allowed}
    original_info=info.copy()
    info.update(changes)
    if info['type'] not in (*TYPES,'Unknown'): raise ValueError('Unknown document type')
    if info['date'] and (not re.fullmatch(r'\d{4}-\d{2}-\d{2}',info['date']) or parse_date(info['date'])!=info['date']):
        raise ValueError('Date must be YYYY-MM-DD or Unknown')
    info['title']=info['title'] or 'Unknown'
    prior=json.loads(doc.get('metadata_provenance') or '{}')
    for key in changes:
        prior[key]=(provenance or {}).get(key,{'source':'user-supplied','value':info[key]})
    evidence=json.loads(doc['date_evidence']) if date_evidence is None else date_evidence
    if 'date' in changes and date_evidence is None:
        evidence=[{'date':info['date'],'source':'user-supplied'}] if info['date'] else []
    folder=Path(doc['original']).parent
    oldstem=Path(doc['original']).stem
    stem=oldstem if basename(info)==basename(original_info) else basename(info)
    created=[]
    oldfiles=[]
    store.db.execute('BEGIN IMMEDIATE')
    try:
        current=store.db.execute('SELECT metadata_provenance,title,type,period,publication_date,publisher FROM archive_documents WHERE id=?',(doc['id'],)).fetchone()
        expected=(doc.get('metadata_provenance','{}'),doc['title'],doc['type'],doc['period'],doc['publication_date'],doc['publisher'])
        if current!=expected: raise ValueError('Document changed; reopen its editor')
        # Preserve all file IDs, including future consumers referencing them.
        registered=store.db.execute('SELECT id,role,path,sha256 FROM archive_files WHERE document_id=?',(doc['id'],)).fetchall()
        if stem!=oldstem:
            suffix=0
            while any(folder.glob(stem+'.*')):
                suffix+=1
                if suffix>57: raise ValueError('Cannot allocate archive filename')
                stem=basename(info)+'--'+doc['source_sha256'][:7+suffix]
        with tempfile.TemporaryDirectory(prefix='.stock-edit-',dir=folder) as temporary:
            staged=[]
            for ident,role,path,digest in registered:
                original=Path(path)
                if not original.is_relative_to(folder): raise ValueError('Registered file is outside archive')
                if not original.is_file() or filehash(original)!=digest: raise ValueError('Archived file missing or changed')
                relative=original.relative_to(folder)
                first=relative.parts[0]
                if first==oldstem+'.assets': relative=Path(stem+'.assets',*relative.parts[1:])
                elif original.parent==folder and original.stem==oldstem: relative=Path(stem+original.suffix)
                target=folder/relative
                body=original.read_bytes()
                if role=='markdown' or (role=='original' and original.suffix.lower()=='.md'):
                    # Native Markdown is an immutable source copy. Avoid changing its bytes.
                    if role=='markdown': body=body.replace((oldstem+'.assets/').encode(),(stem+'.assets/').encode())
                if target==original:
                    if body!=original.read_bytes(): raise ValueError('Cannot rewrite immutable source')
                    continue
                stage=Path(temporary)/str(ident);stage.write_bytes(body)
                staged.append((ident,original,target,stage))
            for ident,original,target,stage in staged:
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as stream:
                    created.append(target)
                    stream.write(stage.read_bytes())
                store.db.execute('UPDATE archive_files SET path=?,sha256=? WHERE id=?',(str(target),filehash(target),ident))
                oldfiles.append(original)
            store.db.execute('''UPDATE archive_documents SET title=?,type=?,period=?,publisher=?,publication_date=?,
                date_evidence=?,metadata_provenance=?,sec_accession=? WHERE id=?''',
                (info['title'],info['type'],info['period'],info['publisher'],info['date'],json.dumps(evidence),json.dumps(prior),
                 accession or doc.get('sec_accession'),doc['id']))
        store.db.commit()
    except BaseException:
        store.db.rollback()
        for path in reversed(created): path.unlink(missing_ok=True)
        _empty_asset_dirs(created,folder)
        raise
    for path in oldfiles: path.unlink(missing_ok=True)
    _empty_asset_dirs(oldfiles,folder)
    return next(d for d in documents(store,doc['ticker']) if d['id']==doc['id'])


def _empty_asset_dirs(files,folder):
    parents=set()
    for path in files:
        parent=path.parent
        while parent!=folder and parent.is_relative_to(folder):
            parents.add(parent)
            parent=parent.parent
    for parent in sorted(parents,key=lambda p:len(p.parts),reverse=True):
        try: parent.rmdir()
        except OSError: pass
