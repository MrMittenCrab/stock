# Semantic correctness continuation from 0893253

The production CoreWeave database and document 13 were not modified. The existing feature branch and draft PR #1 are retained. Model weights, embedding contract, NLI input contract and decision thresholds are unchanged. This is a local development audit, not authorization or evidence of readiness for a production rebuild.

Machine-readable evidence: [paired original-label audit](benchmarks/semantic-correctness-v1.json), [new model comparison](benchmarks/financial-model-comparison-v1.json), [complete disposable Sort replay](benchmarks/semantic-correctness-e2e-v1.json). Existing fixtures and labels are unchanged.

## Supplier-risk adjudication

**Assessment: RELATED (thematic overlap), not a safe mutual equivalence or one-way entailment of the complete statements.** The automatic graph remains UNRESOLVED; this assessment is reported separately rather than injected as a fixture relabel or a manual production correction.

The exact statements and both original references remain in `disputed_labels` in the paired audit, and in `tests/fixtures/sort/semantic-coreweave.json`. Both anchors are in committed document 6, a Q1 2025 quarterly excerpt: `[1330,1660)` and `[10099,10429)`. Both contain the same source paragraph; identical support does not make every reconstruction of that paragraph equivalent.

The summary explicitly asserts a limited supplier base for significant equipment components used for the platform, solutions and services. Its risk trigger is disruption in **component availability**; its consequences include expansion, increasing infrastructure capacity, and replacing defective equipment. The detail instead describes disruption **at suppliers**, with expansion and replacement consequences. Limited suppliers appear in both (including as a presupposition in the detail), so the dispute is not merely whether the short sentence explicitly repeats a supplier-count assertion.

Supplier disruption need not entail component unavailability, and component unavailability need not originate at a supplier. A causal assumption equating these triggers would be needed for either full-statement implication. Capacity expansion can overlap expansion language, but it does not restore all original scope and trigger information. Neither original proposition or citation is discarded. The original gold equivalence is retained for strict scoring; ten presentation groups remain, with no target of nine.

A second separately disputed original label is `mixed-modality` in the older independent set. The longer statement literally repeats an actual-period assertion and appends a forecast conjunct: it entails the shorter actual statement right-to-left. Its original UNRESOLVED label is still scored unchanged. This accounts for the one apparent false asserted entailment in the strict metrics below; no adjudicated score is substituted.

## Three source-grounded failures

All three are **model inference errors on exact notation conversion**, not failed retrieval, measurement-basis mismatches, different periods, rounding, or missing source context in these particular pairs:

| Case | Million expression | Billion expression | MiniLM contradiction, forward / reverse |
|---|---:|---:|---:|
| Microsoft FY2024 revenue | 245122 | 245.122 | 98.43% / 99.22% |
| Apple FY2024 total net sales | 391035 | 391.035 | 99.19% / 98.64% |
| Apple FY2024 net income | 93736 | 93.736 | 98.62% / 98.94% |

