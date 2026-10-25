#!/usr/bin/env python3
"""Deterministic assessment and human packets. Recorded verdicts are never accuracy."""
import copy
from collections import Counter
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stock import evidence, knowledge, proposition_context as pc, sources, editorial
from stock.core import Store
from pilot_proposition_context import RecordedTransport
from validate_proposition_context import ROOT, OUT, write, sha
FIX=ROOT/'tests/fixtures'

def review_fields():
    return dict(standalone_sufficiency=None,truth_condition_preservation=None,source_support=None,
        financial_fidelity={k:None for k in ('issuer','speaker','period','metric','quantity','definition','modality','scope','qualifications')},
        fluency=None,conciseness=None,unsupported_additions=None,meaning_changes=None,missing_information=None,
        verdict=None,confidence=None,reasons=None,completed_at=None)

def assess():
    assert sha(OUT/'raw-baseline.json')==(OUT/'raw-baseline.sha256').read_text().split()[0]
    if (OUT/'assessment.json').exists():raise SystemExit('Assessment exists; do not recycle opened heldout cases')
    fixture=json.loads((FIX/'proposition-context/cases.json').read_text())
    reviews=json.loads((FIX/'proposition-context/reviews.json').read_text())['reviews']
    report=dict(kind='deterministic integrity checks plus recorded-response replay; semantic conclusions require human adjudication',
        baseline_sha256=sha(OUT/'raw-baseline.json'),baseline_freeze_commit='c41a044',
        dataset_sha256=sha(FIX/'proposition-context/cases.json'),reviews_sha256=sha(FIX/'proposition-context/reviews.json'),
        cases=[],runs=[],human_completed=0,human_agreement=None,production_activation=False,cursor_requests=0)
    with tempfile.TemporaryDirectory(prefix='stock-context-assessment-') as tmp:
        for heldout in (False,True):
            for name,source in fixture['sources'].items():
                path=FIX/source['path'];assert sha(path)==source['sha256']
                copied=Path(tmp)/(name+'.md');copied.write_bytes(path.read_bytes());text=copied.read_text()
                doc=dict(id=source['id'],type=source['type'],title='Disposable source fixture',ticker='FIXTURE.US',publisher=None,period=None,metadata_provenance=None,source_sha256=source['sha256'],original=str(copied),markdown=str(copied))
                atoms=knowledge.prepare_atoms(text,doc,source['sha256']);lookup={a['id']:a for a in atoms}
                cases=[c for c in fixture['cases'] if c['source']==name and c['heldout']==heldout]
                store=Store(Path(tmp)/(name+str(heldout)+'.db'));model=RecordedTransport(cases,reviews)
                passages,verify=evidence.extract(store,doc,model,lambda _:None);verify()
                bykey={p['selection_key']:p for p in passages};assert len(bykey)==len(cases)
                bound={**doc,'markdown_sha256':source['sha256']}
                manifest=pc.association(store,bound,passages)
                for c in cases:
                    p=bykey[c['id']];r=pc.read(store,p['context_record_id'],p,bound)
                    assert p['text']==c['original_text']
                    for ref in c['references']:
                        a=lookup[ref['source_id']]
                        assert (a['start'],a['end'],a['text'])==(ref['start'],ref['end'],ref['text'])
                    refs={a['id']:a for a in atoms};pc.validate_proposal(c['proposal'],c['original_text'],refs)
                    edits=[dict(e,original_substring=c['original_text'][slice(*e['original_span'])],evidence=[lookup[i] for i in e['evidence_refs']]) for e in c['proposal']['resolutions']]
                    flags=[]
                    for e in edits:
                        a,z=e['original_span'];original=c['original_text']
                        if (a and a<len(original) and original[a-1].isalnum() and original[a].isalnum()) or (z and z<len(original) and original[z-1].isalnum() and original[z].isalnum()):
                            flags.append('Edit splits a lexical token; semantic review required (not a general rejection rule).')
                    known_unsafe=c['id']=='cw-we'
                    entry=dict(id=c['id'],heldout=heldout,source=source,original=c['original_text'],proposal=copy.deepcopy(c['proposal']),record=r,
                        exact_edits=edits,source_references=c['references'],source_atoms=[lookup[i] for i in sorted({ref['source_id'] for ref in c['references']}|{i for e in c['proposal']['resolutions'] for i in e['evidence_refs']})],
                        deterministic=dict(source_hash=True,exact_anchors=True,edit_reconstruction=True,original_preserved=True,passage_identity_preserved=True,checked_review_binding=True),
                        recorded_model_assessment=reviews[c['id']],semantic_human_assessment=review_fields(),
                        audit_flags=flags,known_unsafe_accepted=known_unsafe,
                        safe_for_downstream=False,
                        downstream_reason='Known malformed issuer replacement accepted by recorded verdict.' if known_unsafe else 'No independent human adjudication; recorded review cannot establish semantic reliability.',
                        validation_model_assessment=dict(author='Codex source inspection; not human or independent blinded review',
                            standalone_sufficiency='fail' if known_unsafe else 'requires_human_review',
                            truth_condition_preservation='fail' if known_unsafe else 'requires_human_review',
                            source_support='fail' if known_unsafe else 'requires_human_review',financial_fidelity='issuer corruption' if known_unsafe else 'requires_human_review',
                            fluency='fail' if known_unsafe else 'requires_human_review',
                            reason='Span [4,6] is We inside CoreWeave, not the first-person pronoun. CoreCoreWeaveave is absent from the source.' if known_unsafe else 'Exact anchors and applicable semantic support are different properties. See per-dimension reviewer form.'))
                    report['cases'].append(entry)
                    pid=sources.passage_id(doc,p);assert pc.lookup(store,manifest,pid,p,bound)==r
                before=len(model.calls);count=store.db.execute('select count(*) from knowledge_artifacts').fetchone()[0]
                assert evidence.extract(store,doc,model,lambda _:None)[0]==passages
                assert before==len(model.calls) and count==store.db.execute('select count(*) from knowledge_artifacts').fetchone()[0]
                report['runs'].append(dict(source=name,heldout=heldout,requests=before,resume_requests=len(model.calls)-before,artifacts=count,manifest=manifest))
                store.db.close()
    report['recorded_development_counts']=dict(Counter(c['record']['context_status'] for c in report['cases'] if not c['heldout']))
    report['recorded_heldout_counts']=dict(Counter(c['record']['context_status'] for c in report['cases'] if c['heldout']))
    report['semantic_counts']=dict(human_sufficiency_pass=0,human_preservation_pass=0,human_pending=24,
        deterministic_semantic_pass=None,known_unsafe_accepted=1,known_unsupported_accepted_addition=1,
        known_meaning_changing_accepted_rewrite=1,recorded_acceptance_is_not_semantic_accuracy=True)
    report['phase3']='BLOCKED'
    write(OUT/'assessment.json',report)
    packets(report)
    print(json.dumps({k:report[k] for k in ('recorded_development_counts','recorded_heldout_counts','semantic_counts','phase3')},indent=2))

