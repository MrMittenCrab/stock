"""Local directional inference evidence and conservative financial decision policy.

Scores are uncalibrated model evidence, not proofs. No generative model or service.
Raw inference is cached separately from the decision policy so policy revisions do
not repeat expensive inference. Source fingerprints include exact citation identity.
"""
import hashlib
import json
import math
import re
import time

MODEL = 'cross-encoder/nli-MiniLM2-L6-H768'
REVISION = 'b95119ce93d3e065de6214e38cd4a97b0f2f2c6d'
ARTIFACT = 'onnx/model.onnx'
CONTRACT = f'{MODEL}@{REVISION}:{ARTIFACT}:pair-no-truncation-512-softmax-v1'
POLICY = 'financial-compatibility-5-uncalibrated'
KINDS = {'EQUIVALENT','ENTAILS','RELATED','CONTRADICTS','UNRESOLVED'}
_BACKEND = None


def schema(store):
    store.db.execute('''CREATE TABLE IF NOT EXISTS source_nli_cache(
        fingerprint TEXT PRIMARY KEY, contract TEXT NOT NULL, payload TEXT NOT NULL)''')


def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


class LocalNLI:
    """Pinned ONNX classifier, bounded batch size, CPU execution on Intel/ARM.

    Overlength pairs receive no prediction: silently truncating a qualification
    would make financial equivalence unsafe.
    """
    def __init__(self):
        started=time.monotonic()
        try:
            import onnxruntime as ort
            from tokenizers import Tokenizer
            from huggingface_hub import snapshot_download
        except ImportError as exc:
            raise ValueError("Local semantic models require: .venv/bin/python -m pip install -e '.[semantic]'") from exc
        from .core import ROOT
        path=snapshot_download(MODEL,revision=REVISION,
            cache_dir=str(ROOT/'.data'/'embedding-models'),
            allow_patterns=['config.json','tokenizer.json',ARTIFACT])
        from pathlib import Path
        config=json.loads((Path(path)/'config.json').read_text())
        if config['id2label']!={'0':'contradiction','1':'entailment','2':'neutral'}:
            raise ValueError('Unexpected NLI label mapping')
        self.tokenizer=Tokenizer.from_file(str(Path(path)/'tokenizer.json'))
        self.tokenizer.no_truncation()
        self.tokenizer.enable_padding(pad_id=1,pad_token='<pad>')
        options=ort.SessionOptions();options.intra_op_num_threads=4
        self.session=ort.InferenceSession(str(Path(path)/ARTIFACT),sess_options=options,
                                         providers=['CPUExecutionProvider'])
        self.initialization_seconds=time.monotonic()-started
        self.inference_seconds=0.0

    def __call__(self,pairs):
        import numpy as np
        from .sort_budget import check
        result=[];started=time.monotonic()
        for offset in range(0,len(pairs),8):
            check()
            chunk=pairs[offset:offset+8]
            # Encode individually before padding to avoid any lossy length handling.
            encoded=[self.tokenizer.encode(a,b) for a,b in chunk]
            valid=[i for i,e in enumerate(encoded) if len(e.ids)<=512]
            output=[None]*len(chunk)
            if valid:
                width=max(len(encoded[i].ids) for i in valid)
                arrays={
                    'input_ids':np.array([encoded[i].ids+[1]*(width-len(encoded[i].ids)) for i in valid],dtype=np.int64),
                    'attention_mask':np.array([encoded[i].attention_mask+[0]*(width-len(encoded[i].ids)) for i in valid],dtype=np.int64),
                    'token_type_ids':np.zeros((len(valid),width),dtype=np.int64)}
                inputs={x.name:arrays[x.name] for x in self.session.get_inputs()}
                logits=self.session.run(None,inputs)[0]
                probabilities=np.exp(logits-logits.max(axis=1,keepdims=True))
                probabilities/=probabilities.sum(axis=1,keepdims=True)
                for i,row in zip(valid,probabilities):
                    output[i]=dict(zip(('contradiction','entailment','neutral'),map(float,row)))
            result.extend(output)
        self.inference_seconds+=time.monotonic()-started
        return result


def backend():
    global _BACKEND
    if _BACKEND is None:_BACKEND=LocalNLI()
    return _BACKEND


