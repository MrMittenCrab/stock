"""Source-grounded reconstruction over the frozen, real document 13 archive."""
import hashlib
import json
from pathlib import Path
import pytest
from stock.evidence import candidates, resolve

FIX=Path(__file__).parent/'fixtures/sort'
TEXT=(FIX/'document-13-live.md').read_text()
DOC=dict(id=13,type='Presentation',title='CoreWeave',original='source.pdf',source_sha256='original',metadata_provenance=None)
HASH=hashlib.sha256(TEXT.encode()).hexdigest()

def statement(cs,text,representation='source_grounded_statement',ambiguities=None):
 return dict(ids=[c['id'] for c in cs],representation=representation,text=text,
             topics=['Operations'],category='Management',speaker=None,ambiguities=ambiguities or [])

def test_real_short_counts_multi_reference():
 cs=candidates(TEXT,DOC,HASH)
 for number,label,result in [('11','Data Centers Added in 2025','CoreWeave added 11 data centers in 2025.'),('43','Active Data Centers','CoreWeave reported 43 active data centers.')]:
  group=[next(c for c in cs if c['text']==f'**{number}**'),next(c for c in cs if c['text']==label)]
  ps,errors=resolve([statement(group,result)],cs,TEXT,DOC,HASH)
  assert not errors and ps[0]['text']==result
  loc=ps[0]['location'];assert loc['representation']=='source_grounded_statement'
  assert len(loc['references'])==2
  for r in loc['references']:assert TEXT[r['start']:r['end']]==r['text'] and r['document_id']==13

def test_headings_tables_and_noncontiguous_context():
 text='# Results\n\nRevenue\n\nOther narrative.\n\n| Period | Revenue |\n| 2025 | $10 million |\n\nFootnote: excludes tax.'
 cs=candidates(text,DOC,HASH,include_context=True)
 assert any(c['text'].startswith('# Results') for c in cs)
 assert any(c['text'].startswith('| Period') for c in cs)
 selected=[c for c in cs if 'Other narrative' not in c['text']]
 ps,errors=resolve([statement(selected,'Revenue was $10 million in 2025, excluding tax.')],cs,text,DOC,HASH)
 assert ps and not errors and len(ps[0]['location']['references'])==4

def test_unresolved_mapping_not_published():
 cs=candidates(TEXT,DOC,HASH);group=[c for c in cs if c['start'] in (4981,5012)]
 ps,errors=resolve([statement(group,None,ambiguities=['Power label/value association needs original layout.'])],cs,TEXT,DOC,HASH)
 assert not ps and 'unresolved' in errors[0]['error'].lower()

def test_unsupported_number_rejected():
 text='Revenue: $10 million';cs=candidates(text,DOC,HASH)
 ps,errors=resolve([statement(cs,'Revenue was $100 million.')],cs,text,DOC,HASH)
 assert not ps and 'number' in errors[0]['error'].lower()

def test_verbatim_edited_and_reconstructed_separate():
 text='Revenue was **$10 million**.';cs=candidates(text,DOC,HASH)
 for kind,published in [('verbatim',None),('edited_quotation','Revenue was $10 million.'),('source_grounded_statement','Revenue totaled $10 million.')]:
  ps,errors=resolve([statement(cs,published,kind)],cs,text,DOC,HASH)
  assert not errors and ps[0]['location']['representation']==kind
  assert ps[0]['text']==(text if published is None else published)
 assert resolve([statement(cs,'Revenue totaled $10 million.','verbatim')],cs,text,DOC,HASH)[1]

def reviewed(index=0,**kw):
 return dict(index=index,fidelity='supported',readability='clear',relevance='useful',warnings=[],reason='The selected label and value explicitly support the statement.',**kw)

