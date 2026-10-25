"""Frozen evidence and effective topic memberships in the existing archive DB."""
import hashlib
import json
import time
from pathlib import Path
from .archive import schema as archive_schema, documents

TOPICS = ('Market', 'Product', 'Operations', 'Financials', 'Capital',
          'Organization', 'Macro', 'Valuation')
CATEGORIES = ('Management', 'Investor', 'Media')


def schema(store):
    archive_schema(store)
    store.db.execute('''CREATE TABLE IF NOT EXISTS source_correction_events(
      id INTEGER PRIMARY KEY, passage_id TEXT NOT NULL, topic TEXT NOT NULL,
      previous INTEGER, present INTEGER, action TEXT NOT NULL, created_at REAL NOT NULL)''')
    # Avoid executescript's implicit COMMIT inside snapshot-checked transactions.
    if store.db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name IN ('source_sort_sections','source_passages','source_topics','source_overrides','source_sorts')").fetchone()[0]==5:
        return
    store.db.executescript('''
    CREATE TABLE IF NOT EXISTS source_sort_sections (
      document_id INTEGER NOT NULL REFERENCES archive_documents(id),
      markdown_hash TEXT NOT NULL, section_index INTEGER NOT NULL,
      payload TEXT NOT NULL, PRIMARY KEY(document_id,markdown_hash,section_index));
    CREATE TABLE IF NOT EXISTS source_passages (
      id TEXT PRIMARY KEY, document_id INTEGER NOT NULL REFERENCES archive_documents(id),
      text TEXT NOT NULL, category TEXT NOT NULL, speaker TEXT,
      location TEXT NOT NULL, publication_date TEXT, date_provenance TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS source_document ON source_passages(document_id);
    CREATE TABLE IF NOT EXISTS source_topics (
      passage_id TEXT NOT NULL REFERENCES source_passages(id), topic TEXT NOT NULL,
      PRIMARY KEY(passage_id,topic));
    CREATE TABLE IF NOT EXISTS source_overrides (
      passage_id TEXT NOT NULL REFERENCES source_passages(id), topic TEXT NOT NULL,
      present INTEGER NOT NULL CHECK(present IN (0,1)), PRIMARY KEY(passage_id,topic));
    CREATE TABLE IF NOT EXISTS source_sorts (
      document_id INTEGER PRIMARY KEY REFERENCES archive_documents(id),
      completed_at REAL NOT NULL, source_hash TEXT NOT NULL, extraction_version INTEGER NOT NULL);
    ''')


def completed(store, document_id):
    return bool(store.db.execute('SELECT 1 FROM source_sorts WHERE document_id=?', (document_id,)).fetchone())


def passage_id(doc,p):
    anchor=json.dumps(p['location'],sort_keys=True)
    return hashlib.sha256(f"{doc['id']}\0{anchor}\0{p['text']}".encode()).hexdigest()


def publish(store, doc, passages, source_hash, extraction_version=3,insight_proposal=None):
    """No LLM/file I/O in this transaction. Competing sorts never replace a winner."""
    from .sort_budget import check
    check()
    from .editorial import validate_publication
    for p in passages: validate_publication(p)
    if insight_proposal:
        from .proposition_graph import validate as validate_graph
        validate_graph(insight_proposal)
    with store.db:
        store.db.execute('BEGIN IMMEDIATE')
        if completed(store, doc['id']):
            return False
        if insight_proposal:
            from . import insights
            if (insight_proposal.get('new_document_id')!=doc['id'] or
                insights.head(store,doc['ticker'])!=insight_proposal['parent'] or
                insights.snapshot(store,doc['ticker'])!=insight_proposal['snapshot']):
                raise ValueError('Evidence changed during document grouping')
            proposed_ids={m for g in insight_proposal['groups'] for m in g['members']}
            if not {passage_id(doc,p) for p in passages}<=proposed_ids:
                raise ValueError('Document insight membership changed')
        for p in passages:
            anchor=json.dumps(p['location'],sort_keys=True)
            ident=hashlib.sha256(f"{doc['id']}\0{anchor}\0{p['text']}".encode()).hexdigest()
            store.db.execute('INSERT INTO source_passages VALUES(?,?,?,?,?,?,?,?)',
                (ident,doc['id'],p['text'],p['category'],p['speaker'],anchor,
                 p['publication_date'],json.dumps(p['date_provenance'])))
            store.db.executemany('INSERT INTO source_topics VALUES(?,?)',
                [(ident,t) for t in p['topics']])
        now=time.time()
        store.db.execute('INSERT INTO source_sorts VALUES(?,?,?,?)',(doc['id'],now,source_hash,extraction_version))
        store.db.execute('UPDATE archive_documents SET sorted_at=? WHERE id=?',(now,doc['id']))
        if insight_proposal:
            store.db.execute('INSERT INTO source_insight_heads VALUES(?,?) ON CONFLICT(ticker) DO UPDATE SET revision_id=excluded.revision_id',
                (doc['ticker'],insight_proposal['id']))
        check()
        # Legacy checkpoints remain available for audit and recovery.
    return True


