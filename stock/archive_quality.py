"""Archive-owned, versioned conversion assessment and exact native recovery.

No semantic relationships are derived from coordinates. A region is exact source
text in PDF content-stream order, with coordinates available for inspection.
"""
import collections
import json
import re
import subprocess
import time
from pathlib import Path

VERSION = 1
POLICY = 'native-quality-3'


def words(text):
    import unicodedata
    text=unicodedata.normalize('NFKC',re.sub(r'<[^>]*>|!\[[^\]]*\]\([^)]*\)', ' ',text))
    text=re.sub(r'(?<=[a-z])(?=[1-9]\b)', ' ',text)
    return re.findall(r"[^\W_]+",text.casefold(),re.UNICODE)


def native_pages(original):
    from .archive import pdf_python
    script='''import json,sys,pymupdf
with pymupdf.open(sys.argv[1]) as d:
 print(json.dumps([dict(page=i+1,width=p.rect.width,height=p.rect.height,
 blocks=[dict(id=f'p{i+1}b{b[5]}',bbox=list(b[:4]),text=b[4]) for b in p.get_text('blocks',sort=False) if b[6]==0],
 images=[list(r) for im in p.get_images() for r in p.get_image_rects(im[0])],
 drawings=len(p.get_drawings())) for i,p in enumerate(d)]))
'''
    r=subprocess.run([pdf_python(),'-c',script,str(original)],capture_output=True,text=True,timeout=120)
    if r.returncode:raise ValueError('Archive quality assessment cannot read original PDF: '+r.stderr[-300:])
    return json.loads(r.stdout)


def assess(pages,markdown):
    """Compare normalized words and individual regions, never character counts.

    Older pdfmd output lacks page delimiters. Exact content anchors are searched
    across its text; we explicitly record this weaker alignment, never invent pages.
    """
    joined=' '.join(words(markdown))
    repeated=collections.Counter()
    for page in pages:
        repeated.update(set(' '.join(words(b['text'])) for b in page['blocks']
            if b['bbox'][1]<page['height']*.12 or b['bbox'][3]>page['height']*.88))
    result=[]
    for page in pages:
        ignored=[b['id'] for b in page['blocks'] if len(words(b['text']))<=30
            and repeated[' '.join(words(b['text']))]>=max(3,len(pages)*.5)
            and (b['bbox'][1]<page['height']*.12 or b['bbox'][3]>page['height']*.88)]
        anchors=[]
        for b in page['blocks']:
            if b['id'] in ignored:continue
            tokens=words(b['text'])
            phrases=[' '.join(tokens)]
            if len(tokens)>6:phrases+=[' '.join(tokens[i:i+6]) for i in range(0,len(tokens)-5,6)]
            for phrase in phrases:
                if len(phrase)>=24 and joined.count(phrase)==1:
                    a=joined.index(phrase);anchors.append((a,a+len(phrase)))
        merged=[]
        for a,z in sorted(set(anchors)):
            if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(z,merged[-1][1]))
            else:merged.append((a,z))
        anchors=merged
        native_size=sum(len(' '.join(words(b['text']))) for b in page['blocks'])
        anchored=sum(z-a for a,z in anchors)>=native_size*.4
        page_output=joined[min(a for a,z in anchors):max(z for a,z in anchors)] if anchors and anchored else joined
        page_words=collections.Counter(page_output.split())
        page_pairs=set(zip(page_output.split(),page_output.split()[1:]))
        missing=[];total=0;lost=0
        for b in page['blocks']:
            if b['id'] in ignored:continue
            tokens=words(b['text']);meaningful=[w for w in tokens if len(w)>1]
            if not meaningful:continue
            count=collections.Counter(meaningful);absent={w:n for w,n in count.items() if w not in page_words}
            total+=len(meaningful);lost+=sum(absent.values())
            # A short named region matters even when whole-document recall is high.
            acronyms={w.casefold() for w in re.findall(r'\b[A-Z]{2,}\b',b['text'])}
            unique_loss=[w for w in absent if len(w)>=3 or w in acronyms or any(c.isdigit() for c in w)]
            phrase=' '.join(tokens)
            disrupted=sum((a,z) not in page_pairs for a,z in zip(tokens,tokens[1:]))
            if phrase not in page_output and (unique_loss or (len(tokens)>=6 and disrupted>max(2,len(tokens)*.25))):
                missing.append({**b,'missing_words':unique_loss})
        visual=bool(page.get('drawings',0)>12 or any((r[2]-r[0])*(r[3]-r[1])>page['width']*page['height']*.12 for r in page.get('images',[])))
        empty=total==0
        numeric_layout=any(len(re.findall(r'\d[\d.,]*(?:MW|GW|%|\+)',b['text']))>=2 and ' '.join(words(b['text'])) not in joined for b in page['blocks'])
        column_starts={round(b['bbox'][0]/(page['width']*.12)) for b in page['blocks'] if len(words(b['text']))>12}
        column_damage=len(column_starts)>=4 and bool(missing) and '|' in markdown
        layout=numeric_layout or column_damage
        result.append(dict(page=page['page'],alignment=('native block content anchors' if anchors and anchored else 'unpaginated fallback; page alignment unresolved'),
                           output_anchor_spans=anchors,ignored_repeated_margin_regions=ignored,
                           native_words=total,missing_words=lost,word_recall=round(1-lost/max(1,total),4),
                           missing_regions=missing,visual=visual,image_only=empty and visual,
                           defects=(['missing_native_text'] if missing else [])+(['unresolved_visual_relationships'] if visual else [])+
                           (['no_readable_text'] if empty and not visual else [])+(['damaged_reading_order'] if layout else [])))
    return result


