"""Disposable Phase 2 context artifacts; semantics live in docs/proposition-decontextualization.md."""
import hashlib
import json
import time
from .insights import digest, packed, passage_fingerprint as evidence_fingerprint
from .evidence import ProtocolError, IntegrityError

CONTRACT = 'stock-proposition-context-1'
GENERATION = CONTRACT + ':generation-1'
REVIEW = CONTRACT + ':review-1'
GENERATION_PROMPT = '''
Additionally return selection_key (unique nonempty string within this response) and
context for EACH selection, in the SAME response. Retain all existing selection fields.
context has exactly context_status, standalone_text, resolutions, unresolved.
context_status: unnecessary, resolved, unresolved. Stock supplies the original from
selection resolution (verbatim uses exact source text, never your invented quotation).
Unnecessary means already independently interpretable: copy original exactly, no edits.
Resolved means minimal necessary meaning-preserving edits, no unresolved items.
Unresolved means preserve original exactly, no edits, specific missing/ambiguous reasons.
resolutions: ordered [{original_span:[start,end],replacement,purpose,evidence_refs:[source ID]}].
Offsets are half-open Unicode code points in the exact ORIGINAL proposition, not source.
Edits must not overlap and must exactly reconstruct standalone_text. Every edit needs
exact supplied source IDs proving its content AND applicability to this proposition.
Do not use metadata as evidence; use anchored source text or abstain. No summary or
optional background enrichment. Resolve we/our/it/they, quoted customer versus issuer,
fiscal/calendar periods, year-end and comparison periods only when source establishes
referents. Publication date, ticker and publisher do not establish issuer or period.
Preserve speaker attribution IN the sentence, management assertions, forecast/actual/
target distinctions, active/contracted capacity, revenue/backlog/bookings, geographic
and segment scope, GAAP/adjusted bases, units, rounding, inequalities, footnotes and
material caveats. A nearby true statement does not belong automatically in this claim.
Never remove a qualification to shorten text. Missing evidence requires abstention.
'''
REVIEW_PROMPT = '''
For each review with context_proposal also return context_preservation: accepted,
rejected, unresolved; and context_reason: a specific source-based explanation.
Keep fidelity as the separate judgment of ORIGINAL support by selected references.
Judge context independently: is the proposed sentence independently interpretable,
with EXACTLY the original truth conditions in verified source context? Check EVERY
insertion/deletion/replacement and the content AND applicability of each edit's anchors.
context_references support edits only, never replace original selected citations.
Reject unsupported or meaning-changing edits even if fluent. Preserve attribution,
customer/issuer, modality, forecasts versus actuals, active versus contracted capacity,
metrics, periods (fiscal/calendar/as-of versus publication), units, rounding, scope,
GAAP/adjusted bases, table labels, footnotes, comparisons and material qualifications.
Unnecessary is an affirmative source-reviewed standalone judgment, not an empty edit list.
Unresolved proposals cannot be accepted. Do not accept partial interpretations.
Original readability remains a separate judgment of the ORIGINAL text.
'''


def split_selection(s):
    return {k:v for k,v in s.items() if k not in ('selection_key','context')}


def validate_selections(raw):
    from . import editorial
    if not isinstance(raw,list):raise ProtocolError('Selections must be an array')
    keys=set()
    for s in raw:
        if not isinstance(s,dict) or set(s)!=editorial.FIELDS|{'selection_key','context'}:
            raise ProtocolError('Context requires one keyed proposal per selection')
        key=s['selection_key']
        if not isinstance(key,str) or not key.strip() or key in keys:
            raise ProtocolError('Missing or duplicate selection key')
        keys.add(key)
        editorial.validate_selections([split_selection(s)])
        validate_proposal_shape(s['context'])
    return raw