def test_independent_review_gate_and_checkpoint_tampering():
 from stock.editorial import review,validate_publication
 from stock.evidence import IntegrityError
 text='Revenue: $10 million';cs=candidates(text,DOC,HASH)
 ps,_=resolve([statement(cs,'Revenue was $10 million.')],cs,text,DOC,HASH)
 with pytest.raises(IntegrityError):validate_publication(ps[0])
 class Model:
  def extract(self,u,c):
   assert u['review'][0]['references'][0]['text']==text
   return [reviewed()]
 accepted,rejected=review(ps,Model(),'')
 assert accepted and not rejected
 validate_publication(accepted[0])
 accepted[0]['text']='Revenue was $100 million.'
 with pytest.raises(IntegrityError):validate_publication(accepted[0])

@pytest.mark.parametrize('change',[dict(fidelity='unsupported',reason='Invented causality.'),dict(fidelity='unresolved',reason='Unknown unit.'),dict(readability='fragment'),dict(relevance='irrelevant')])
def test_review_distinguishes_three_qualities(change):
 from stock.editorial import review
 text='Revenue: $10 million';cs=candidates(text,DOC,HASH)
 ps,_=resolve([statement(cs,'Revenue was $10 million.')],cs,text,DOC,HASH)
 class Model:
  def extract(self,u,c):return [{**reviewed(),**change}]
 accepted,rejected=review(ps,Model(),'')
 assert not accepted and rejected[0]['proposed']['location']['review']['fidelity']==change.get('fidelity','supported')

def test_edited_quote_cannot_hide_paraphrase():
 text='Revenue was $10 million.';cs=candidates(text,DOC,HASH)
 assert resolve([statement(cs,'Revenue totaled $10 million.','edited_quotation')],cs,text,DOC,HASH)[1]
 assert resolve([statement(cs,'Revenue [...] $10 million.','edited_quotation')],cs,text,DOC,HASH)[0]

def test_real_power_mapping_needs_independent_layout(monkeypatch):
 from legacy_layout import attach,context
 layout=json.loads((FIX/'document-13-power-layout.json').read_text())
 cs=candidates(TEXT,DOC,HASH,include_context=True)
 group=[c for c in cs if c['start'] in (4981,5012)]
 claim='CoreWeave reported active power of 850MW+ and contracted power of 3.1GW+.'
 pending,errors=resolve([statement(group,claim)],cs,TEXT,DOC,HASH)
 assert pending and not errors
 from stock.editorial import validate_publication
 from stock.evidence import IntegrityError
 with pytest.raises(IntegrityError):validate_publication(pending[0])
 monkeypatch.setattr('legacy_layout.pdf_layout',lambda p:[layout])
 pages=attach(cs,DOC,lambda _:None)
 assert context(group,pages)==[layout]
 by_text={b['text']:b['bbox'] for b in layout['blocks']}
 # Original PDF line geometry, independently extracted, establishes each column.
 assert by_text['Active Power'][0]==by_text['850MW+'][0]
 assert by_text['Contracted Power'][0]==by_text['3.1GW+'][0]
 assert by_text['Active Power'][0]!=by_text['3.1GW+'][0]
 ps,errors=resolve([statement(group,claim)],cs,TEXT,DOC,HASH)
 assert not errors and ps[0]['location']['references'][0]['page']==5

def test_real_financial_comparisons_and_footnotes():
 cs=candidates(TEXT,DOC,HASH,include_context=True)
 disclosures=[c for c in cs if c['start']>=13569 and c['end']<=16673]
 for source_term,result in [
  ('**Revenue:**','CoreWeave reported revenue of $1.6 billion, up 110% YoY, driven by strong demand for its AI Cloud Platform.'),
  ('**Adjusted Net Loss:**','Adjusted net loss was $(284) million, compared to $(36) million in Q4\'24.'),
  ('**Adjusted EBITDA:**','Adjusted EBITDA was $898 million compared to $486 million in Q4\'24.'),
  ('**Revenue Backlog:**','Revenue backlog was $66.8 billion, up 342% YoY, driven by substantial growth from existing and new customers.'),
  ('**Capital Expenditures:**','Capital expenditures were $8.2 billion, driven by scaling the platform to meet customer demand.')]:
  c=next(c for c in disclosures if source_term in c['text'])
  group=[c]
  if '$' not in c['text']:
   group.append(cs[cs.index(c)+1])
  ps,errors=resolve([statement(group,result)],cs,TEXT,DOC,HASH)
  assert ps and not errors
 footnote=next(c for c in cs if 'Capital expenditures are additions' in c['text'])
 capex=next(c for c in cs if c['start']==16579)
 ps,errors=resolve([statement(sorted([capex,footnote],key=lambda c:c["start"]),'Capital expenditures were $8.2 billion, including assets acquired under finance leases, less changes in construction in progress.')],cs,TEXT,DOC,HASH)
 assert not errors and len(ps[0]['location']['references'])==2