def packets(report):
    representations={c['id']:c['representation'] for c in json.loads((FIX/'proposition-context/cases.json').read_text())['cases']}
    entries=[dict(id=c['id'],candidate=c['proposal']['standalone_text'],original=c['original'],representation=representations[c['id']],proposal_status=c['proposal']['context_status'],missing_information=c['proposal']['unresolved'],edits=c['exact_edits'],references=c['source_references'],source=dict(c['source'],path='tests/fixtures/'+c['source']['path'])) for c in report['cases']]
    # Historical authenticated selections are also reviewable, including pre-review exclusions.
    live=json.loads((ROOT/'docs/benchmarks/proposition-context-live.json').read_text())
    selections=next(a['payload'] for a in live['artifacts'] if a['operation']=='understand')
    source_text=(FIX/'proposition-context/microsoft-fy25q4-excerpt.md').read_text()
    for s in selections:
        entries.append(dict(id='phase2-live:'+s['selection_key'],candidate=s['context']['standalone_text'],original=s['text'],representation=s['representation'],proposal_status=s['context']['context_status'],missing_information=s['context']['unresolved'],edits=s['context']['resolutions'],references=[dict(source_id=i,start=0,end=1132,text=source_text,path='tests/fixtures/proposition-context/microsoft-fy25q4-excerpt.md',sha256=live['source_sha256']) for i in s['ids']],source=dict(path='tests/fixtures/proposition-context/microsoft-fy25q4-excerpt.md',sha256=live['source_sha256'])))
    current=OUT/'authenticated.json'
    if current.exists():
        auth=json.loads(current.read_text())
        for i,call in enumerate(auth.get('calls',[])):
            if 'review' not in call['unit']:
                for s in call.get('output',[]):
                    refs=[a for a in call['unit']['candidates'] if a['id'] in s['ids']]
                    original=s['text'] if s['representation']!='verbatim' else '\n\n'.join(a['text'] for a in refs)
                    entries.append(dict(id='phase25-live:'+s['selection_key'],candidate=s['context']['standalone_text'],original=original,representation=s['representation'],proposal_status=s['context']['context_status'],missing_information=s['context']['unresolved'],edits=s['context']['resolutions'],references=refs,source=dict(path='docs/benchmarks/proposition-context-validation/authenticated.json',field='source_slices')))
    for index, entry in enumerate(entries, 1):
        entry['source_case_id']=entry['id']
        entry['id']=f'case-{index:03d}'
    for reviewer,ordered in [('A',entries),('B',list(reversed(entries)))]:
        directory=OUT/('reviewer-'+reviewer);directory.mkdir(exist_ok=True)
        write(directory/'stage1.json',dict(reviewer=reviewer,instructions='Review independently. Open ONLY stage1 first, without title, sources, original or other reviewer judgments. Save standalone sufficiency and fluency with confidence and reasons, then timestamp and lock these answers BEFORE opening stage2. Evaluate all material referents. null means pending, never pass.',cases=[dict(id=e['id'],statement=e['candidate'],standalone_sufficiency=None,fluency=None,conciseness=None,confidence=None,reasons=None,locked_at=None) for e in ordered]))
        write(directory/'stage2.json',dict(reviewer=reviewer,instructions='Open only after stage1 is locked. Consult exact source path/hash, full context and edit anchors. Assess original support separately from contextual preservation; resolve every material financial dimension. Do not consult recorded model judgments or the other reviewer. Mark unresolved when evidence is insufficient. Return completed files without modifying originals.',cases=[dict(**e,assessment=review_fields()) for e in ordered]))
    write(OUT/'adjudication.json',dict(instructions='After both independent reviews are locked, compare every A–E dimension; record disagreement and evidence-based resolution. Do not fill agreement for missing reviews.',cases=[dict(id=e['id'],reviewer_A=None,reviewer_B=None,disagreements=None,adjudicator=None,evidence=None,resolution=None,confidence=None,completed_at=None) for e in entries]))
if __name__=='__main__':assess()