def validate_proposal_shape(q):
    if (not isinstance(q,dict) or set(q)!={'context_status','standalone_text','resolutions','unresolved'}
        or q['context_status'] not in ('unnecessary','resolved','unresolved')
        or not isinstance(q['standalone_text'],str) or not isinstance(q['resolutions'],list)
        or not isinstance(q['unresolved'],list)
        or any(not isinstance(x,str) or not x.strip() for x in q['unresolved'])):
        raise ProtocolError('Invalid context proposal')
    for e in q['resolutions']:
        if (not isinstance(e,dict) or set(e)!={'original_span','replacement','purpose','evidence_refs'}
            or not isinstance(e['original_span'],list) or len(e['original_span'])!=2
            or any(type(i) is not int for i in e['original_span'])
            or not isinstance(e['replacement'],str) or not isinstance(e['purpose'],str) or not e['purpose'].strip()
            or not isinstance(e['evidence_refs'],list) or not e['evidence_refs']
            or any(not isinstance(x,str) for x in e['evidence_refs'])
            or len(set(e['evidence_refs']))!=len(e['evidence_refs'])):
            raise ProtocolError('Invalid context resolution')


def validate_proposal(q, original, references):
    validate_proposal_shape(q)
    state=q['context_status'];edits=q['resolutions']
    if state!='resolved':
        if edits or q['standalone_text']!=original:raise ProtocolError('Unchanged context must preserve exact original')
        if bool(q['unresolved'])!=(state=='unresolved'):raise ProtocolError('Invalid abstention reasons')
    elif not edits or q['unresolved'] or q['standalone_text']==original:raise ProtocolError('Resolved context requires complete edits')
    end=0;parts=[]
    for e in edits:
        a,z=e['original_span']
        if not 0<=a<=z<=len(original) or a<end:
            raise ProtocolError('Illegal or overlapping context offsets')
        if any(x not in references for x in e['evidence_refs']):raise ProtocolError('Unknown context evidence ID')
        parts.extend([original[end:a],e['replacement']]);end=z
    parts.append(original[end:])
    if ''.join(parts)!=q['standalone_text']:raise ProtocolError('Context edits do not reconstruct proposed text')
    # Existing quantitative guard is additional to independent semantic judgment.
    from .quantities import unsupported
    support='\n'.join(r['text'] for r in references.values())
    if unsupported(q['standalone_text'],support):raise ProtocolError('Unsupported contextual quantity')


def attach(s,p,atoms,text,doc,sha):
    from .editorial import source_reference
    q=s['context'];ids={i for e in q['resolutions'] for i in e['evidence_refs']}
    lookup={c['id']:c for c in atoms}
    if not ids<=lookup.keys():raise ProtocolError('Unknown context evidence ID')
    refs=[]
    for i in sorted(ids):
        c=lookup[i]
        if text[c['start']:c['end']]!=c['text']:raise IntegrityError('Context source offsets changed')
        refs.append(source_reference(c,doc,sha))
    validate_proposal(q,p['text'],{r['source_id']:r for r in p['location']['references']+refs})
    p['context_proposal']=q;p['context_references']=refs;p['selection_key']=s['selection_key']
    p['context_selection_digest']=digest(s)


def validate_reviews(raw, count):
    from . import editorial
    if not isinstance(raw,list) or len(raw)!=count:raise ProtocolError('Missing context review')
    for r in raw:
        if not isinstance(r,dict) or r.get('context_preservation') not in ('accepted','rejected','unresolved') or not isinstance(r.get('context_reason'),str) or not r['context_reason'].strip():
            raise ProtocolError('Invalid independent context verdict')
    editorial.validate_reviews([{k:v for k,v in r.items() if k not in ('context_preservation','context_reason')} for r in raw],count)
    return {r['index']:r for r in raw}


def save(store,doc,operation,inputs,output,contract=CONTRACT):
    key=digest([contract,operation,inputs,output]);payload=packed(dict(inputs=inputs,output=output))
    with store.db:
        store.db.execute('INSERT OR IGNORE INTO knowledge_artifacts VALUES(?,?,?,?,?,?,?,?)',
            (key,contract,doc['id'],operation,digest(inputs),payload,hashlib.sha256(payload.encode()).hexdigest(),time.time()))
    return key


def load(store,key):
    row=store.db.execute('SELECT payload,checksum FROM knowledge_artifacts WHERE id=?',(key,)).fetchone()
    if not row or hashlib.sha256(row[0].encode()).hexdigest()!=row[1]:raise IntegrityError('Missing or corrupt context artifact')
    try:data=json.loads(row[0])
    except ValueError as exc:raise IntegrityError('Invalid context artifact') from exc
    if not isinstance(data,dict) or set(data)!={'inputs','output'}:
        raise IntegrityError('Incomplete context artifact')
    return data


