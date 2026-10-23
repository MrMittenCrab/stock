"""Notation checks only. Equivalent quantities never prove equivalent propositions."""
import re
from decimal import Decimal

SCALES={'k':3,'thousand':3,'m':6,'million':6,'b':9,'billion':9,'t':12,'trillion':12}
PATTERN=re.compile(r'(?=[+−($€£0-9-]|negative)(?P<negative>negative\s+)?(?P<sign>[+−-])?\s*(?P<currency>[$€£])?\s*(?P<paren>\()?\s*(?P<number>\d+(?:,\d{3})*(?:\.\d+)?)\s*(?(paren)\))\s*(?P<unit>basis points|bps|percent(?:age)?|%|[KMGT]Wh?|[KMGT]W|trillion|billion|million|thousand|[KMBT](?![a-zA-Z]))?',re.I)


def temporal_text(text):
    text=re.sub(r"(?i)\bQ([1-4])\s*FY\s*['’]?(20\d{2}|\d{2})\b",lambda m:'Q'+m[1]+' '+m[2],text)
    ordinals={'first':'1','second':'2','third':'3','fourth':'4'}
    text=re.sub(r"(?i)\b(first|second|third|fourth) (?:fiscal )?quarter (?:of )?(?:FY\s*)?['’]?(20\d{2}|\d{2})\b",lambda m:'Q'+ordinals[m[1].lower()]+' '+m[2],text)
    return text


def quantities(text):
    text=temporal_text(text)
    text=re.sub(r'<[^>]*>',' ',text).replace('\\','').replace('*','')
    for word,symbol in [('kilowatts','kW'),('megawatts','MW'),('gigawatts','GW'),('terawatts','TW'),('megawatt-hours','MWh'),('gigawatt-hours','GWh')]:
        text=re.sub(r'(?i)\b'+word+r'\b',symbol,text)
    # Fiscal notation is deterministic presentation, not an inference of period.
    text=re.sub(r"(?i)\b(FY|Q[1-4])\s*['’]?(\d{2})(?!\d)",lambda m:m[1]+' 20'+m[2],text)
    text=re.sub(r'(?i)\bQ[1-4](?=\s*20\d{2})','quarter ',text)
    default=re.search(r'(?i)(?:\bin |[$€£]\s*)(thousands?|millions?|billions?)\b',text)
    out=[]
    for m in PATTERN.finditer(text):
        value=Decimal(m['number'].replace(',',''))
        if m['negative'] or m['sign'] in ('-','−') or m['paren']:value=-value
        unit=(m['unit'] or '').lower();currency=m['currency'] or ''
        if unit in SCALES:value*=Decimal(10)**SCALES[unit];unit='money' if currency else 'scalar'
        elif unit in ('%','percent','percentage'):value/=100;unit='ratio'
        elif unit in ('basis points','bps'):value/=10000;unit='ratio'
        elif re.fullmatch(r'[kmgt]wh?',unit):
            value*=Decimal(10)**{'k':3,'m':6,'g':9,'t':12}[unit[0]];unit='energy' if unit.endswith('h') else 'power'
        elif default and (currency or not Decimal(1900)<=value<=Decimal(2099)):
            # A detached scale header creates a possible interpretation, never
            # changes every unrelated count. Independent review resolves its scope.
            if not currency:out.append((value,'scalar',''))
            value*=Decimal(10)**SCALES[default[1].lower().rstrip('s')];unit='money'
        else:unit='money' if currency else 'scalar'
        out.append((value,unit,currency))
    return out


def periods(text):
    text=temporal_text(text)
    result=set()
    for m in re.finditer(r"(?i)\bQ([1-4])\s*['’]?(20\d{2}|\d{2})\b",text):
        result.add((int(m[2])+2000 if len(m[2])==2 else int(m[2]),int(m[1])))
    months={'march':1,'june':2,'september':3,'december':4}
    for m in re.finditer(r'(?i)(?:three months|quarter) ended (March|June|September|December)\s+(?:30|31)',text):
        for year in re.findall(r'\b20\d{2}\b',text[m.end():m.end()+400]):result.add((int(year),months[m[1].lower()]))
    return result


def unsupported(claim,support):
    available=quantities(support)
    def compatible(q,s):
        if q[0]!=s[0]:return False
        if q[2] and s[2] and q[2]!=s[2]:return False
        # Unspecified source unit needs semantic review (tables/headings), not a guess.
        return q[1]==s[1] or s[1]=='scalar' or (q[1]=='scalar' and s[1]=='money')
    return ([q for q in quantities(claim) if not any(compatible(q,s) for s in available)]
            +list(periods(claim)-periods(support)))
