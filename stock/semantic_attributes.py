"""Bounded financial notation and context recovery, never a general fact parser.

Only full KPI sentences can supply deterministic equivalence. Partial parses
must never discard a geographical restriction, forecast or qualification.
"""
import json
import re

MONTHS='january february march april may june july august september october november december'.split()


def period_text(text):
    """Canonicalize explicit dates; keep flow years distinct from stock dates."""
    from .quantities import temporal_text
    text=temporal_text(text).lower()
    text=re.sub(r'\b(first|second) half (?:of )?(?:fiscal |calendar )?(20\d{2})\b',
                lambda m:m[2]+'-h'+('1' if m[1]=='first' else '2'),text)
    text=re.sub(r'\bh([12])\s*(?:fy\s*)?(20\d{2})\b',r'\2-h\1',text)
    text=re.sub(r'\b(?:ended|ending) (20\d{2})(?= with\b)',r'as of december 31, \1',text)
    text=re.sub(r'\b(?:by |at )?the end of (20\d{2})\b',r'as of december 31, \1',text)
    for i,month in enumerate(MONTHS,1):
        text=re.sub(r'\b'+month+r'\s+(\d{1,2}),?\s+(20\d{2})\b',
                    lambda m:f'{m[2]}-{i:02d}-{int(m[1]):02d}',text)
    text=re.sub(r'\bq([1-4])\s*(20\d{2})\b',r'\2-q\1',text)
    return text


# A currency/quantity resembling a year is not temporal context. Use the same
# spans for extraction and quantity removal so the two views cannot disagree.
PERIOD = re.compile(r'(?<![$€£\w])(?:19|20)\d{2}(?:-\d{2}-\d{2}|-q[1-4]|-h[12])?\b'
    r'(?!\s*(?:million|billion|thousand|bn|mw|gw|kw|usd|dollars|%|data centers)\b)', re.I)


def periods(text):
    return sorted(set(PERIOD.findall(period_text(text))))


def without_periods(text):
    return PERIOD.sub(' ',period_text(text))


def with_context(p,doc):
    """Attach available source context without rewriting evidence or citations.

    Publisher is not issuer. A document's period only resolves explicit deictic
    wording; it does not date all facts mentioned in the document.
    """
    structured=doc.get('structured_metadata') or {}
    if isinstance(structured,str):structured=json.loads(structured)
    attrs={};provenance={}
    issuer=structured.get('registrant') or structured.get('issuer')
    if issuer and re.search(r'\b(?:we|our|us)\b',p['text'],re.I):
        attrs['issuer']=issuer;provenance['issuer']={'document_id':doc.get('id'),'field':'structured_metadata.registrant/issuer'}
    period_field='report_period_end' if doc.get('type')=='Annual' and structured.get('report_period_end') else 'period_end'
    period_end=structured.get(period_field)
    if period_end and re.fullmatch(r'20\d{2}-\d{2}-\d{2}',str(period_end)) and re.search(r'\b(?:ended|ending) the year\b',p['text'],re.I):
        attrs['period']=period_end;provenance['period']={'document_id':doc.get('id'),'field':'structured_metadata.'+period_field,'deictic':'ended the year'}
    notes=[]
    for ref in p.get('location',{}).get('references',[]):
        match=re.match(r'(?i)^Notes: Figures as of ([A-Za-z]+ \d{1,2}, \d{4})\.',ref.get('text',''))
        if match and len(periods(match[1]))==1:
            notes.append((periods(match[1])[0],ref))
    if notes and len({date for date,_ in notes})==1 and not periods(p['text']) and 'period' not in attrs:
        attrs['period']=notes[0][0]
        provenance['period']={'document_id':doc.get('id'),'source_id':notes[0][1].get('source_id'),'field':'anchored Figures as of note'}
    inconsistencies=[]
    note_dates={date for date,_ in notes}
    explicit_dates=set(periods(p['text']))
    if attrs.get('period'):explicit_dates.add(attrs['period'])
    if len(note_dates)>1 or (note_dates and explicit_dates and not note_dates<=explicit_dates):
        inconsistencies.append('source_note_period')
    # Exact reference identity and statement attribution stay on the proposition.
    # Surrounding paragraphs can contain multiple periods/issuers: never union
    # every attribute found in the references into this statement.
    return dict(p,semantic_context=dict(attributes=attrs,provenance=provenance,
        reference_ids=[r.get('source_id') for r in p.get('location',{}).get('references',[])],
        speaker=p.get('speaker'),source_notes=[ref['text'] for _,ref in notes],inconsistencies=inconsistencies))


def note_restrictions(notes):
    """Only a recognized visual-footprint disclaimer is nonrestrictive.

    Unknown note tails are financial context requiring review, not permission
    to assert agreement. Do not expand a keyword blacklist to guess their scope.
    """
    restrictions=[]
    visual=(r'this (?:graphic|map) provides an illustrative representation of '
            r'(?:our|the) (?:infrastructure )?footprint and may not precisely '
            r'reflect all current locations or capacities[.]?')
    for note in notes:
        tail=re.sub(r'(?i)^Notes: Figures as of [A-Za-z]+ \d{1,2}, \d{4}\.\s*','',note).strip()
        if tail and not re.fullmatch(visual,tail.lower()):restrictions.append(tail.lower())
    return sorted(set(restrictions))


