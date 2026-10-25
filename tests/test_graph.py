import pytest
from stock import insights, relationships, semantic_map, sources
from test_insights import library


@pytest.fixture
def local(monkeypatch):
    import numpy as np
    class Encoder:
        def embed(self,texts,batch_size=None):
            for _ in texts:
                v=np.zeros(384,dtype=np.float32);v[0]=1;yield v
    monkeypatch.setattr(semantic_map,'_model',lambda:Encoder())
    calls=[]
    def infer(pairs):
        calls.extend(pairs)
        return [dict(entailment=.995,contradiction=.002,neutral=.003) for _ in pairs]
    monkeypatch.setattr(relationships,'backend',lambda:infer)
    return calls


def test_graph_no_cursor_and_cache(library,local):
    s,_,add=library;add('CoreWeave serves customers.');add('CoreWeave serves clients.',1)
    class NoCursor:
        def extract(self,*args):raise AssertionError('No Cursor deduplication')
    p=insights.stage(s,'CRWV.US',NoCursor(),lambda _:None)
    assert len(p['groups'])==1 and p['relationships'][0]['kind']=='EQUIVALENT'
    assert p['model_requests']==0 and len(local)==2
    again=insights.stage(s,'CRWV.US',None,lambda _:None)
    assert len(local)==2 and again['cached_decisions']==1
    insights.activate(s,p['id'])
    assert len(insights.entries(s,'CRWV.US'))==1


def test_one_way_keeps_both_and_inline_relationship(library,local,monkeypatch):
    s,_,add=library
    add('CoreWeave serves many customers.');add('CoreWeave has customers.',1)
    monkeypatch.setattr(relationships,'backend',lambda:lambda pairs:[
        dict(entailment=.995,contradiction=.002,neutral=.003),
        dict(entailment=.002,contradiction=.003,neutral=.995)])
    p=insights.stage(s,'CRWV.US',None,lambda _:None);insights.activate(s,p['id'])
    entries=insights.entries(s,'CRWV.US')
    assert len(entries)==2 and all(e['relationships'] for e in entries)
    from stock.sources_ui import passage_lines
    assert 'ENTAILS' in '\n'.join(passage_lines(entries[0],100,True))
    assert {m['text'] for e in entries for m in e['members']}=={'CoreWeave serves many customers.','CoreWeave has customers.'}


def test_manual_relation_survives_refinement_and_ungroup(library,local):
    s,_,add=library;a=add('CoreWeave serves customers.');b=add('CoreWeave serves clients.',1)
    p=insights.stage(s,'CRWV.US',None,lambda _:None);insights.activate(s,p['id'])
    insights.ungroup(s,'CRWV.US',p['groups'][0]['id'])
    p=insights.stage(s,'CRWV.US',None,lambda _:None,refine=True);insights.activate(s,p['id'])
    assert len(p['groups'])==2
    insights.correct_relationship(s,'CRWV.US',a,b,'RELATED','Different perspective')
    p=insights.stage(s,'CRWV.US',None,lambda _:None,refine=True)
    assert p['relationships'][0]['kind']=='RELATED' and p['relationships'][0]['provenance']=='manual'


def test_complete_link_graph_does_not_close_chains(library,local,monkeypatch):
    s,_,add=library
    for t in ['CoreWeave serves customers.','CoreWeave serves clients.','CoreWeave has customers.']:add(t)
    def infer(pairs):
        neutral={'CoreWeave serves customers.','CoreWeave has customers.'}==set(pairs[0])
        return [dict(entailment=.002 if neutral else .995,contradiction=.003,neutral=.995 if neutral else .002)]*2
    monkeypatch.setattr(relationships,'backend',lambda:infer)
    p=insights.stage(s,'CRWV.US',None,lambda _:None)
    assert sorted(len(g['members']) for g in p['groups'])==[1,2]


def test_failed_inference_does_not_activate(library,local,monkeypatch):
    s,_,add=library;add('CoreWeave serves customers.');add('CoreWeave serves clients.',1)
    monkeypatch.setattr(relationships,'backend',lambda:lambda pairs:[])
    with pytest.raises(ValueError):insights.stage(s,'CRWV.US',None,lambda _:None)
    assert insights.head(s,'CRWV.US') is None and len(sources.passages(s,'CRWV.US'))==2


