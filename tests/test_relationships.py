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
    changed=rel.judge(s,a,b,'changed-source','fb',infer)
    assert len(calls)==2 and changed['source_fingerprints']==['changed-source','fb']


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


@pytest.mark.parametrize('a,b',[
 ('CoreWeave revenue was $5 billion in 2025.', 'In 2025 CoreWeave generated $5 billion of revenue.'),
 ('CoreWeave ended 2025 with more than 850 megawatts of active power.', 'As of December 31, 2025, CoreWeave reported 850MW+ of active power.'),
 ('CoreWeave reported 43 active data centers as of December 31, 2025.', 'CoreWeave ended 2025 with 43 active data centers.'),
])
def test_semantically_compatible_financial_notation(a,b):
    assert rel.decide(p(a),p(b),scores(),scores())['kind']=='EQUIVALENT'


def test_complete_kpi_parse_can_resolve_model_date_notation_failure():
    a=p('CoreWeave ended 2025 with more than 850 megawatts of active power.')
    b=p('CoreWeave reached more than 850 megawatts of active power as of December 31, 2025.')
    r=rel.decide(a,b,scores(.02,.005,.975),scores(.96,.005,.035))
    assert r['kind']=='EQUIVALENT' and r['decision_basis']=='complete_kpi_parse'


@pytest.mark.parametrize('tail',[
 ' excluding leased sites.', ' in Europe.', ' subject to permits.',
 ' and expected to reach 90 by 2027.',
])
def test_complete_parse_never_discards_material_tail(tail):
    a=p('CoreWeave ended 2025 with 43 active data centers.')
    b=p('CoreWeave ended 2025 with 43 active data centers'+tail)
    assert rel.decide(a,b,scores(.02,.005,.975),scores(.96,.005,.035))['kind']!='EQUIVALENT'


def test_may_modal_is_not_reporting_month():
    assert rel.attributes(p('CoreWeave may expand.'))['period']==[]


def test_context_recovery_does_not_use_publication_or_publisher():
    row=p('Revenue increased.',attributes={})
    enriched=rel.with_context(row,dict(publication_date='2026-05-01',publisher='Reuters',period='2025'))
    assert enriched['text']==row['text']
    assert not rel.attributes(enriched)['entity']
    assert not rel.attributes(enriched)['period']


def test_source_context_is_audited_and_only_resolves_deictic_period():
    row=p('We ended the year with 43 active data centers.')
    enriched=rel.with_context(row,dict(id=12,period='2025',structured_metadata={'registrant':'CoreWeave','period_end':'2025-12-31'}))
    attrs=rel.attributes(enriched)
    assert attrs['entity']==['coreweave'] and attrs['period']==['2025-12-31']
    assert enriched['semantic_context']['provenance']
    assert row.get('semantic_context') is None


def test_scope_aliases_and_verified_context_are_semantic():
    a=p('CoreWeave revenue was $5 billion in 2025 globally.',attributes={'scope':'global'})
    b=p('CoreWeave revenue totaled $5 billion in 2025 worldwide.',attributes={'scope':'worldwide'})
    assert rel.decide(a,b,scores(),scores())['kind']=='EQUIVALENT'


def test_structured_conflicts_with_text_do_not_disappear():
    a=p('CoreWeave revenue was $5 billion in 2025.',attributes={'issuer':'Microsoft'})
    b=p('CoreWeave revenue totaled $5 billion in 2025.',attributes={'issuer':'Microsoft'})
    assert rel.decide(a,b,scores(),scores())['kind']=='UNRESOLVED'


def test_literal_conjunct_entailment_keeps_direction():
    a=p('CoreWeave serves customers and operates data centers.')
    b=p('CoreWeave serves customers.')
    r=rel.decide(a,b,scores(),scores(.005,.005,.99))
    assert r['kind']=='ENTAILS' and r['direction']=='left_to_right'


def test_kpi_parser_does_not_equate_fiscal_and_calendar_year_end():
    a=p('CoreWeave ended fiscal 2025 with 43 active data centers.')
    b=p('CoreWeave reported 43 active data centers as of December 31, 2025.')
    assert rel.decide(a,b,scores(.02,.005,.975),scores(.96,.005,.035))['kind']!='EQUIVALENT'


def test_explicit_anchored_source_note_resolves_missing_asof():
    row=p('CoreWeave reported 43 active data centers.')
    row['location']['references']=[dict(source_id='note:1',text='Notes: Figures as of December 31, 2025. This graphic is illustrative.')]
    enriched=rel.with_context(row,dict(id=13,publication_date='2026-02-01'))
    assert rel.attributes(enriched)['period']==['2025-12-31']
    assert enriched['semantic_context']['provenance']['period']['source_id']=='note:1'
    assert row['location']==enriched['location']


