"""Portable v1 metadata codec and conservative archive identity matching."""
import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

VERSION='stock.archive.metadata.v1'
DATES={'publication_date','filing_date','document_date','event_date','report_period_end'}
FIELDS={'type','period','title','publisher','sec_accession','sec_filing_type','sec_cik',
        'publisher_evidence'} | DATES
FIELDS |= {d+s for d in DATES for s in ('_basis','_evidence_url')}
MATCH={'original_filename','official_document_url','sha256','source_sha256','document_id','content_indicators'}


def normalized(value):
    return re.sub(r'[^\w]+','',unicodedata.normalize('NFKC',value).casefold())


def load(path,ticker):
    from .archive import parse_date,TYPES
    def pairs(items):
        out={}
        for k,v in items:
            if k in out: raise ValueError(f'Duplicate JSON key: {k}')
            out[k]=v
        return out
    try:
        data=json.loads(Path(path).expanduser().read_text(encoding='utf-8-sig'),object_pairs_hook=pairs)
    except (json.JSONDecodeError,UnicodeError) as exc:
        raise ValueError(f'Invalid metadata JSON: {exc}') from exc
    if not isinstance(data,dict) or data.get('schema_version')!=VERSION:
        raise ValueError(f'Metadata schema_version must be {VERSION}')
    if data.get('ticker')!=ticker: raise ValueError('Metadata ticker does not match archive')
    if set(data)-{'schema_version','ticker','issuer','purpose','matching_policy','documents'}:
        raise ValueError('Unknown metadata envelope field')
    if 'issuer' in data and (not isinstance(data['issuer'],str) or not data['issuer'].strip()):
        raise ValueError('issuer must be a nonempty string')
    if 'purpose' in data and not isinstance(data['purpose'],str): raise ValueError('purpose must be a string')
    if 'matching_policy' in data and not isinstance(data['matching_policy'],dict): raise ValueError('matching_policy must be an object')
    records=data.get('documents')
    if not isinstance(records,list) or not records: raise ValueError('Metadata documents must be a nonempty array')
    for record in records:
        if not isinstance(record,dict) or set(record)!={'match','metadata'}: raise ValueError('Each document needs match and metadata')
        match,meta=record['match'],record['metadata']
        if not isinstance(match,dict) or not match or set(match)-MATCH: raise ValueError('Invalid document match fields')
        if not isinstance(meta,dict) or not meta or set(meta)-FIELDS: raise ValueError('Invalid document metadata fields')
        for key,value in meta.items():
            if value is not None and (not isinstance(value,str) or not value.strip()): raise ValueError(f'{key} must be a nonempty string or null')
            if key in DATES and value is not None and (not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value) or parse_date(value)!=value):
                raise ValueError(f'Invalid {key}; expected YYYY-MM-DD')
            if key.endswith('_evidence_url') and value is not None: validate_url(value)
        if meta.get('type') is not None and meta['type'] not in (*TYPES,'Unknown'): raise ValueError('Invalid document type')
        if meta.get('sec_accession') and not re.fullmatch(r'\d{10}-\d{2}-\d{6}',meta['sec_accession']): raise ValueError('Invalid SEC accession')
        if meta.get('sec_cik') and not re.fullmatch(r'\d{1,10}',meta['sec_cik']): raise ValueError('Invalid SEC CIK')
        for key,value in match.items():
            if key=='content_indicators':
                if not isinstance(value,list) or not value or any(not isinstance(v,str) or len(normalized(v))<5 for v in value):
                    raise ValueError('content_indicators must contain substantive strings')
            elif key=='document_id':
                if type(value) is not int or value<1: raise ValueError('Invalid document_id')
            elif not isinstance(value,str) or not value: raise ValueError(f'Invalid {key}')
            elif key in ('sha256','source_sha256') and not re.fullmatch('[a-fA-F0-9]{64}',value): raise ValueError('Invalid SHA-256')
            elif key=='official_document_url': validate_url(value)
        if match.get('sha256') and match.get('source_sha256') and match['sha256'].lower()!=match['source_sha256'].lower():
            raise ValueError('Contradictory SHA-256 fields')
        if not (match.get('sha256') or match.get('source_sha256') or match.get('content_indicators')):
            raise ValueError('Filename alone cannot identify a document; supply hash or content indicators')
    return data