def test_refinement_does_not_extract_or_reverify(library,local,monkeypatch):
    s,_,add=library
    add('CoreWeave serves customers.');add('CoreWeave serves clients.',1)
    p=insights.stage(s,'CRWV.US',None,lambda _:None);insights.activate(s,p['id'])
    before=s.db.execute('SELECT * FROM source_passages ORDER BY id').fetchall()
    monkeypatch.setattr('stock.evidence.extract',lambda *a:pytest.fail('No extraction'))
    again=insights.stage(s,'CRWV.US',None,lambda _:None,refine=True);insights.activate(s,again['id'])
    assert len(local)==2 and again['semantic_map']['score_cache_hit']
    assert before==s.db.execute('SELECT * FROM source_passages ORDER BY id').fetchall()


def test_graph_integrity_rejects_missing_direct_edge(library,local):
    s,_,add=library;add('CoreWeave serves customers.');add('CoreWeave serves clients.',1)
    p=insights.stage(s,'CRWV.US',None,lambda _:None)
    p['relationships']=[]
    with pytest.raises(ValueError,match='complete-link'):insights.save_revision(s,p)


def test_failed_local_inference_resumes_completed_pairs(library,local,monkeypatch):
    s,_,add=library
    for text in ['CoreWeave serves customers.','CoreWeave serves clients.','CoreWeave has customers.']:add(text)
    count=[]
    def interrupted(pairs):
        count.append(True)
        if len(count)==2:raise ValueError('interrupted')
        return [dict(entailment=.995,contradiction=.002,neutral=.003)]*2
    monkeypatch.setattr(relationships,'backend',lambda:interrupted)
    with pytest.raises(ValueError,match='interrupted'):insights.stage(s,'CRWV.US',None,lambda _:None)
    assert not insights.head(s,'CRWV.US')
    assert s.db.execute('SELECT count(*) FROM source_nli_cache').fetchone()[0]==1
    monkeypatch.setattr(relationships,'backend',lambda:lambda pairs:[dict(entailment=.995,contradiction=.002,neutral=.003)]*2)
    p=insights.stage(s,'CRWV.US',None,lambda _:None)
    assert p['cached_decisions']==1 and p['semantic_map']['nli_inference_count']==4


async def test_keyboard_relationship_jump_and_source(library,local,monkeypatch):
    from stock.sources_ui import SourcesApp
    s,_,add=library
    a=add('CoreWeave serves customers.',topics=('Market',))
    b=add('CoreWeave has clients.',1,topics=('Operations',))
    p=insights.stage(s,'CRWV.US',None,lambda _:None);insights.activate(s,p['id'])
    insights.correct_relationship(s,'CRWV.US',a,b,'ENTAILS','Reviewed containment','left_to_right')
    opened=[];monkeypatch.setattr('stock.sources_ui.open_file',lambda path:opened.append(path))
    app=SourcesApp('CRWV.US',s)
    async with app.run_test(size=(100,30)) as pilot:
        await pilot.press('right','space','r','o')
        assert app.topic=='Operations'
        assert app.member(app.visible()[app.selected])['id']==b and opened
        await pilot.press('escape')


def test_manual_split_tombstone_survives_retired_member(library,local):
    s,_,add=library;a=add('CoreWeave serves customers.');b=add('CoreWeave serves clients.',1)
    p=insights.stage(s,'CRWV.US',None,lambda _:None);insights.activate(s,p['id'])
    insights.ungroup(s,'CRWV.US',p['groups'][0]['id'])
    with s.db:
        s.db.execute('DELETE FROM source_topics WHERE passage_id=?',(b,))
        s.db.execute('DELETE FROM source_passages WHERE id=?',(b,))
    p=insights.stage(s,'CRWV.US',None,lambda _:None);insights.activate(s,p['id'])
    assert tuple(sorted((a,b))) in set(map(tuple,p['suppressed_pairs']))
    assert add('CoreWeave serves clients.',1)==b
    p=insights.stage(s,'CRWV.US',None,lambda _:None)
    assert len(p['groups'])==2


