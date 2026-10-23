"""Read-only original PDF context, with independently matched pages and coordinates."""
import hashlib
import json
import re
import subprocess
from pathlib import Path


def normalized(text):
    return re.sub(r'[^a-z0-9]+','',re.sub(r'<[^>]*>','',text).lower())


def pdf_layout(path):
    from .archive import pdf_python
    script='''import json,sys,pymupdf
with pymupdf.open(sys.argv[1]) as pdf:
 print(json.dumps([dict(page=i+1,width=p.rect.width,height=p.rect.height,
 blocks=[dict(bbox=l['bbox'],text=''.join(s['text'] for s in l['spans']))
 for b in p.get_text('dict')['blocks'] if 'lines' in b for l in b['lines']]) for i,p in enumerate(pdf)]))
'''
    from .sort_process import run
    result=run([pdf_python(),'-c',script,str(path)],capture_output=True,text=True,timeout=120)
    if result.returncode: raise ValueError('Original PDF layout unavailable')
    return json.loads(result.stdout)


def attach(atoms,doc,progress,store=None):
    """No guessed asset filenames/pages. Matching text locates pages, not metric associations."""
    if Path(doc['original']).suffix.lower()!='.pdf': return []
    def cached(key, compute):
        if store is not None:
            try:row=store.get(key)
            except (ValueError,TypeError):
                progress('Invalid PDF preparation cache; recomputing from original')
                row=None
            if row:
                envelope=row[0]
                if (isinstance(envelope,dict) and 'value' in envelope
                    and envelope.get('sha256')==hashlib.sha256(json.dumps(envelope['value'],sort_keys=True).encode()).hexdigest()):
                    return envelope['value']
                progress('Invalid PDF preparation cache; recomputing from original')
        value=compute()
        if store is not None:
            store.put(key,dict(value=value,sha256=hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()))
        return value
    prefix='sort-layout-v2:'+doc['source_sha256']
    try:pages=cached(prefix,lambda:pdf_layout(doc['original']))
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        progress(f'Original PDF layout unavailable; ambiguous mappings must remain unresolved: {exc}')
        return []
    key=hashlib.sha256(json.dumps([(c['id'],c['text']) for c in atoms]).encode()).hexdigest()
    def match():
        # Normalize every PDF page once, rather than once per candidate/page pair.
        page_text=[(p['page'],normalized(' '.join(b['text'] for b in p['blocks']))) for p in pages]
        mapping={}
        for c in atoms:
            needle=normalized(c['text'])
            if len(needle)<12:continue  # Scalars cannot locate a page independently.
            matches=[number for number,body in page_text if needle in body]
            if len(matches)==1:mapping[c['id']]=matches[0]
        return mapping
    mapping=cached(prefix+':matches:'+key,match)
    for c in atoms:
        if c['id'] in mapping:
            c['page']=mapping[c['id']]
            c['visual']=dict(kind='original PDF text blocks',page=c['page'],
                             original_sha256=doc['source_sha256'],basis='Unique normalized text page match; association requires layout review')
    return pages


def context(batch,pages):
    selected={c.get('page') for c in batch}
    return [p for p in pages if p['page'] in selected]



def bounded_context(batch,pages):
    """Relevant line neighborhoods, headers and notes; never flatten chart geometry.

    No text is clipped. If matching cannot isolate lines, retain the matched page.
    All bottom-of-page lines survive as possible qualifications/footnotes. Source
    spans remain referenceable separately; layout is interpretive context only.
    """
    result=[]
    needles=[normalized(c['text']) for c in batch]
    for page in context(batch,pages):
        blocks=page['blocks'];keep=set()
        for i,b in enumerate(blocks):
            n=normalized(b['text'])
            if n and any(n==v or (len(n)>=4 and n in v) or (len(v)>=12 and v in n) for v in needles):
                keep.update(range(max(0,i-2),min(len(blocks),i+3)))
            qualification=re.search(r'(?i)\b(?:notes?|sources?|exclud\w*|includ\w*|illustrative|as of|non.GAAP|unaudited|subject to|may not|definitions?|footnotes?)\b|^\s*(?:[0-9]+[.)]|[*†‡])',b['text'])
            if qualification:
                keep.update(range(max(0,i-2),min(len(blocks),i+4)))
            if i<2 or b['bbox'][1]>=page['height']*.80:
                keep.add(i)
        if not keep or keep.issubset({0,1}):
            result.append(page)
        else:
            result.append({**page,'blocks':[b for i,b in enumerate(blocks) if i in keep],
                           'scope':'Relevant original lines, neighbors, headers, qualification lines and bottom notes; not the full page'})
    return result
