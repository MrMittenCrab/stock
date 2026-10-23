"""Historical extraction retained solely for provenance/failure reproduction tests."""
import json,hashlib,subprocess
from pathlib import Path
from stock import sources
from stock.archive import filehash,documents,_convert_registered
from stock.sort import units,markdown_text,pdf_pages,validate,original_match

import stock.sort as sorting
def legacy_sort_document(store,doc,cursor,progress=print):
    sources.schema(store)
    if sources.completed(store,doc['id']): return None
    original=Path(doc['original'] or '')
    if not original.is_file() or sorting.filehash(original)!=doc['source_sha256']:
        raise ValueError('Original archive file missing or changed')
    markdown=Path(doc['markdown']) if doc.get('markdown') else None
    if original.suffix.lower()=='.pdf' and not (markdown and markdown.is_file() and markdown_text(markdown).strip()):
        if sorting._convert_registered(store,doc)=='running':
            raise ValueError('Archived Markdown unavailable: Archive conversion is still running; retry later')
        doc=next(d for d in documents(store,doc['ticker']) if d['id']==doc['id'])
        markdown=Path(doc['markdown']) if doc.get('markdown') else None
    if not markdown or not markdown.is_file():
        reason='successful conversion is missing its Markdown; restore the archived file' if doc.get('conversion_status')=='converted' else 'conversion running or failed; '+(doc.get('conversion_error') or 'retry later')
        raise ValueError('Archived Markdown unavailable: '+reason)
    archived=markdown.read_bytes()
    text=archived.decode('utf-8-sig');markdown_hash=hashlib.sha256(archived).hexdigest()
    work=list(sorting.units(text))
    if not work: raise ValueError('Archived Markdown has no usable text; successful conversions are never replaced')
    context='Document title: '+doc['title']+'\nPublisher: '+(doc['publisher'] or 'Unknown')+'\nFront matter (untrusted):\n'+text[:6500]
    # PDF text supplies optional reference pages only, never quotation authority.
    pages=None
    if original.suffix.lower()=='.pdf':
        try: pages=sorting.pdf_pages(original)
        except (ValueError,OSError,subprocess.SubprocessError): pass
    extracted=[];failures=[]

    def unchanged():
        if sorting.filehash(original)!=doc['source_sha256']: raise ValueError('Original changed during sorting')
        if not markdown.is_file() or sorting.filehash(markdown)!=markdown_hash: raise ValueError('Markdown changed during sorting')

    for index,unit in enumerate(work):
        row=store.db.execute('SELECT payload FROM source_sort_sections WHERE document_id=? AND markdown_hash=? AND section_index=?',(doc['id'],markdown_hash,index)).fetchone()
        state=json.loads(row[0]) if row else dict(accepted=[],pending=[],complete=False)
        nearby=context
        if index: nearby+='\nPreceding context (untrusted):\n'+work[index-1]['text'][-2500:]
        accepted=state['accepted']
        pending=[]

        def save(complete=False):
            unchanged()
            with store.db:
                store.db.execute('INSERT OR REPLACE INTO source_sort_sections VALUES(?,?,?,?)',
                    (doc['id'],markdown_hash,index,json.dumps(dict(accepted=accepted,pending=pending,complete=complete))))

        def check(raw):
            passage=validate(raw,unit,nearby,doc,None,'archived Markdown',markdown_hash)
            loc=passage['location']
            if pages:
                try:
                    page,_,_,_=sorting.original_match(passage['text'],pages)
                    loc.update(page=page,page_reference_basis='Unique original PDF text match; reference only')
                except ValueError: pass
            if any(p['location']['start']==loc['start'] and p['location']['end']==loc['end'] for p in extracted+accepted): return
            if any(max(p['location']['start'],loc['start'])<min(p['location']['end'],loc['end']) for p in extracted+accepted):
                raise ValueError('Overlapping passage; return only the uncovered exact span')
            accepted.append(passage)

        if not state['complete']:
            if state['pending']:
                queue=state['pending']
            else:
                try: queue=[dict(candidate=r,error=None) for r in cursor.extract(unit,nearby)]
                except (ValueError,OSError,subprocess.SubprocessError) as exc:
                    queue=[dict(candidate=None,error=str(exc),section_error=True)]
            pending=queue.copy();save()
            rejected=[]
            for offset,item in enumerate(queue):
                try:
                    if item.get('section_error'): raise ValueError(item['error'])
                    check(item['candidate'])
                except ValueError as exc:
                    repair={**unit,'retry':{**item,'error':str(exc),'accepted':[p['text'] for p in accepted]}}
                    try:
                        repaired=cursor.extract(repair,nearby)
                        if not repaired and not item.get('section_error'): raise ValueError(str(exc))
                        for candidate in repaired:
                            try: check(candidate)
                            except ValueError as error:
                                rejected.append(dict(candidate=candidate,error=str(error)))
                    except (ValueError,OSError,subprocess.SubprocessError) as error:
                        rejected.append({**item,'error':str(error)})
                pending=rejected+queue[offset+1:];save()
            pending=rejected
            save(complete=not pending)
        extracted.extend(accepted)
        if pending:
            failures.append((index+1,len(pending),[p['error'] for p in pending]))
    unchanged()
    if failures:
        sections=','.join(str(i) for i,_,_ in failures)
        rejected=sum(count for _,count,_ in failures)
        errors=list(dict.fromkeys(error for _,_,messages in failures for error in messages))
        detail='; '.join(error[:300] for error in errors[:3])
        if len(errors)>3: detail+=f'; {len(errors)-3} more errors'
        raise ValueError(f"Incomplete · {len(extracted)} verified passages retained; {rejected} rejected in sections {sections} · {detail}")
    published=sources.publish(store,doc,extracted,doc['source_sha256'])
    return len(extracted) if published else None

