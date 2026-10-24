"""Immutable graph revisions; presentation groups are conservative graph views."""
from itertools import combinations
from collections import Counter
from . import insights as views, sources, relationships as nli

GRAPH_CONTRACT='proposition-graph-1'


def groups(rows,edges,suppressed):
    positive={tuple(sorted((e['left'],e['right']))) for e in edges if e['kind']=='EQUIVALENT'}-set(suppressed)
    result=[]
    for p in rows:
        ident=p['id']
        target=next((g for g in result if all(tuple(sorted((ident,m))) in positive for m in g['members'])),None)
        if target is None:
            target=dict(members=[],canonical=ident);result.append(target)
        target['members'].append(ident)
    lookup={p['id']:p for p in rows}
    for g in result:
        g['canonical']=min(g['members'],key=lambda m:(lookup[m]['location'].get('review',{}).get('readability')!='clear',len(lookup[m]['text']),m))
        g['id']='i:'+views.digest(sorted(g['members']))[:24]
        g['basis']=[dict(pair=views.digest([e['left'],e['right']]),equivalent=True,
            relation=e['kind'],reason=e['reason'],information_preserved=True,
            dimensions_agree=True,differences=[]) for e in edges
            if e['kind']=='EQUIVALENT' and e['left'] in g['members'] and e['right'] in g['members']]
    return result


def validate(proposal):
    if 'graph_contract' not in proposal:return  # historical immutable views
    if proposal['graph_contract']!=GRAPH_CONTRACT:raise ValueError('Unsupported graph contract')
    ids=set(proposal['fingerprints']);assigned=[];positive=set();seen=set()
    for e in proposal['relationships']:
        pair=(e['left'],e['right'])
        if (e['kind'] not in nli.KINDS or e['left']==e['right'] or not set(pair)<=ids
            or tuple(sorted(pair)) in seen):raise ValueError('Invalid graph edge')
        seen.add(tuple(sorted(pair)))
        if e['source_fingerprints']!=[proposal['fingerprints'][m] for m in pair]:raise ValueError('Stale graph source fingerprints')
        if e['kind']=='ENTAILS' and e['direction'] not in ('left_to_right','right_to_left'):raise ValueError('Missing entailment direction')
        if e['kind']=='EQUIVALENT':positive.add(tuple(sorted(pair)))
    suppressed=set(map(tuple,proposal['suppressed_pairs']))
    for g in proposal['groups']:
        if not g['members'] or g['canonical'] not in g['members']:raise ValueError('Invalid presentation group')
        assigned.extend(g['members'])
        for pair in combinations(g['members'],2):
            pair=tuple(sorted(pair))
            if pair not in positive or pair in suppressed:raise ValueError('Group lacks direct complete-link support')
    if set(assigned)!=ids or len(assigned)!=len(ids):raise ValueError('Graph lost or duplicated evidence')
    if {p['id'] for p in proposal['evidence']}!=ids:raise ValueError('Graph evidence mismatch')