def kpi_fact(p):
    """Fully consume an unqualified issuer-level point-in-time capacity fact.

    Deliberately excludes revenue flows, free-form prose and future clauses.
    '+' is presentation notation for 'more than' only in this KPI grammar.
    """
    text=period_text(p['text']).rstrip('.').strip()
    date=r'20\d{2}-\d{2}-\d{2}'
    issuer=r'(?P<issuer>[a-z][a-z0-9]*(?:weave)?)'
    amount=r'(?P<bound>more than |over )?(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>megawatts?|gigawatts?|mw|gw)?(?P<plus>\+)?'
    metric=r'(?P<state>active|contracted) (?P<metric>power|capacity|data centers)'
    body=amount+r' (?:of )?'+metric
    patterns=[r'as of (?P<date>'+date+r'), '+issuer+r' (?:reported|had|reached) '+body,
              issuer+r' (?:reported|had|reached) '+body+r' as of (?P<date>'+date+r')',
              issuer+r' (?:as of (?P<date>'+date+r')) with '+body]
    match=next((m for pat in patterns if (m:=re.fullmatch(pat,text))),None)
    if not match:return None
    d=match.groupdict()
    if d['issuer'] in ('we','it','company','the'):return None
    if d['metric']=='data centers':
        if d['unit']:return None
        unit='count'
    else:
        if not d['unit']:return None
        unit='power'
    from decimal import Decimal
    value=Decimal(d['value'])*(1000000000 if (d['unit'] or '').startswith('g') else 1000000 if unit=='power' else 1)
    return dict(issuer=d['issuer'],period=d['date'],metric='data centers' if unit=='count' else 'power',
        state=d['state'],value=str(value.normalize()),unit=unit,bound='greater_than' if d['bound'] or d['plus'] else 'exact')


def financial_fact(p):
    """Consume one exact, asserted issuer money-flow sentence, or abstain.

    No fuzzy arithmetic, currency conversion, inferred fiscal basis, inherited
    table scale, GAAP assumption, or removal of residual clauses. A match is a
    proposition parse, not merely a bag of matching numerical attributes.
    Unqualified reported metrics only match the same unqualified definition.
    """
    text=p['text'].strip().lower()
    issuer=r'(?P<issuer>[a-z][a-z0-9]*)'
    metric=r'(?P<metric>revenue|total net sales|net sales|net income|operating income)'
    number=r'(?P<number>\d+(?:,\d{3})*(?:\.\d+)?)'
    value=r'(?P<currency>[$€£])'+number+r'\s*(?P<scale>million|billion|thousand)'
    pattern=issuer+' '+metric+r' (?:was|were|totaled) '+value+r' in fiscal (?P<year>20\d{2})[.]?'
    match=re.fullmatch(pattern,text)
    if not match:return None
    d=match.groupdict()
    if d['issuer'] in ('we','it','company','the','our','total','consolidated','adjusted',
        'annual','global','reported','actual','fiscal','calendar','net','gross'):return None
    # A capitalized word is not issuer identity ("Quarterly revenue", for
    # example). Unlisted issuers need explicit audited statement/source context.
    known={'coreweave','microsoft','openai','nvidia','amazon','google','meta','oracle','apple'}
    structured=p.get('attributes') or p.get('location',{}).get('attributes') or {}
    recovered=p.get('semantic_context',{}).get('attributes',{})
    declared=structured.get('issuer') or recovered.get('issuer')
    if d['issuer'] not in known and str(declared or '').strip().lower()!=d['issuer']:return None
    from decimal import Decimal, localcontext
    digits=d['number'].replace(',','')
    if len(digits.replace('.',''))>40:return None
    with localcontext() as context:
        context.prec=64
        value=Decimal(digits)*Decimal(10)**{'thousand':3,'million':6,'billion':9}[d['scale']]
        exact_value=format(value.normalize(),'f')
        decimals=len(digits.split('.')[1]) if '.' in digits else 0
        resolution=Decimal(10)**({'thousand':3,'million':6,'billion':9}[d['scale']]-decimals)
    return dict(issuer=d['issuer'],metric=d['metric'],definition='unqualified_reported',
        period=d['year'],year_basis='fiscal',modality='asserted',scope='issuer',
        currency=d['currency'],value=exact_value,display_resolution=format(resolution,'f'))


def contradiction_signature(p):
    """Known matching conditions for retrieval only; no relationship judgment.

    Unknown dimensions abstain. Values and polarity are deliberately absent.
    Extra detected restrictions remain in the key. Cached vectors/scores remain
    text-only; this signature is recomputed when source context changes.
    """
    from .relationships import attributes
    a=attributes(p)
    if p.get('semantic_context',{}).get('inconsistencies'):return None
    dimensions=[]
    for key,declared in (('entity','issuer'),('metric','metric'),('period','period'),('scope','scope')):
        explicit=a[key]
        structured=a.get('structured:'+declared)
        if structured and explicit and structured not in explicit:return None
        values=tuple(explicit) if explicit else ((structured,) if structured else ())
        if len(values)!=1:return None
        dimensions.append(values)
    for key in ('definition','year_basis','capacity_state','qualification','modality','modality_terms','named_entities','source_restrictions','speaker','category'):
        value=a.get(key)
        dimensions.append(tuple(value) if isinstance(value,list) else value)
    # Preserve other supplied dimensions rather than silently ignoring them.
    dimensions.append(tuple(sorted((k,v) for k,v in a.items() if k.startswith('structured:') and
        k not in ('structured:issuer','structured:metric','structured:period','structured:scope'))))
    return tuple(dimensions)
