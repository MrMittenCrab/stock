"""Read-only original PDF context, with independently matched pages and coordinates."""
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
    result=subprocess.run([pdf_python(),'-c',script,str(path)],capture_output=True,text=True,timeout=120)
    if result.returncode: raise ValueError('Original PDF layout unavailable')
    return json.loads(result.stdout)


def attach(atoms,doc,progress):
    """No guessed asset filenames/pages. Matching text locates pages, not metric associations."""
    if Path(doc['original']).suffix.lower()!='.pdf': return []
    try:pages=pdf_layout(doc['original'])
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        progress(f'Original PDF layout unavailable; ambiguous mappings must remain unresolved: {exc}')
        return []
    for c in atoms:
        needle=normalized(c['text'])
        # Short scalars cannot locate a page independently.
        if len(needle)<12:continue
        matches=[p for p in pages if needle in normalized(' '.join(b['text'] for b in p['blocks']))]
        if len(matches)==1:
            c['page']=matches[0]['page']
            c['visual']=dict(kind='original PDF text blocks',page=c['page'],
                             original_sha256=doc['source_sha256'],basis='Unique normalized text page match; association requires layout review')
    return pages


def context(batch,pages):
    selected={c.get('page') for c in batch}
    return [p for p in pages if p['page'] in selected]