def reset(store,ticker,reference):
    schema(store)
    matches=[d for d in documents(store,ticker) if str(d['id'])==reference or
             any(reference==Path(f['path']).name for f in d['files'])]
    if len(matches)!=1:
        raise ValueError('DOCUMENT must be an unambiguous Archive ID or archived filename')
    doc=matches[0]
    if not completed(store,doc['id']): raise ValueError('Document has not been sorted')
    with store.db:
        for ident,topic,present in store.db.execute('SELECT o.* FROM source_overrides o JOIN source_passages p ON p.id=o.passage_id WHERE p.document_id=?',(doc['id'],)).fetchall():
            store.db.execute('INSERT INTO source_correction_events(passage_id,topic,previous,present,action,created_at) VALUES(?,?,?,?,?,?)',
                (ident,topic,present,None,'reset',time.time()))
        store.db.execute('DELETE FROM source_overrides WHERE passage_id IN (SELECT id FROM source_passages WHERE document_id=?)',(doc['id'],))
    return doc


def passages(store,ticker):
    schema(store)
    cursor=store.db.execute('''SELECT p.* FROM source_passages p
        JOIN archive_documents d ON d.id=p.document_id WHERE d.ticker=?
        ORDER BY p.publication_date IS NULL,p.publication_date DESC,p.document_id,p.id''',(ticker,))
    rows=[dict(zip([c[0] for c in cursor.description],r)) for r in cursor.fetchall()]
    auto={}
    for ident,topic in store.db.execute('SELECT passage_id,topic FROM source_topics'):
        auto.setdefault(ident,set()).add(topic)
    overrides={}
    for ident,topic,present in store.db.execute('SELECT passage_id,topic,present FROM source_overrides'):
        overrides.setdefault(ident,{})[topic]=present
    for row in rows:
        row['location']=json.loads(row['location'])
        row['representation']=row['location'].get('representation','verbatim')
        row['verification_state']=row['location'].get('review',{}).get('state','legacy_exact_source')
        row['date_provenance']=json.loads(row['date_provenance'])
        row['topics']=auto.get(row['id'],set()).copy()
        for topic,present in overrides.get(row['id'],{}).items():
            if present: row['topics'].add(topic)
            else: row['topics'].discard(topic)
    return rows


def set_topic(store,ident,topic,present):
    if topic not in TOPICS: raise ValueError('Unknown topic')
    if not store.db.execute('SELECT 1 FROM source_passages WHERE id=?',(ident,)).fetchone():
        raise ValueError('Unknown passage')
    with store.db:
        old=store.db.execute('SELECT present FROM source_overrides WHERE passage_id=? AND topic=?',(ident,topic)).fetchone()
        store.db.execute('INSERT INTO source_correction_events(passage_id,topic,previous,present,action,created_at) VALUES(?,?,?,?,?,?)',
            (ident,topic,old[0] if old else None,int(present),'topic',time.time()))
        store.db.execute('INSERT INTO source_overrides VALUES(?,?,?) ON CONFLICT(passage_id,topic) DO UPDATE SET present=excluded.present',
                         (ident,topic,int(present)))
