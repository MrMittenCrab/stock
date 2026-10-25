"""Deterministic transport tests, not independent semantic accuracy observations."""
import copy
import hashlib
import json
from pathlib import Path
import pytest
from stock import evidence, editorial, knowledge, sources, proposition_context as pc
from stock.core import Store
from stock.archive import import_document


@pytest.fixture
def disposable(tmp_path,monkeypatch):
    monkeypatch.setattr('stock.archive.ROOT',tmp_path)
    path=tmp_path/'input.md'
    path.write_text('# Investor Presentation FY2027\n\nAcme management says: We expect contracted capacity of approximately 850 MW by fiscal year-end 2027, subject to power availability.\n\nAcme defines fiscal year-end as June 30.\n\nBeta management says: We report adjusted revenue, excluding divested operations.')
    store=Store(tmp_path/'disposable.db');doc=import_document(store,'ACME.US',path)
    return store,doc


class Replay:
    contextualize=True
    disposable_context=True
    def __init__(self,state='resolved',verdict='accepted',fidelity='supported'):
        self.calls=[];self.state=state;self.verdict=verdict;self.fidelity=fidelity;self.interrupt=False
    def extract(self,u,c):
        self.calls.append(copy.deepcopy(u))
        if 'review' in u:
            if self.interrupt:raise KeyboardInterrupt
            return [dict(index=i,fidelity=self.fidelity,readability='clear',relevance='useful',warnings=[],reason='Recorded original evidence judgment',context_preservation=self.verdict,context_reason='Recorded contextual interpretation judgment') for i,_ in enumerate(u['review'])]
        a=next(a for a in u['candidates'] if '850' in a['text']);text=a['text'];edits=[]
        if self.state=='resolved':
            start=text.index('We');edits=[dict(original_span=[start,start+2],replacement='Acme',purpose='Resolve management first-person referent',evidence_refs=[a['id']])]
        q=dict(context_status=self.state,standalone_text=text.replace('We','Acme') if edits else text,resolutions=edits,unresolved=['Fiscal year-end interpretation missing'] if self.state=='unresolved' else [])
        return [dict(selection_key='capacity',context=q,ids=[a['id']],topics=['Operations'],category='Management',speaker=None,representation='source_grounded_statement',text=text,ambiguities=[])]


def test_real_pipeline_replay_and_resume(disposable):
    store,doc=disposable;m=Replay()
    ps,_=evidence.extract(store,doc,m,lambda _:None)
    assert len(ps)==1 and len(m.calls)==2
    p=ps[0];r=pc.read(store,p['context_record_id'],p,m_doc(store,doc))
    assert pc.eligible(r) and r['standalone_text']!=p['text']
    def keys(value):
        if isinstance(value,dict):return set(value)|set().union(*(keys(v) for v in value.values()))
        if isinstance(value,list):return set().union(*(keys(v) for v in value))
        return set()
    assert not {'context_proposal','context_status','standalone_text','proposition_context'} & keys(p['location'])
    ident=sources.passage_id(doc,p)
    stripped={k:v for k,v in p.items() if k not in ('context_proposal','context_references','proposition_context','context_record_id','selection_key')}
    assert sources.passage_id(doc,stripped)==ident
    original=p['location']['references'][0]
    assert Path(doc['original']).read_text()[original['start']:original['end']]==original['text']
    assert evidence.extract(store,doc,m,lambda _:None)[0]==ps and len(m.calls)==2
    manifest=pc.association(store,m_doc(store,doc),ps)
    assert pc.load(store,manifest)['output'][ident]['record_id']==p['context_record_id']
    assert not sources.completed(store,doc['id'])


def m_doc(store,doc):
    # The same full metadata envelope used by knowledge.Operations.
    md=Path(doc.get('markdown') or doc['original'])
    return {**{k:doc.get(k) for k in ('id','title','type','ticker','publisher','period','source_sha256','metadata_provenance')},'markdown_sha256':hashlib.sha256(md.read_bytes()).hexdigest(),'original':doc['original'],'markdown':str(md)}