def test_transcript_attribution_keeps_turn_boundary():
 text='Alice Smith\n\nChief Executive Officer\n\nJane Brown\n\nAnalyst\n\n## Alice Smith\n\nRevenue rose 10%.\n\n## Jane Brown\n\nWhy did revenue rise?'
 d={**DOC,'type':'Transcript'};cs=candidates(text,d,HASH)
 ps,errors=resolve([statement(cs[:1],'Revenue increased 10%.')],cs,text,d,HASH)
 assert ps[0]['speaker']=='Alice Smith' and not errors
 assert resolve([statement(cs,'Revenue increased 10%.')],cs,text,d,HASH)[1]

@pytest.fixture
def staged_editorial(tmp_path,monkeypatch):
 from stock.archive import import_document
 from stock.core import Store
 import stock.archive as archive
 monkeypatch.setattr(archive,'ROOT',tmp_path)
 source=tmp_path/'input.md';source.write_text('# Investor Presentation\n\nData Centers Added in 2025: **11**')
 store=Store(tmp_path/'copy.sqlite3');doc=import_document(store,'CRWV.US',source)
 class Model:
  def __init__(self):self.calls=[];self.wording='CoreWeave added 11 data centers in 2025.';self.fail_review=False
  def extract(self,u,c):
   self.calls.append('review' if 'review' in u else 'selection')
   if 'review' in u:
    if self.fail_review:raise KeyboardInterrupt
    return [reviewed()]
   return [statement([c for c in u['candidates'] if not c.get('context_only')],self.wording)]
 return store,doc,Model()

def test_interrupted_review_resumes_staged_selection(staged_editorial):
 from stock.evidence import extract
 from stock import sources
 s,d,m=staged_editorial;m.fail_review=True
 with pytest.raises(KeyboardInterrupt):extract(s,d,m,lambda _:None)
 assert not sources.completed(s,d['id'])
 assert not sources.passages(s,'CRWV.US')
 m.fail_review=False
 ps,_=extract(s,d,m,lambda _:None)
 assert m.calls==['selection','review','review']
 assert extract(s,d,m,lambda _:None)[0]==ps
 assert m.calls==['selection','review','review']
 sources.publish(s,d,ps,d['source_sha256'])
 row=sources.passages(s,'CRWV.US')[0]
 assert row['representation']=='source_grounded_statement' and row['verification_state']=='model_reviewed'

def test_editorial_override_transfer_and_rollback(staged_editorial):
 from stock.evidence import extract
 from stock.rebuild import rebuild
 from stock import sources
 s,d,m=staged_editorial
 ps,_=extract(s,d,m,lambda _:None);sources.publish(s,d,ps,d['source_sha256'])
 old=sources.passages(s,'CRWV.US')[0];sources.set_topic(s,old['id'],'Capital',True)
 before=s.db.execute('select * from source_passages').fetchall()
 with s.db:s.db.execute('delete from knowledge_artifacts')
 m.wording='In 2025, CoreWeave added 11 data centers.'
 assert not rebuild(s,'CRWV.US',str(d['id']),lambda:m,lambda _:None,lambda:False)
 assert s.db.execute('select * from source_passages').fetchall()==before
 assert rebuild(s,'CRWV.US',str(d['id']),lambda:m,lambda _:None,lambda:True)
 p=sources.passages(s,'CRWV.US')[0]
 assert p['text']==m.wording and 'Capital' in p['topics']

