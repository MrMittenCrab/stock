"""Frozen, uncalibrated CPU model comparison. Never connects to a Stock DB.

Downloads pretrained artifacts only; all inference is local. Raw scores and
per-case policy decisions are committed so numerical proofs cannot hide model
failures. Fixture labels are frozen before first inference, not edited for scores.
"""
import argparse
import gc
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
import time
import types

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from stock import relationships as rel

MODELS=[(rel.MODEL,rel.REVISION),
 ('cross-encoder/nli-distilroberta-base','b14d131f9d32668a5e6a982729b57ff6ed5dfcbd'),
 ('cross-encoder/nli-deberta-v3-small','fa2804872c3b4bd748f38c0185cc85775361e735')]
FIXTURE=ROOT/'tests/fixtures/financial-model-comparison-v1.json'
FROZEN_SHA='e178d06f9811f656c2ca3e9d426f58eb94291951b96d56c2bf18c567a982ef54'


def baseline_module(name):
    module=types.ModuleType('stock._baseline_'+name)
    exec(compile(subprocess.check_output(['git','show','0893253:stock/'+name+'.py'],cwd=ROOT),'<baseline '+name+'>','exec'),module.__dict__)
    return module


def summarize(rows,field):
    kinds=('EQUIVALENT','ENTAILS','RELATED','CONTRADICTS','UNRESOLVED')
    def correct(r):
        d=r[field]
        return d['kind']==r['gold'] and (r['gold']!='ENTAILS' or d.get('direction')=='left_to_right')
    material=[r for r in rows if r['gold'] in ('EQUIVALENT','ENTAILS','CONTRADICTS')]
    asserted=[r for r in rows if r[field]['kind'] in ('EQUIVALENT','ENTAILS','CONTRADICTS')]
    return dict(total=len(rows),correct=sum(map(correct,rows)),accuracy=sum(map(correct,rows))/len(rows),
        asserted_precision=sum(map(correct,asserted))/len(asserted) if asserted else None,
        material_recall=sum(map(correct,material))/len(material) if material else None,
        missed_relationships=sum(not correct(r) for r in material),
        false_merges=sum(r['gold']!='EQUIVALENT' and r[field]['kind']=='EQUIVALENT' for r in rows),
        by_kind={k:dict(gold=sum(r['gold']==k for r in rows),predicted=sum(r[field]['kind']==k for r in rows),
            correct=sum(correct(r) and r['gold']==k for r in rows),
            precision=(sum(correct(r) and r['gold']==k for r in rows)/sum(r[field]['kind']==k for r in rows)) if any(r[field]['kind']==k for r in rows) else None,
            recall=(sum(correct(r) and r['gold']==k for r in rows)/sum(r['gold']==k for r in rows)) if any(r['gold']==k for r in rows) else None) for k in kinds})


def raw_decision(forward,reverse):
    if forward['entailment']>=.985 and reverse['entailment']>=.985:return dict(kind='EQUIVALENT')
    if forward['entailment']>=.985 and reverse['neutral']>=.95:return dict(kind='ENTAILS',direction='left_to_right')
    if reverse['entailment']>=.985 and forward['neutral']>=.95:return dict(kind='ENTAILS',direction='right_to_left')
    if min(forward['contradiction'],reverse['contradiction'])>=.985:return dict(kind='CONTRADICTS')
    if min(forward['neutral'],reverse['neutral'])>=.95:return dict(kind='RELATED')
    return dict(kind='UNRESOLVED')