@pytest.mark.parametrize('state,verdict,eligible',[('unnecessary','accepted',True),('resolved','accepted',True),('resolved','rejected',False),('unresolved','unresolved',False)])
def test_states(disposable,state,verdict,eligible):
    store,doc=disposable;m=Replay(state,verdict)
    ps,_=evidence.extract(store,doc,m,lambda _:None);r=ps[0]['proposition_context']
    assert pc.eligible(r)==eligible
    if r['context_status']!='resolved':assert r['standalone_text']==ps[0]['text'] and not r['resolutions']
    if verdict=='rejected':assert r['context_status']=='unresolved' and r['verification']['context_preservation']=='rejected'
    old=pc.read(store,None,ps[0],doc)
    assert old['context_status']=='not_attempted' and old['verification']['context_preservation']=='not_checked'


def test_unsupported_original_never_published(disposable):
    store,doc=disposable;m=Replay(fidelity='unsupported')
    ps,_=evidence.extract(store,doc,m,lambda _:None)
    assert not ps and not sources.completed(store,doc['id'])
    records=store.db.execute("select id from knowledge_artifacts where operation='context-record'").fetchall()
    assert records and all(not pc.eligible(pc.load(store,r[0])['output']) for r in records)


def test_interrupted_review_reuses_extraction(disposable):
    store,doc=disposable;m=Replay();m.interrupt=True
    with pytest.raises(KeyboardInterrupt):evidence.extract(store,doc,m,lambda _:None)
    assert not sources.completed(store,doc['id'])
    m.interrupt=False;assert evidence.extract(store,doc,m,lambda _:None)[0]
    assert sum('review' not in u for u in m.calls)==1


@pytest.mark.parametrize('mutation',['text','source','proposal','metadata','qualification','speaker','context_evidence'])
def test_stale_record_fails_closed(disposable,mutation):
    store,doc=disposable;m=Replay();p=evidence.extract(store,doc,m,lambda _:None)[0][0];d=m_doc(store,doc)
    if mutation=='text':p['text']+=' Changed.'
    if mutation=='qualification':p['location']['references'][0]['text']=p['location']['references'][0]['text'].replace('subject to power availability','')
    if mutation=='source':p['location']['references'][0]['start']+=1
    if mutation=='proposal':p['context_proposal']['standalone_text']+=' Guaranteed.'
    if mutation=='metadata':d['period']='2028'
    if mutation=='speaker':p['speaker']='Another person'
    if mutation=='context_evidence':p['context_references'][0]['text']+=' Other issuer.'
    with pytest.raises(evidence.IntegrityError):pc.read(store,p['context_record_id'],p,d)


@pytest.mark.parametrize('change',['negative','overlap','beyond','bool','mismatch','unknown','unchanged','reason'])
def test_edit_validation(change):
    text='We expect 850 MW, subject to availability.'
    e=dict(original_span=[0,2],replacement='Acme',purpose='Resolve issuer',evidence_refs=['a'])
    q=dict(context_status='resolved',standalone_text=text.replace('We','Acme'),resolutions=[e],unresolved=[])
    if change=='negative':e['original_span']=[-1,2]
    if change=='overlap':q['resolutions'].append(copy.deepcopy(e))
    if change=='beyond':e['original_span']=[0,100]
    if change=='bool':e['original_span']=[False,2]
    if change=='mismatch':q['standalone_text']='Acme operates 850 MW.'
    if change=='unknown':e['evidence_refs']=['fabricated']
    if change=='unchanged':q['context_status']='unnecessary'
    if change=='reason':q.update(context_status='unresolved',standalone_text=text,resolutions=[])
    with pytest.raises(evidence.ProtocolError):pc.validate_proposal(q,text,{'a':{'text':text}})


def test_unicode_and_insertion_deletion():
    original='😀 We expect it.'
    edits=[dict(original_span=[2,4],replacement='Acme',purpose='issuer',evidence_refs=['a']),dict(original_span=[12,14],replacement='capacity',purpose='antecedent',evidence_refs=['a'])]
    q=dict(context_status='resolved',standalone_text='😀 Acme expect capacity.',resolutions=edits,unresolved=[])
    pc.validate_proposal(q,original,{'a':dict(text=original)})
    q.update(standalone_text='Acme expects.',resolutions=[dict(original_span=[0,len(original)],replacement='Acme expects.',purpose='test code points',evidence_refs=['a'])])
    pc.validate_proposal(q,original,{'a':dict(text=original)})


@pytest.mark.parametrize('bad',['missing','duplicate','unknown_field','missing_proposal'])
def test_selection_mapping(disposable,bad):
    store,doc=disposable;m=Replay();text=Path(doc['original']).read_text();atoms=knowledge.prepare_atoms(text,doc,doc['source_sha256'])
    raw=m.extract(dict(candidates=atoms),'')
    if bad=='missing':raw[0]['selection_key']=''
    if bad=='duplicate':raw+=copy.deepcopy(raw)
    if bad=='unknown_field':raw[0]['unknown_selection_key']='other'
    if bad=='missing_proposal':del raw[0]['context']
    with pytest.raises(evidence.ProtocolError):pc.validate_selections(raw)