# General attribute extraction is a veto layer, not proof of equivalence.
# A separate full-sentence KPI grammar can establish narrow deterministic facts.
# Missing attributes are tracked separately from observed conflicts.
from .semantic_attributes import with_context, kpi_fact
PATTERNS={
    'period':r'\b(?:19|20)\d{2}\b|\bq[1-4]\b|\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b',
    'entity':r'\b(?:coreweave|microsoft|openai|nvidia|amazon|google|meta|oracle)\b',
    'metric':r'\b(?:revenue|backlog|bookings|arr|ebitda|profit|cash flow|capacity|power|debt|capex|data centers?|expense|margin)\b',
    'capacity_state':r'\b(?:active|contracted|available|planned|operational|installed)\b',
    'scope':r'\b(?:europe|asia|global|globally|worldwide|us|u\.s\.|uk|inference|training|segment|consolidated)\b',
    'qualification':r'\b(?:except|excluding|including|unless|subject to|only|approximately|up to|at least|more than|less than|over|under)\b',
    'definition':r'\b(?:gaap|non-gaap|adjusted|annualized|recognized|gross|net|committed|remaining)\b',
    'numbers':r'[-+−]?\$?\d[\d,]*(?:\.\d+)?\s*(?:%|billion|million|thousand|bn|mw|gw|kw|usd|dollars)?',
}


def attributes(p):
    text=p['text'].lower()
    found={key:sorted({m.strip() for m in re.findall(pattern,text)}) for key,pattern in PATTERNS.items()}
    from .quantities import quantities
    from .semantic_attributes import periods, without_periods
    found['period']=periods(p['text'])
    found['year_basis']=sorted(set(re.findall(r'\b(?:fiscal|calendar)\b',text)))
    found['numbers']=sorted((format(value.normalize(),'f'),unit,currency) for value,unit,currency in quantities(without_periods(p['text'])))
    found['parenthetical_numbers']=re.findall(r'\([^)]*\d[^)]*\)',p['text'])
    # Preserve previously unseen issuers/counterparties as well as familiar names.
    # This is a veto heuristic, not a named-entity recognizer or source authority.
    common=set('A An The In As At On By For From We Our It Its Revenue Backlog Bookings Active Contracted Available Planned Capacity Power Demand Customer Sales Marketing Expense Management Investor Media January February March April May June July August September October November December Q1 Q2 Q3 Q4 FY'.lower().split())
    names={name.lower() for name in re.findall(r'\b[A-Z][A-Za-z0-9]*(?:\s+(?:Inc|Corp|Ltd|LLC))?\b',p['text']) if name.lower() not in common}
    names-=set('As Disruption Europe Asia Globally Global In December January February March April May June July August September October November MW GW GPUs'.lower().split())
    found['named_entities']=sorted(names)
    modality=re.findall(r'\b(?:forecast|forecasts|expected|expects|expect|projected|target|targets|intend|intends|planned|plans|may|might|could|risk|will)\b',text)
    found['modality']='prospective' if modality else 'asserted'
    found['modality_terms']=sorted(set(modality))
    found['scope']=sorted({'global' if x in ('globally','worldwide') else x for x in found['scope']})
    notes=p.get('semantic_context',{}).get('source_notes',[])
    from .semantic_attributes import note_restrictions
    found['source_restrictions']=note_restrictions(notes)
    found['speaker']=p.get('speaker')
    found['category']=p.get('category')
    # Do not mistake document publication dates for reporting periods.
    structured=p.get('attributes') or p.get('location',{}).get('attributes') or {}
    for key,value in structured.items():
        normalized=str(value).strip().lower()
        if key=='scope':normalized={'globally':'global','worldwide':'global'}.get(normalized,normalized)
        if key in ('period','as_of'):
            from .semantic_attributes import period_text
            normalized=period_text(normalized)
        found['structured:'+key]=normalized

    context=p.get('semantic_context',{}).get('attributes',{})
    if not found['entity'] and context.get('issuer'):
        found['entity']=[context['issuer'].lower()]
        found['named_entities']=sorted(set(found['named_entities'])|set(found['entity']))
    if not found['period'] and context.get('period'):found['period']=[context['period']]
    # Issuer-level scope is syntactically expressed by an issuer's own metric,
    # not inferred from jointly empty geographical attributes.
    if not found['scope'] and found['entity'] and re.search(
            r'\b'+re.escape(found['entity'][0])+r"(?:'s)? (?:revenue|backlog|bookings|arr|ebitda|profit|cash flow|debt|capex|margin|generated)\b",text):
        found['scope']=['issuer']
    fact=kpi_fact(p)
    if fact:
        found.update(period=[fact['period']],entity=[fact['issuer']],named_entities=[fact['issuer']],
            metric=[fact['metric']],scope=['issuer'],numbers=[(fact['value'],fact['unit'],'')],
            qualification=[fact['bound']],capacity_state=[fact['state']])
    return found