def model_predictions(model,revision,pairs):
    import numpy as np
    import onnxruntime as ort
    from tokenizers import Tokenizer
    from huggingface_hub import snapshot_download
    started=time.monotonic()
    path=Path(snapshot_download(model,revision=revision,cache_dir=str(ROOT/'.data/embedding-models'),
        allow_patterns=['config.json','tokenizer.json','onnx/model.onnx'],local_files_only=True))
    config=json.loads((path/'config.json').read_text())
    labels=[config['id2label'][str(i)].lower() for i in range(3)]
    if set(labels)!={'entailment','contradiction','neutral'}:raise ValueError(labels)
    tokenizer=Tokenizer.from_file(str(path/'tokenizer.json'));tokenizer.no_truncation();tokenizer.no_padding()
    options=ort.SessionOptions();options.intra_op_num_threads=4
    session=ort.InferenceSession(str(path/'onnx/model.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
    init=time.monotonic()-started
    def predict():
        raw=[];lengths=[];started=time.monotonic()
        for offset in range(0,len(pairs),8):
            encoded=[tokenizer.encode(a,b) for a,b in pairs[offset:offset+8]]
            if any(len(e.ids)>512 for e in encoded):raise ValueError('Overlength comparison; never truncate')
            lengths.extend(len(e.ids) for e in encoded);width=max(len(e.ids) for e in encoded)
            arrays={name:np.array([getattr(e,attr)+[pad]*(width-len(e.ids)) for e in encoded],dtype=np.int64)
                for name,attr,pad in [('input_ids','ids',config['pad_token_id']),('attention_mask','attention_mask',0),('token_type_ids','type_ids',0)]}
            logits=session.run(None,{x.name:arrays[x.name] for x in session.get_inputs()})[0]
            prob=np.exp(logits-logits.max(axis=1,keepdims=True));prob/=prob.sum(axis=1,keepdims=True)
            raw.extend(dict(zip(labels,map(float,row))) for row in prob)
        return raw,time.monotonic()-started,lengths
    raw,first,lengths=predict()
    _,warm,_=predict()
    return raw,dict(model=model,revision=revision,artifact='onnx/model.onnx',artifact_bytes=(path/'onnx/model.onnx').stat().st_size,
        cpu_threads=4,batch_size=8,directional_predictions=len(pairs),max_tokens=max(lengths),
        initialization_seconds=init,first_inference_seconds=first,warm_inference_seconds=warm,
        milliseconds_per_direction=1000*warm/len(pairs),label_order=labels)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--rescore',type=Path);args=parser.parse_args()
    if hashlib.sha256(FIXTURE.read_bytes()).hexdigest()!=FROZEN_SHA:raise ValueError('Frozen fixture modified')
    fixture=json.loads(FIXTURE.read_text());old=baseline_module('relationships')
    pairs=[pair for c in fixture['cases'] for pair in [(c['left'],c['right']),(c['right'],c['left'])]]
    reports=[]
    saved=json.loads(args.rescore.read_text()) if args.rescore else None
    if saved and saved['fixture_sha256']!=FROZEN_SHA:raise ValueError('Raw score fixture mismatch')
    for model,revision in MODELS:
        if saved:
            prior=next(m for m in saved['models'] if m['cost']['model']==model and m['cost']['revision']==revision)
            raw=[c['raw'][key] for c in prior['cases'] for key in ('left_to_right','right_to_left')];cost=prior['cost']
            if [(c['id'],c['left'],c['right'],c['gold']) for c in prior['cases']]!=[(c['id'],c['left'],c['right'],c['gold']) for c in fixture['cases']]:raise ValueError('Raw case identity mismatch')
        else:raw,cost=model_predictions(model,revision,pairs)
        rows=[]
        for i,c in enumerate(fixture['cases']):
            a,b=[dict(text=c[key],category='Management',speaker=None,location={}) for key in ('left','right')]
            forward,reverse=raw[2*i:2*i+2]
            # Separate diagnostic ablation: supply only issuer identity for
            # explicit names. This is not a change to the frozen bare-text set.
            def issuer_context(p):
                names=re.findall(r'\b(?:Adobe|Salesforce|Intel|Netflix)\b',p['text'])
                return dict(p,attributes={'issuer':names[0]}) if len(set(names))==1 else p
            ca,cb=issuer_context(a),issuer_context(b)
            rows.append(dict(c,issuer_context_before=old.decide(ca,cb,forward,reverse),
                issuer_context_after=rel.decide(ca,cb,forward,reverse),raw=dict(left_to_right=forward,right_to_left=reverse),
                raw_gate=raw_decision(forward,reverse),before=old.decide(a,b,forward,reverse),after=rel.decide(a,b,forward,reverse)))
        # Directional argmax is meaningful only where gold specifies an NLI
        # relation. UNRESOLVED is a policy abstention, not an NLI neutral label.
        supported=[r for r in rows if r['gold'] in ('EQUIVALENT','ENTAILS','CONTRADICTS','RELATED')]
        hit=0
        for r in supported:
            expected={'EQUIVALENT':['entailment']*2,'ENTAILS':['entailment','neutral'],
                'CONTRADICTS':['contradiction']*2,'RELATED':['neutral']*2}[r['gold']]
            hit+=sum(max(s,key=s.get)==e for s,e in zip(r['raw'].values(),expected))
        negatives=[r for r in rows if r['gold']!='EQUIVALENT']
        argmax_equivalents=[r for r in rows if all(max(score,key=score.get)=='entailment' for score in r['raw'].values())]
        risk=dict(non_equivalent_cases=len(negatives),argmax_equivalence_predictions=len(argmax_equivalents),
            argmax_false_equivalences=sum(r['gold']!='EQUIVALENT' for r in argmax_equivalents),
            confident_raw_false_equivalences=sum(r['gold']!='EQUIVALENT' and r['raw_gate']['kind']=='EQUIVALENT' for r in rows),
            note='Observed counts only; zero errors on 32 negatives cannot establish a safe production false-merge rate.')
        reports.append(dict(cost=cost,false_equivalence_risk=risk,raw_directional_accuracy=dict(correct=hit,total=2*len(supported),accuracy=hit/(2*len(supported))),
            **{field:summarize(rows,field) for field in ('raw_gate','before','after','issuer_context_before','issuer_context_after')},cases=rows))
        print(model,json.dumps({k:reports[-1][k] for k in ('cost','raw_directional_accuracy','before','after')}),flush=True)
        gc.collect()
    args.output.write_text(json.dumps(dict(fixture_sha256=FROZEN_SHA,provenance=fixture['provenance'],
        baseline_commit='0893253',decision_policy=rel.POLICY,rescored_from_cached_raw=bool(saved),issuer_context_ablation='Separate derived evaluation supplies explicit issuer names as statement metadata, never changes texts or labels; not independently source-audited identity.',thresholds='Unchanged .985 entailment/contradiction, .95 neutral; no tuning',
        limitations='Small authored balanced challenge, not representative calibration; model-specific temperature and length effects uncalibrated. No production model replacement justified by this alone.',models=reports),indent=2)+'\n')

if __name__=='__main__':main()