def test_per_claim_rebatch_cache(disposable):
    store,doc=disposable;m=Replay();knowledge.schema(store)
    ops=knowledge.Operations(store,m_doc(store,doc),m,lambda:None)
    claims=[dict(index=i,text=t,references=[],context_references=[],context_proposal=dict(context_status='unnecessary',standalone_text=t,resolutions=[],unresolved=[])) for i,t in enumerate(['Acme expects growth.','Beta expects growth.'])]
    first=ops.review_claims(dict(review=claims),'{}');assert len(m.calls)==1
    assert ops.review_claims(dict(review=[dict(claims[1],index=0)]),'{}')[0]['fidelity']=='supported'
    assert len(m.calls)==1
    changed=copy.deepcopy(claims[0]);changed['context_proposal']['standalone_text']='Changed interpretation'
    ops.review_claims(dict(review=[changed]),'{}');assert len(m.calls)==2
    assert first[0]['context_preservation']=='accepted'


def test_corruption(disposable):
    store,doc=disposable;m=Replay();p=evidence.extract(store,doc,m,lambda _:None)[0][0]
    with store.db:store.db.execute("update knowledge_artifacts set payload='{}' where operation='context-review'")
    with pytest.raises(evidence.IntegrityError):pc.read(store,p['context_record_id'],p,m_doc(store,doc))


def test_production_opt_in_required(disposable):
    store,doc=disposable;m=Replay();m.disposable_context=False
    with pytest.raises(evidence.IntegrityError):evidence.extract(store,doc,m,lambda _:None)


def test_association_version_rollback_and_failure(disposable):
    store,doc=disposable;m=Replay();p=evidence.extract(store,doc,m,lambda _:None)[0][0];d=m_doc(store,doc)
    first=pc.association(store,d,[p]);pid=sources.passage_id(doc,p)
    assert pc.lookup(store,first,pid,p,d)==p['proposition_context']
    empty=pc.association(store,d,[],parent=first)
    assert pc.lookup(store,empty,pid,p,d)['context_status']=='not_attempted'
    assert pc.lookup(store,first,pid,p,d)['context_status']=='resolved'
    bad=copy.deepcopy(p);bad['text']='Corrupted input'
    count=store.db.execute("select count(*) from knowledge_artifacts where operation='context-association'").fetchone()[0]
    with pytest.raises(evidence.IntegrityError):pc.association(store,d,[p,bad],parent=empty)
    assert store.db.execute("select count(*) from knowledge_artifacts where operation='context-association'").fetchone()[0]==count
    assert pc.lookup(store,first,pid,p,d)['context_status']=='resolved'


def test_two_proposals_for_same_original_are_both_reviewed(disposable):
    store,doc=disposable
    class Conflicting(Replay):
        def extract(self,u,c):
            out=super().extract(u,c)
            if 'review' not in u:
                other=copy.deepcopy(out[0]);other['selection_key']='second';other['context']['resolutions'][0]['replacement']='Beta';a,z=other['context']['resolutions'][0]['original_span'];other['context']['standalone_text']=other['text'][:a]+'Beta'+other['text'][z:];out.append(other)
            return out
    m=Conflicting()
    with pytest.raises(evidence.IntegrityError,match='Conflicting context records'):evidence.extract(store,doc,m,lambda _:None)
    assert len(m.calls[1]['review'])==2 and not sources.completed(store,doc['id'])