def validate_url(value):
    parsed=urlsplit(value)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Evidence/document URL must use HTTP or HTTPS')


def normalized_metadata(meta):
    """v1 examples used publication_date for filing/document-based claims."""
    meta=dict(meta)
    basis=meta.get('publication_date_basis') or ''
    if meta.get('publication_date') and re.search(r'SEC filing date|filed as of',basis,re.I):
        for suffix in ('','_basis','_evidence_url'):
            if 'publication_date'+suffix in meta:
                meta.setdefault('filing_date'+suffix,meta['publication_date'+suffix])
        meta['publication_date']=None
        meta['publication_date_basis']='Earliest publication not established; supplied date retained as filing_date.'
        meta.pop('publication_date_evidence_url',None)
    elif meta.get('publication_date') and re.search(r'^Dated .*in presentation',basis,re.I):
        meta.setdefault('document_date',meta['publication_date'])
        meta.setdefault('document_date_basis',basis)
        if meta.get('publication_date_evidence_url'): meta.setdefault('document_date_evidence_url',meta['publication_date_evidence_url'])
        meta['publication_date']=None
        meta['publication_date_basis']='Earliest publication not established; supplied date retained as document_date.'
        meta.pop('publication_date_evidence_url',None)
    return meta


def select(store,docs,record,issuer):
    from .archive import read_document,identify,filehash
    match,meta=record['match'],record['metadata']
    candidates=[]
    for doc in docs:
        names={doc['original_filename']} | {r[0] for r in store.db.execute('SELECT original_filename FROM archive_imports WHERE document_id=?',(doc['id'],))}
        context=json.loads(doc['source_metadata']).get('source_information',{})
        urls={doc['source_path'],context.get('source_url'),context.get('document_url')}
        explicit=match.get('document_id')==doc['id'] or match.get('original_filename') in names or bool(match.get('official_document_url') and match['official_document_url'] in urls)
        digest=match.get('sha256') or match.get('source_sha256')
        content_only=not any(match.get(k) for k in ('document_id','original_filename','official_document_url','sha256','source_sha256'))
        if digest and digest.lower()!=doc['source_sha256']: continue
        if not explicit and not digest and not content_only: continue
        if 'document_id' in match and match['document_id']!=doc['id']: continue
        if digest and match.get('original_filename') and match['original_filename'] not in names:
            raise ValueError('Contradictory original filename')
        if not doc['original'] or filehash(doc['original'])!=doc['source_sha256']: raise ValueError('Archived original missing or changed')
        text,embedded=read_document(doc['original'])
        body=normalized(text)
        indicators=match.get('content_indicators',[])
        if indicators and not all(normalized(v) in body for v in indicators):
            if content_only: continue
            raise ValueError(f'Content indicators contradict {doc["original_filename"]}')
        if not digest and (len(indicators)<2 or sum(len(normalized(v)) for v in indicators)<25):
            raise ValueError('Content matching needs at least two substantive indicators or an exact hash')
        info=identify(text,embedded)
        for key in ('type','period'):
            if meta.get(key) and info.get(key) and meta[key]!=info[key]: raise ValueError(f'Contradictory document {key}')
        if info.get('accession') and meta.get('sec_accession') and info['accession']!=meta['sec_accession']:
            raise ValueError('Contradictory SEC accession')
        # Require the claimed issuer in the actual document, not just its filename.
        if issuer and normalized(re.sub(r',?\s+(?:Inc\.?|Limited|Ltd\.?)$', '',issuer,flags=re.I)) not in body:
            raise ValueError('Document issuer does not match metadata')
        candidates.append(doc)
    if len(candidates)!=1: raise ValueError('Ambiguous or unmatched metadata record: '+str(match.get('original_filename',match)))
    return candidates[0]


