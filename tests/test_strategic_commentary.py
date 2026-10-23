import hashlib
import json
from pathlib import Path
from stock import editorial, evidence, knowledge
from stock.core import Store


def doc():
 return dict(id=13,type='Presentation',original='source.pdf',source_sha256='original')


def selection(ids,text):
 return dict(ids=ids,text=text,topics=['Product'],category='Management',speaker=None,representation='source_grounded_statement',ambiguities=[])


def test_reference_order_is_canonicalized_without_losing_support():
 text='# Products\n\nCoreWeave launched Serverless RL.\n\nIt shortens feedback cycles.'
 cs=evidence.candidates(text,doc(),'sha',True)
 ps,bad=evidence.resolve([selection([c['id'] for c in reversed(cs)],'CoreWeave launched Serverless RL to shorten feedback cycles.')],cs,text,doc(),'sha')
 assert not bad and ps
 assert [r['start'] for r in ps[0]['location']['references']]==sorted(c['start'] for c in cs)


def test_table_cells_keep_exact_offsets_and_structure():
 text='# Updates\n\n| | Other |\n|---|---|\n| Launched Serverless RL | Acquired Monolith and Marimo | extra |'
 cs=knowledge.prepare_atoms(text,doc(),'sha')
 event=next(c for c in cs if c['text']=='Acquired Monolith and Marimo')
 assert text[event['start']:event['end']]==event['text']
 assert event['table']['column']==1 and event['table']['row']==2
 parent=event['table'];assert parent['sha256']==hashlib.sha256(text[parent['start']:parent['end']].encode()).hexdigest()
 assert all(len(c['text'])<100 for c in cs)


def test_contextual_language_cannot_be_published_after_positive_model_review():
 text='CoreWeave launched Serverless RL.';cs=evidence.candidates(text,doc(),'sha',True)
 ps,_=evidence.resolve([selection([cs[0]['id']], 'On that slide, the company said it launched Serverless RL.')],cs,text,doc(),'sha')
 class Model:
  def extract(self,u,c):return [dict(index=0,fidelity='supported',readability='clear',relevance='useful',warnings=[],reason='Recorded positive review.')]
 accepted,rejected=editorial.review(ps,Model(),'')
 assert not accepted and 'standalone' in rejected[0]['error'].lower()


def test_review_cache_survives_batch_reordering(tmp_path):
 s=Store(tmp_path/'copy.db');knowledge.schema(s)
 text='CoreWeave launched Serverless RL.\n\nCoreWeave acquired Marimo.'
 cs=evidence.candidates(text,doc(),'sha',True)
 ps,_=evidence.resolve([selection([c['id']],c['text']) for c in cs],cs,text,doc(),'sha')
 class Model:
  def __init__(self):self.calls=0
  def extract(self,u,c):
   self.calls+=1
   return [dict(index=i,fidelity='supported',readability='clear',relevance='useful',warnings=[],reason='Supported by the exact supplied reference.') for i in range(len(u['review']))]
 m=Model();ops=knowledge.Operations(s,doc(),m,lambda:None)
 editorial.review(ps,ops,'')
 ps2,_=evidence.resolve([selection([c['id']],c['text']) for c in reversed(cs)],cs,text,doc(),'sha')
 for p in reversed(ps2):editorial.review([p],ops,'')
 assert m.calls==1
 # A changed claim must still receive an independent review.
 ps2[0]['text']='CoreWeave announced the launch of Serverless RL.'
 editorial.review([ps2[0]],ops,'')
 assert m.calls==2


def test_retrieval_does_not_fill_budget_with_unrelated_same_turn():
 atoms=[dict(id=str(i),text=('CoreWeave launched Serverless RL' if i==0 else 'Unrelated accounting disclosure'),turn=None,start=i) for i in range(50)]
 rejection=dict(proposed=dict(text='CoreWeave launched Serverless RL',location=dict(references=[dict(source_id='0',turn=None)])),error='Missing purpose')
 found=editorial.recovery_sources(rejection,atoms)
 assert len(found)<10


def test_layout_context_deduplicates_identical_pages():
 page=dict(page=6,original_sha256='sha',matched_source_ids=['a'],blocks=[])
 ps=[dict(location=dict(visual_context=[page])) for _ in range(10)]
 assert knowledge.layout_context(ps)==[page]


def test_validation_summary_is_compact():
 import runpy
 summary=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/validate_knowledge.py'))['summary']
 assert summary(13,22,650.6)=='13 · Verified · 22 statements · 10:50'


