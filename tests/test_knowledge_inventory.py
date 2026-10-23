"""Representative real-source information inventory, with recorded support judgments.

These checks establish contract fidelity for known facts, not model recall/accuracy.
"""
import hashlib
import json
from pathlib import Path
from stock.evidence import candidates,resolve
from stock.editorial import review,validate_publication

FIX=Path(__file__).parent/'fixtures/sort'
INVENTORY=json.loads((FIX/'knowledge-inventory.json').read_text())
TEXT=(FIX/'document-13-live.md').read_bytes().decode('utf-8-sig')


def selection(ids,text,topic):
 return dict(ids=ids,text=text,topics=[topic],category='Management',speaker=None,representation='source_grounded_statement',ambiguities=[])

class RecordedReview:
 def __init__(self,supported):self.supported=supported
 def extract(self,u,c):
  return [dict(index=i,fidelity='supported' if self.supported else 'unsupported',readability='clear',relevance='useful',warnings=[],reason='Recorded inventory source/period/metric/qualification check.' if self.supported else 'Recorded material metric, definition or qualification mismatch.') for i,_ in enumerate(u['review'])]


def test_document13_expected_readable_facts_and_exact_support():
 doc=INVENTORY['document'];sha=INVENTORY['markdown_sha256']
 assert hashlib.sha256((FIX/'document-13-live.md').read_bytes()).hexdigest()==sha
 cs=candidates(TEXT,doc,sha,True)
 for expected in INVENTORY['claims']:
  for r in expected['references']:assert TEXT[r['start']:r['end']]==r['text']
  raw=selection([r['id'] for r in expected['references']],expected['text'],expected['topic'])
  ps,errors=resolve([raw],cs,TEXT,doc,sha)
  assert ps and not errors, (expected['key'],errors)
  if expected.get('layout'):
   ps[0]['location']['visual_context']=json.loads((FIX/'document-13-financial-layout.json').read_text())['pages']
  verified,bad=review(ps,RecordedReview(True),'')
  assert verified and not bad
  validate_publication(verified[0])
  assert verified[0]['text']==expected['text']


def test_wrong_label_matching_numbers_and_lost_qualifications_fail_review():
 doc=INVENTORY['document'];sha=INVENTORY['markdown_sha256'];cs=candidates(TEXT,doc,sha,True)
 for bad in INVENTORY['negative_cases']:
  # Give the adversarial proposal every number in the source: lexical presence
  # still cannot establish the right metric, definition or reporting period.
  ps,_=resolve([selection([c['id'] for c in cs],bad['text'],'Financials')],cs,TEXT,doc,sha)
  if ps:
   accepted,rejected=review(ps,RecordedReview(False),'')
   assert not accepted and rejected


def test_platform_product_requires_both_narrative_citations_and_attribution():
 text=(FIX/'platform-product.md').read_text();sha=hashlib.sha256(text.encode()).hexdigest()
 d={**INVENTORY['document'],'id':12,'type':'Transcript'}
 cs=candidates(text,d,sha,True);fact=INVENTORY['product']
 ps,errors=resolve([selection([c['id'] for c in cs],fact['text'],'Product')],cs,text,d,sha)
 assert not errors and len(ps[0]['location']['references'])==2
 assert ps[0]['speaker']=='Michael Intrator'
 verified,bad=review(ps,RecordedReview(True),'')
 assert verified and not bad
