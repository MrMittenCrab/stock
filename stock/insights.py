"""Reversible, audited semantic views over immutable source evidence.

Retrieval is a workload heuristic, never an equivalence decision. Missing decisions
and uncertainty leave separate insights. No transitive closure of pair judgments.
"""
import hashlib
import json
import re
import time
from collections import Counter, defaultdict
from . import sources

CONTRACT='insights-1'
NEIGHBORS=8
# Legacy retrieval/packing helpers below support historical benchmark reproduction.
# Active staging is delegated exclusively to proposition_graph and local NLI.


def packed(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'))


def digest(value):
    return hashlib.sha256(packed(value).encode()).hexdigest()


def schema(store):
    sources.schema(store)
    store.db.executescript('''
    CREATE TABLE IF NOT EXISTS source_semantic_cache (
      fingerprint TEXT PRIMARY KEY, contract TEXT NOT NULL, payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS source_insight_revisions (
      id TEXT PRIMARY KEY, ticker TEXT NOT NULL, created_at REAL NOT NULL,
      payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS source_model_calls (
      id INTEGER PRIMARY KEY, document_id INTEGER, recorded_at REAL, payload TEXT);
    CREATE TABLE IF NOT EXISTS source_insight_heads (
      ticker TEXT PRIMARY KEY, revision_id TEXT NOT NULL REFERENCES source_insight_revisions(id));
    ''')


def passage_fingerprint(p,doc):
    # Topics/overrides affect visibility, not factual identity; edits reuse judgments.
    return digest([CONTRACT,{k:p.get(k) for k in ('id','document_id','text','category','speaker','publication_date','date_provenance','location')},doc])


def snapshot(store,ticker):
    rows=sources.passages(store,ticker)
    from .archive import documents
    docs=documents(store,ticker)
    return digest([rows_to_json(rows),docs])


def rows_to_json(rows):
    return [{**p,'topics':sorted(p['topics'])} for p in rows]


def head(store,ticker):
    row=store.db.execute('SELECT revision_id FROM source_insight_heads WHERE ticker=?',(ticker,)).fetchone()
    return row[0] if row else None


def load(store,ident):
    row=store.db.execute('SELECT payload FROM source_insight_revisions WHERE id=?',(ident,)).fetchone()
    if not row:raise ValueError('Unknown insight revision')
    p=json.loads(row[0])
    from .proposition_graph import validate as validate_graph
    validate_graph(p)
    if p['contract']!=CONTRACT:raise ValueError('Unsupported insight contract')
    return p


STOP=set('the a an and or to of in our we is are was were for as by with that this it its has have had on at from be been coreweave company'.split())


def tokens(text):
    # A small transparent inverted index, no embedding infrastructure.
    return set(re.findall(r'[a-z0-9]+',text.lower()))-STOP


def retrieve(rows):
    postings=defaultdict(list)
    terms={p['id']:tokens(p['text']) for p in rows}
    for p in rows:
        for t in terms[p['id']]:postings[t].append(p['id'])
    lookup={p['id']:p for p in rows};pairs=set()
    for p in rows:
        scores=Counter()
        for term in sorted(terms[p['id']],key=lambda t:(len(postings[t]),t))[:12]:
            # Very broad tokens are poor retrieval signals. Sampling is deterministic.
            for other in postings[term][:128]:
                if other!=p['id']:scores[other]+=1/len(postings[term])
        ranked=sorted(scores,key=lambda ident:(-scores[ident],ident))
        plausible=[ident for ident in ranked if terms[p['id']] & terms[ident]]
        for ident in plausible[:NEIGHBORS]:pairs.add(tuple(sorted((p['id'],ident))))
    return sorted(pairs)


def evidence_payload(p,doc):
    loc=p['location']
    return dict(id=p['id'],text=p['text'],category=p['category'],speaker=p['speaker'],
        publication_date=p['publication_date'],document=doc,
        section=loc.get('section'),turn=loc.get('turn'),
        evidence=[{k:r.get(k) for k in ('text','section','turn','page')} for r in loc.get('references',[dict(text=p['text'],**{k:loc.get(k) for k in ('section','turn','page')})])],
        review=loc.get('review',{'state':'legacy_exact_source'}))


def comparison_payload(pairs):
    """Send shared statements, document context and source fragments only once."""
    statements={};documents={};evidence={};links=[]
    for pair in pairs:
        links.append(dict(id=pair['id'],left=pair['left']['id'],right=pair['right']['id']))
        for p in (pair['left'],pair['right']):
            doc=p['document'];documents[str(doc['id'])]=doc
            refs=[]
            for r in p['evidence']:
                key=digest(r);evidence[key]=r;refs.append(key)
            statements[p['id']]={**p,'document':str(doc['id']),'evidence':refs}
    return dict(pairs=links,statements=statements,documents=documents,evidence=evidence)


def validate(raw,pairs):
    from .evidence import ProtocolError
    required={'pair','equivalent','relation','dimensions_agree','information_preserved','reason','differences'}
    if not isinstance(raw,list) or len(raw)!=len(pairs):raise ProtocolError('One semantic judgment required per pair')
    allowed={p['id'] for p in pairs};results={}
    for r in raw:
        if (not isinstance(r,dict) or set(r)!=required or not isinstance(r['pair'],str)
            or r['pair'] not in allowed or r['pair'] in results
            or any(type(r[k]) is not bool for k in ('equivalent','dimensions_agree','information_preserved'))
            or r['relation'] not in ('repeated_assertion','independent_corroboration','unknown','different')
            or not isinstance(r['reason'],str) or not r['reason'].strip()
            or not isinstance(r['differences'],list) or any(not isinstance(x,str) for x in r['differences'])):
            raise ProtocolError('Invalid semantic judgment')
        # Never accept a merge which the judgment itself qualifies.
        if r['equivalent'] and (not r['dimensions_agree'] or not r['information_preserved'] or r['differences'] or r['relation']=='different'):
            raise ProtocolError('Equivalence contradicts preservation assessment')
        results[r['pair']]=r
    return results


def identical_support(a,b):
    if any(a.get(k)!=b.get(k) for k in ('document_id','text','category','speaker','publication_date')):return False
    def anchors(p):
        loc=p['location']
        return loc.get('references') or [{k:loc.get(k) for k in ('markdown_sha256','sha256','start','end','section','turn')}]
    return anchors(a)==anchors(b)


def suppressed_pairs(store,previous):
    """Recover old manual splits once, without modifying historical revisions."""
    from itertools import combinations
    suppressed=set();ancestor=previous;seen=set()
    while ancestor:
        if 'suppressed_pairs' in ancestor:
            suppressed.update(tuple(pair) for pair in ancestor['suppressed_pairs']);break
        parent_id=ancestor.get('parent')
        if not parent_id or parent_id in seen:break
        seen.add(parent_id);prior=load(store,parent_id)
        if ancestor.get('action')=='ungroup':
            for group in prior['groups']:
                if group['id']==ancestor.get('ungrouped'):
                    suppressed.update(tuple(sorted(pair)) for pair in combinations(group['members'],2))
        ancestor=prior
    return suppressed


def valid_cached_decision(r):
    # insights-1 used to persist these as negative decisions without a review.
    # Keep real judgments under the same contract and exact source identities.
    return not (r.get('reason','').startswith(('Unchanged evidence without a verified equivalence',
        'Full evidence exceeds comparison budget')))


def historical_backlog_count(store,retrieved,fingerprints,incoming,judgments,suppressed):
    unresolved=0
    for a,b in retrieved:
        if a in incoming or b in incoming or (a,b) in judgments or (a,b) in suppressed:continue
        key=digest([CONTRACT,*sorted((fingerprints[a],fingerprints[b]))])
        cached=store.db.execute('SELECT payload FROM source_semantic_cache WHERE fingerprint=? AND contract=?',(key,CONTRACT)).fetchone()
        if not cached or not valid_cached_decision(json.loads(cached[0])):unresolved+=1
    return unresolved


def stage(store,ticker,cursor=None,progress=print,new_document=None,new_documents=None,identity_map=None,refine=False):
    # cursor is retained in the call signature for extraction pipeline compatibility.
    # No semantic operation calls it.
    from .proposition_graph import stage as graph_stage
    return graph_stage(store,ticker,progress,new_document,new_documents,identity_map,refine)


def correct_relationship(store,ticker,left,right,kind,reason,direction=None):
    from .proposition_graph import correct
    return correct(store,ticker,left,right,kind,reason,direction)


def save_revision(store,proposal):
    from .proposition_graph import validate as validate_graph
    validate_graph(proposal)
    # Identical substantive proposals reuse a deterministic revision ID. All historical rows remain.
    identity={k:v for k,v in proposal.items() if k not in ('model_requests','cached_decisions','deterministic_decisions')}
    proposal={**proposal,'id':digest(identity)}
    from .sort_budget import check
    check()
    with store.db:
        store.db.execute('INSERT OR IGNORE INTO source_insight_revisions VALUES(?,?,?,?)',
            (proposal['id'],proposal['ticker'],time.time(),packed(proposal)))
    return proposal


def activate(store,revision_id):
    from .sort_budget import check
    check()
    schema(store);p=load(store,revision_id)
    if p.get('preview_only'):raise ValueError('Preview proposal cannot be activated')
    if p.get('new_document_id'):raise ValueError('Document proposal must be activated atomically with publication')
    with store.db:
        store.db.execute('BEGIN IMMEDIATE')
        if head(store,p['ticker'])!=p['parent'] or snapshot(store,p['ticker'])!=p['snapshot']:
            raise ValueError('Evidence, topics or active grouping changed; stage again')
        check()
        store.db.execute('INSERT INTO source_insight_heads VALUES(?,?) ON CONFLICT(ticker) DO UPDATE SET revision_id=excluded.revision_id',
            (p['ticker'],revision_id))
        check()
    return True


def current(store,ticker):
    schema(store)
    active=head(store,ticker)
    if not active:return False
    p=load(store,active)
    from .proposition_graph import GRAPH_CONTRACT
    from .relationships import POLICY,CONTRACT as nli_contract
    from .semantic_map import CONTRACT as embedding_contract
    model_state=p.get('semantic_map') or {}
    if (p.get('graph_contract')!=GRAPH_CONTRACT or model_state.get('decision_policy')!=POLICY
        or model_state.get('inference_model')!=nli_contract or model_state.get('model')!=embedding_contract):return False
    from .archive import documents
    docs={d['id']:{k:d.get(k) for k in ('id','title','type','publisher','period','publication_date','source_sha256','metadata_provenance')} for d in documents(store,ticker)}
    rows=sources.passages(store,ticker)
    return p.get('fingerprints')=={r['id']:passage_fingerprint(r,docs[r['document_id']]) for r in rows}


def entries(store,ticker,document_id=None,topic=None):
    schema(store);rows=sources.passages(store,ticker);lookup={p['id']:p for p in rows}
    active=head(store,ticker);revision=load(store,active) if active else {}
    groups=revision.get('groups',[])
    relationships=revision.get('relationships',[])
    assigned=set();result=[]
    def emit(members,g=None):
        members=[lookup[m] for m in members if m in lookup and m not in assigned]
        assigned.update(p['id'] for p in members)
        members=[p for p in members if (document_id is None or p['document_id']==document_id) and
            (topic is None or (not p['topics'] if topic=='Unclassified' else topic in p['topics']))]
        if not members:return
        canonical=next((p for p in members if g and p['id']==g['canonical']),members[0])
        result.append({**canonical,'id':g['id'] if g and len(g['members'])>1 else canonical['id'],
            'members':members,'topics':set().union(*(p['topics'] for p in members)),
            'relationships':[dict(e,other=lookup.get(e['right'] if e['left'] in {m['id'] for m in members} else e['left'])) for e in relationships if any(m['id'] in (e['left'],e['right']) for m in members) and e['left'] in lookup and e['right'] in lookup],
            'basis':g.get('basis',[]) if g else [],'total_members':sum(m in lookup for m in g['members']) if g else 1})
    for g in groups:emit(g['members'],g)
    for p in rows:
        if p['id'] not in assigned:emit([p['id']])
    return result


def ungroup(store,ticker,group_id):
    schema(store);active=head(store,ticker)
    if not active:raise ValueError('No active insight grouping')
    previous=load(store,active);groups=[];found=False
    suppressed=suppressed_pairs(store,previous)
    for g in previous['groups']:
        if g['id']==group_id:
            found=True
            from itertools import combinations
            suppressed.update(tuple(sorted(pair)) for pair in combinations(g['members'],2))
            groups.extend(dict(id='i:'+digest([m])[:24],members=[m],canonical=m,basis=[]) for m in g['members'])
        else:groups.append(g)
    if not found:raise ValueError('Unknown insight group')
    relationships=[dict(e,kind='UNRESOLVED',direction=None,provenance='manual_split',reason='Manual ungroup retained.') if tuple(sorted((e['left'],e['right']))) in suppressed and e['kind']=='EQUIVALENT' else e for e in previous.get('relationships',[])]
    p=save_revision(store,{**previous,'relationships':relationships,'parent':active,'snapshot':snapshot(store,ticker),'groups':groups,'action':'ungroup','ungrouped':group_id,'new_document_id':None,'suppressed_pairs':sorted(suppressed)})
    activate(store,p['id']);return p


def review_text(proposal):
    lookup={p['id']:p for p in proposal['evidence']}
    local_count=sum(g['canonical'] in lookup for g in proposal['groups'])
    lines=[f"Existing {proposal['passage_count']} passages · Proposed {local_count} distinct insights",
        f"{proposal['comparison_count']} reviewed pairs · {proposal['model_requests']} Cursor deduplication requests · {proposal['cached_decisions']} reused decisions",
        "Local graph: "+packed(proposal.get('semantic_map',{})),
        f"Manual edits: {len(proposal['manual_edits'])}; all retained on original member IDs, no topic propagation.",
        'Possible information loss: no evidence removed; canonical is one member. Model equivalence may still be wrong; inspect all groups.',
        f"Scope: {proposal.get('grouping_scope','legacy')}; unresolved historical retrieval candidates: {proposal.get('historical_backlog_pairs','unknown')}. No global completeness claim.",
        'Ungrouping creates an audited revision. Uncertain/nonretrieved pairs remain separate.']
    for g in proposal['groups']:
        if g['canonical'] not in lookup:continue
        lines.append('\n'+('Equivalent group' if len(g['members'])>1 else 'Separate insight')+' · '+g['id'])
        lines.append('Canonical: '+lookup[g['canonical']]['text'])
        for ident in g['members']:
            p=lookup[ident]
            from .editorial import inspection
            lines.append(f"  Member {ident} · document {p['document_id']} · {p['publication_date']} · {', '.join(p['topics'])}")
            lines.extend([p['text'],inspection(p)])
        lines.extend(f"  {b['relation']} · {b['reason']} · information preserved={b['information_preserved']}" for b in g['basis'])
    lines.append('\nMaterial differences retained:')
    lines.extend(' / '.join(d['members'])+' · '+d['reason']+' · '+'; '.join(d['differences']) for d in proposal['differences'])
    return '\n'.join(lines)