def compatibility(a,b):
    left,right=attributes(a),attributes(b)
    conflicts=[];missing=[];agreements=[]
    for side,p in (('left',a),('right',b)):
        conflicts.extend('inconsistent_'+side+'_'+x for x in p.get('semantic_context',{}).get('inconsistencies',[]))
    ignored={'modality_terms'}
    for side,attrs in (('left',left),('right',right)):
        for key,alias in (('entity','issuer'),('period','period'),('scope','scope')):
            declared=attrs.get('structured:'+alias)
            if declared and attrs[key] and declared not in attrs[key]:
                conflicts.append('inconsistent_'+side+'_'+key)

    for key in sorted(left.keys()|right.keys()):
        if key in ignored:continue
        x,y=left.get(key),right.get(key)
        if x==y:
            if x:agreements.append(key)
        elif x and y:conflicts.append(key)
        else:missing.append(key)
    # An omitted material restriction is still insufficient for merging, but
    # it is not evidence of a positive conflict.
    required=set(missing)
    if left['metric'] or right['metric']:
        for side,attrs in (('left',left),('right',right)):
            if not attrs['entity'] and not attrs.get('structured:issuer') and not attrs.get('structured:entity'):
                required.add('unknown_'+side+'_entity')
    if left['numbers'] or right['numbers'] or any(
            m in ('revenue','backlog','bookings','arr','ebitda','debt','capex','margin')
            for m in left['metric']+right['metric']):
        for side,attrs in (('left',left),('right',right)):
            for key,alternatives in (('entity',('entity','issuer')),('period',('period','as_of')),('scope',('scope',))):
                known=bool(attrs[key]) or any(attrs.get('structured:'+k) for k in alternatives)
                if not known:required.add('unknown_'+side+'_'+key)
    return dict(conflicts=conflicts,missing=sorted(required),agreements=agreements)


def safeguards(a,b):
    check=compatibility(a,b)
    return check['conflicts']+check['missing']


def validate_scores(row):
    if row is None:return
    if (set(row)!={'entailment','contradiction','neutral'} or
        any(not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1 for v in row.values()) or
        abs(sum(row.values())-1)>.001):
        raise ValueError('Invalid local NLI probabilities')