def prepare(original,markdown,converter,*,ocr=None,document_type=None,conversion_seconds=None):
    """Write one immutable evidence bundle alongside a staged Markdown file.

    Recovery is supplemental, not a rewrite of old Markdown. OCR is attempted at
    most once for at most three affected pages; results never replace native text.
    """
    from .archive import filehash
    started=time.monotonic();original=Path(original);markdown=Path(markdown)
    body=markdown.read_bytes().decode('utf-8-sig');pages=native_pages(original)
    diagnostics=assess(pages,body);regions=[];attempts=[]
    if document_type=='Transcript':
        for page in diagnostics:
            if 'damaged_reading_order' in page['defects']:
                page['defects'].remove('damaged_reading_order')
                page['transcript_layout_policy']='Retain exact native turns; numeric prose alone does not justify OCR'
    for page in diagnostics:
        for b in page['missing_regions']:
            body+=f"\n\n## Archive native evidence · PDF page {page['page']} · {b['id']}\n\n"
            start=len(body);exact=b['text'].rstrip('\n');body+=exact
            regions.append(dict(kind='native_pdf_region',page=page['page'],block=b['id'],bbox=b['bbox'],
                                start=start,end=len(body),text=exact,reading_order='PDF content stream; no inferred column relationships'))
        if page['missing_regions']:page['defects'].remove('missing_native_text');page['recovered_regions']=len(page['missing_regions'])
    # Native text absence needs OCR; visual diagrams alone never trigger OCR.
    affected=[p['page'] for p in diagnostics if p['image_only'] or 'no_readable_text' in p['defects'] or 'damaged_reading_order' in p['defects']]
    if affected and ocr:
        for number in affected[:3]:
            try:
                recovered=ocr(original,[number],markdown.parent/f'ocr-page-{number}')
                attempt=dict(method='local Marker balanced forced OCR',pages=[number],**recovered)
                content=attempt.pop('markdown',None)
                attempts.append(attempt)
                if content and len(words(content))>=6 and recovered.get('returncode')==0:
                    body+=f"\n\n## Archive local OCR evidence · PDF page {number}\n\n"
                    start=len(body);body+=content
                    page=pages[number-1]
                    regions.append(dict(kind='local_ocr_region',page=number,block=f'p{number}ocr',
                        bbox=[0,0,page['width'],page['height']],start=start,end=len(body),text=content,
                        reading_order='Local balanced forced OCR; verify relationships against original PDF'))
                    diagnostics[number-1]['ocr_candidate_retained']=True
            except (OSError,ValueError,subprocess.SubprocessError) as exc:
                attempts.append(dict(method='local Marker balanced forced OCR',pages=[number],error=str(exc)))
    # OCR prose is retained for inspection but not automatically trusted as a
    # replacement for relationships. Unreadable essential pages remain repairable.
    needs=any((p['image_only'] or 'no_readable_text' in p['defects']) and not p.get('ocr_candidate_retained') for p in diagnostics)
    visual=any(p['visual'] or 'damaged_reading_order' in p['defects'] for p in diagnostics)
    status='needs_repair' if needs else 'prepared_with_visual_limitations' if visual else 'prepared'
    markdown.write_text(body,encoding='utf-8')
    manifest=dict(schema='stock.archive.evidence',version=VERSION,policy=POLICY,original=str(original),original_sha256=filehash(original),
                  markdown_sha256=filehash(markdown),converter=converter,settings={'native_order':'content stream','use_llm':False,'normal_mode':'fast / automatic' if converter=='pdfmd / Marker' else converter},
                  quality_status=status,pages=diagnostics,regions=regions,attempts=attempts,
                  elapsed_seconds=round(time.monotonic()-started,3))
    manifest['normal_conversion_seconds']=conversion_seconds
    manifest['converter_versions']={}
    python=Path.home()/'.venvs/marker/bin/python'
    if python.is_file():
        script="import json,importlib.metadata as m; print(json.dumps({p:m.version(p) for p in ('marker-pdf','surya-ocr')}))"
        try:
            versions=subprocess.run([str(python),'-c',script],capture_output=True,text=True,timeout=10)
            if versions.returncode==0:manifest['converter_versions']=json.loads(versions.stdout)
        except (OSError,ValueError,subprocess.SubprocessError):pass
    manifest['marker_metadata']={}
    for path in markdown.parent.rglob('*.json'):
        if path.name.endswith('.evidence.json'):continue
        try:
            data=json.loads(path.read_text())
            if isinstance(data,dict) and ('page_stats' in data or 'versions' in data):
                manifest['marker_metadata'][str(path.relative_to(markdown.parent))]=data
        except (ValueError,OSError):continue
    markdown.with_suffix('.evidence.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    return manifest


def local_ocr(original,pages,output,previous=None):
    from .pdf_review import convert
    import tempfile, shutil
    result=None;reused=False
    if previous:
        prior=Path(previous).parent/f'ocr-page-{pages[0]}'
        review=prior/'review.json'
        if review.is_file():
            cached=json.loads(review.read_text())
            from .archive import filehash
            if (cached.get('source_sha256')==filehash(original) and cached.get('pdf_pages')==pages
                and cached.get('profile')=='high-fidelity' and cached.get('returncode')==0):
                shutil.copytree(prior,output)
                result=cached;reused=True
    # The review runner deliberately forbids production destinations. Run in a
    # disposable directory, then copy its bounded result into the candidate.
    if result is None:
        import sys
        print(f"Archive · PDF page {pages[0]} · local balanced forced OCR · 180s limit",file=sys.stderr,flush=True)
        with tempfile.TemporaryDirectory(prefix='stock-archive-ocr-') as temporary:
            staged=Path(temporary)/'conversion'
            result=convert(original,staged,pages=','.join(map(str,pages)),seconds=180,rss_mib=8192)
            shutil.copytree(staged,output)
    data={k:result.get(k) for k in ('returncode','elapsed_seconds','limit','configuration','versions')}
    data['reused']=reused
    paths=list(output.rglob('*.md'))
    if result.get('returncode')==0 and len(paths)==1:
        body=paths[0].read_text()
        body=re.sub(r'(!\[[^\]]*\]\()((?!/|https?:)[^)]+)(\))',lambda m:m[1]+str(paths[0].parent.relative_to(output.parent)/m[2])+m[3],body)
        data['markdown']=body
    return data


def load(doc):
    path=doc.get('evidence')
    if not path:return None
    from .archive import filehash
    registered=next((f for f in doc.get('files',[]) if f['path']==path),None)
    if registered and filehash(path)!=registered['sha256']:raise ValueError('Archive evidence manifest changed')
    data=json.loads(Path(path).read_text())
    if (not isinstance(data,dict) or data.get('schema')!='stock.archive.evidence'
        or not {'original_sha256','markdown_sha256','regions','pages'}<=set(data)
        or not isinstance(data['regions'],list)):
        raise ValueError('Invalid Archive evidence manifest; repair through Archive')
    body=Path(doc['markdown']).read_bytes().decode('utf-8-sig')
    for r in data['regions']:
        if body[r['start']:r['end']]!=r['text']:
            raise ValueError('Archive region offsets changed')
    if data['original_sha256']!=doc['source_sha256'] or data['markdown_sha256']!=filehash(doc['markdown']):
        raise ValueError('Archive evidence identity changed; repair through Archive')
    return data