def stage(store,ticker,progress=print,new_document=None,new_documents=None,identity_map=None,refine=False):
    views.schema(store)
    from .archive import documents
    docs={d['id']:{k:d.get(k) for k in ('id','title','type','publisher','period','publication_date','source_sha256','metadata_provenance')} for d in documents(store,ticker)}
    rows=sources.passages(store,ticker)
    initial=views.snapshot(store,ticker);parent=views.head(store,ticker)
    previous=views.load(store,parent) if parent else {}
    replacements=new_documents or ([new_document] if new_document else [])
    for doc,passages in replacements:
        rows=[p for p in rows if p['document_id']!=doc['id']]+[dict(p,id=sources.passage_id(doc,p),document_id=doc['id']) for p in passages]
        docs[doc['id']]={k:doc.get(k) for k in ('id','title','type','publisher','period','publication_date','source_sha256','metadata_provenance')}
    from .editorial import validate_publication
    for p in rows:validate_publication(p)
    lookup={p['id']:p for p in rows}
    fps={p['id']:views.passage_fingerprint(p,docs[p['document_id']]) for p in rows}
    remap=identity_map or {}
    suppressed={tuple(sorted((remap.get(a,a),remap.get(b,b)))) for a,b in views.suppressed_pairs(store,previous)}
    prior_fps=previous.get('fingerprints',{})
    edges={}
    overrides={tuple(sorted((e['left'],e['right']))):e for e in previous.get('relationship_overrides',[])}
    overrides.update({tuple(sorted((e['left'],e['right']))):e for e in previous.get('relationships',[]) if e.get('provenance')=='manual'})
    prior_edges=[e for e in previous.get('relationships',[]) if e.get('provenance')!='manual']+list(overrides.values())
    for e in prior_edges:
        a,b=e['left'],e['right'];ma,mb=remap.get(a,a),remap.get(b,b)
        if ma not in lookup or mb not in lookup:continue
        unchanged=e.get('source_fingerprints')==[fps.get(a),fps.get(b)]
        if e['provenance']=='manual':
            updated=dict(e,left=ma,right=mb,source_fingerprints=[fps[ma],fps[mb]])
            if not unchanged:
                updated.update(kind='UNRESOLVED',direction=None,prior_manual_decision=e,
                    reason='Manual correction retained for review after evidence identity changed: '+e['reason'])
            edges[tuple(sorted((ma,mb)))]=updated
            overrides.pop(tuple(sorted((a,b))),None)
            overrides[tuple(sorted((ma,mb)))]=updated
        elif unchanged and e.get('policy')==nli.POLICY and e.get('model')==nli.CONTRACT:
            edges[tuple(sorted((a,b)))]=e
    # Legacy groups retain their exact direct independent judgments in history;
    # current graph members are reconsidered locally, never treated as transitive proof.
    incoming={p['id'] for p in rows if p['document_id'] in {d['id'] for d,_ in replacements}} if replacements else set(lookup)
    prior_frontier=previous.get('semantic_map',{}).get('frontier',0) if previous.get('semantic_map') else 0
    # Explicit refinement always moves to a broader empirical band. Strong observed
    # discoveries justify skipping a band; sparse samples do not claim calibration.
    prior_outcomes=Counter(e['kind'] for e in previous.get('relationships',[]) if e.get('provenance')=='local_nli')
    material=sum(prior_outcomes[k] for k in ('EQUIVALENT','ENTAILS','CONTRADICTS'))
    step=2 if material>=20 and material/max(1,sum(prior_outcomes.values()))>.5 else 1
    frontier=prior_frontier+step if refine else prior_frontier if previous.get('fingerprints')==fps else 0
    from .semantic_map import candidate_pairs
    selected,stats=candidate_pairs(store,rows,incoming,progress,frontier=frontier)
    # Prior reviewed relationships survive retrieval changes, while unreviewed
    # candidates remain auditable in source_candidate_scores.
    selected=set(selected)|set(edges)|{pair for pair in suppressed if set(pair)<=lookup.keys()}
    cache_hits=0;inferences=0;elapsed=0.0
    model_was_initialized=nli._BACKEND is not None
    prior_execution_seconds=getattr(nli._BACKEND,'inference_seconds',0.0)
    ranked={}
    if stats['candidate_run']:
        ranked={(a,b):score for a,b,score in store.db.execute('SELECT left_id,right_id,similarity FROM source_candidate_scores WHERE run=?',(stats['candidate_run'],))}
    from .sort_budget import check
    for index,(a,b) in enumerate(sorted(selected,key=lambda pair:(-ranked.get(pair,-2.0),pair)),1):
        check()
        if (a,b) in edges:
            cache_hits+=1;continue
        if (a,b) in suppressed:
            e=dict(kind='UNRESOLVED',direction=None,reason='Manual ungroup; retain separate presentation.',
                provenance='manual_split',policy=nli.POLICY,scores={},model=None,
                source_fingerprints=[fps[a],fps[b]],safeguards=['manual_split'])
        else:
            progress(f'Local relationships · {index}/{len(selected)}')
            e=nli.judge(store,lookup[a],lookup[b],fps[a],fps[b])
            cache_hits+=int(e['cache_hit']);inferences+=e['inference_count'];elapsed+=e['elapsed_seconds']
        edges[(a,b)]=dict(e,left=a,right=b)
    # A split is a presentation veto even if an older positive edge survives.
    edge_list=list(edges.values())
    presentation=groups(rows,edge_list,suppressed)
    kinds=Counter(e['kind'] for e in edge_list)
    stats.update(nli_inference_count=inferences,nli_seconds=elapsed,
        nli_execution_seconds=getattr(nli._BACKEND,'inference_seconds',0.0)-prior_execution_seconds,
        all_inventory_pairs=len(rows)*(len(rows)-1)//2,
        unreviewed_inventory_pairs=len(rows)*(len(rows)-1)//2-len(edge_list),
        nli_initialization_seconds=getattr(nli._BACKEND,'initialization_seconds',0.0) if inferences and not model_was_initialized else 0.0,
        cached_inference_pairs=cache_hits,checked_relationships=len(edge_list),
        equivalence_groups=sum(len(g['members'])>1 for g in presentation),
        entailment_edges=kinds['ENTAILS'],contradictions=kinds['CONTRADICTS'],uncertain=kinds['UNRESOLVED'],
        decision_policy=nli.POLICY,inference_model=nli.CONTRACT,calibrated=False,prior_outcomes=dict(prior_outcomes))
    proposal=dict(graph_contract=GRAPH_CONTRACT,relationships=edge_list,relationship_overrides=list(overrides.values()),
        semantic_map=stats,contract=views.CONTRACT,ticker=ticker,parent=parent,snapshot=initial,
        groups=presentation,preview_only=bool(new_documents),fingerprints=fps,
        suppressed_pairs=sorted(suppressed),new_document_id=new_document[0]['id'] if new_document else None,
        passage_count=len(rows),comparison_count=len(selected),model_requests=0,cached_decisions=cache_hits,
        deterministic_decisions=len(suppressed),historical_cached_decisions=0,
        grouping_scope='replacement' if replacements else 'refinement' if refine else 'archive_candidates',
        historical_backlog_pairs=stats['deferred'],evidence=views.rows_to_json(rows),
        differences=[dict(members=[e['left'],e['right']],reason=e['kind']+': '+e['reason'],differences=e.get('safeguards',[])) for e in edge_list if e['kind']!='EQUIVALENT'],
        manual_edits=[list(r) for r in store.db.execute('''SELECT o.* FROM source_overrides o JOIN source_passages p ON p.id=o.passage_id
            JOIN archive_documents d ON d.id=p.document_id WHERE d.ticker=? ORDER BY o.passage_id,o.topic''',(ticker,))])
    validate(proposal)
    if views.snapshot(store,ticker)!=initial or views.head(store,ticker)!=parent:raise ValueError('Evidence changed during graph staging')
    if hasattr(progress,'log_event'):progress.log_event(dict(proposition_graph=stats))
    return views.save_revision(store,proposal)