def test_actual_cursor_transport_contract(disposable,monkeypatch):
    from subprocess import CompletedProcess
    from stock.sort import Cursor
    import stock.sort_process as process
    store,doc=disposable;replay=Replay();prompts=[]
    # Inject only the process boundary; exercise actual bounded read-only Cursor packing.
    def run(command,**kwargs):
        prompt=command[-1];prompts.append(prompt)
        assert '--mode' in command and command[command.index('--mode')+1]=='ask'
        config=json.loads((Path(kwargs['cwd'])/'.cursor/cli.json').read_text())
        assert 'Shell(*)' in config['permissions']['deny'] and 'Write(**)' in config['permissions']['deny']
        if 'evidence_review' in prompt:
            results=[dict(index=0,fidelity='supported',readability='clear',relevance='useful',warnings=[],reason='Recorded review',context_preservation='accepted',context_reason='Recorded context review')]
            key='reviews'
        else:
            text=Path(doc['original']).read_text();atoms=knowledge.prepare_atoms(text,doc,doc['source_sha256'])
            results=replay.extract(dict(candidates=atoms),'');key='selections'
        return CompletedProcess(command,0,json.dumps(dict(type='result',result=json.dumps({key:results}))), '')
    monkeypatch.setattr(process,'run',run)
    cursor=Cursor.__new__(Cursor);cursor.command='recorded';cursor.contextualize=True;cursor.disposable_context=True
    ps,_=evidence.extract(store,doc,cursor,lambda _:None)
    assert ps and len(prompts)==2 and all('UNTRUSTED DATA' in p for p in prompts)
    assert 'selection_key' in prompts[0] and 'context_preservation' in prompts[1] and 'context_references' in prompts[1]
    assert len(cursor.metrics)==2