def test_surrounding_paragraph_does_not_supply_arbitrary_period_or_scope():
    row=p('CoreWeave reported 43 active data centers.')
    row['location']['references']=[dict(source_id='paragraph',text='In 2024 we operated globally. We ended 2025 with 43 sites and plan 60 in 2027.')]
    enriched=rel.with_context(row,dict(id=12,period='2025'))
    assert not rel.attributes(enriched)['period']


def test_conflicting_explicit_source_notes_remain_unknown():
    row=p('CoreWeave reported 43 active data centers.')
    row['location']['references']=[dict(source_id=str(i),text=f'Notes: Figures as of December 31, {year}.') for i,year in enumerate((2024,2025))]
    enriched=rel.with_context(row,dict(id=13))
    assert not rel.attributes(enriched)['period']


def test_complete_issuer_kpi_retains_missing_source_speaker_without_veto():
    a=p('CoreWeave ended 2025 with 43 active data centers.')
    a['speaker']='Michael Intrator'
    b=p('CoreWeave reported 43 active data centers as of December 31, 2025.')
    r=rel.decide(a,b,scores(.02,.005,.975),scores(.96,.005,.035))
    assert r['kind']=='EQUIVALENT'
    assert 'speaker' in r['compatibility']['missing']
    assert 'speaker' not in r['compatibility']['agreements']


def test_complete_issuer_kpi_preserves_explicit_attribution_disagreement():
    a=p('CoreWeave ended 2025 with 43 active data centers.');a['speaker']='Michael Intrator'
    b=p('CoreWeave reported 43 active data centers as of December 31, 2025.');b['speaker']='Another Person'
    assert rel.decide(a,b,scores(),scores())['kind']=='UNRESOLVED'
    b['speaker']=None;b['category']='Analyst'
    assert rel.decide(a,b,scores(),scores())['kind']=='UNRESOLVED'


def test_source_qualifications_veto_complete_kpi_equivalence():
    rows=[]
    for qualifier in ('Excluding leased sites.','Including leased sites.'):
        row=p('CoreWeave reported 43 active data centers as of December 31, 2025.')
        row['location']['references']=[dict(source_id=qualifier,text='Notes: Figures as of December 31, 2025. '+qualifier)]
        rows.append(rel.with_context(row,dict(id=13)))
    assert rel.decide(*rows,scores(),scores())['kind']=='UNRESOLVED'
    rows[1]['location']={};rows[1]=rel.with_context(rows[1],dict(id=13))
    assert rel.decide(*rows,scores(),scores())['kind']=='UNRESOLVED'


def test_context_correction_reuses_raw_text_inference(tmp_path):
    s=Store(tmp_path/'db');calls=[]
    def infer(pairs):
        calls.extend(pairs);return [scores()]*2
    a=p('CoreWeave serves customers.');b=p('CoreWeave serves clients.')
    rel.judge(s,a,b,'original-a','original-b',infer)
    r=rel.judge(s,a,b,'new-context-a','new-context-b',infer)
    assert len(calls)==2 and r['cache_hit']
    assert r['source_fingerprints']==['new-context-a','new-context-b']


def test_legacy_raw_cache_migrates_without_reinference(tmp_path):
    import json
    s=Store(tmp_path/'db');rel.schema(s)
    a=p('CoreWeave serves customers.');b=p('CoreWeave serves clients.')
    legacy=rel._digest([rel.CONTRACT,'fa','fb',a['text'],b['text']])
    with s.db:s.db.execute('INSERT INTO source_nli_cache VALUES(?,?,?)',(legacy,rel.CONTRACT,json.dumps([scores(),scores()])))
    def forbidden(_):pytest.fail('Legacy raw inference must be reused')
    assert rel.judge(s,a,b,'fa','fb',forbidden)['cache_hit']
    assert rel.judge(s,a,b,'corrected','fb',forbidden)['cache_hit']
    changed=dict(a,text='CoreWeave serves nobody.')
    calls=[]
    rel.judge(s,changed,b,'corrected','fb',lambda pairs:(calls.extend(pairs) or [scores(),scores()]))
    assert len(calls)==2


@pytest.mark.parametrize('note',['Europe.','Non-GAAP.','Forecast capacity.','In gigawatts.'])
def test_source_note_scope_definition_and_units_are_not_dropped(note):
    a=p('CoreWeave reported 43 active data centers as of December 31, 2025.')
    a['location']['references']=[dict(source_id='note',text='Notes: Figures as of December 31, 2025. '+note)]
    b=p(a['text'])
    a=rel.with_context(a,dict(id=13));b=rel.with_context(b,dict(id=12))
    assert rel.decide(a,b,scores(),scores())['kind']=='UNRESOLVED'


