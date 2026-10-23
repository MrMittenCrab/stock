"""Isolated rebuild preparation and explicitly approved atomic replacement."""
import fcntl
import hashlib
import json
from pathlib import Path
from . import sources
from .archive import documents
from .core import ROOT
from .evidence import extract, IntegrityError, quality_flags


def match_key(p):
    loc=p['location']
    refs=loc.get('references')
    if refs:
        merged=[]
        for r in refs:
            anchor=(r['markdown_sha256'],r['start'],r['end'])
            if (merged and 'gap_before' in r and not r['gap_before'].strip()
                and merged[-1][0]==anchor[0] and merged[-1][2]+len(r['gap_before'])==anchor[1]):
                merged[-1]=(anchor[0],merged[-1][1],anchor[2])
            else: merged.append(anchor)
        anchors=tuple(merged)
    else:
        anchors=((loc.get('markdown_sha256',loc.get('sha256')),loc.get('markdown_start',loc.get('start')),
                  loc.get('markdown_end',loc.get('end'))),)
    # Ignore editorial wording, but keep source identity and attribution stable.
    return (anchors,p.get('category'),p.get('speaker'))



def review_passages(passages):
    lines=['All proposed passages. Exact source verification does not prove relevance.',
           'Review warnings are advisory; unflagged text still requires judgment.']
    for i,p in enumerate(passages,1):
        flags=quality_flags(p['text'])
        lines.append(f"\n[{i}/{len(passages)}] {p['location']['candidate_id']} · {', '.join(p['topics'])}")
        lines.extend('! '+flag for flag in flags)
        lines.append(p['text'])
        from .editorial import inspection
        lines.append(inspection(p))
    return '\n'.join(lines)


def rebuild(store,ticker,reference,cursor_factory,progress,approve):
    sources.schema(store)
    matches=[d for d in documents(store,ticker) if str(d['id'])==reference or any(Path(f['path']).name==reference for f in d['files'])]
    if len(matches)!=1: raise ValueError('DOCUMENT must be an unambiguous Archive ID or archived filename')
    doc=matches[0];directory=ROOT/'.data'/'sort-locks';directory.mkdir(exist_ok=True)
    # DB identity avoids interference between disposable verification databases.
    dbpath=store.db.execute('PRAGMA database_list').fetchone()[2]
    lockname=hashlib.sha256(f'{dbpath}:{doc["id"]}'.encode()).hexdigest()
    with (directory/lockname).open('a') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise ValueError('Document rebuild already running')
        previous=[p for p in sources.passages(store,ticker) if p['document_id']==doc['id']]
        def published_snapshot():
            return tuple(store.db.execute('SELECT * FROM source_passages WHERE document_id=? ORDER BY id',(doc['id'],)).fetchall())
        snapshot=published_snapshot()
        from .sort_process import DeferredCursor
        worker=DeferredCursor(cursor_factory)
        proposed,verify=extract(store,doc,worker,progress)
        insight_proposal=None
        if worker.supports_distillation:
            from .insights import stage
            insight_proposal=stage(store,ticker,worker,progress,new_document=(doc,proposed))
        keys={}
        for p in proposed: keys.setdefault(match_key(p),[]).append(p)
        overrides=store.db.execute('''SELECT o.passage_id,o.topic,o.present FROM source_overrides o
            JOIN source_passages p ON p.id=o.passage_id WHERE p.document_id=?''',(doc['id'],)).fetchall()
        old={p['id']:p for p in previous};transferred=[];unmatched=[]
        for ident,topic,present in overrides:
            key=match_key(old[ident])
            if len(keys.get(key,[]))==1: transferred.append((key,topic,present))
            else: unmatched.append((ident,topic,present))
        review=getattr(progress,'review',progress)
        review(f'Previous {len(previous)} · Proposed {len(proposed)} passages · {len(transferred)} manual topic overrides transferable')
        review(f"Quality concerns: previous {sum(bool(quality_flags(p['text'])) for p in previous)}; proposed {sum(bool(quality_flags(p['text'])) for p in proposed)} (advisory)")
        if insight_proposal:
            from .insights import review_text
            review(f"Before: {len(previous)} published passages · After: {len(proposed)} support passages")
            getattr(progress,'review_all',review)(review_text(insight_proposal))
        else:
            getattr(progress,'review_all',review)(review_passages(proposed))
        for ident,topic,present in unmatched: review(f'Unmatched manual correction: {ident} · {topic}={bool(present)}')
        if unmatched:
            progress('Replacement blocked: unmatched manual corrections require explicit reconciliation. Original evidence retained.')
            return False
        if not approve(): progress('Rebuild rejected; original evidence retained');return False
        verify()
        from .editorial import validate_publication
        for p in proposed: validate_publication(p)
        with store.db:
            store.db.execute('BEGIN IMMEDIATE')
            if insight_proposal:
                from .insights import head
                if head(store,ticker)!=insight_proposal['parent']:raise IntegrityError('Insight groups changed during rebuild')
            if published_snapshot()!=snapshot: raise IntegrityError('Published evidence changed during rebuild')
            actual_overrides=store.db.execute('SELECT o.passage_id,o.topic,o.present FROM source_overrides o JOIN source_passages p ON p.id=o.passage_id WHERE p.document_id=?',(doc['id'],)).fetchall()
            if sorted(actual_overrides)!=sorted(overrides): raise IntegrityError('Manual corrections changed during rebuild')
            for table in ('source_overrides','source_topics'):
                store.db.execute(f'DELETE FROM {table} WHERE passage_id IN (SELECT id FROM source_passages WHERE document_id=?)',(doc['id'],))
            store.db.execute('DELETE FROM source_passages WHERE document_id=?',(doc['id'],))
            store.db.execute('DELETE FROM source_sorts WHERE document_id=?',(doc['id'],))
            # publish uses its own context; use a savepoint-compatible insertion here.
            import time
            ids={}
            for p in proposed:
                anchor=json.dumps(p['location'],sort_keys=True)
                ident=hashlib.sha256(f'{doc["id"]}\0{anchor}\0{p["text"]}'.encode()).hexdigest();ids[match_key(p)]=ident
                store.db.execute('INSERT INTO source_passages VALUES(?,?,?,?,?,?,?,?)',(ident,doc['id'],p['text'],p['category'],p['speaker'],anchor,p['publication_date'],json.dumps(p['date_provenance'])))
                store.db.executemany('INSERT INTO source_topics VALUES(?,?)',[(ident,t) for t in p['topics']])
            store.db.executemany('INSERT INTO source_overrides VALUES(?,?,?)',[(ids[k],t,v) for k,t,v in transferred])
            now=time.time()
            store.db.execute('INSERT INTO source_sorts VALUES(?,?,?,4)',(doc['id'],now,doc['source_sha256']))
            store.db.execute('UPDATE archive_documents SET sorted_at=? WHERE id=?',(now,doc['id']))
            if insight_proposal:
                store.db.execute('INSERT INTO source_insight_heads VALUES(?,?) ON CONFLICT(ticker) DO UPDATE SET revision_id=excluded.revision_id',(ticker,insight_proposal['id']))
            # Retain staging checkpoints and model selections for audit.
        progress(f'Replaced document {doc["id"]} · {len(proposed)} passages')
        return True