def test_legacy_group_matches_exact_multireference_reconstruction():
 from stock.rebuild import match_key
 frozen=json.loads((FIX/'document-13-live.json').read_text())['passages'][0]
 cs=candidates(TEXT,DOC,HASH);group=[c for c in cs if c['start'] in (4945,4953)]
 ps,_=resolve([statement(group,'CoreWeave added 11 data centers in 2025.')],cs,TEXT,DOC,HASH)
 # Classification and source spans, rather than editorial wording, preserve manual topics.
 assert match_key({**frozen,'category':'Management','speaker':None})==match_key(ps[0])

def test_protocol_review_retries_are_bounded():
 from stock.editorial import review
 from stock.evidence import ProtocolError
 from unittest.mock import Mock
 text='Revenue: $10 million';cs=candidates(text,DOC,HASH)
 ps,_=resolve([statement(cs,'Revenue was $10 million.')],cs,text,DOC,HASH)
 model=Mock();model.extract.return_value=[]
 with pytest.raises(ProtocolError):review(ps,model,'')
 assert model.extract.call_count==1

async def test_sources_inline_editorial_inspection(staged_editorial):
 from stock.evidence import extract
 from stock import sources
 from stock.sources_ui import SourcesApp
 s,d,m=staged_editorial;ps,_=extract(s,d,m,lambda _:None);sources.publish(s,d,ps,d['source_sha256'])
 app=SourcesApp('CRWV.US',s)
 async with app.run_test(size=(90,35)) as pilot:
  await pilot.press('down','down','right','space')
  rendered='\n'.join(str(w.render()) for w in app.row_widgets)
  assert 'CoreWeave added 11' in rendered and 'source_grounded_statement' in rendered
  assert '**11**' in rendered and 'Data Centers Added in 2025' in rendered
  assert 'Source d' in rendered and 'characters' in rendered


def test_explicit_textual_mapping_is_recoverable_without_pdf():
 text='2024 2025\n\nRevenue ($ million), left to right: 10 20.'
 cs=candidates(text,DOC,HASH)
 ps,errors=resolve([statement(cs,'Revenue was $10 million in 2024 and $20 million in 2025.')],cs,text,DOC,HASH)
 assert ps and not errors  # still pending separate semantic review


def test_original_identity_invalidates_checkpoint(staged_editorial,tmp_path):
 from stock.evidence import extract
 s,d,m=staged_editorial
 extract(s,d,m,lambda _:None)
 replacement=tmp_path/'replacement.md';replacement.write_bytes(Path(d['original']).read_bytes())
 changed={**d,'original':str(replacement),'markdown':d.get('markdown') or d['original']}
 ps,_=extract(s,changed,m,lambda _:None)
 assert m.calls==['selection','review','selection','review']
 assert all(r['original']==str(replacement) for r in ps[0]['location']['references'])
 assert s.db.execute('select count(*) from knowledge_propositions').fetchone()[0]==2

def test_protocol_schema_is_distinct_from_evidence_failure():
 from stock.editorial import validate_selections
 from stock.evidence import ProtocolError
 cs=candidates('Revenue: $10 million',DOC,HASH)
 valid=statement(cs,'Revenue was $100 million.')
 assert validate_selections([valid])==[valid]  # well-formed but factually unsupported
 assert resolve([valid],cs,'Revenue: $10 million',DOC,HASH)[1]
 with pytest.raises(ProtocolError):validate_selections([{**valid,'ids':7}])

def test_edited_omissions_must_be_disclosed():
 text='Revenue declined because costs rose.';cs=candidates(text,DOC,HASH)
 assert resolve([statement(cs,'Revenue rose.','edited_quotation')],cs,text,DOC,HASH)[1]

