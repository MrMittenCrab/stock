#!/usr/bin/env python3
"""Versioned Phase 2.6 assessment; offline, disposable, no baseline regeneration."""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stock import proposition_context as pc, evidence
from pilot_proposition_context import run as replay

ROOT=Path(__file__).resolve().parents[1]
PRIOR=ROOT/'docs/benchmarks/proposition-context-validation'
OUTPUT=ROOT/'docs/benchmarks/proposition-context-safety-repair-v1.json'
ERRATA=ROOT/'docs/benchmarks/proposition-context-review-packet-errata-v1.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def assess():
    historical=json.loads((PRIOR/'assessment.json').read_text())
    assert sha(PRIOR/'raw-baseline.json')==(PRIOR/'raw-baseline.sha256').read_text().split()[0]
    cases=[]
    for c in historical['cases']:
        error=None
        try:pc.validate_proposal(c['proposal'],c['original'],{a['id']:a for a in c['source_atoms']})
        except evidence.ProtocolError as exc:error=str(exc)
        cases.append(dict(id=c['id'],observed_development_evidence=True,previously_heldout=c['heldout'],
            historical_validation_passed=all(c['deterministic'].values()),
            historical_context_verdict=c['record']['verification']['context_preservation'],
            current_validation_passed=error is None,current_error=error,
            current_eligible=pc.eligible(c['record']),human_adjudicated=False))
    changed=[c['id'] for c in cases if not c['current_validation_passed']]
    assert changed==['cw-we']
    packets={};errata=[]
    for reviewer in ('A','B'):
        stage1=PRIOR/f'reviewer-{reviewer}/stage1.json'
        stage2=PRIOR/f'reviewer-{reviewer}/stage2.json'
        blind=json.loads(stage1.read_text());source=json.loads(stage2.read_text())
        assert {c['id'] for c in blind['cases']}=={c['id'] for c in source['cases']}
        assert all(c['locked_at'] is None for c in blind['cases'])
        assert all(c['assessment']['completed_at'] is None for c in source['cases'])
        for c in source['cases']:
            path=ROOT/c['source']['path']
            assert sha(path)==c['source']['sha256']
            for index,ref in enumerate(c['references']):
                exact=path.read_text()[ref['start']:ref['end']]
                if exact!=ref['text']:
                    # Existing live packet copied the whole file rather than the
                    # atom text, including one terminal newline. Preserve packet.
                    assert c['source_case_id'].startswith('phase2-live:')
                    assert ref['text']==exact+'\n' and (ref['start'],ref['end'])==(0,1132)
                    errata.append(dict(reviewer=reviewer,case_id=c['id'],reference_index=index,
                        source_id=ref['source_id'],start=ref['start'],end=ref['end'],
                        source_path=c['source']['path'],source_sha256=sha(path),corrected_text=exact))
        packets[reviewer]=dict(stage1_sha256=sha(stage1),stage2_sha256=sha(stage2),cases=len(blind['cases']),
            changed_policy_cases=[c['id'] for c in source['cases'] if c['source_case_id'] in changed])
    auth=json.loads((PRIOR/'authenticated.json').read_text())
    assert not auth['artifacts'] and auth['requests']==1 and auth['error']['type']=='BudgetExceeded'
    return dict(phase='2.6',assessment_version=1,edit_validation=pc.EDIT_VALIDATION,
        historical_commit='a82d806',historical_assessment_sha256=sha(PRIOR/'assessment.json'),
        baseline_sha256=sha(PRIOR/'raw-baseline.json'),baseline_regenerated=False,
        cases=cases,changed_policy_cases=changed,human_packets=packets,human_completed=0,
        stage2_anchor_errata=dict(version=1,instructions='Apply only when opening stage2 after stage1 is locked. Replace reference text at the specified index; source IDs, coordinates, original statements and all judgments remain unchanged.',entries=errata),
        packet_use='Original statements remain reviewable as historical development evidence. cw-we cannot authorize current use; any corrected candidate needs new blinded sufficiency and meaning-preservation review.',
        fresh_evaluation='If required, select new source passages independently before model outputs or policy tuning, freeze exact anchors and criteria, use two blinded independent humans and adjudication; exclude all 24 opened cases and all opened live examples.',
        replay=replay(),authenticated_requests=0,transport_observation=auth['events'][0]['model']['process'],
        gates=dict(deterministic_safety='PASS for tested lexical and compatibility cases; not semantic truth',
            semantic_validation='BLOCKED: human reviews/adjudications missing',
            retrieval_baseline='AVAILABLE and hash intact',
            authenticated_resolved_demonstration='NOT COMPLETED'),phase3='BLOCKED',production_activation=False)


if __name__=='__main__':
    if OUTPUT.exists() or ERRATA.exists():raise SystemExit('Versioned follow-up exists; choose a new version instead of overwriting')
    report=assess()
    ERRATA.write_text(json.dumps(report.pop('stage2_anchor_errata'),ensure_ascii=False,indent=2)+'\n')
    report['stage2_anchor_errata']=dict(path=str(ERRATA.relative_to(ROOT)),sha256=sha(ERRATA))
    OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(phase3=report['phase3'],changed=report['changed_policy_cases'],replay=report['replay']['counts'],packets=report['human_packets']),indent=2))
