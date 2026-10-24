"""Offline persistent vector-map tests; no model downloads or Cursor calls."""
import pytest
np = pytest.importorskip('numpy')
from stock.core import Store
from stock import semantic_map


def passage(ident, text):
    return {'id': ident, 'text': text}


class FakeEncoder:
    def __init__(self):
        self.calls = []
    def embed(self, texts, batch_size=None):
        self.calls.append(list(texts))
        for text in texts:
            vector = np.zeros(384, dtype=np.float32)
            if '850MW' in text or 'active power' in text:
                vector[0] = 1
            elif 'revenue' in text.lower():
                vector[1] = 1
            else:
                vector[2] = 1
            yield vector


def test_global_index_scans_every_pair_and_caches_embeddings(tmp_path):
    store=Store(tmp_path/'stock.db')
    encoder=FakeEncoder()
    rows=[passage('new','CoreWeave reported 850MW active power.')]
    rows += [passage('old-'+str(i),'Revenue was stable '+str(i)) for i in range(120)]
    rows += [passage('actual','Active power exceeded 850MW.')]
    pairs,stats=semantic_map.candidate_pairs(store,rows,{'new'},encoder=encoder)
    assert stats['scanned']==121
    assert ('actual','new') in pairs
    assert len(pairs)<60
    assert stats['embedded']==len(rows)
    assert len(encoder.calls)==4
    again=FakeEncoder()
    repeated,metrics=semantic_map.candidate_pairs(store,rows,{'new'},encoder=again)
    assert repeated==pairs
    assert metrics['embedded']==0 and not again.calls
    store.db.close()


def test_text_hash_change_reembeds_only_one_vector(tmp_path):
    store=Store(tmp_path/'stock.db')
    original=[passage('a','CoreWeave reported 850MW active power.'),
              passage('b','Revenue increased.')]
    encoder=FakeEncoder()
    semantic_map.vectors(store,original,encoder=encoder)
    new=[passage('a','CoreWeave reported 850MW active power.'),
         passage('b','Revenue decreased.')]
    second=FakeEncoder()
    semantic_map.vectors(store,new,encoder=second)
    assert second.calls==[['Revenue decreased.']]
    assert store.db.execute('SELECT COUNT(*) FROM source_semantic_vectors').fetchone()[0]==3
    store.db.close()


def test_does_not_merge_semantically_close_statements_without_verification(tmp_path):
    store=Store(tmp_path/'stock.db')
    rows=[passage('n','CoreWeave reported 850MW active power.'),
          passage('o','Active power exceeded 850MW.')]
    pairs,stats=semantic_map.candidate_pairs(store,rows,{'n'},encoder=FakeEncoder())
    assert ('n','o') in pairs
    assert stats['status']=='adaptive_candidates_not_verified_equivalence'
    # There is no grouping or equivalence output in the candidate map at all.
    assert all(len(pair)==2 for pair in pairs)
    store.db.close()


def test_invalid_vectors_cannot_be_cached(tmp_path):
    import pytest
    store=Store(tmp_path/'stock.db')
    class Invalid:
        def embed(self,texts,batch_size=None):
            return [np.full(384,np.nan,dtype=np.float32) for _ in texts]
    with pytest.raises(ValueError,match='nonfinite'):
        semantic_map.vectors(store,[passage('a','Claim')],encoder=Invalid())
    assert store.db.execute('SELECT COUNT(*) FROM source_semantic_vectors').fetchone()[0]==0
    store.db.close()


def test_no_forced_neighbors_or_distant_new_pairs(tmp_path):
    store=Store(tmp_path/'stock.db')
    encoder=FakeEncoder()
    rows=[
        passage('new-a','CoreWeave reported 850MW active power.'),
        passage('new-b','Revenue increased.'),
        passage('historical-far','Revenue decreased.'),
        passage('historical-near','Active power exceeded 850MW.'),
    ]
    pairs,stats=semantic_map.candidate_pairs(
        store,rows,{'new-a','new-b'},encoder=encoder)
    assert ('historical-near','new-a') in pairs
    assert ('historical-far','new-a') not in pairs
    assert ('new-a','new-b') not in pairs
    assert stats['minimum_neighbors']==0
    assert stats['new_new_scanned']==1
    assert stats['scanned']==4
    store.db.close()


def test_frontier_refinement_reuses_scores_and_vectors(tmp_path):
    store=Store(tmp_path/'stock.db')
    class Graded:
        def embed(self,texts,batch_size=None):
            for text in texts:
                angle=float(text)
                v=np.zeros(384,dtype=np.float32);v[0]=np.cos(angle);v[1]=np.sin(angle)
                yield v
    rows=[passage(str(i),str(i*.25)) for i in range(8)]
    first,stats=semantic_map.candidate_pairs(store,rows,{'0'},encoder=Graded())
    later,more=semantic_map.candidate_pairs(store,rows,{'0'},encoder=Graded(),frontier=2)
    assert first < later
    assert more['embedded']==0 and more['score_cache_hit']
    assert stats['deferred']>more['deferred']
    assert more['cursor_deduplication_requests']==0


def test_single_proposition_needs_no_model(tmp_path,monkeypatch):
    store=Store(tmp_path/'stock.db')
    monkeypatch.setattr(semantic_map,'_model',lambda:pytest.fail('No pair requires no model'))
    pairs,stats=semantic_map.candidate_pairs(store,[passage('a','Only claim')],{'a'})
    assert not pairs and stats['similarity_calculations']==stats['embedded']==0


def test_lone_close_neighbor_uses_empirical_null_reference(tmp_path):
    store=Store(tmp_path/'stock.db')
    class Close:
        def embed(self,texts,batch_size=None):
            for text in texts:
                v=np.zeros(384,dtype=np.float32)
                if text=='a':v[0]=1
                elif text=='b':v[0]=.99;v[1]=np.sqrt(1-.99**2)
                else:v[2]=1
                yield v
    pairs,stats=semantic_map.candidate_pairs(store,[passage('a','a'),passage('b','b')],{'a'},encoder=Close())
    assert pairs=={('a','b')}
    assert stats['null_reference_comparisons']>0