def test_recorded_pilot():
    historical=json.loads((Path(__file__).parents[1]/'docs/benchmarks/proposition-context-replay.json').read_text())
    assert historical['total_proposals']==21 and historical['counts']['eligible']==11
    import importlib.util
    spec=importlib.util.spec_from_file_location('context_pilot',Path(__file__).parents[1]/'scripts/pilot_proposition_context.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result=module.run()
    assert result['total_cases']==24 and result['held_out']==3 and result['total_proposals']==20
    assert result['excluded']==['cw-we']
    assert result['counts']['context_rejected']==6 and result['counts']['eligible']==10
    assert all(r['resume_requests']==0 for r in result['requests'])


def test_authenticated_capture_replays_on_current_pipeline(tmp_path):
    capture=json.loads((Path(__file__).parents[1]/'docs/benchmarks/proposition-context-live.json').read_text())
    raw=next(a['payload'] for a in capture['artifacts'] if a['operation']=='understand')
    judgments=next(a['payload'] for a in capture['artifacts'] if a['operation']=='verify')
    source=Path(__file__).parent/'fixtures/proposition-context/microsoft-fy25q4-excerpt.md'
    copied=tmp_path/'microsoft.md';copied.write_bytes(source.read_bytes())
    assert hashlib.sha256(source.read_bytes()).hexdigest()==capture['source_sha256']
    store=Store(tmp_path/'disposable.db')
    doc=dict(id=203,type='Filing',title='Disposable Microsoft release excerpt',ticker='MSFT.US',publisher=None,period=None,metadata_provenance=None,original=str(copied),markdown=str(copied),source_sha256=capture['source_sha256'])
    class Capture:
        contextualize=True;disposable_context=True
        def __init__(self):self.calls=[]
        def extract(self,u,c):
            self.calls.append(u)
            return copy.deepcopy(judgments if 'review' in u else raw)
    model=Capture();events=[]
    class Progress:
        def __call__(self,m):pass
        def log_event(self,e):events.append(e)
    ps,_=evidence.extract(store,doc,model,Progress())
    assert len(ps)==1 and len(raw)==4 and len(model.calls)==2
    assert len(events[-1]['excluded'])==3
    assert all(e['error']=='Unsupported speaker' for e in events[-1]['excluded'])
    p=ps[0];r=pc.read(store,p['context_record_id'],p,m_doc(store,doc))
    assert pc.eligible(r) and r['context_status']=='unnecessary'
    assert r['proposition_id']==store.db.execute('select id from knowledge_propositions').fetchone()[0]
    assert evidence.extract(store,doc,model,Progress())[0]==ps and len(model.calls)==2


def test_source_change_invalidates_pipeline(disposable):
    store,doc=disposable;m=Replay();evidence.extract(store,doc,m,lambda _:None)
    Path(doc['original']).write_text('Changed source')
    with pytest.raises(evidence.IntegrityError):evidence.extract(store,doc,m,lambda _:None)
    assert len(m.calls)==2


def test_original_only_cache_remains_available(disposable):
    store,doc=disposable;knowledge.schema(store)
    base=Replay();base.contextualize=False
    ops=knowledge.Operations(store,m_doc(store,doc),base,lambda:None)
    claim=dict(index=0,text='Acme expects growth.',references=[])
    class OriginalReview:
        def __init__(self):self.calls=[]
        def extract(self,u,c):
            self.calls.append(u)
            return [dict(index=0,fidelity='supported',readability='clear',relevance='useful',warnings=[],reason='Original factual review')]
    original=OriginalReview();ops.cursor=original
    first=ops.review_claims(dict(review=[claim]),'{}')
    ops.cursor=Replay()
    contextual=dict(claim,context_proposal=dict(context_status='unnecessary',standalone_text=claim['text'],resolutions=[],unresolved=[]),context_references=[])
    assert ops.review_claims(dict(review=[contextual]),'{}')[0]['context_preservation']=='accepted'
    ops.cursor=original
    assert ops.review_claims(dict(review=[claim]),'{}')==first and len(original.calls)==1


def test_generation_rebatch_reuses_completed_coverage(disposable):
    store,doc=disposable;knowledge.schema(store);m=Replay();ops=knowledge.Operations(store,m_doc(store,doc),m,lambda:None)
    text=Path(doc['original']).read_text();atoms=knowledge.prepare_atoms(text,doc,doc['source_sha256'])
    first=ops.extract(dict(candidates=atoms,primary_ids=[a['id'] for a in atoms],operation='understand'),'{}')
    assert len(m.calls)==1
    combined=[]
    for atom in atoms:
        combined+=ops.extract(dict(candidates=[atom],primary_ids=[atom['id']],operation='understand'),'{}')
    assert len(m.calls)==1 and combined==first
    assert ops.context_generations


def test_insertions_deletions_and_unsupported_number():
    original='We expect approximately 850 MW.'
    edit=lambda span,replacement:dict(original_span=span,replacement=replacement,purpose='Source-local interpretation',evidence_refs=['a'])
    q=dict(context_status='resolved',standalone_text='Acme: We expect approximately 850 MW.',resolutions=[edit([0,0],'Acme: ')],unresolved=[])
    pc.validate_proposal(q,original,{'a':dict(text='Acme management: '+original)})
    q.update(standalone_text='We expect 850 MW.',resolutions=[edit([10,24],'')])
    pc.validate_proposal(q,original,{'a':dict(text=original)})  # Structure alone cannot certify preserved approximation.
    q.update(standalone_text=original.replace('850','900'),resolutions=[edit([24,27],'900')])
    with pytest.raises(evidence.ProtocolError,match='quantity'):pc.validate_proposal(q,original,{'a':dict(text=original)})


def test_context_staging_does_not_modify_published_evidence(disposable):
    store,doc=disposable;m=Replay();ps,_=evidence.extract(store,doc,m,lambda _:None)
    sources.publish(store,doc,ps,doc['source_sha256'])
    pid=sources.passage_id(doc,ps[0]);sources.set_topic(store,pid,'Capital',True)
    manifest=pc.association(store,m_doc(store,doc),ps)
    published=sources.passages(store,doc['ticker'])[0]
    assert pc.lookup(store,manifest,pid,published,doc)==ps[0]['proposition_context']
    before=store.db.execute('select * from source_passages').fetchall()
    overrides=store.db.execute('select * from source_overrides').fetchall()
    changed=copy.deepcopy(ps[0]);changed['context_proposal']['standalone_text']=changed['context_proposal']['standalone_text'].replace('Acme management says','Acme management states')
    with pytest.raises(evidence.IntegrityError):pc.association(store,m_doc(store,doc),[changed])
    assert store.db.execute('select * from source_passages').fetchall()==before
    assert store.db.execute('select * from source_overrides').fetchall()==overrides


def test_partial_rebatch_extracts_only_unfinished_primary_atoms(disposable):
    store,doc=disposable;knowledge.schema(store);m=Replay();ops=knowledge.Operations(store,m_doc(store,doc),m,lambda:None)
    atoms=knowledge.prepare_atoms(Path(doc['original']).read_text(),doc,doc['source_sha256'])
    capacity=next(a for a in atoms if '850' in a['text'])
    old=ops.extract(dict(candidates=[capacity],primary_ids=[capacity['id']],operation='understand'),'{}')
    result=ops.extract(dict(candidates=atoms,primary_ids=[a['id'] for a in atoms],operation='understand'),'{}')
    assert result==old and len(m.calls)==2
    assert capacity['id'] not in m.calls[-1]['primary_ids']
    assert capacity in m.calls[-1]['candidates']  # Exact context remains available.
    assert ops.extract(dict(candidates=atoms,primary_ids=[a['id'] for a in atoms],operation='understand'),'{}')==old
    assert len(m.calls)==2