Microsoft's source is its [FY2024 annual report, consolidated income statements](https://www.microsoft.com/investor/reports/ar24/). Apple's source is [page 1 of the FY2024 consolidated financial statements](https://www.apple.com/newsroom/pdfs/fy2024-q4/FY24_Q4_Consolidated_Financial_Statements.pdf). These are fiscal annual flows: Microsoft's fiscal year ends June 30; Apple's annual column covers the twelve months ended September 28, 2024. Apple's quarterly columns, regional sales, product/service breakdowns, net sales and net income must remain distinct. The original source URLs, sections and exact original texts remain in the unchanged disclosure fixture and audit.

The conversion factor is exactly 1000 million per billion, and each pair expresses the same reported amount at the same displayed resolution. Rounding to 245.1 billion, confusing fiscal and calendar years, substituting a quarterly column, or using adjusted income would be different cases requiring abstention. Dollar-symbol equality is not currency exchange reasoning.

## Bounded financial reasoning and retrieval

The new full-consumption grammar supports one asserted issuer-level money-flow sentence, with an explicit fiscal year, currency symbol, exact decimal amount and thousand/million/billion scale. It preserves the distinct revenue, total net sales, net sales, net income and operating income metric names. It identifies the definition as **unqualified reported**, never assumes GAAP, and excludes adjusted definitions, inferred table scales, missing fiscal basis, forecasts, bounds, restrictions and extra clauses. Unknown issuer names require explicit statement/source issuer metadata; a noun or capitalized adjective cannot become issuer identity. Known issuer recognition uses the existing entity vocabulary plus Apple for the audited disclosure cases.

Equality requires a complete matching proposition (issuer, metric, definition, fiscal period, modality, issuer scope and currency), exact Decimal equality, and passing context, attribution and source-restriction safeguards. General extracted-attribute equality is not a proof. Both original propositions and their citations remain immutable even when presentation groups combine them. Arithmetic uses bounded input length and sufficient Decimal precision; it cannot silently round large values into equality.

Different values can be contradiction candidates, but become CONTRADICTS only with the same complete conditions, the original high bidirectional NLI contradiction gate, and disjoint possible rounding intervals. Intervals are an abstention safeguard, never a proof of equality: 19,750 million versus 19.8 billion remains UNRESOLVED, not EQUIVALENT or CONTRADICTS. This conservative allowance does not establish the actual source's rounding convention. Generic mismatched numbers outside the complete grammar remain unresolved. First/second-half periods are now distinct even under incorrect high NLI entailment.

A separate structured candidate channel indexes entity, metric, period and scope, preserving detected definition, fiscal/calendar basis, state, qualifications, modality, attribution and other supplied dimensions. Unknown/inconsistent required context abstains. Values and polarity are omitted deliberately. It recomputes from current audited source context while reusing text-only vectors and similarity scores. At most 32 structured edges touch any incoming endpoint, including edges chosen from another incoming endpoint. The existing embedding-tail channel remains separate; its natural candidate count is not subject to this new cap. No remote semantic request or all-pairs NLI pass is introduced.

## Before / after, original labels

These are the same 142 previously observed pairs and identical cached raw NLI predictions, comparing 0893253 with the revised policy. They are development fixtures, not untouched calibration. Direction must be correct for entailment. Precision covers asserted EQUIVALENT/ENTAILS/CONTRADICTS relationships; recall covers their gold relationships. RELATED and UNRESOLVED are reported separately in the JSON.

| Measure | Before | After |
|---|---:|---:|
| Overall exact classification accuracy | 130/142 (91.5%) | 133/142 (93.7%) |
| Asserted relationship precision | 26/27 (96.3%) | 29/30 (96.7%) |
| Material relationship recall | 26/36 (72.2%) | 29/36 (80.6%) |
| Equivalence precision | 14/14 (100%) | 17/17 (100%) |
| Equivalence recall | 14/19 (73.7%) | 17/19 (89.5%) |
| False merges | 0 | 0 |
| Missed material relationships | 10 | 7 |
| Missed equivalences | 5 | 2 |
| Initial contradiction candidate recall | 6/8 (75%) | 8/8 (100%) |
| Initial candidates across the four inventories | 437 | 459 |

All three source-grounded financial misses recover. The remaining two gold equivalence misses are supplier-risk (disputed above) and the older `revenue-notation` example without explicit fiscal basis. Remaining strict-label material misses also include a qualified directional statement and four contradictions. Existing contradiction decision recall remains 4/8: retrieval recovery does not itself repair a classifier or attribute failure. The JSON distinguishes classification from end-to-end retrieval-gated scores; retrieval is not treated as negative truth. The extra 22 retrieval candidates would require at most 44 additional directional predictions when uncached in these inventories. This audit reused recorded scores for its 142 labeled pairs and ran **zero new NLI predictions** on them; resumed inference is also zero.

## Untouched financial model comparison

The new 40-case authored synthetic set was frozen before first inference with SHA256 `e178d06f9811f656c2ca3e9d426f58eb94291951b96d56c2bf18c567a982ef54`. It contains new issuer names, financial metrics, notation, containment, negation, scope/period/definition/currency differences, rounding and missing-context controls. Values are invented, not disclosures. No labels, thresholds or weights were tuned to increase its score. Safety changes following independent review were rescored from the original cached raw predictions; it is now an observed development set and must not be reused as a future untouched holdout.

All models execute locally using pinned unquantized ONNX artifacts, four CPU threads, batch size eight, no truncation, and the same original texts. Each receives the same 80 unique directional inputs per pass: 160 prediction executions over first and warm passes, with both times recorded separately. Raw outputs from the first pass are retained; policy rescoring repeats no inference. Model choices are the pretrained [DistilRoBERTa NLI model](https://huggingface.co/cross-encoder/nli-distilroberta-base) and [DeBERTa-v3-small NLI model](https://huggingface.co/cross-encoder/nli-deberta-v3-small), alongside the existing MiniLM. These provide practical local architecture alternatives, not financial-specialist guarantees.

| Model | Raw directional accuracy | Warm 80-direction time | ms / direction | Argmax false equivalences / 32 negatives |
|---|---:|---:|---:|---:|
| Current MiniLM | 25/34 (73.5%) | 1.095 s | 13.69 | 3/32 |
| DistilRoBERTa | 26/34 (76.5%) | 1.029 s | 12.86 | 7/32 |
| DeBERTa-v3-small | 26/34 (76.5%) | 1.191 s | 14.89 | 1/32 |

Raw directional accuracy excludes the 23 policy-UNRESOLVED cases: abstention is not an NLI neutral label. Raw argmax false equivalence means entailment is the highest-probability label in both directions despite non-equivalent gold. At the unchanged confidence gates, raw confident false equivalences are 0/32 for each model. That small authored negative set cannot establish a production false-merge rate. Artifacts are approximately 329 MB / 329 MB / 568 MB; these are disk bytes, not peak memory measurements. Initialization, token counts, all raw probabilities and each policy decision are recorded in JSON. Timing is a two-pass local observation, not a statistical performance study.

The final guarded policy conservatively returns UNRESOLVED for all 40 bare-text pairs: the new issuer identities are outside the existing vocabulary and lack audited context. Thus bare-text five-class accuracy is 23/40 (57.5%), material recall 0/16 and asserted precision undefined, both before and after. This is an explicit coverage blocker, not model accuracy or a successful zero-error result.

A separately labeled diagnostic ablation supplies issuer metadata only for explicit issuer names, leaving all texts, labels and raw scores unchanged. It is not independently source-audited identity. Current-policy exact accuracy becomes 31/40 (MiniLM), 30/40 (DistilRoBERTa) and 27/40 (DeBERTa); material recall is 8/16, 7/16 and 4/16, asserted precision 100% for all, and false merges zero. Missed relationships are 8, 9 and 12. The MiniLM result includes four exact unit conversions and four one-way projections, retaining both members for each projection. A provisional earlier parser accepted unknown names and a rounding contradiction; review tightened those rules despite reducing bare-text scores.

**Decision: retain MiniLM.** A one-direction gain on 34 raw labels, mixed false-equivalence risk, and no superior guarded-policy result do not justify replacement. Scores are uncalibrated; this experiment does not establish equivalent model confidence calibration.

## Verification, preservation and limits

Focused tests cover parser safety under incorrect high NLI scores; issuer, metric, definition, scope, fiscal/calendar/half-year differences; numeric rounding and precision; source restrictions; attribution; endpoint budgets; context propagation; raw-cache reuse; manual corrections and splits; complete-link grouping; exact evidence/citation coverage; failure/stale publication and transactional safeguards. Final focused verification: **195 passed in 72.06 seconds** using the six-file pytest command below and a dedicated temporary directory. No full-suite repetition was needed. Independent review found issuer invention, incomplete half-year periods, numerical-contradiction vetoes and an endpoint-budget leak; regression tests reproduced those defects before correction. Additional safety tests reproduced Decimal rounding and possible source rounding errors before correction.

The complete disposable Sort replay uses identical committed source selections and recorded extraction/review transport, with real local semantic inference. It preserves all 13 evidence propositions, 22 exact citations and 10 presentation groups both before and after, makes ten recorded extraction/review requests and zero authenticated or semantic service requests, and makes zero new requests on completed resume. Existing source anchors are asserted retained; resume adds no NLI, embedding or similarity-cache rows. All database mutations target disposable files. Both runs create 12 raw cached pairs (24 unique directional predictions), 19 embedding vectors including null probes, and 78 similarity-score rows. Total local NLI execution is **0.330 seconds before / 0.306 seconds after**, with initialization **0.713 / 0.677 seconds**; these small differences are timing observations, not a speed claim. Replay local inference totals and cache counts are in the JSON; cold wall times include initialization and should not be interpreted as algorithmic speedup.

Production SQLite SHA256 before and after verified work (unchanged): `a0a7817a796895f8016d3ccd2480568fe4cd0c1e1e5485975e5073359c9f8a04`.

Production readiness blockers remain:

- Independent human adjudication of the supplier and mixed-modality gold disputes; production changes require a separate authorized review.
- Representative, independently labeled financial and real-inventory retrieval evaluation, including candidate precision and saturation beyond the bounded channel. Small authored fixtures do not calibrate confidence or establish a safe false-merge rate.
- Reliable audited issuer identities, metric definitions and complete reporting windows beyond the bounded grammar. Missing context must remain unresolved; generic text heuristics are not a general financial parser.
- Four existing contradiction decision misses, broader fiscal/period language, qualified directional paraphrases and numeric negation. Rounded values and unspecified measurement bases require abstention.
- Model confidence calibration, broader latency/memory measurement, long-context evaluation and financial reasoning beyond exact scalar conversions. No alternative model replacement is authorized by these results.

Reproduction (model artifacts must already be available in the local Hugging Face cache, at the pinned revisions in `compare_financial_nli.py`):

```sh
.venv/bin/python scripts/compare_financial_nli.py --output /tmp/financial-model-comparison.json
.venv/bin/python scripts/compare_financial_nli.py --rescore docs/benchmarks/financial-model-comparison-v1.json --output /tmp/financial-policy-rescore.json
.venv/bin/python scripts/audit_semantic_correctness.py --output /tmp/semantic-correctness.json
.venv/bin/python scripts/benchmark_unified_sort.py --baseline 0893253 > /tmp/semantic-correctness-e2e.json
.venv/bin/python -m pytest -q tests/test_relationships.py tests/test_semantic_map.py tests/test_graph.py tests/test_insights.py tests/test_sort_efficiency.py tests/test_evidence.py --basetemp=.data/semantic-correctness-check
```
