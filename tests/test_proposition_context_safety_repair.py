"""Phase 2.6 development safety evidence, never human semantic adjudication."""
import copy
import json
from pathlib import Path
import pytest
from stock import evidence, proposition_context as pc
from test_proposition_context import disposable, Replay, m_doc

ROOT=Path(__file__).resolve().parents[1]
HISTORY=json.loads((ROOT/'docs/benchmarks/proposition-context-validation/assessment.json').read_text())
CASE=next(c for c in HISTORY['cases'] if c['id']=='cw-we')


def proposal(original, span, replacement, purpose='Resolve source-local reference'):
    a,z=span
    return dict(context_status='resolved',standalone_text=original[:a]+replacement+original[z:],
        resolutions=[dict(original_span=list(span),replacement=replacement,purpose=purpose,evidence_refs=['a'])],unresolved=[])


def test_known_malformed_edit_rejected_despite_recorded_approval():
    with pytest.raises(evidence.ProtocolError,match='referring expression'):
        pc.validate_proposal(CASE['proposal'],CASE['original'],{a['id']:a for a in CASE['source_atoms']})
    assert CASE['known_unsafe_accepted']  # Immutable observation remains true of Phase 2.5.
    assert not pc.eligible(CASE['record'])


# Purpose cannot authorize a malformed pronoun target. Unicode letters, combining
# marks, numbers, connectors and format controls cannot disguise word interiors.
INVALID=[('CoreWeave said: We grew.',(4,6),'CoreWeave'),
    ('éWe grew.',(1,3),'Acme'),('We\u0301 grew.',(0,2),'Acme'),
    ('中We grew.',(1,3),'Acme'),('We_Inc grew.',(0,2),'Acme'),
    ('We2 grew.',(0,2),'Acme'),('We\u200dCo grew.',(0,2),'Acme'),
    ("We're growing.",(0,2),'Acme'),('We’re growing.',(0,2),'Acme'),
    ('this facilityX grew.',(0,13),'Acme facility'),
    ('(We’re growing.',(0,3),'(Acme'),
    ('e\u0301 grew.',(1,2),'x')]

@pytest.mark.parametrize('original,span,replacement',INVALID)
@pytest.mark.parametrize('purpose',['Resolve pronoun','Legitimate name completion'])
def test_invalid_referring_boundaries(original,span,replacement,purpose):
    with pytest.raises(evidence.ProtocolError,match='boundary|referring expression'):
        pc.validate_proposal(proposal(original,span,replacement,purpose),original,{'a':dict(text='Acme '+original)})


VALID=[('We grew.',(0,2),'Acme'),('“We,” management said.',(1,3),'Acme'),
    ('(WE) grew.',(1,3),'Acme'),('😀 we grew.',(2,4),'Acme'),
    ('«We» grew.',(1,3),'Acme'),('Our capacity grew.',(0,3),"Acme’s"),
    ('Their customers grew.',(0,5),"Acme's"),
    ("We're growing.",(0,5),'Acme is'),('We’re growing.',(0,5),'Acme is'),
    ('This facility grew.',(0,13),'Acme’s facility'),
    ('Its customer’s demand grew.',(0,12),'Acme’s customer'),
    ('Nadella said demand grew.',(0,0),'Satya '),
    ('Micro reported demand.',(5,5),'soft'), # Partial-token name completion remains possible.
    ('AcmeCo reported demand.',(4,6),''), # Nonreferential partial-token deletion.
    ('However, Acme grew.',(0,9),''),
    ('Acme grew.',(0,4),'Beta')] # Wrong referent is lexically valid; semantics remain separate.

@pytest.mark.parametrize('original,span,replacement',VALID)
def test_legitimate_edit_structure_remains_possible(original,span,replacement):
    q=proposal(original,span,replacement)
    pc.validate_proposal(q,original,{'a':dict(text=original+' '+q['standalone_text'])})


def test_repeated_identical_pronouns_use_exact_coordinates():
    original='We said: We grew.'
    q=proposal(original,(9,11),'Acme')
    pc.validate_proposal(q,original,{'a':dict(text='Acme management: '+original)})
    assert q['standalone_text']=='We said: Acme grew.'


