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
POLICY = 'financial-conservative-3-uncalibrated'
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


# Structured extraction is a conservative veto layer, never an equivalence engine.
# Unknown structured attributes on either side prevent asserting matching scope.
PATTERNS={
    'period':r'\b(?:19|20)\d{2}\b|\bq[1-4]\b|\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b',
    'entity':r'\b(?:coreweave|microsoft|openai|nvidia|amazon|google|meta|oracle)\b',
    'metric':r'\b(?:revenue|backlog|bookings|arr|ebitda|profit|cash flow|capacity|power|debt|capex|data centers?|expense|margin)\b',
    'capacity_state':r'\b(?:active|contracted|available|planned|operational|installed)\b',
    'scope':r'\b(?:europe|asia|global|globally|us|u\.s\.|uk|inference|training|segment|consolidated)\b',
    'qualification':r'\b(?:except|excluding|including|unless|subject to|only|approximately|up to|at least|more than|less than|over|under)\b',
    'definition':r'\b(?:gaap|non-gaap|adjusted|annualized|recognized|gross|net|committed|remaining)\b',
    'numbers':r'[-+−]?\$?\d[\d,]*(?:\.\d+)?\s*(?:%|billion|million|thousand|bn|mw|gw|kw|usd|dollars)?',
}


def attributes(p):
    text=p['text'].lower()
    found={key:sorted({m.strip() for m in re.findall(pattern,text)}) for key,pattern in PATTERNS.items()}
    from .quantities import quantities
    found['numbers']=sorted((format(value.normalize(),'f'),unit,currency) for value,unit,currency in quantities(p['text']))
    found['parenthetical_numbers']=re.findall(r'\([^)]*\d[^)]*\)',p['text'])
    # Preserve previously unseen issuers/counterparties as well as familiar names.
    # This is a veto heuristic, not a named-entity recognizer or source authority.
    common=set('A An The In As At On By For From We Our It Its Revenue Backlog Bookings Active Contracted Available Planned Capacity Power Demand Customer Sales Marketing Expense Management Investor Media January February March April May June July August September October November December Q1 Q2 Q3 Q4 FY'.lower().split())
    names={name.lower() for name in re.findall(r'\b[A-Z][A-Za-z0-9]*(?:\s+(?:Inc|Corp|Ltd|LLC))?\b',p['text']) if name.lower() not in common}
    found['named_entities']=sorted(names)
    modality=re.findall(r'\b(?:forecast|forecasts|expected|expects|expect|projected|target|targets|intend|intends|planned|plans|may|might|could|risk|will)\b',text)
    found['modality']='prospective' if modality else 'asserted'
    found['modality_terms']=sorted(set(modality))
    found['speaker']=p.get('speaker')
    found['category']=p.get('category')
    # Do not mistake document publication dates for reporting periods.
    structured=p.get('attributes') or p.get('location',{}).get('attributes') or {}
    found.update({'structured:'+key:value for key,value in structured.items()})
    return found


def safeguards(a,b):
    left,right=attributes(a),attributes(b)
    conflicts=[key for key in sorted(left.keys()|right.keys()) if left.get(key)!=right.get(key)]
    if left['metric'] or right['metric'] or left['numbers'] or right['numbers']:
        for side,attrs in (('left',left),('right',right)):
            for key,alternatives in (('entity',('entity','issuer')),('period',('period','as_of')),('scope',('scope',))):
                known=bool(attrs[key]) or any(attrs.get('structured:'+k) for k in alternatives)
                if not known:conflicts.append('unknown_'+side+'_'+key)
    return conflicts


def validate_scores(row):
    if row is None:return
    if (set(row)!={'entailment','contradiction','neutral'} or
        any(not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1 for v in row.values()) or
        abs(sum(row.values())-1)>.001):
        raise ValueError('Invalid local NLI probabilities')


def decide(a,b,forward,reverse):
    validate_scores(forward);validate_scores(reverse)
    conflicts=safeguards(a,b)
    result=dict(kind='UNRESOLVED',direction=None,safeguards=conflicts,policy=POLICY,
                reason='Insufficient evidence; retain both propositions.')
    if forward is None or reverse is None:
        result['reason']='Pair exceeds model context; no truncated inference.'
        return result
    if conflicts:
        result['reason']='Material attributes differ or are unknown: '+', '.join(conflicts)
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
    key=_digest([CONTRACT,fa,fb,a['text'],b['text']])
    cached=store.db.execute('SELECT payload FROM source_nli_cache WHERE fingerprint=? AND contract=?',(key,CONTRACT)).fetchone()
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