def test_reject_inference_even_when_numbers_match():
 from stock.editorial import review
 text='Revenue grew 10%.';cs=candidates(text,DOC,HASH)
 ps,_=resolve([statement(cs,'Revenue grew 10%, proving management will acquire a competitor.')],cs,text,DOC,HASH)
 class Reviewer:
  def extract(self,u,c):
   assert 'acquire' in u['review'][0]['text']
   assert u['review'][0]['references'][0]['text']==text
   return [{**reviewed(),'fidelity':'unsupported','reason':'The source provides no acquisition intention.'}]
 accepted,rejected=review(ps,Reviewer(),'')
 assert not accepted and 'no acquisition intention' in rejected[0]['error']

@pytest.mark.parametrize('source,result',[('Revenue: $10 million','Revenue was €10 million.'),('Capacity: 850MW','Capacity was 850GW.'),('Revenue: $10 million','Revenue was $10 billion.'),('Revenue: $10 million','Revenue grew 10%.')])
def test_unattested_units_currency_scale_and_percent_rejected(source,result):
 cs=candidates(source,DOC,HASH)
 assert resolve([statement(cs,result)],cs,source,DOC,HASH)[1]

def test_chart_pointer_is_preserved_without_invented_page():
 text='![Chart: revenue grew 50%](assets/_page_9_Figure.jpeg)'
 cs=candidates(text,DOC,HASH,include_context=True)
 assert len(cs)==1 and cs[0]['source_kind']=='visual_pointer'
 assert cs[0]['text']==text and 'page' not in cs[0]

def test_table_headers_units_and_qualified_financial_statement():
 cs=candidates(TEXT,DOC,HASH,include_context=True)
 table=next(c for c in cs if c['text'].startswith('|                                  |') and 'Adjusted EBITDA' in c['text'])
 units=next(c for c in cs if c['text']=='*(in millions, except percentages)*')
 qualification=next(c for c in cs if c['text'].startswith('1. Adjusted EBITDA, Adjusted EBITDA Margin'))
 group=sorted([table,units,qualification],key=lambda c:c['start'])
 ps,errors=resolve([statement(group,'Adjusted EBITDA, a non-GAAP measure, was $898 million for the three months ended December 31, 2025, compared to $486 million in 2024; adjusted EBITDA margin was 57% versus 65%.')],cs,TEXT,DOC,HASH)
 assert ps and not errors
 assert len(ps[0]['location']['references'])==3

def test_replay_actual_live_cursor_selection_and_independent_review(monkeypatch):
 from stock.editorial import review,validate_publication
 from legacy_layout import attach
 fixture=json.loads((FIX/'document-13-editorial-live.json').read_text())
 layout=json.loads((FIX/'document-13-power-layout.json').read_text())
 monkeypatch.setattr('legacy_layout.pdf_layout',lambda p:[layout])
 cs=candidates(TEXT,DOC,HASH,include_context=True);attach(cs,DOC,lambda _:None)
 ps,errors=resolve(fixture['selections'],cs,TEXT,DOC,HASH)
 assert not errors and len(ps)==1
 class Replay:
  def extract(self,u,c):return fixture['reviews']
 accepted,rejected=review(ps,Replay(),'')
 assert not rejected
 validate_publication(accepted[0])
 assert len(accepted[0]['location']['references'])==7
 assert 'illustrative' in accepted[0]['text'] and '850MW+' in accepted[0]['text']


def test_completed_rebuild_review_does_not_launch_cursor(staged_editorial):
 from stock.evidence import extract
 from stock.rebuild import rebuild
 from unittest.mock import Mock
 s,d,m=staged_editorial
 extract(s,d,m,lambda _:None)
 factory=Mock(side_effect=AssertionError('Verified staging does not require Cursor'))
 assert not rebuild(s,'CRWV.US',str(d['id']),factory,lambda _:None,lambda:False)
 factory.assert_not_called()
