"""Offline source inventory and recorded-output regression. Never authenticates or publishes.

The corrected selections and support judgments are human-authored regression inputs;
passing them establishes acceptance capability, not fresh-model selection recall.
"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def evaluate(directory):
 from stock import evidence,editorial,knowledge
 from stock.core import Store
 from stock.sort import Cursor
 import stock.sort_process as process
 from stock.source_layout import matched_pages
 fix=ROOT/'tests/fixtures/sort'
 inventory=json.loads((fix/'strategic-inventory.json').read_text())
 recorded=json.loads((fix/'document-13-recorded-operations.json').read_text())['operations']
 text=(fix/'document-13-live.md').read_text();doc=inventory['document'];sha=inventory['markdown_sha256']
 assert hashlib.sha256((fix/'document-13-live.md').read_bytes()).hexdigest()==sha
 atoms=knowledge.prepare_atoms(text,doc,sha)
 layout=json.loads((fix/'document-13-strategic-layout.json').read_text())['pages']
 for page in layout:
  page['matched_source_ids']=[c['id'] for c in atoms if matched_pages(c,[''.join(b['text'] for b in p['blocks']) for p in layout])==[layout.index(page)+1]]
 selections=[dict(ids=[r['id'] for r in c['references']],text=c['text'],topics=['Operations'] if c['key'] in ('footprint','power-pipeline','operating-capabilities') else ['Capital'] if c['key'] in ('convertible-financing','revolver','capacity-investment') else ['Market'] if c['key'] in ('customer-position','named-customers','hyperscaler-expansion','backlog-visibility','demand-execution') else ['Product'],category='Management',speaker=None,representation='source_grounded_statement',ambiguities=[]) for c in inventory['claims']]
 for c in inventory['claims']:
  for r in c['references']:assert text[r['start']:r['end']]==r['text']
 ps,errors=evidence.resolve(selections,atoms,text,doc,sha)
 assert not errors,errors
 by_text={c['text']:c for c in inventory['claims']}
 for p in ps:
  if by_text[p['text']]['layout']:
   ids={r['source_id'] for r in p['location']['references']}
   p['location']['visual_context']=[page for page in layout if ids & set(page['matched_source_ids'])]
   assert p['location']['visual_context'],p['text']
 metrics=[]
 class RecordedReview(Cursor):
  command='offline-recorded'
  def extract(self,u,c):
   result=[dict(index=i,fidelity='supported',readability='clear',relevance='useful',warnings=[],reason='Human source inventory: '+by_text[p['text']]['why']) for i,p in enumerate(u['review'])]
   def transport(command,**kwargs):
    from subprocess import CompletedProcess
    metrics.append(dict(prompt_characters=len(command[-1]),statements=len(result)))
    return CompletedProcess(command,0,json.dumps(dict(type='result',result=json.dumps(dict(reviews=result)))),'')
   old=process.run;process.run=transport
   try:return super().extract(u,c)
   finally:process.run=old
 store=Store(Path(directory)/'copy.sqlite3');knowledge.schema(store)
 ops=knowledge.Operations(store,doc,RecordedReview(),lambda:None)
 context=lambda group:json.dumps(dict(document=doc,original_pdf_layout=knowledge.layout_context(group)))
 started=time.perf_counter();accepted,rejected=editorial.review(ps,ops,context);elapsed=time.perf_counter()-started
 assert len(accepted)==len(inventory['claims']) and not rejected
 for p in accepted:editorial.validate_publication(p)
 calls=len(metrics)
 # Re-resolve to remove the in-memory judgments, and change batching.
 fresh,_=evidence.resolve(selections,atoms,text,doc,sha)
 for p,old in zip(fresh,ps):
  if old['location'].get('visual_context'):p['location']['visual_context']=old['location']['visual_context']
 for p in reversed(fresh):editorial.review([p],ops,context)
 assert len(metrics)==calls,'Valid independent work repeated after batch changes'
 # Replay original model selections through new resolver; no new semantic verdicts.
 old_atoms=evidence.candidates(text,doc,sha,True)
 resolved,failed=evidence.resolve(recorded[0]['output'],old_atoms,text,doc,sha)
 selected={c['key'] for c in inventory['claims'] if c['selected_indices']}
 survived={c['key'] for c in inventory['claims'] if c['verified_indices']}
 report=dict(baseline='4a58069 / observed knowledge-1 live run',contract=knowledge.CONTRACT,
  expected_propositions=len(inventory['claims']),baseline_selected=len(selected),baseline_survived=len(survived),
  baseline_missing=sorted(set(by_text[c['text']]['key'] for c in inventory['claims'])-survived),
  corrected_recorded_inputs_accepted=len(accepted),corrected_recorded_missing=[],
  original_selection_resolver_after=dict(resolved=len(resolved),rejected=len(failed),note='Same recorded model output; independent verdicts for newly resolvable claims are not fabricated.'),
  review_requests=calls,review_prompt_characters=sum(m['prompt_characters'] for m in metrics),rebatched_review_requests=len(metrics)-calls,
  local_review_seconds=elapsed,live_model_seconds=None,fresh_model_recall=None,
  limitation='Human-corrected selections and recorded support judgments, not a new extraction. Review prompt size is measured through real serialization, excludes understanding/recovery. No live speed claim.',
  statements=[dict(key=by_text[p['text']]['key'],text=p['text'],reference_characters=sum(len(r['text']) for r in p['location']['references']),references=p['location']['references']) for p in accepted])
 store.db.close()
 return report


def main(show_statements=False):
 base=ROOT/'.data';base.mkdir(exist_ok=True)
 directory=Path(tempfile.mkdtemp(prefix='strategic-evaluation-',dir=base))
 report=evaluate(directory);path=directory/'result.json';path.write_text(json.dumps(report,indent=2)+'\n')
 print(f'13 · Offline inventory · {report["corrected_recorded_inputs_accepted"]}/{report["expected_propositions"]} recorded propositions · live recall unmeasured')
 print('Report · '+str(path.relative_to(ROOT)))
 if show_statements:
  for p in report['statements']:print(p['text'])
 return 0

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--show-statements',action='store_true')
 raise SystemExit(main(parser.parse_args().show_statements))