def passage_fingerprint(p,doc):
    """Use the existing evidence fingerprint on the same future published envelope.

    Staging/association identity must not itself make unchanged publication stale.
    """
    from .sources import passage_id
    ident=passage_id(doc,p)
    if p.get('id',ident)!=ident or p.get('document_id',doc['id'])!=doc['id']:
        raise IntegrityError('Changed published source identity')
    envelope={**p,'id':ident,'document_id':doc['id']}
    metadata={k:doc.get(k) for k in ('id','title','type','ticker','publisher','period','source_sha256','metadata_provenance')}
    metadata.update(markdown_sha256=p['location'].get('markdown_sha256'),
        original=str(doc['original']),markdown=str(doc.get('markdown') or doc['original']))
    return evidence_fingerprint(envelope,metadata)


def legacy(proposition_id,original_text,source_fingerprint=''):
    return dict(contract_version=CONTRACT,proposition_id=proposition_id,original_text=original_text,
        source_fingerprint=source_fingerprint,context_status='not_attempted',standalone_text=original_text,
        resolutions=[],unresolved=[],verification=dict(original_support='not_checked',context_preservation='not_checked',reason='No contextualization review performed',artifact_id=None))


def finalize(store,doc,p,judgment,review_inputs,generation_artifact_id):
    from .knowledge import CONTRACT as KNOWLEDGE_CONTRACT
    q=p['context_proposal'];r=legacy(digest([KNOWLEDGE_CONTRACT,p['text'],p['category'],p['speaker'],p['location']['references']]),p['text'],passage_fingerprint(p,doc))
    if generation_artifact_id is None:raise IntegrityError('Missing context generation association')
    save(store,doc,'context-selection',
        dict(generation_artifact_id=generation_artifact_id,selection_key=p['selection_key'],selection_digest=p['context_selection_digest']),
        dict(proposition_id=r['proposition_id']))
    verdict=judgment['context_preservation']
    if q['context_status']=='unresolved' and verdict=='accepted':raise ProtocolError('Cannot accept unresolved context')
    review_inputs={**review_inputs,'source_fingerprint':r['source_fingerprint']}
    artifact=save(store,doc,'context-review',review_inputs,judgment,REVIEW)
    r['verification']=dict(original_support=judgment['fidelity'],context_preservation=verdict,
        reason=judgment['context_reason'],artifact_id=artifact)
    if verdict=='accepted' and judgment['fidelity']=='supported':r.update(q)
    else:r.update(context_status='unresolved',unresolved=q['unresolved'] or [judgment['context_reason']])
    key=digest(r)
    save(store,doc,'context-record',dict(record_id=key),r)
    p['proposition_context']=r;p['context_record_id']=key
    return r


def eligible(record):
    return (record.get('contract_version')==CONTRACT and record.get('context_status') in ('unnecessary','resolved')
        and record.get('verification',{}).get('original_support')=='supported'
        and record['verification'].get('context_preservation')=='accepted')


def read(store,record_id,p,doc):
    """Checked read, including current evidence and immutable independent review binding."""
    if record_id is None:return legacy(p.get('id','legacy'),p['text'],passage_fingerprint(p,doc))
    rows=store.db.execute('SELECT id FROM knowledge_artifacts WHERE contract=? AND operation=? AND input_hash=?',
        (CONTRACT,'context-record',digest(dict(record_id=record_id)))).fetchall()
    if len(rows)!=1:raise IntegrityError('Missing or ambiguous context record')
    record=load(store,rows[0][0])['output']
    if digest(record)!=record_id or record['contract_version']!=CONTRACT or record['original_text']!=p['text'] or record['source_fingerprint']!=passage_fingerprint(p,doc):
        raise IntegrityError('Stale context record')
    artifact=load(store,record['verification']['artifact_id'])
    if artifact['inputs'].get('source_fingerprint')!=record['source_fingerprint']:
        raise IntegrityError('Unbound context approval')
    claim=artifact['inputs']['claim']
    q=claim['context_proposal'];refs={r['source_id']:r for r in claim['references']+claim['context_references']}
    validate_proposal(q,p['text'],refs)
    if claim['references']!=p['location']['references'] or claim['speaker']!=p['speaker'] or claim['category']!=p['category'] or claim['representation']!=p['location']['representation']:
        raise IntegrityError('Changed review evidence')
    if 'context_proposal' in p and (p['context_proposal']!=q or p['context_references']!=claim['context_references']):
        raise IntegrityError('Changed context proposal')
    output=artifact['output'];v=record['verification']
    if v['original_support']!=output['fidelity'] or v['context_preservation']!=output['context_preservation'] or v['reason']!=output['context_reason']:
        raise IntegrityError('Changed context verdict')
    if eligible(record) and any(record[k]!=q[k] for k in q):raise IntegrityError('Record does not match approved proposal')
    return record


