"""Document analysis into independently verified, exactly cited propositions.

Historical section checkpoints are audit data, never execution instructions.
Published passage envelopes are a projection for the existing Sources contract.
"""
import hashlib
import json
import re
import time
from pathlib import Path
from . import editorial, sources
from .evidence import IntegrityError, ProtocolError, candidates, resolve
from .insights import digest, packed
from .sort_transport import source_payload

CONTRACT='knowledge-2-strategic'
CONTEXT=60000


def schema(store):
    sources.schema(store)
    store.db.executescript('''
    CREATE TABLE IF NOT EXISTS knowledge_schema(version INTEGER PRIMARY KEY);
    INSERT OR IGNORE INTO knowledge_schema VALUES(1);
    CREATE TABLE IF NOT EXISTS knowledge_artifacts(
      id TEXT PRIMARY KEY, contract TEXT NOT NULL, document_id INTEGER NOT NULL,
      operation TEXT NOT NULL, input_hash TEXT NOT NULL, payload TEXT NOT NULL,
      checksum TEXT NOT NULL, created_at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS knowledge_attempts(
      id TEXT PRIMARY KEY, document_id INTEGER NOT NULL, operation TEXT NOT NULL,
      state TEXT NOT NULL, error TEXT, updated_at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS knowledge_anchors(
      id TEXT PRIMARY KEY, document_id INTEGER NOT NULL, markdown_hash TEXT NOT NULL,
      start INTEGER NOT NULL, end INTEGER NOT NULL, text TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS knowledge_propositions(
      id TEXT PRIMARY KEY, document_id INTEGER NOT NULL, contract TEXT NOT NULL,
      text TEXT NOT NULL, representation TEXT NOT NULL, category TEXT NOT NULL, speaker TEXT);
    CREATE TABLE IF NOT EXISTS knowledge_supports(
      proposition_id TEXT NOT NULL REFERENCES knowledge_propositions(id),
      anchor_id TEXT NOT NULL REFERENCES knowledge_anchors(id), ordinal INTEGER NOT NULL,
      PRIMARY KEY(proposition_id,anchor_id));
    CREATE TABLE IF NOT EXISTS knowledge_judgments(
      proposition_id TEXT PRIMARY KEY REFERENCES knowledge_propositions(id),
      contract TEXT NOT NULL, input_hash TEXT NOT NULL, payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS source_model_calls(
      id INTEGER PRIMARY KEY, document_id INTEGER, recorded_at REAL, payload TEXT);
    ''')


def table_spans(line):
    """Markdown cell offsets, including optional outer pipes and escaped literals."""
    bars=[]
    for i,char in enumerate(line):
        if char!='|':continue
        slashes=0;j=i-1
        while j>=0 and line[j]=='\\':slashes+=1;j-=1
        if not slashes%2:bars.append(i)
    edges=bars[:]
    if not bars or line[:bars[0]].strip():edges.insert(0,-1)
    if not bars or line[bars[-1]+1:].strip():edges.append(len(line))
    return [(a+1,z) for a,z in zip(edges,edges[1:])]