def test_year_shaped_amount_is_never_removed_as_reporting_period():
    a=p('CoreWeave revenue was $2024 million in 2025.')
    b=p('CoreWeave revenue was $2025 million in 2025.')
    assert rel.decide(a,b,scores(),scores())['kind']=='UNRESOLVED'
    assert rel.attributes(a)['period']==['2025']
    assert rel.attributes(a)['numbers']!=rel.attributes(b)['numbers']


def test_deictic_fiscal_year_does_not_invent_december_end():
    row=p('We ended the year with 43 active data centers.')
    enriched=rel.with_context(row,dict(id=12,period='2025',structured_metadata={'registrant':'Microsoft'}))
    assert not rel.attributes(enriched)['period']


def test_financial_first_conjunct_entails_without_discarding_extra_numbers():
    a=p('CoreWeave revenue was $5 billion in 2025 and profit was $1 billion.')
    b=p('CoreWeave revenue was $5 billion in 2025.')
    result=rel.decide(a,b,scores(),scores(.005,.005,.99))
    assert result['kind']=='ENTAILS' and result['direction']=='left_to_right'
    assert rel.decide(b,a,scores(.005,.005,.99),scores())['direction']=='right_to_left'
    b['attributes']={'issuer':'Microsoft'}
    assert rel.decide(a,b,scores(),scores(.005,.005,.99))['kind']=='UNRESOLVED'


def test_source_note_date_conflicting_with_claim_blocks_complete_kpi():
    a=p('CoreWeave reported 43 active data centers as of December 31, 2025.')
    a['location']['references']=[dict(source_id='note',text='Notes: Figures as of December 31, 2024.')]
    b=p('CoreWeave ended 2025 with 43 active data centers.')
    a=rel.with_context(a,dict(id=13))
    assert rel.decide(a,b,scores(),scores())['kind']=='UNRESOLVED'


def test_written_quarters_and_fiscal_years_remain_material():
    a=p('CoreWeave revenue rose globally in the first quarter of 2025.')
    b=p('CoreWeave revenue rose globally in the second quarter of 2025.')
    assert rel.decide(a,b,scores(),scores())['kind']=='UNRESOLVED'
    a=p('CoreWeave revenue rose globally in fiscal 2025.')
    b=p('CoreWeave revenue rose globally in calendar 2025.')
    assert rel.decide(a,b,scores(),scores())['kind']=='UNRESOLVED'


def test_annual_archive_reporting_end_resolves_deictic_year():
    row=p('We ended the year with 43 active data centers.')
    doc=dict(id=7,type='Annual',structured_metadata={'report_period_end':'2025-06-30','issuer':'Microsoft'})
    enriched=rel.with_context(row,doc)
    assert rel.attributes(enriched)['period']==['2025-06-30']
    assert enriched['semantic_context']['provenance']['period']['field']=='structured_metadata.report_period_end'
    doc['type']='Quarterly'
    assert not rel.attributes(rel.with_context(row,doc))['period']


def test_source_note_conflicts_with_recovered_reporting_period():
    row=p('We ended the year with 43 active data centers.',attributes={'scope':'issuer'})
    row['location']['references']=[dict(source_id='note',text='Notes: Figures as of December 31, 2024.')]
    doc=dict(id=7,type='Annual',structured_metadata={'report_period_end':'2025-06-30','issuer':'Microsoft'})
    a=rel.with_context(row,doc)
    b=rel.with_context(dict(row,location={}),doc)
    assert rel.decide(a,b,scores(),scores())['kind']=='UNRESOLVED'


@pytest.mark.parametrize('metric,value,billions',[
 ('revenue','245122','245.122'),('total net sales','391035','391.035'),
 ('net income','93736','93.736'),
])
def test_full_money_fact_recovers_exact_units_despite_wrong_nli(metric,value,billions):
    a=p(f'Exampleco {metric} was ${value} million in fiscal 2024.',attributes={'issuer':'Exampleco'})
    b=p(f'Exampleco {metric} totaled ${billions} billion in fiscal 2024.',attributes={'issuer':'Exampleco'})
    r=rel.decide(a,b,scores(.001,.998,.001),scores(.001,.998,.001))
    assert r['kind']=='EQUIVALENT' and r['decision_basis']=='complete_financial_parse'
    assert r['normalized_fact']['scope']=='issuer'


