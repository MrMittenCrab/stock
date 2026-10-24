"""Isolated rebuild preparation and verified unattended atomic replacement."""
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


def rebuild(store,ticker,reference,cursor_factory,progress,approve=None,review_only=False):
    sources.schema(store)
    store.db.execute('''CREATE TABLE IF NOT EXISTS source_publication_history(
      id INTEGER PRIMARY KEY, document_id INTEGER NOT NULL, retired_at REAL NOT NULL,
      payload TEXT NOT NULL)''')
    store.db.commit()
    matches=[d for d in documents(store,ticker) if str(d['id'])==reference or any(Path(f['path']).name==reference for f in d['files'])]
    if len(matches)!=1: raise ValueError('DOCUMENT must be an unambiguous Archive ID or archived filename')
    doc=matches[0]
    candidate=store.db.execute('SELECT id,markdown,manifest,quality_status FROM archive_evidence_versions WHERE document_id=? AND active=0 AND id>(SELECT COALESCE(MAX(id),0) FROM archive_evidence_versions WHERE document_id=? AND active=1) ORDER BY id DESC LIMIT 1',(doc['id'],doc['id'])).fetchone()
    if candidate:
        if candidate[3]=='needs_repair':raise ValueError('Archive candidate still needs repair; original publication retained')
        doc={**doc,'evidence_version':candidate[0],'markdown':candidate[1],'evidence':candidate[2],'quality_status':candidate[3]}
    from .sort_budget import CURRENT, check
    budget=CURRENT.get()
    if budget:budget.use_document(doc['id'])
    directory=ROOT/'.data'/'sort-locks';directory.mkdir(exist_ok=True)
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
        verify()
        from . import insights
        insights.schema(store)
        active=insights.head(store,ticker)
        splits=insights.suppressed_pairs(store,insights.load(store,active)) if active else set()
        keys={};old_keys={}
        for p in proposed:keys.setdefault(match_key(p),[]).append(p)
        for p in previous:old_keys.setdefault(match_key(p),[]).append(p)
        overrides=store.db.execute('''SELECT o.passage_id,o.topic,o.present FROM source_overrides o
            JOIN source_passages p ON p.id=o.passage_id WHERE p.document_id=?''',(doc['id'],)).fetchall()
        old={p['id']:p for p in previous};transferred=[];unmatched=[];identity_map={}
        # Identity transfer is not a semantic judgment. Both sides must have a
        # unique exact source/attribution identity, including for manual splits.
        required={ident for ident,_,_ in overrides}
        required.update(m for pair in splits for m in pair if m in old)
        if active:
            required.update(m for e in insights.load(store,active).get('relationships',[]) if e.get('provenance')=='manual' for m in (e['left'],e['right']) if m in old)
        for ident in required:
            key=match_key(old[ident])
            if len(keys.get(key,[]))!=1 or len(old_keys.get(key,[]))!=1:
                unmatched.append(ident)
            else:identity_map[ident]=sources.passage_id(doc,keys[key][0])
        if unmatched:
            raise IntegrityError('Replacement blocked: unmatched or ambiguous manual corrections/splits: '+', '.join(sorted(unmatched)))
        for ident,topic,present in overrides:transferred.append((match_key(old[ident]),topic,present))
        insight_proposal=insights.stage(store,ticker,worker,progress,new_document=(doc,proposed),identity_map=identity_map)
        review=getattr(progress,'review',progress)
        review(f"{doc['id']} · Replace · {len(previous)} → {len(proposed)} sources · {len(transferred)} corrections")
        from .insights import review_text
        details=review_text(insight_proposal)
        getattr(progress,'proposed_details',getattr(progress,'review_all',review))(details)
        if review_only:
            progress('Rebuild review only; original evidence retained')
            return True
        # --rebuild is the replacement authorization. No terminal interaction.
        verify()
        check()
        from .editorial import validate_publication
        for p in proposed: validate_publication(p)
        from .proposition_graph import validate as validate_graph
        validate_graph(insight_proposal)
        with store.db:
            store.db.execute('BEGIN IMMEDIATE')
            if insight_proposal:
                from .insights import head,snapshot as insight_snapshot
                if head(store,ticker)!=insight_proposal['parent'] or insight_snapshot(store,ticker)!=insight_proposal['snapshot']:
                    raise IntegrityError('Evidence, topics or insight groups changed during rebuild')
            if published_snapshot()!=snapshot: raise IntegrityError('Published evidence changed during rebuild')
            actual_overrides=store.db.execute('SELECT o.passage_id,o.topic,o.present FROM source_overrides o JOIN source_passages p ON p.id=o.passage_id WHERE p.document_id=?',(doc['id'],)).fetchall()
            if sorted(actual_overrides)!=sorted(overrides): raise IntegrityError('Manual corrections changed during rebuild')
            import time
            retired=dict(passages=[list(r) for r in snapshot],
                topics=[list(r) for r in store.db.execute('SELECT t.* FROM source_topics t JOIN source_passages p ON p.id=t.passage_id WHERE p.document_id=?',(doc['id'],))],
                overrides=[list(r) for r in overrides],
                sort=[list(r) for r in store.db.execute('SELECT * FROM source_sorts WHERE document_id=?',(doc['id'],))])
            store.db.execute('INSERT INTO source_publication_history(document_id,retired_at,payload) VALUES(?,?,?)',(doc['id'],time.time(),json.dumps(retired)))
            for table in ('source_overrides','source_topics'):
                store.db.execute(f'DELETE FROM {table} WHERE passage_id IN (SELECT id FROM source_passages WHERE document_id=?)',(doc['id'],))
            store.db.execute('DELETE FROM source_passages WHERE document_id=?',(doc['id'],))
            store.db.execute('DELETE FROM source_sorts WHERE document_id=?',(doc['id'],))
            # Keep replacement and activation in the same checked transaction.
            ids={}
            for p in proposed:
                anchor=json.dumps(p['location'],sort_keys=True)
                ident=hashlib.sha256(f'{doc["id"]}\0{anchor}\0{p["text"]}'.encode()).hexdigest();ids[match_key(p)]=ident
                store.db.execute('INSERT INTO source_passages VALUES(?,?,?,?,?,?,?,?)',(ident,doc['id'],p['text'],p['category'],p['speaker'],anchor,p['publication_date'],json.dumps(p['date_provenance'])))
                store.db.executemany('INSERT INTO source_topics VALUES(?,?)',[(ident,t) for t in p['topics']])
            store.db.executemany('INSERT INTO source_overrides VALUES(?,?,?)',[(ids[k],t,v) for k,t,v in transferred])
            now=time.time()
            store.db.execute('INSERT INTO source_sorts VALUES(?,?,?,5)',(doc['id'],now,doc['source_sha256']))
            store.db.execute('UPDATE archive_documents SET sorted_at=? WHERE id=?',(now,doc['id']))
            if insight_proposal:
                store.db.execute('INSERT INTO source_insight_heads VALUES(?,?) ON CONFLICT(ticker) DO UPDATE SET revision_id=excluded.revision_id',(ticker,insight_proposal['id']))
            check()
            if candidate:
                store.db.execute('UPDATE archive_evidence_versions SET active=0 WHERE document_id=?',(doc['id'],))
                store.db.execute('UPDATE archive_evidence_versions SET active=1 WHERE id=?',(candidate[0],))
            # Retain staging checkpoints and model selections for audit.
        progress(f'Replaced document {doc["id"]} · {len(proposed)} passages')
        return True