def association(store,doc,passages,parent=None):
    """Build an immutable disposable manifest, with no active head or publication side effects.

    A future publisher must atomically commit its pointer with evidence/head/corrections.
    Parent is a prior manifest artifact for rollback; ambiguous evidence replacement blocks.
    """
    from .sources import passage_id
    entries={}
    for p in passages:
        record=read(store,p['context_record_id'],p,doc)
        key=passage_id(doc,p)
        if key in entries:raise IntegrityError('Ambiguous context association')
        entries[key]=dict(staging_id=record['proposition_id'],record_id=p['context_record_id'],source_fingerprint=record['source_fingerprint'])
    if parent:
        previous=load(store,parent)['output']
        if not isinstance(previous,dict) or any('record_id' not in e for e in previous.values()):
            raise IntegrityError('Invalid parent context association')
    return save(store,doc,'context-association',dict(parent=parent),entries)


def lookup(store,manifest_id,passage_id,p,doc):
    """A single immutable manifest is the lookup snapshot; pass an older ID to roll back."""
    manifest=load(store,manifest_id)
    entry=manifest['output'].get(passage_id)
    if entry is None:return legacy(passage_id,p['text'],passage_fingerprint(p,doc))
    record=read(store,entry['record_id'],p,doc)
    if record['proposition_id']!=entry['staging_id'] or record['source_fingerprint']!=entry['source_fingerprint']:
        raise IntegrityError('Invalid context association binding')
    return record


def generation_replay(ops,unit,context,allow_partial=False):
    """Reuse completed source coverage when only the transport section packing changes."""
    if unit.get('operation')!='understand':return None
    wanted={c['id']:c for c in unit['candidates']};covered=set();completed=[]
    rows=ops.store.db.execute('SELECT id FROM knowledge_artifacts WHERE document_id=? AND contract=? AND operation=? ORDER BY id',
        (ops.doc['id'],GENERATION,'context-generation-input')).fetchall()
    for row in rows:
        saved=load(ops.store,row[0]);inputs=saved['inputs']
        if inputs['document']!=ops.doc or inputs['context']!=context:continue
        previous=inputs['unit'];available={c['id']:c for c in previous['candidates']}
        overlap=wanted.keys() & available.keys()
        if not overlap or any(wanted[i]!=available[i] for i in overlap):continue
        primary=set(previous.get('primary_ids',available))
        covered.update(overlap & primary)
        completed.append((saved['output']['generation_artifact_id'],available,primary))
    if not wanted.keys()<=covered and not allow_partial:return None
    if not covered:return ([],set(wanted)) if allow_partial else None
    selected={}
    for key,available,primary in completed:
        row=ops.store.db.execute('SELECT payload,checksum FROM knowledge_artifacts WHERE id=? AND contract=?',(key,GENERATION)).fetchone()
        if not row or hashlib.sha256(row[0].encode()).hexdigest()!=row[1]:raise IntegrityError('Corrupt completed context generation')
        raw=json.loads(row[0]);validate_selections(raw)
        for selection in raw:
            if any(i not in available for i in selection['ids']):raise IntegrityError('Invalid completed selection source')
            substantive=set(selection['ids']) & primary
            if not substantive:continue
            owner=min(substantive,key=lambda i:available[i]['start'])
            if owner not in wanted:continue
            identity=digest(selection)
            selected[identity]=selection;ops.context_generations[identity]=key
    ops.verify()
    result=list(selected.values())
    return (result,set(wanted)-covered) if allow_partial else result