def import_metadata(store,ticker,path,*,interactive=None):
    from .archive import documents,update_metadata,_empty_asset_dirs
    from .core import symbol
    ticker=symbol(ticker)
    data=load(path,ticker)
    docs=documents(store,ticker)
    plans=[];seen=set()
    interactive=sys.stdin.isatty() if interactive is None else interactive
    for record in data['documents']:
        doc=select(store,docs,record,data.get('issuer'))
        if doc['id'] in seen: raise ValueError('Multiple records match the same document')
        seen.add(doc['id'])
        meta=normalized_metadata(record['metadata'])
        prior=json.loads(doc['metadata_provenance'])
        structured=json.loads(doc['structured_metadata'])
        changes={};provenance=dict(prior)
        decisions=structured.get('metadata_decisions',{}).copy()
        blocked=set()
        for field,value in sorted(meta.items(),key=lambda item:(item[0] not in DATES,item[0])):
            root=field.removesuffix('_evidence_url').removesuffix('_basis')
            if field=='publisher_evidence': root='publisher'
            if root in blocked: continue
            key='date' if field=='publication_date' else field
            old=doc['publication_date'] if key=='date' else doc.get(key,structured.get(field))
            if prior.get(key,{}).get('source') in ('user-supplied','metadata JSON') and old!=value:
                if decisions.get(field)=={'incoming':value,'retained':old}:
                    blocked.add(field)
                    continue
                if not interactive: raise ValueError(f'Metadata conflict: document {doc["id"]} {field}; rerun interactively')
                answer=input(f'{doc["id"]} {field}: keep {old!r} or JSON {value!r}? [K/j] ').strip().lower()
                if answer not in ('j','json'):
                    decisions[field]={'incoming':value,'retained':old}
                    blocked.add(field)
                    continue
                decisions.pop(field,None)
            if prior.get(key,{}).get('source')=='user-supplied' and old==value: continue
            evidence={'source':'metadata JSON','value':value}
            for suffix in ('_basis','_evidence_url'):
                if meta.get(field+suffix): evidence[suffix[1:]]=meta[field+suffix]
            provenance[key]=evidence
            if key in ('type','period','title','publisher','date'): changes[key]=value
            structured[field]=value
        if decisions: structured['metadata_decisions']=decisions
        else: structured.pop('metadata_decisions',None)
        structured['schema_version']=VERSION
        structured['identity']={'sha256':doc['source_sha256'],**record['match']}
        # Compare values AND provenance so a repeated import performs no writes.
        changes={k:v for k,v in changes.items() if v!=(doc['publication_date'] if k=='date' else doc[k]) or provenance[k]!=prior.get(k)}
        if structured!=json.loads(doc['structured_metadata']) or provenance!=prior or changes:
            plans.append((doc,changes,provenance,structured))
    journal=[]
    store.db.execute('BEGIN IMMEDIATE')
    try:
        for doc,changes,provenance,structured in plans:
            update_metadata(store,doc,changes,provenance=provenance,structured=structured,
                date_evidence=([{'date':changes['date'],**provenance['date']}] if changes.get('date') else [] ) if 'date' in changes else None,
                accession=structured.get('sec_accession'),_journal=journal)
        store.db.commit()
    except BaseException:
        store.db.rollback()
        for created,oldfiles,folder in reversed(journal):
            for p in reversed(created): p.unlink(missing_ok=True)
            _empty_asset_dirs(created,folder)
        raise
    for created,oldfiles,folder in journal:
        for p in oldfiles: p.unlink(missing_ok=True)
        _empty_asset_dirs(oldfiles,folder)
    return len(plans)


def export_metadata(store,ticker):
    """Return the portable representation; SQLite remains the source of truth."""
    from .archive import documents
    from .core import symbol
    records=[]
    for doc in documents(store,ticker):
        stored=json.loads(doc['structured_metadata'])
        meta={k:v for k,v in stored.items() if k in FIELDS}
        meta.update({k:doc[k] for k in ('type','period','title','publisher')})
        meta['publication_date']=doc['publication_date']
        provenance=json.loads(doc['metadata_provenance'])
        for field in DATES:
            evidence=provenance.get('date' if field=='publication_date' else field,{})
            if evidence:
                meta.setdefault(field+'_basis',evidence.get('basis') or evidence.get('source'))
                url=evidence.get('evidence_url') or evidence.get('url')
                if url: meta.setdefault(field+'_evidence_url',url)
        records.append({'match':{'original_filename':doc['original_filename'],'sha256':doc['source_sha256']},'metadata':meta})
    return {'schema_version':VERSION,'ticker':symbol(ticker),'documents':records}
