"""Local graph policy tests; injected inference is evidence, never an API call."""
import pytest
from stock import relationships as rel
from stock.core import Store


def p(text, **kw):
    return dict(text=text, speaker=None, category='Management', location={}, **kw)


def scores(e=.99, c=.005, n=.005):
    return dict(entailment=e, contradiction=c, neutral=n)


def test_directions_and_uncertainty():
    a=p('CoreWeave serves customers.');b=p('CoreWeave serves clients.')
    assert rel.decide(a,b,scores(),scores())['kind']=='EQUIVALENT'
    assert rel.decide(a,b,scores(),scores(.005,.005,.99))['kind']=='ENTAILS'
    assert rel.decide(a,b,scores(.005,.005,.99),scores())['direction']=='right_to_left'
    assert rel.decide(a,b,scores(.4,.2,.4),scores(.4,.2,.4))['kind']=='UNRESOLVED'
    assert rel.decide(a,b,scores(.005,.005,.99),scores(.005,.005,.99))['kind']=='RELATED'


@pytest.mark.parametrize('left,right',[
 ('Revenue was $5 billion in 2025.','Revenue was $5 billion in 2026.'),
 ('Revenue was $5 billion.','Revenue is forecast to be $5 billion.'),
 ('Active capacity is 850 MW.','Contracted capacity is 850 MW.'),
 ('Revenue is $5 billion.','Backlog is $5 billion.'),
 ('Revenue is $5 billion in Europe.','Revenue is $5 billion globally.'),
 ('Demand exceeds capacity.','Demand exceeds capacity except in Europe.'),
 ('CoreWeave revenue rose.','Microsoft revenue rose.'),
 ('Revenue is $5 billion.','Revenue is $6 billion.'),
])
def test_material_conflicts_veto_even_confident_equivalence(left,right):
    r=rel.decide(p(left),p(right),scores(),scores())
    assert r['kind']=='UNRESOLVED' and r['safeguards']


def test_unknown_structured_scope_is_conservative():
    a=p('Revenue rose.',attributes={'scope':'Europe'})
    b=p('Revenue increased.')
    assert rel.decide(a,b,scores(),scores())['kind']=='UNRESOLVED'


def test_contradiction_requires_matching_conditions():
    a=p('CoreWeave revenue increased globally in 2025.')
    b=p('CoreWeave revenue decreased globally in 2025.')
    assert rel.decide(a,b,scores(.005,.99,.005),scores(.005,.99,.005))['kind']=='CONTRADICTS'
    b=p('CoreWeave revenue decreased globally in 2026.')
    assert rel.decide(a,b,scores(.005,.99,.005),scores(.005,.99,.005))['kind']=='UNRESOLVED'


def test_cached_bidirectional_inference_and_policy_reuse(tmp_path):
    s=Store(tmp_path/'db');calls=[]
    def infer(pairs):
        calls.extend(pairs);return [scores() for _ in pairs]
    a=p('CoreWeave serves customers.');b=p('CoreWeave serves clients.')
    first=rel.judge(s,a,b,'fa','fb',infer)
    assert len(calls)==2 and first['kind']=='EQUIVALENT'
    second=rel.judge(s,a,b,'fa','fb',infer)
    assert second['cache_hit'] and len(calls)==2
    rel.judge(s,a,b,'changed-source','fb',infer)
    assert len(calls)==4


def test_invalid_scores_fail_closed(tmp_path):
    s=Store(tmp_path/'db')
    with pytest.raises(ValueError):
        rel.judge(s,p('A'),p('B'),'a','b',lambda pairs:[scores(float('nan'))]*2)


def test_jointly_missing_financial_attributes_are_not_agreement():
    a=p('Revenue was $5 billion.');b=p('Revenue totaled $5 billion.')
    r=rel.decide(a,b,scores(),scores())
    assert r['kind']=='UNRESOLVED' and any('unknown' in s for s in r['safeguards'])


def test_same_claim_with_conflicting_verified_reporting_context():
    a=p('Revenue was $5 billion.',attributes={'issuer':'CoreWeave','period':'2025','scope':'company'})
    b=p('Revenue was $5 billion.',attributes={'issuer':'CoreWeave','period':'2026','scope':'company'})
    assert rel.decide(a,b,scores(),scores())['kind']=='UNRESOLVED'


def test_unlisted_counterparties_are_material():
    a=p('CoreWeave signed a partnership with IBM.')
    b=p('CoreWeave signed a partnership with AMD.')
    assert rel.decide(a,b,scores(),scores())['kind']=='UNRESOLVED'


def test_model_refuses_overlength_without_inference():
    obj=object.__new__(rel.LocalNLI)
    class Tokenizer:
        def encode(self,a,b):
            from types import SimpleNamespace
            return SimpleNamespace(ids=[0]*513,attention_mask=[1]*513)
    class Session:
        def run(self,*args):pytest.fail('No truncated inference')
    obj.tokenizer=Tokenizer();obj.session=Session();obj.inference_seconds=0
    assert obj([('long','pair')])==[None]


def test_abbreviated_magnitude_is_material_even_with_known_scope():
    context={'issuer':'CoreWeave','period':'2025','scope':'company'}
    a=p('CoreWeave revenue was $5B in 2025.',attributes=context)
    b=p('CoreWeave revenue was $5M in 2025.',attributes=context)
    r=rel.decide(a,b,scores(),scores())
    assert r['kind']=='UNRESOLVED' and 'numbers' in r['safeguards']


def test_policy_change_reuses_raw_inference(tmp_path,monkeypatch):
    s=Store(tmp_path/'db');calls=[]
    def infer(pairs):
        calls.extend(pairs);return [scores() for _ in pairs]
    a=p('CoreWeave serves customers.');b=p('CoreWeave serves clients.')
    rel.judge(s,a,b,'a','b',infer)
    monkeypatch.setattr(rel,'POLICY','future-policy')
    result=rel.judge(s,a,b,'a','b',infer)
    assert result['policy']=='future-policy' and result['cache_hit'] and len(calls)==2