def prepare_atoms(text,doc,sha):
    """Exact cell spans; preserve archived table structure without pretending it is PDF layout."""
    atoms=[]
    for c in candidates(text,doc,sha,include_context=True):
        if c['text'].lstrip().startswith('|'):
            rows=[[line[a:z] for a,z in table_spans(line)] for line in c['text'].splitlines()]
            ambiguous=bool(rows and (len({len(row) for row in rows})>1 or sum(bool(x.strip()) for x in rows[0])<=1))
            fragmented=ambiguous and (len(c['text'])>2400 or len({len(row) for row in rows})>1)
            parent=dict(id=c['id'],start=c['start'],end=c['end'],ambiguous=ambiguous,fragmented=fragmented,
                        sha256=hashlib.sha256(c['text'].encode()).hexdigest())
            offset=c['start']
            for row,line in enumerate(c['text'].splitlines(keepends=True)):
                if not fragmented:
                    body=line.strip()
                    if body and not re.fullmatch(r'[|: \-]+',body):
                        start=offset+len(line)-len(line.lstrip());end=start+len(body)
                        atoms.append({**c,'id':f'd{doc["id"]}:{sha[:16]}:{start}:{end}',
                                      'start':start,'end':end,'text':text[start:end],
                                      'table':dict(parent,row=row),'context_only':False,'source_kind':'table_row'})
                    offset+=len(line)
                    continue
                # Only unescaped Markdown delimiters establish cell boundaries.
                for column,(left,right) in enumerate(table_spans(line)):
                    body=line[left:right];trimmed=body.strip()
                    if not trimmed or re.fullmatch(r':?-+:?',trimmed):continue
                    start=offset+left+len(body)-len(body.lstrip());end=start+len(trimmed)
                    atoms.append({**c,'id':f'd{doc["id"]}:{sha[:16]}:{start}:{end}',
                                  'start':start,'end':end,'text':text[start:end],
                                  'table':dict(parent,row=row,column=column),
                                  'context_only':False,'source_kind':'table_cell'})
                offset+=len(line)
        else:atoms.append(c)
    # Context-only tables were historically assigned the following heading.
    heading=None
    for c in atoms:
        if c['text'].lstrip().startswith('#'):heading=c.get('section')
        elif c.get('table'):c['section']=heading
    from .archive_quality import load
    evidence=load(doc)
    if evidence:
        for c in atoms:
            for region in evidence['regions']:
                if region['start']<=c['start'] and c['end']<=region['end']:
                    c.update(source_kind=region['kind'],page=region['page'],pdf_region=region)
                    if doc.get('type')=='Transcript':
                        c.update(turn='native-'+region['block'],speaker=None,role=None,speaker_role=None)
                        # Never inherit the last Markdown speaker for supplemental PDF text.
                    break
    return atoms


def review_context_for(context,ids,allowed_pages=None):
    try:data=json.loads(context) if isinstance(context,str) else context
    except ValueError:return context
    if isinstance(data,dict) and 'original_pdf_layout' in data:
        pages=[]
        for page in data['original_pdf_layout']:
            if allowed_pages is not None and (page.get('original_sha256'),page.get('page')) not in allowed_pages:continue
            matched=sorted(ids & set(page.get('matched_source_ids',[])))
            if matched:pages.append({**page,'matched_source_ids':matched})
        return packed({**data,'original_pdf_layout':sorted(pages,key=lambda p:(p.get('original_sha256',''),p.get('page',0)))})
    return context


def layout_context(passages):
    pages={}
    for p in passages:
        for page in p['location'].get('visual_context',[]):
            key=(page.get('original_sha256'),page.get('page'))
            if key not in pages:pages[key]={**page,'matched_source_ids':list(page.get('matched_source_ids',[]))}
            else:pages[key]['matched_source_ids']=sorted(set(pages[key]['matched_source_ids'])|set(page.get('matched_source_ids',[])))
    return list(pages.values())


