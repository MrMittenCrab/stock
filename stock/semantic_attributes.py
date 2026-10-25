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
    text=re.sub(r'\b(?:ended|ending) (20\d{2})(?= with\b)',r'as of december 31, \1',text)
    text=re.sub(r'\b(?:by |at )?the end of (20\d{2})\b',r'as of december 31, \1',text)
    for i,month in enumerate(MONTHS,1):
        text=re.sub(r'\b'+month+r'\s+(\d{1,2}),?\s+(20\d{2})\b',
                    lambda m:f'{m[2]}-{i:02d}-{int(m[1]):02d}',text)
    text=re.sub(r'\bq([1-4])\s*(20\d{2})\b',r'\2-q\1',text)
    return text


# A currency/quantity resembling a year is not temporal context. Use the same
# spans for extraction and quantity removal so the two views cannot disagree.
PERIOD = re.compile(r'(?<![$€£\w])(?:19|20)\d{2}(?:-\d{2}-\d{2}|-q[1-4])?\b'
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