def correct(store,ticker,left,right,kind,reason,direction=None):
    """Audited manual graph correction; source identity and citations remain intact."""
    if kind not in nli.KINDS or not reason.strip():raise ValueError('Relationship kind and reason required')
    if kind=='ENTAILS' and direction not in ('left_to_right','right_to_left'):raise ValueError('Entailment direction required')
    active=views.head(store,ticker)
    if not active:raise ValueError('No active graph')
    p=views.load(store,active)
    if p.get('graph_contract')!=GRAPH_CONTRACT:raise ValueError('Run local graph staging before relationship corrections')
    if not views.current(store,ticker):raise ValueError('Evidence changed; rebuild graph before correcting relationships')
    if not {left,right}<=p['fingerprints'].keys() or left==right:raise ValueError('Unknown relationship nodes')
    edges=[e for e in p.get('relationships',[]) if {e['left'],e['right']}!={left,right}]
    edges.append(dict(left=left,right=right,kind=kind,direction=direction,reason=reason,
        provenance='manual',policy=nli.POLICY,model=None,scores={},safeguards=[],
        source_fingerprints=[p['fingerprints'][left],p['fingerprints'][right]]))
    suppressed=set(map(tuple,p.get('suppressed_pairs',[])))
    if kind=='EQUIVALENT':suppressed.discard(tuple(sorted((left,right))))
    overrides=[e for e in p.get('relationship_overrides',[]) if {e['left'],e['right']}!={left,right}]+[edges[-1]]
    updated=dict(p,parent=active,snapshot=views.snapshot(store,ticker),relationships=edges,relationship_overrides=overrides,
        groups=groups(p['evidence'],edges,suppressed),suppressed_pairs=sorted(suppressed),
        new_document_id=None,action='relationship_correction')
    validate(updated);updated=views.save_revision(store,updated);views.activate(store,updated['id'])
    return updated
