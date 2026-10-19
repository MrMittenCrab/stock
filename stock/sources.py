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


def publish(store, doc, passages, source_hash):
    """No LLM/file I/O in this transaction. Competing sorts never replace a winner."""
    with store.db:
        store.db.execute('BEGIN IMMEDIATE')
        if completed(store, doc['id']):
            return False
        for p in passages:
            anchor=json.dumps(p['location'],sort_keys=True)
            ident=hashlib.sha256(f"{doc['id']}\0{anchor}\0{p['text']}".encode()).hexdigest()
            store.db.execute('INSERT INTO source_passages VALUES(?,?,?,?,?,?,?,?)',
                (ident,doc['id'],p['text'],p['category'],p['speaker'],anchor,
                 p['publication_date'],json.dumps(p['date_provenance'])))
            store.db.executemany('INSERT INTO source_topics VALUES(?,?)',
                [(ident,t) for t in p['topics']])
        now=time.time()
        store.db.execute('INSERT INTO source_sorts VALUES(?,?,?,2)',(doc['id'],now,source_hash))
        store.db.execute('UPDATE archive_documents SET sorted_at=? WHERE id=?',(now,doc['id']))
        store.db.execute('DELETE FROM source_sort_sections WHERE document_id=?',(doc['id'],))
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
        store.db.execute('INSERT INTO source_overrides VALUES(?,?,?) ON CONFLICT(passage_id,topic) DO UPDATE SET present=excluded.present',
                         (ident,topic,int(present)))