def test_positive_review_cannot_finalize_malformed_edit(disposable):
    store,doc=disposable
    p=evidence.extract(store,doc,Replay(),lambda _:None)[0][0]
    p['text']=CASE['original'];p['context_proposal']=CASE['proposal']
    count=store.db.execute('select count(*) from knowledge_artifacts').fetchone()[0]
    with pytest.raises(evidence.ProtocolError,match='referring expression'):
        pc.finalize(store,m_doc(store,doc),p,dict(fidelity='supported',context_preservation='accepted',context_reason='Historical positive judgment'),{},'recorded')
    assert store.db.execute('select count(*) from knowledge_artifacts').fetchone()[0]==count


def test_historical_artifact_cannot_resume_past_current_gate(disposable,monkeypatch):
    """Create the historical defect only in disposable storage, then enforce new code."""
    from stock import sources
    store,doc=disposable
    class Malformed(Replay):
        def extract(self,u,c):
            raw=super().extract(u,c)
            if 'review' not in u:
                s=raw[0];s['text']='CoreWeave management says: We expect approximately 850 MW.'
                s['context']=proposal(s['text'],(4,6),'CoreWeave')
                s['context']['resolutions'][0]['evidence_refs']=s['ids']
            return raw
    model=Malformed()
    with monkeypatch.context() as old:
        old.setattr(pc,'validate_edit_boundary',lambda *args:None)
        p=evidence.extract(store,doc,model,lambda _:None)[0][0]
        manifest=pc.association(store,m_doc(store,doc),[p])
    before=store.db.execute('select id,payload,checksum from knowledge_artifacts order by id').fetchall()
    assert not pc.eligible(p['proposition_context'])
    with pytest.raises(evidence.ProtocolError,match='referring expression'):
        pc.lookup(store,manifest,sources.passage_id(doc,p),p,m_doc(store,doc))
    calls=len(model.calls)
    assert evidence.extract(store,doc,model,lambda _:None)[0]==[]
    assert len(model.calls)==calls # Complete generation is reused, revalidated and excluded.
    assert store.db.execute('select id,payload,checksum from knowledge_artifacts order by id').fetchall()==before


@pytest.mark.parametrize('stage',['generation','review'])
@pytest.mark.parametrize('failure',['process','budget'])
def test_transport_timeout_discards_partial_positive_response(disposable,monkeypatch,stage,failure):
    from subprocess import CompletedProcess, TimeoutExpired
    from stock.sort import Cursor
    from stock import knowledge
    from stock.sort_budget import BudgetExceeded
    import stock.sort_process as process
    store,doc=disposable
    model=Replay();calls=[];fail=[True]
    def run(command,**kwargs):
        review='evidence_review' in command[-1]
        calls.append('review' if review else 'generation')
        if fail[0] and review==(stage=='review'):
            # Even a valid-looking approval on stdout is not a completed response.
            if failure=='budget':raise BudgetExceeded('Request timeout')
            raise TimeoutExpired(command,0.01,output='{"type":"result","result":"accepted"}')
        atoms=knowledge.prepare_atoms(Path(doc['original']).read_text(),doc,doc['source_sha256'])
        unit=dict(review=[{}]) if review else dict(candidates=atoms)
        raw=model.extract(unit,'')
        return CompletedProcess(command,0,json.dumps(dict(type='result',result=json.dumps({'reviews' if review else 'selections':raw}))), '')
    monkeypatch.setattr(process,'run',run)
    cursor=Cursor.__new__(Cursor);cursor.command='disposable-recorded';cursor.contextualize=True;cursor.disposable_context=True
    with pytest.raises(BudgetExceeded if failure=='budget' else ValueError,match='Request timeout|process failed'):
        evidence.extract(store,doc,cursor,lambda _:None)
    operations=[r[0] for r in store.db.execute('select operation from knowledge_artifacts')]
    assert not {'verify','claim-review','context-review','context-record'} & set(operations)
    assert ('understand' in operations)==(stage=='review')
    assert store.db.execute("select count(*) from knowledge_attempts where state='failed'").fetchone()[0]==1
    first=len(calls);fail[0]=False
    ps,_=evidence.extract(store,doc,cursor,lambda _:None)
    assert len(ps)==1 and pc.eligible(pc.read(store,ps[0]['context_record_id'],ps[0],m_doc(store,doc)))
    assert calls[first:]==(['generation','review'] if stage=='generation' else ['review'])
    completed=len(calls)
    assert evidence.extract(store,doc,cursor,lambda _:None)[0]==ps and len(calls)==completed