@pytest.mark.parametrize('change',[
 lambda s:s.replace('2024','2023'),lambda s:s.replace('fiscal','calendar'),
 lambda s:s.replace('Microsoft','Otherco'),lambda s:s.replace('revenue','net income'),
 lambda s:s.replace('revenue','adjusted revenue'),lambda s:s.replace('$','€'),
 lambda s:s.replace('123.456','123.5'),lambda s:s.replace('totaled','is forecast to total'),
 lambda s:s.replace('totaled','did not total'),lambda s:s.replace('revenue','revenue in Europe'),
 lambda s:s[:-1]+' excluding leases.',lambda s:s[:-1]+' and cash increased.',
 lambda s:s.replace('fiscal 2024','2024'),lambda s:s.replace('123.456','approximately 123.456'),
])
@pytest.mark.parametrize('entailment',[.2,.99])
def test_financial_proof_requires_complete_matching_proposition(change,entailment):
    a=p('Microsoft revenue was $123456 million in fiscal 2024.')
    b=p(change('Microsoft revenue totaled $123.456 billion in fiscal 2024.'))
    r=rel.decide(a,b,scores(entailment,.005,1-entailment-.005),scores(entailment,.005,1-entailment-.005))
    assert r['kind']!='EQUIVALENT'


def test_money_parser_restrictions_and_attribution_veto():
    a=p('Microsoft revenue was $123456 million in fiscal 2024.')
    b=p('Microsoft revenue totaled $123.456 billion in fiscal 2024.')
    b['semantic_context']={'source_notes':['Notes: Figures as of December 31, 2024. Excludes Europe.']}
    assert rel.decide(a,b,scores(),scores())['kind']!='EQUIVALENT'
    b.pop('semantic_context');b['speaker']='different speaker'
    assert rel.decide(a,b,scores(),scores())['kind']!='EQUIVALENT'


@pytest.mark.parametrize('prefix',['Total','Consolidated','Adjusted','Annual','Global','Reported'])
def test_money_grammar_does_not_invent_issuer_from_qualifier(prefix):
    a=p(f'{prefix} revenue was $1000 million in fiscal 2024.')
    b=p(f'{prefix} revenue totaled $1 billion in fiscal 2024.')
    assert rel.decide(a,b,scores(.001,.998,.001),scores(.001,.998,.001))['kind']!='EQUIVALENT'


def test_half_year_mismatch_vetoes_even_wrong_high_entailment():
    a=p('Microsoft revenue was $10 million in the first half of fiscal 2024.')
    b=p('Microsoft revenue was $10 million in the second half of fiscal 2024.')
    assert rel.decide(a,b,scores(),scores())['kind']=='UNRESOLVED'


def test_numeric_contradiction_only_under_complete_same_conditions():
    a=p('Microsoft revenue was $10 million in fiscal 2024.')
    b=p('Microsoft revenue was $20 million in fiscal 2024.')
    r=rel.decide(a,b,scores(.001,.998,.001),scores(.001,.998,.001))
    assert r['kind']=='CONTRADICTS'
    assert rel.decide(a,b,scores(),scores())['kind']=='UNRESOLVED'
    b['text']=b['text'].replace('fiscal','calendar')
    assert rel.decide(a,b,scores(.001,.998,.001),scores(.001,.998,.001))['kind']=='UNRESOLVED'


def test_financial_arithmetic_never_rounds_long_values_to_equivalence():
    a=p('Microsoft revenue was $123456789012345678901234567891 million in fiscal 2024.')
    b=p('Microsoft revenue was $123456789012345678901234567892 million in fiscal 2024.')
    assert rel.decide(a,b,scores(.001,.998,.001),scores(.001,.998,.001))['kind']!='EQUIVALENT'


def test_complete_financial_values_veto_wrong_high_nli_without_decimal_rounding():
    a=p('Microsoft revenue was $123456789012345678901234567891 million in fiscal 2024.')
    b=p('Microsoft revenue was $123456789012345678901234567892 million in fiscal 2024.')
    assert rel.decide(a,b,scores(),scores())['kind']=='UNRESOLVED'


def test_unknown_noun_cannot_be_promoted_to_financial_issuer():
    a=p('Quarterly revenue was $1000 million in fiscal 2024.')
    b=p('Quarterly revenue totaled $1 billion in fiscal 2024.')
    assert rel.decide(a,b,scores(.001,.998,.001),scores(.001,.998,.001))['kind']!='EQUIVALENT'


def test_different_display_precision_is_not_a_financial_contradiction_proof():
    a=p('Microsoft revenue was $19750 million in fiscal 2024.')
    b=p('Microsoft revenue was $19.8 billion in fiscal 2024.')
    assert rel.decide(a,b,scores(.001,.998,.001),scores(.001,.998,.001))['kind']=='UNRESOLVED'


def test_equal_numerical_expression_can_have_different_display_precision():
    a=p('Microsoft revenue was $1000 million in fiscal 2024.')
    b=p('Microsoft revenue was $1 billion in fiscal 2024.')
    assert rel.decide(a,b,scores(.001,.998,.001),scores(.001,.998,.001))['kind']=='EQUIVALENT'