def sections(atoms,limit=CONTEXT):
    """Pack complete heading sections. Oversized sections split at exact anchors.

    No source overlap. Global outline plus targeted retrieval handles distant context.
    """
    if sum(len(packed(source_payload(c))) for c in atoms)<=limit:
        return [atoms] if atoms else []
    groups=[];group=[];size=0
    for c in atoms:
        cost=len(packed(source_payload(c)))
        if group and (size+cost>limit or (size>limit//2 and c.get('section')!=group[-1].get('section'))):
            groups.append(group);group=[];size=0
        group.append(c);size+=cost
    if group:groups.append(group)
    return groups


def repair_work(rejections,atoms,limit=CONTEXT):
    """Pack complete uncertainty cases, never split sources then repeat a failure."""
    lookup={c['id']:c for c in atoms};batch=[];failures=[];ids=set();size=0
    for r in rejections:
        selection=r.get('selection',{});p=r.get('proposed')
        refs=[x['source_id'] for x in p['location']['references']] if p else selection.get('ids',[])
        chosen={x for x in refs if x in lookup}
        # Readability repair needs the original support, not a document search.
        if p and 'standalone' not in r['error'].lower():
            chosen.update(c['id'] for c in editorial.recovery_sources(r,atoms,limit=6000))
        elif not p:
            original_ids=set(chosen)
            for pos,c in enumerate(atoms):
                if c['id'] in original_ids:chosen.update(a['id'] for a in atoms[max(0,pos-2):pos+3])
        extra=[c for c in atoms if c['id'] in chosen-ids]
        cost=sum(len(packed(source_payload(c))) for c in extra)
        if failures and size+cost>limit:
            yield sorted(batch,key=lambda c:c['start']),failures
            batch=[];failures=[];ids=set();size=0
            extra=[c for c in atoms if c['id'] in chosen]
            cost=sum(len(packed(source_payload(c))) for c in extra)
        batch+=extra;ids.update(chosen);size+=cost
        failures.append(dict(text=p['text'] if p else selection.get('text'),reason=r['error'],ids=refs))
    if failures:yield sorted(batch,key=lambda c:c['start']),failures


class Operations:
    def __init__(self,store,doc,cursor,verify):
        self.store=store;self.doc=doc;self.cursor=cursor;self.verify=verify
    def review_claims(self,unit,context):
        # Independent judgments keyed by complete evidence, not batch index/order.
        cached={};pending=[];keys={}
        for i,p in enumerate(unit['review']):
            claim={k:v for k,v in p.items() if k!='index'}
            data=review_context_for(context,{r['source_id'] for r in p['references']},{tuple(v) for v in p.get('layout_pages',[])} if 'layout_pages' in p else None)
            key=digest([CONTRACT,self.doc,'claim-review',claim,data]);keys[i]=key
            row=self.store.db.execute('SELECT payload,checksum FROM knowledge_artifacts WHERE id=? AND contract=?',(key,CONTRACT)).fetchone()
            if row:
                if hashlib.sha256(row[0].encode()).hexdigest()!=row[1]:raise IntegrityError('Corrupt claim review artifact')
                judgment=json.loads(row[0]);editorial.validate_reviews([dict(judgment,index=0)],1)
                cached[i]=dict(judgment,index=i)
            else:pending.append((i,p))
        if pending:
            subset=[dict(p,index=i) for i,(_,p) in enumerate(pending)]
            # Filter page context again after removing already reviewed claims.
            data=review_context_for(context,{r['source_id'] for p in subset for r in p['references']},{tuple(v) for p in subset for v in p.get('layout_pages',[])} if all('layout_pages' in p for p in subset) else None)
            results=editorial.validate_reviews(self.extract({**unit,'review':subset},data,_batch_review=True),len(subset))
            with self.store.db:
                for j,(i,_) in enumerate(pending):
                    judgment={k:v for k,v in results[j].items() if k!='index'};payload=packed(judgment);key=keys[i]
                    if (judgment['fidelity'],judgment['readability'],judgment['relevance'])==('supported','clear','useful'):
                        self.store.db.execute('INSERT OR IGNORE INTO knowledge_artifacts VALUES(?,?,?,?,?,?,?,?)',
                            (key,CONTRACT,self.doc['id'],'claim-review',key,payload,hashlib.sha256(payload.encode()).hexdigest(),time.time()))
                    cached[i]=dict(judgment,index=i)
        self.verify()
        return [cached[i] for i in range(len(unit['review']))]

    def extract(self,unit,context,_batch_review=False):
        if 'review' in unit and not _batch_review:return self.review_claims(unit,context)
        operation=unit.get('operation','verify' if 'review' in unit else 'understand')
        identity=[CONTRACT,self.doc,unit,context]
        key=digest(identity)
        row=self.store.db.execute('SELECT payload,checksum FROM knowledge_artifacts WHERE id=? AND contract=?',(key,CONTRACT)).fetchone()
        if row:
            if hashlib.sha256(row[0].encode()).hexdigest()!=row[1]:raise IntegrityError('Corrupt knowledge artifact')
            return json.loads(row[0])
        with self.store.db:
            self.store.db.execute('INSERT OR REPLACE INTO knowledge_attempts VALUES(?,?,?,?,?,?)',
                (key,self.doc['id'],operation,'running',None,time.time()))
        try:
            for attempt in range(2):
                try:
                    raw=self.cursor.extract(unit,context)
                    if 'review' in unit:editorial.validate_reviews(raw,len(unit['review']))
                    else:editorial.validate_selections(raw)
                    break
                except ProtocolError:
                    if attempt:raise
        except BaseException as exc:
            with self.store.db:
                self.store.db.execute('UPDATE knowledge_attempts SET state=?,error=?,updated_at=? WHERE id=?',
                    ('interrupted' if isinstance(exc,KeyboardInterrupt) else 'failed',
                     packed(dict(type=type(exc).__name__,reason=str(exc))),time.time(),key))
            raise
        self.verify()
        payload=packed(raw)
        with self.store.db:
            self.store.db.execute('INSERT OR IGNORE INTO knowledge_artifacts VALUES(?,?,?,?,?,?,?,?)',
                (key,CONTRACT,self.doc['id'],operation,key,payload,hashlib.sha256(payload.encode()).hexdigest(),time.time()))
            self.store.db.execute('UPDATE knowledge_attempts SET state=?,error=NULL,updated_at=? WHERE id=?',('complete',time.time(),key))
        return raw


def extract(store,doc,cursor,progress):
    from .archive import filehash
    original=Path(doc['original']);md=Path(doc.get('markdown') or doc['original'])
    if not original.is_file() or filehash(original)!=doc['source_sha256']:raise IntegrityError('Original missing or changed')
    if not md.is_file() or md.suffix.lower()!='.md':raise IntegrityError('Archived Markdown unavailable; restore or convert through Archive')
    data=md.read_bytes();sha=hashlib.sha256(data).hexdigest();text=data.decode('utf-8-sig')
    if not text.strip():raise IntegrityError('Archived Markdown is empty')
    def verify():
        from .archive_quality import load
        load(doc)
        if filehash(md)!=sha or filehash(original)!=doc['source_sha256']:raise IntegrityError('Source changed during sorting')
        from .sort_budget import check
        check()
    schema(store)
    atoms=prepare_atoms(text,doc,sha)
    # Bound unusually large raw tables without dropping any archived text.
    bounded=[]
    for c in atoms:
        for a in range(c['start'],c['end'],CONTEXT//2):
            z=min(c['end'],a+CONTEXT//2)
            bounded.append({**c,'start':a,'end':z,'text':text[a:z],
                'id':f'd{doc["id"]}:{sha[:16]}:{a}:{z}'})
    atoms=bounded;lookup={c['id']:c for c in atoms}
    with store.db:
        store.db.executemany('INSERT OR IGNORE INTO knowledge_anchors VALUES(?,?,?,?,?,?)',
            [(c['id'],doc['id'],sha,c['start'],c['end'],c['text']) for c in atoms])
    metadata={k:doc.get(k) for k in ('id','title','type','ticker','publisher','period','source_sha256','metadata_provenance')}
    outline=[dict(id=c['id'],heading=c['text']) for c in atoms if c['text'].lstrip().startswith('#')]
    # Keep full outline identities; headings alone are not substantive claim support.
    from .source_layout import selective
    # Only demonstrably damaged tables get original geometry during understanding.
    damaged=[c for c in atoms if c.get('table',{}).get('fragmented') or c.get('source_kind')=='local_ocr_region']
    table_layout=selective(damaged,doc,store) if damaged else []
    from .archive_quality import load as load_archive_evidence
    load_quality=load_archive_evidence(doc)
    context=packed(dict(document=metadata,outline=outline,original_pdf_layout=table_layout,
        archive_quality=({'status':doc.get('quality_status'),'unresolved_visual_pages':[p['page'] for p in load_quality['pages'] if p['visual']]} if load_quality else None)))
    ops=Operations(store,{**metadata,'markdown_sha256':sha,'original':str(original),'markdown':str(md)},cursor,verify)
    def metrics(metric):
        if hasattr(progress,'log_event'):progress.log_event(dict(model=metric))
        with store.db:store.db.execute('INSERT INTO source_model_calls(document_id,recorded_at,payload) VALUES(?,?,?)',
            (doc['id'],time.time(),packed(dict(metric,contract=CONTRACT))))
    cursor.record_metrics=metrics
    raw=[];work=sections(atoms)
    for i,batch in enumerate(work,1):
        progress(f'{doc["id"]} · {i}/{len(work)} · selection')
        raw.extend(ops.extract(dict(candidates=batch,text='',primary_ids=[c['id'] for c in batch],operation='understand'),context))
    accepted,rejected=resolve(raw,atoms,text,doc,sha)
    from .source_layout import selective
    def visual_risk(p):
        refs=p['location']['references']
        def numeric_tile(body):
            body=re.sub(r'<[^>]+>|[#*`\\]','',body)
            body=re.sub(r'(?i)\b(?:million|billion|trillion|thousand|[KMGT]Wh?|[KMGT]W)\b','',body)
            body=re.sub(r'(?i)(?<=\d)[KMBT]\b','',body)
            return bool(re.search(r'\d',body)) and not re.search(r'[A-Za-z]',body)
        numeric=[r for r in refs if numeric_tile(r['text'])]
        if numeric:return True
        for r in refs:
            if r.get('table',{}).get('ambiguous'):return True
            if r['text'].lstrip().startswith('|'):
                rows=[line.strip().strip('|').split('|') for line in r['text'].splitlines() if line.strip().startswith('|')]
                if rows and (len({len(row) for row in rows})>1 or
                    (len(rows[0])>2 and sum(bool(cell.strip()) for cell in rows[0])<=1)):
                    return True
            body=re.sub(r'<[^>]+>|[#*`\\]','',r['text'])
            if ('\n' in body and '|' not in body and ':' not in body
                and len(re.findall(r'\d+(?:[,.]\d+)*',body))>1
                and not re.search(r'[.!?](?:\s|$)',body)):
                return True
        return False
    def claim_layout(p,pages):
        ids={r['source_id'] for r in p['location']['references']}
        return [page for page in pages if page.get('original_sha256')==doc['source_sha256']
                and ids & set(page.get('matched_source_ids',[]))]
    risky=[p for p in accepted if visual_risk(p)]
    if risky:
        ids={r['source_id'] for p in risky for r in p['location']['references']}
        positions=[i for i,c in enumerate(atoms) if c['id'] in ids]
        nearby={c['id'] for pos in positions for c in atoms[max(0,pos-4):pos+5]}
        layout=selective([c for c in atoms if c['id'] in nearby],doc,store)
        for p in risky:p['location']['visual_context']=claim_layout(p,layout)
    # Independent review is cached per exact input, never inferred from generation.
    def review_context(ps):
        return packed(dict(document=metadata,original_pdf_layout=layout_context(ps)))
    progress(f'{doc["id"]} · 1/1 · semantic review')
    accepted,failed=editorial.review(accepted,ops,review_context)
    rejected+=failed
    # A single targeted operation for the document, followed by independent review.
    # Deterministic unsupported numbers are excluded; semantic missing support/visual
    # ambiguity can retrieve original evidence. No per-claim retry fanout.
    uncertain=[r for r in rejected if (r.get('proposed') or r.get('error','').startswith('Unresolved contextual ambiguity'))
               and r.get('proposed',{}).get('location',{}).get('review',{}).get('relevance') not in ('irrelevant','redundant')]
    if uncertain:
        repaired=[];errors=[]
        prior_layout=layout_context([r['proposed'] for r in uncertain if r.get('proposed')])
        followups=list(repair_work(uncertain,atoms))
        for i,(targeted,relevant) in enumerate(followups,1):
            needs_layout=(any(c.get('table',{}).get('ambiguous') for c in targeted) or
                          any(re.search(r'(?i)layout|visual|chart|column|mapping|pairing|flattened|interleav|label.*value',r['reason']) for r in relevant))
            targeted_ids={c['id'] for c in targeted}
            inherited=[v for v in prior_layout if targeted_ids & set(v.get('matched_source_ids',[]))]
            fetched=selective(targeted,doc,store) if needs_layout else []
            layout=layout_context([dict(location=dict(visual_context=inherited+fetched))])
            progress(f'{doc["id"]} · {i}/{len(followups)} · citation recovery')
            repair_context=packed(dict(document=metadata,failed_claims=relevant,original_pdf_layout=layout,
                task='Correct or narrow only these failed claims; make each standalone. Cite required support and keep an original anchor per correction. Preserve source stance and strategic purpose. Omit unsupported claims. Do not repeat supported claims or analyze unrelated evidence.'))
            fixed=ops.extract(dict(candidates=targeted,text='',operation='resolve-uncertainty'),repair_context)
            allowed=[set(f['ids']) for f in relevant]
            fixed=[r for r in fixed if any(set(r['ids']) & refs for refs in allowed)]
            good,invalid=resolve(fixed,targeted,text,doc,sha)
            for p in good:p['location']['visual_context']=claim_layout(p,layout)
            repaired+=good;errors+=invalid
        good,bad=editorial.review(repaired,ops,review_context)
        accepted+=good;rejected+=errors+bad
    verify()
    unique={}
    for p in accepted:
        editorial.validate_publication(p)
        if visual_risk(p) and not claim_layout(p,p['location'].get('visual_context',[])):
            rejected.append(dict(error='Original layout required for ambiguous multi-value relationship',proposed=p))
            continue
        for r in p['location']['references']:
            if (r['markdown_sha256']!=sha or r['original_sha256']!=doc['source_sha256'] or
                text[r['start']:r['end']]!=r['text']):raise IntegrityError('Source anchor failed verification')
        ident=digest([CONTRACT,p['text'],p['category'],p['speaker'],p['location']['references']])
        if ident in unique:unique[ident]['topics']=sorted(set(unique[ident]['topics'])|set(p['topics']))
        else:unique[ident]=p
    with store.db:
        for ident,p in unique.items():
            store.db.execute('INSERT OR IGNORE INTO knowledge_propositions VALUES(?,?,?,?,?,?,?)',
                (ident,doc['id'],CONTRACT,p['text'],p['location']['representation'],p['category'],p['speaker']))
            store.db.executemany('INSERT OR IGNORE INTO knowledge_supports VALUES(?,?,?)',
                [(ident,r['source_id'],i) for i,r in enumerate(p['location']['references'])])
            store.db.execute('INSERT OR IGNORE INTO knowledge_judgments VALUES(?,?,?,?)',
                (ident,CONTRACT,editorial.fingerprint(p),packed(p['location']['review'])))
    if hasattr(progress,'log_event'):
        selected_ids={x for r in raw for x in r['ids']}
        verified_ids={r['source_id'] for p in unique.values() for r in p['location']['references']}
        progress.log_event(dict(document=doc['id'],excluded=rejected,verified=len(unique),contract=CONTRACT,
            coverage=[dict(id=c['id'],section=c.get('section'),selected=c['id'] in selected_ids,
                           verified=c['id'] in verified_ids) for c in atoms if not c.get('context_only')]))
    return list(unique.values()),verify