def test_unsupported_period_is_evidence_failure_not_boundary_failure():
    original='Acme reported capacity in 2025.'
    q=proposal(original,(26,30),'2028')
    pc.validate_edit_application(q,original)
    with pytest.raises(evidence.ProtocolError,match='quantity'):
        pc.validate_proposal(q,original,{'a':dict(text=original)})


def test_valid_coordinates_do_not_prove_correct_referent(disposable):
    store,doc=disposable
    class WrongReferent(Replay):
        def extract(self,u,c):
            raw=super().extract(u,c)
            if 'review' not in u:
                s=raw[0];e=s['context']['resolutions'][0];e['replacement']='Beta'
                a,z=e['original_span'];s['context']['standalone_text']=s['text'][:a]+'Beta'+s['text'][z:]
            return raw
    m=WrongReferent(verdict='rejected')
    ps,_=evidence.extract(store,doc,m,lambda _:None)
    assert len(m.calls)==2 and len(ps)==1 # Reached independent review.
    assert ps[0]['proposition_context']['context_status']=='unresolved'
    assert not pc.eligible(ps[0]['proposition_context'])


def test_actual_child_partial_stdout_is_discarded_on_timeout():
    import subprocess
    import sys
    from stock import sort_process
    with pytest.raises(subprocess.TimeoutExpired) as result:
        sort_process.run([sys.executable,'-c',
            'import time; print(\'{"type":"result","result":"accepted"}\',flush=True); time.sleep(30)'],
            text=True,timeout=.2)
    assert result.value.process_diagnostics['stdout_bytes']>0
    assert result.value.process_diagnostics['timed_out']
    assert sort_process.ACTIVE_PROCESS is None


def test_packet_anchor_errata_preserve_historical_materials():
    import hashlib
    report=json.loads((ROOT/'docs/benchmarks/proposition-context-safety-repair-v1.json').read_text())
    path=ROOT/report['stage2_anchor_errata']['path']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==report['stage2_anchor_errata']['sha256']
    errata=json.loads(path.read_text())
    assert len(errata['entries'])==8
    for reviewer,info in report['human_packets'].items():
        for stage in ('stage1','stage2'):
            packet=ROOT/f'docs/benchmarks/proposition-context-validation/reviewer-{reviewer}/{stage}.json'
            assert hashlib.sha256(packet.read_bytes()).hexdigest()==info[f'{stage}_sha256']
    for e in errata['entries']:
        source=ROOT/e['source_path']
        assert hashlib.sha256(source.read_bytes()).hexdigest()==e['source_sha256']
        assert source.read_text()[e['start']:e['end']]==e['corrected_text']


def test_punctuation_prefix_cannot_hide_incomplete_referring_expression():
    original='(Weave) grew.'
    with pytest.raises(evidence.ProtocolError,match='referring expression'):
        pc.validate_proposal(proposal(original,(0,3),'(Acme'),original,{'a':dict(text=original)})


def test_adjacent_split_edits_cannot_hide_incomplete_referring_expression():
    q=copy.deepcopy(CASE['proposal'])
    e=q['resolutions'][0]
    q['resolutions']=[dict(e,original_span=[4,5],replacement='CoreWeav'),dict(e,original_span=[5,6],replacement='e')]
    with pytest.raises(evidence.ProtocolError,match='referring expression'):
        pc.validate_proposal(q,CASE['original'],{a['id']:a for a in CASE['source_atoms']})
