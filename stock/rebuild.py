"""Isolated rebuild preparation and explicitly approved atomic replacement."""
import fcntl
import hashlib
import json
from pathlib import Path
from . import sources
from .archive import documents
from .core import ROOT
from .evidence import extract, IntegrityError


def match_key(p):
    loc=p['location']
    return (loc.get('markdown_sha256',loc.get('sha256')),loc.get('markdown_start',loc.get('start')),
            loc.get('markdown_end',loc.get('end')),p['text'])


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
        proposed,verify=extract(store,doc,cursor_factory(),progress)
        keys={match_key(p):p for p in proposed}
        overrides=store.db.execute('''SELECT o.passage_id,o.topic,o.present FROM source_overrides o
            JOIN source_passages p ON p.id=o.passage_id WHERE p.document_id=?''',(doc['id'],)).fetchall()
        old={p['id']:p for p in previous};transferred=[];unmatched=[]
        for ident,topic,present in overrides:
            key=match_key(old[ident])
            if key in keys: transferred.append((key,topic,present))
            else: unmatched.append((ident,topic,present))
        review=getattr(progress,'review',progress)
        review(f'Previous {len(previous)} · Proposed {len(proposed)} passages · {len(transferred)} manual topic overrides transferable')
        def quality(ps):
            return f'{sum("|" in p["text"] for p in ps)} table-containing; {sum(len(p["text"].split())<8 for p in ps)} short; {sum(bool(p["speaker"]) for p in ps)} named'
        review('Previous: '+quality(previous)+' · Proposed: '+quality(proposed))
        review('Relevance is model-judged; inspect these source quotations before approval:')
        for p in proposed[:5]: review(f'{p["location"]["candidate_id"]} · {", ".join(p["topics"])}\n{p["text"]}')
        for ident,topic,present in unmatched: review(f'Unmatched manual correction: {ident} · {topic}={bool(present)}')
        if unmatched:
            progress('Replacement blocked: unmatched manual corrections require explicit reconciliation. Original evidence retained.')
            return False
        if not approve(): progress('Rebuild rejected; original evidence retained');return False
        verify()
        with store.db:
            store.db.execute('BEGIN IMMEDIATE')
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
            store.db.execute('INSERT INTO source_sorts VALUES(?,?,?,3)',(doc['id'],now,doc['source_sha256']))
            store.db.execute('UPDATE archive_documents SET sorted_at=? WHERE id=?',(now,doc['id']))
            store.db.execute('DELETE FROM source_work_v3 WHERE document_id=?',(doc['id'],))
        progress(f'Replaced document {doc["id"]} · {len(proposed)} passages')
        return True
