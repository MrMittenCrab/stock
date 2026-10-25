"""Phase 2.5 audit regressions. These do not certify model semantic accuracy."""
import hashlib
import json
from pathlib import Path
import pytest
from stock import editorial, knowledge, evidence, proposition_context as pc
from test_proposition_context import disposable, Replay, m_doc

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/benchmarks/proposition-context-validation'


def test_frozen_baseline_identity_and_no_heldout_labels():
    baseline=OUT/'raw-baseline.json'
    assert hashlib.sha256(baseline.read_bytes()).hexdigest()==(OUT/'raw-baseline.sha256').read_text().split()[0]
    protocol=json.loads((OUT/'protocol.json').read_text())
    assert protocol['frontier']==0 and protocol['budgets']==[10,25,50,100]
    assert set(protocol['datasets'])=={'coreweave','development_challenge'}
    data=json.loads(baseline.read_text())
    assert data['protocol_sha256']==hashlib.sha256((OUT/'protocol.json').read_bytes()).hexdigest()
    for d in data['datasets'].values():
        assert d['resume_metrics']['embedded']==0
        assert d['resume_metrics']['similarity_calculations']==0


def test_known_unsafe_recorded_acceptance_is_not_certified():
    data=json.loads((OUT/'assessment.json').read_text())
    case=next(c for c in data['cases'] if c['id']=='cw-we')
    assert case['exact_edits'][0]['original_substring']=='We'
    assert 'CoreCoreWeaveave' in case['record']['standalone_text']
    assert pc.eligible(case['record'])  # Reproduce the existing semantic gate failure honestly.
    assert case['known_unsafe_accepted'] and not case['safe_for_downstream']
    assert data['phase3']=='BLOCKED' and data['human_completed']==0
    assert len(data['cases'])==24 and sum(c['heldout'] for c in data['cases'])==3
    assert all(all(c['deterministic'].values()) for c in data['cases'])


def test_independent_packets_are_unfilled_and_stage1_blinded():
    a=json.loads((OUT/'reviewer-A/stage1.json').read_text())
    b=json.loads((OUT/'reviewer-B/stage1.json').read_text())
    assert {c['id'] for c in a['cases']}=={c['id'] for c in b['cases']}
    for packet in (a,b):
        for c in packet['cases']:
            assert not {'original','references','source','recorded_model_assessment','heldout'} & c.keys()
            assert c['standalone_sufficiency'] is c['locked_at'] is None


@pytest.mark.parametrize('field,value',[
    ('title','Different source'),('type','Transcript'),('ticker','BETA.US'),
    ('publisher','Different publisher'),('period','FY2028'),
    ('metadata_provenance',{'issuer':'new unverified provenance'}),
    ('source_sha256','0'*64),('original','/different/original.md'),('markdown','/different/source.md')])
def test_all_document_metadata_invalidates_checked_approval(disposable,field,value):
    store,doc=disposable
    p=evidence.extract(store,doc,Replay(),lambda _:None)[0][0]
    bound=m_doc(store,doc);bound[field]=value
    with pytest.raises(evidence.IntegrityError):pc.read(store,p['context_record_id'],p,bound)


def test_filing_mixed_quoted_speakers_cannot_inherit_issuer():
    source=ROOT/'tests/fixtures/proposition-context/microsoft-fy25q4-excerpt.md'
    text=source.read_text();sha=hashlib.sha256(source.read_bytes()).hexdigest()
    atoms=knowledge.prepare_atoms(text,dict(id=203,type='Filing',source_sha256=sha,original=str(source)),sha)
    assert len(atoms)==1
    atom=atoms[0]
    assert 'Satya Nadella' in atom['text'] and 'Amy Hood' in atom['text']
    assert atom['speaker'] is None and atom['turn'] is None
    capture=json.loads((ROOT/'docs/benchmarks/proposition-context-live.json').read_text())
    selections=next(a['payload'] for a in capture['artifacts'] if a['operation']=='understand')
    for selection in selections:
        if selection['speaker']:
            with pytest.raises(ValueError,match='Unsupported speaker'):
                editorial.resolve_selection(selection,atoms,text,dict(id=203),sha)


def test_management_and_analyst_turns_stay_distinct():
    text='''# Alpha call

Alice Smith

Chief Executive Officer, Alpha

Bob Jones

Analyst, Beta

## Alice Smith

We expect demand to grow.

## Bob Jones

Our customer reports lower demand.
'''
    atoms=knowledge.prepare_atoms(text,dict(id=301,type='Transcript'),'f'*64)
    claims=[a for a in atoms if not a.get('context_only')]
    assert [(a['speaker'],a['role']) for a in claims]==[('Alice Smith','Management'),('Bob Jones','Investor')]
    selection=dict(ids=[claims[1]['id']],topics=['Market'],category='Management',speaker='Alice Smith',representation='source_grounded_statement',text='Alpha expects lower demand.',ambiguities=[])
    with pytest.raises(ValueError,match='Unsupported speaker'):
        editorial.resolve_selection(selection,atoms,text,dict(id=301),'f'*64)


SAFETY=json.loads((ROOT/'tests/fixtures/proposition-context/phase25-safety.json').read_text())['cases']

@pytest.mark.parametrize('case',SAFETY,ids=[c['id'] for c in SAFETY])
def test_financial_counterfactuals_with_recorded_rejection(tmp_path,case):
    """Gate simulation, not a claim that a real judge detects these mutations."""
    from stock.core import Store
    source=tmp_path/'source.md';source.write_text(case['source'])
    sha=hashlib.sha256(source.read_bytes()).hexdigest()
    doc=dict(id=501,type='Filing',title='Disposable development safety case',ticker='ALPHA.US',publisher=None,period=None,metadata_provenance=None,original=str(source),markdown=str(source),source_sha256=sha)
    class Model:
        contextualize=True;disposable_context=True
        def extract(self,unit,context):
            if 'review' in unit:
                return [dict(index=i,fidelity='supported',readability='clear',relevance='useful',warnings=[],reason='Recorded original support expectation',context_preservation='rejected',context_reason=case['reason']) for i,_ in enumerate(unit['review'])]
            atom=unit['candidates'][0]
            return [dict(selection_key=case['id'],ids=[atom['id']],topics=['Operations'],category='Management',speaker=None,representation='source_grounded_statement',text=case['original'],ambiguities=[],context=dict(context_status='resolved',standalone_text=case['proposal'],resolutions=[dict(original_span=[0,len(case['original'])],replacement=case['proposal'],purpose='Adversarial development mutation',evidence_refs=[atom['id']])],unresolved=[]))]
    store=Store(tmp_path/'disposable.db')
    passages,_=evidence.extract(store,doc,Model(),lambda _:None)
    assert len(passages)==(0 if case['id']=='currency-scale-rounding' else 1)
    for p in passages:
        r=p['proposition_context']
        assert r['verification']['original_support']=='supported'
        assert r['context_status']=='unresolved' and r['standalone_text']==case['original']
        assert not pc.eligible(r)
    assert store.db.execute("select count(*) from knowledge_artifacts where operation='understand'").fetchone()[0]==1
    from stock import sources
    assert not sources.completed(store,doc['id'])