def test_review_context_identity_ignores_unrelated_claim_page_matches():
 page=dict(page=6,original_sha256='sha',matched_source_ids=['b','a'],blocks=[])
 left=knowledge.review_context_for(json.dumps(dict(original_pdf_layout=[page])),{'a'})
 page['matched_source_ids']=['a']
 right=knowledge.review_context_for(json.dumps(dict(original_pdf_layout=[page])),{'a'})
 assert left==right


def test_damaged_table_cell_locates_pdf_by_unique_literal_fragments():
 from stock.source_layout import matched_pages
 atom=dict(text='Launched CoreWeave Federal, in an upsized offering support government and public sector use cases',table=dict(ambiguous=True))
 pages=['Launched CoreWeave Federal, extending our AI cloud platform to support government and public sector use cases','An unrelated page']
 assert matched_pages(atom,pages)==[1]
 # Ordinary prose does not opt into fragment matching.
 assert matched_pages(dict(text=atom['text']),pages)==[]
 assert matched_pages(atom,pages+[pages[0]])==[]


def test_document13_strategic_inventory_with_recorded_reviews(tmp_path):
 import runpy
 evaluate=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/evaluate_strategic_commentary.py'))['evaluate']
 report=evaluate(tmp_path)
 assert report['baseline_selected']==22 and report['baseline_survived']==17
 assert report['corrected_recorded_inputs_accepted']==24
 assert report['rebatched_review_requests']==0
 assert report['fresh_model_recall'] is None and report['live_model_seconds'] is None
 assert not report['corrected_recorded_missing']
 assert max(p['reference_characters'] for p in report['statements'] if p['key'] in ('federal','serverless-rl','acquisitions'))<1500


def test_structured_table_rows_remain_exact_without_cell_prompt_expansion():
 text='# Results\n\n| Item | 2025 | 2024 |\n|---|---|---|\n| Capacity | 43 | 32 |'
 cs=knowledge.prepare_atoms(text,doc(),'sha')
 rows=[c for c in cs if c.get('table')]
 assert len(rows)==2 and all('column' not in c['table'] for c in rows)
 assert all(text[c['start']:c['end']]==c['text'] for c in rows)


def test_targeted_cases_keep_complete_support_without_repeating_failures():
 atoms=[dict(id=str(i),text='CoreWeave launched product '+str(i),start=i,turn=None) for i in range(50)]
 raw=[dict(selection=dict(ids=[str(i)],text='Product update'),error='Unresolved contextual ambiguity: missing purpose') for i in (0,49)]
 work=list(knowledge.repair_work(raw,atoms,limit=200))
 assert len(work)==2
 assert [f['ids'] for _,fs in work for f in fs]==[['0'],['49']]
 assert all(len(cs)==3 for cs,_ in work)


def test_fragmented_table_optional_trailing_pipes_preserve_every_cell():
 text='# Updates\n\n| Event | Purpose\n|---|---\n| Launched product | Improve training | Extra\n'
 cs=knowledge.prepare_atoms(text,doc(),'sha')
 assert {c['text'] for c in cs}=={'# Updates','Event','Purpose','Launched product','Improve training','Extra'}
 assert all(text[c['start']:c['end']]==c['text'] for c in cs)


def test_batch_dependent_rejection_is_not_cached_per_claim(tmp_path):
 s=Store(tmp_path/'copy.db');knowledge.schema(s)
 text='CoreWeave launched Serverless RL.\n\nCoreWeave announced Serverless RL.'
 cs=evidence.candidates(text,doc(),'sha',True)
 ps,_=evidence.resolve([selection([c['id']],c['text']) for c in cs],cs,text,doc(),'sha')
 class Model:
  def __init__(self):self.calls=0
  def extract(self,u,c):
   self.calls+=1
   return [dict(index=i,fidelity='supported',readability='clear',relevance='redundant' if len(u['review'])>1 and i==1 else 'useful',warnings=[],reason='Recorded peer-dependent rejection.' if len(u['review'])>1 and i==1 else 'Independent supported useful claim.') for i in range(len(u['review']))]
 m=Model();ops=knowledge.Operations(s,doc(),m,lambda:None)
 accepted,rejected=editorial.review(ps,ops,'')
 assert len(accepted)==1 and len(rejected)==1
 accepted,rejected=editorial.review([ps[1]],ops,'')
 assert len(accepted)==1 and not rejected and m.calls==2