def test_cli_map_refine_uses_only_local_graph(library,local,monkeypatch,capsys):
    from stock.cli import main
    s,_,add=library;add('CoreWeave serves customers.');add('CoreWeave serves clients.',1)
    before=s.db.execute('SELECT * FROM source_passages ORDER BY id').fetchall()
    db_path=s.db.execute('PRAGMA database_list').fetchone()[2]
    monkeypatch.setattr('stock.cli.Store',lambda:s)
    monkeypatch.setattr('sys.argv',['stock','map','CRWV.US','--refine'])
    assert main()==0
    assert '0 Cursor deduplication requests' in capsys.readouterr().out
    # CLI closes the connection; reopen the disposable test database.
    import sqlite3
    s.db=sqlite3.connect(db_path)
    assert insights.head(s,'CRWV.US')
    assert before==s.db.execute('SELECT * FROM source_passages ORDER BY id').fetchall()


def test_current_requires_current_graph_and_model_policy(library,local,monkeypatch):
    s,_,add=library;add('CoreWeave serves customers.');add('CoreWeave serves clients.',1)
    p=insights.stage(s,'CRWV.US',None,lambda _:None);insights.activate(s,p['id'])
    assert insights.current(s,'CRWV.US')
    monkeypatch.setattr(relationships,'POLICY','next-policy')
    assert not insights.current(s,'CRWV.US')


def test_policy_revision_reuses_original_source_raw_scores(library,local,monkeypatch):
    s,_,add=library;add('CoreWeave serves customers.');add('CoreWeave serves clients.',1)
    p=insights.stage(s,'CRWV.US',None,lambda _:None);insights.activate(s,p['id'])
    before=[e['scores'] for e in p['relationships']]
    monkeypatch.setattr(relationships,'POLICY','revised-decision-only')
    p=insights.stage(s,'CRWV.US',None,lambda _:None)
    assert p['semantic_map']['nli_inference_count']==0 and len(local)==2
    assert [e['scores'] for e in p['relationships']]==before
    assert all(e['policy']=='revised-decision-only' for e in p['relationships'])


def test_structured_source_context_changes_invalidate_graph(library,local):
    s,_,add=library;add('CoreWeave serves customers.');add('CoreWeave serves clients.',1)
    p=insights.stage(s,'CRWV.US',None,lambda _:None);insights.activate(s,p['id'])
    assert insights.current(s,'CRWV.US')
    with s.db:
        s.db.execute("UPDATE archive_documents SET structured_metadata=?",('{"registrant":"Microsoft"}',))
    assert not insights.current(s,'CRWV.US')


def test_empty_context_preserves_historical_source_fingerprints():
    row=dict(text='Claim',id='p')
    doc=dict(id=1,period='2025')
    assert insights.passage_fingerprint(row,doc)==insights.passage_fingerprint(row,dict(doc,structured_metadata='{}'))
    assert insights.passage_fingerprint(row,doc)!=insights.passage_fingerprint(row,dict(doc,structured_metadata='{"issuer":"CoreWeave"}'))


def test_legacy_cache_survives_context_fingerprint_upgrade(library,local,monkeypatch):
    s,_,add=library;add('CoreWeave serves customers.');add('CoreWeave serves clients.',1)
    p=insights.stage(s,'CRWV.US',None,lambda _:None);insights.activate(s,p['id'])
    # Recreate the original commit's source-keyed cache with no text-only key.
    import json
    edge=p['relationships'][0];lookup={r['id']:r for r in p['evidence']}
    a,b=edge['left'],edge['right']
    legacy=relationships._digest([relationships.CONTRACT,*edge['source_fingerprints'],lookup[a]['text'],lookup[b]['text']])
    with s.db:
        s.db.execute('DELETE FROM source_nli_cache')
        s.db.execute('INSERT INTO source_nli_cache VALUES(?,?,?)',(legacy,relationships.CONTRACT,json.dumps(list(edge['scores'].values()))))
        s.db.execute('UPDATE archive_documents SET structured_metadata=?',('{"issuer":"CoreWeave"}',))
    def forbidden():pytest.fail('Unchanged original texts must reuse legacy scores across context changes')
    monkeypatch.setattr(relationships,'backend',forbidden)
    revised=insights.stage(s,'CRWV.US',None,lambda _:None)
    assert revised['semantic_map']['nli_inference_count']==0
    assert revised['fingerprints']!=p['fingerprints']