def decide(a,b,forward,reverse):
    validate_scores(forward);validate_scores(reverse)
    comparison=compatibility(a,b)
    conflicts=comparison['conflicts']+comparison['missing']
    result=dict(kind='UNRESOLVED',direction=None,safeguards=conflicts,policy=POLICY,
                compatibility=comparison,decision_basis='nli',
                context=[a.get('semantic_context',{}),b.get('semantic_context',{})],
                reason='Insufficient evidence; retain both propositions.')
    if forward is None or reverse is None:
        result['reason']='Pair exceeds model context; no truncated inference.'
        return result
    # Literal first-conjunct projection is directional only. Extra attributes
    # from an additional conjunct cannot turn this into an equivalence merge.
    def first_conjunct(premise,hypothesis):
        return premise['text'].lower().startswith(hypothesis['text'].rstrip('.').lower()+' and ')
    def projection_compatible(premise,hypothesis):
        # Compare the literal projected clause with source context still attached.
        # Attributes of a separate conjunct cannot contradict this clause, while
        # source restrictions and attribution must continue to pass safeguards.
        projected=dict(premise,text=hypothesis['text'])
        check=compatibility(projected,hypothesis)
        return not check['conflicts'] and not check['missing']
    if forward['entailment']>=.985 and reverse['neutral']>=.95 and first_conjunct(a,b) and projection_compatible(a,b):
        result.update(kind='ENTAILS',direction='left_to_right',reason='High NLI entailment and literal first conjunct; both retained.')
        return result
    if reverse['entailment']>=.985 and forward['neutral']>=.95 and first_conjunct(b,a) and projection_compatible(b,a):
        result.update(kind='ENTAILS',direction='right_to_left',reason='High NLI entailment and literal first conjunct; both retained.')
        return result
    facts=kpi_fact(a),kpi_fact(b)
    fact_compatible=(not comparison['conflicts'] and
        (not comparison['missing'] or (comparison['missing']==['speaker'] and
         a.get('category')==b.get('category')=='Management')))
    if facts[0] and facts[0]==facts[1] and fact_compatible:
        result.update(kind='EQUIVALENT',decision_basis='complete_kpi_parse',
            reason='Complete issuer capacity KPI parses agree; source speaker attribution remains independently preserved.',
            normalized_fact=facts[0])
        return result
    if conflicts:
        result['reason']='Conflicts: '+', '.join(comparison['conflicts'])+'; missing context: '+', '.join(comparison['missing'])
        return result
    # Conservative provisional cutoffs; these are NOT empirical calibration.
    fe,re=forward['entailment']>=.985,reverse['entailment']>=.985
    if fe and re:
        result.update(kind='EQUIVALENT',reason='High bidirectional entailment; no detected financial mismatch.')
    elif fe and reverse['neutral']>=.95:
        result.update(kind='ENTAILS',direction='left_to_right',reason='Directional entailment evidence; both propositions retained.')
    elif re and forward['neutral']>=.95:
        result.update(kind='ENTAILS',direction='right_to_left',reason='Directional entailment evidence; both propositions retained.')
    elif min(forward['contradiction'],reverse['contradiction'])>=.985:
        attrs=attributes(a)
        if attrs['entity'] and attrs['metric'] and attrs['period']:
            result.update(kind='CONTRADICTS',reason='Bidirectional contradiction evidence under matching detected conditions.')
    elif min(forward['neutral'],reverse['neutral'])>=.95:
        result.update(kind='RELATED',reason='Retrieved semantic neighborhood; bidirectional neutrality evidence.')
    return result


def judge(store,a,b,fa,fb,infer=None):
    schema(store)
    key=_digest([CONTRACT,a['text'],b['text']])
    legacy_key=_digest([CONTRACT,fa,fb,a['text'],b['text']])
    cached=store.db.execute('SELECT payload FROM source_nli_cache WHERE fingerprint=? AND contract=?',(key,CONTRACT)).fetchone()
    # Upgrade the old source-keyed cache lazily. Model outputs depend only on
    # exact ordered texts; source/context freshness belongs to the decision.
    if not cached:
        cached=store.db.execute('SELECT payload FROM source_nli_cache WHERE fingerprint=? AND contract=?',(legacy_key,CONTRACT)).fetchone()
        if cached:
            with store.db:
                store.db.execute('INSERT OR REPLACE INTO source_nli_cache VALUES(?,?,?)',(key,CONTRACT,cached[0]))
    started=time.monotonic()
    if cached:
        raw=json.loads(cached[0]);hit=True
    else:
        predictor=infer if infer is not None else backend()
        raw=predictor([(a['text'],b['text']),(b['text'],a['text'])]);hit=False
        if not isinstance(raw,list) or len(raw)!=2:raise ValueError('Two directional predictions required')
        for scores in raw:validate_scores(scores)
        with store.db:
            store.db.execute('INSERT OR REPLACE INTO source_nli_cache VALUES(?,?,?)',(key,CONTRACT,json.dumps(raw)))
    if not isinstance(raw,list) or len(raw)!=2:raise ValueError('Corrupt NLI cache')
    result=decide(a,b,*raw)
    result.update(scores=dict(left_to_right=raw[0],right_to_left=raw[1]),
                  model=CONTRACT,source_fingerprints=[fa,fb],inference_key=key,
                  provenance='local_nli',cache_hit=hit,
                  inference_count=0 if hit else sum(r is not None for r in raw),
                  elapsed_seconds=time.monotonic()-started)
    return result
