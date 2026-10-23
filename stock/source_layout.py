"""Read-only original PDF context, with independently matched pages and coordinates."""
import hashlib
import json
import re
import subprocess
from pathlib import Path


def normalized(text):
    return re.sub(r'[^a-z0-9]+','',re.sub(r'<[^>]*>','',text).lower())


def matched_pages(atom,pages,*,normalized_index=None):
    """Locate evidence, never prove a table's relationships by text matching."""
    needle=normalized(atom['text'])
    if len(needle)<12:return []
    normalized_pages=normalized_index if normalized_index is not None else [normalized(t) for t in pages]
    matches=[i+1 for i,t in enumerate(normalized_pages) if needle in t]
    if len(matches)==1:return matches
    if not matches and atom.get('table',{}).get('ambiguous'):
        # Interleaved table cells can contain fragments from several columns.
        # Literal windows may locate a page only when all matches agree uniquely.
        windows=[needle[i:i+24] for i in range(0,len(needle)-23,8)]
        found={i+1 for i,t in enumerate(normalized_pages) if any(w in t for w in windows)}
        if len(found)==1:return sorted(found)
    return []


def selective(atoms,doc,store):
    """Read text index once on demand; fetch geometry only for uniquely located pages.

    No image filenames, Markdown order or converter descriptions locate a page.
    Unlocatable relationships remain unresolved. Full-PDF geometry is never prepared.
    """
    if Path(doc['original']).suffix.lower()!='.pdf':return []
    from .archive import pdf_python, filehash
    if filehash(doc['original'])!=doc['source_sha256']:raise ValueError('Original changed during layout request')
    def cached(key,compute):
        row=store.get(key)
        if row:
            data=row[0]
            if data.get('sha256')!=hashlib.sha256(json.dumps(data['value'],sort_keys=True).encode()).hexdigest():raise ValueError('Corrupt selective PDF cache')
            return data['value']
        value=compute();store.put(key,dict(value=value,sha256=hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()));return value
    def read(script,*args):
        from .sort_process import run
        r=run([pdf_python(),'-c',script,doc['original'],*args],capture_output=True,text=True,timeout=120)
        if r.returncode:raise ValueError('Requested original layout unavailable')
        return json.loads(r.stdout)
    prefix='selective-layout-1:'+doc['source_sha256']
    try:
        index=cached(prefix+':index',lambda:read("import sys,json,pymupdf\nwith pymupdf.open(sys.argv[1]) as d: print(json.dumps([p.get_text() for p in d]))"))
        normalized_index=[normalized(t) for t in index];numbers=set();matched={}
        for a in atoms:
            matches=matched_pages(a,index,normalized_index=normalized_index)
            if len(matches)==1:
                numbers.add(matches[0]);matched.setdefault(matches[0],[]).append(a['id'])
        pages=[]
        for number in sorted(numbers):
            script="""import json,sys,pymupdf
with pymupdf.open(sys.argv[1]) as d:
 p=d[int(sys.argv[2])-1]
 print(json.dumps(dict(page=int(sys.argv[2]),width=p.rect.width,height=p.rect.height,
 blocks=[dict(bbox=l['bbox'],text=''.join(s['text'] for s in l['spans'])) for b in p.get_text('dict')['blocks'] if 'lines' in b for l in b['lines']])))
"""
            page=cached(prefix+':page:'+str(number),lambda n=number:read(script,str(n)))
            pages.append({**page,'original_sha256':doc['source_sha256'],'matched_source_ids':matched[number]})
        return pages
    except (OSError,ValueError,subprocess.SubprocessError):
        return []  # Optional layout unavailability never vetoes ordinary narrative.
