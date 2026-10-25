# Semantic quality audit against 4e01591

Production document 13 was not rebuilt. All replay/model writes used disposable databases; inventory was opened read-only. PR #1 remains draft. This improves organization but is **not ready for an unattended production document-13 rebuild**: financial notation and risk paraphrases still fail, and the initial candidate frontier misses contradictions.

## Diagnosis and corrections

The original mutual-revenue example has entailment 0.99324 / 0.99195, exceeding unchanged 0.985 thresholds, but both absent geographic scopes vetoed it. An explicit issuer-level metric can establish issuer scope; jointly empty attributes cannot. The five CoreWeave positive pairs were all retrieved. Four capacity/date pairs also expose genuine MiniLM errors or below-threshold support; removing unknown-scope vetoes alone would not fix them.

Compatibility now records observed agreement, missing context and conflict separately. Canonical notation handles explicit dates, written quarters, unit magnitudes, and bounded complete capacity KPI sentences. Complete KPI equivalence is a separate deterministic decision basis, not an inflated NLI confidence. Its entire sentence must parse; geographic, forecast and qualification tails cannot disappear. Reporting years remain distinct from dates and fiscal years from calendar years. Four-digit monetary amounts are retained.

Context recovery retains original reference IDs, source-note text, speaker, field and document provenance. A publisher is never used as issuer. Structured issuer/registrant resolves deictic issuer wording; an explicit annual reporting end resolves “ended the year.” A plain year does not establish December 31. Anchored “Figures as of” notes supply dates only when consistent with both explicit and recovered periods. Publication/event dates never supply reporting periods. The fixture’s exact illustrative-map disclaimer is treated as a qualification of the drawing rather than the separately labeled KPI; the disclaimer remains attached. Other note tails veto merging when missing/different. That interpretation should remain a human review point.

High-confidence literal first-conjunct projection preserves directional entailment despite extra premise metrics/numbers. Context and attribution safeguards still apply to the projected clause. ENTAILS never groups propositions. Complete-link grouping, manual splits/corrections, original citations and transaction publication rules are preserved.

Raw inference keys now depend on exact ordered texts and the unchanged model contract. Legacy source-keyed entries migrate lazily; historical source fingerprints are used only after both original texts are verified unchanged. Current context is always reclassified and current fingerprints attached. Embedding/retrieval contracts remain unchanged. No model replacement, threshold reduction or frontier tuning was made.

## Identical-case results

Each policy consumes the same original-text bidirectional scores. Classification below is exhaustive over labeled cases, independent of retrieval. Precision is correct/predicted; — means undefined. CoreWeave covers all 78 pairs, including negative pairs. Other sets are labeled challenge pairs, not exhaustive cross-pair ground truth.

| Set | Initial material candidate recall | Equivalence correct/gold before → after | Merge precision after | Entailment correct/gold before → after | Contradiction correct/gold before → after | Unresolved before → after | False merges before → after | Missed pairs before → after |
|---|---|---|---|---|---|---|---|---|
| coreweave | 5/5 | 0/5 → 4/5 | 4/4 | 0/0 → 0/0 | 0/0 → 0/0 | 78 → 74 | 0 → 0 | 5 → 1 |
| original_challenge | 4/6 | 1/2 → 2/2 | 2/2 | 1/2 → 2/2 | 1/2 → 2/2 | 13 → 10 | 0 → 0 | 1 → 0 |
| independent_heldout | 17/17 | 4/8 → 7/8 | 7/7 | 1/5 → 4/5 | 1/4 → 1/4 | 30 → 23 | 0 → 0 | 4 → 1 |
| disclosures_heldout | 8/8 | 1/4 → 1/4 | 1/1 | 0/2 → 2/2 | 1/2 → 1/2 | 10 → 8 | 0 → 0 | 3 → 3 |

After-policy entailment precision: original challenge 2/2; synthetic financial set 4/5 against frozen labels; disclosures 2/2. The synthetic mismatch is a right-to-left entailment from an actual KPI plus a forecast conjunct to the exact actual KPI. It is logically valid but the frozen negative label expects UNRESOLVED. The label was not changed to improve scores. The other missed directional case has 0.9846 forward entailment and added geographic information; it remains below the unchanged threshold. Contradiction precision among assertions is 2/2, 1/1, 1/1 respectively; CoreWeave has no contradiction gold or predictions (undefined precision/recall). These small denominators are not calibration or a population precision guarantee.

CoreWeave presentation groups: **13 → 10**, versus 9 expected. Equivalent pair recall is **0/5 → 4/5**; one triple accounts for three pairwise positives but only two group reductions. The remaining supplier-risk pair compresses an explicit limited-supplier premise and deictic issuer context; NLI is 0.3827 / 0.1014. It remains separate rather than inventing a period/scope or assuming every shared-source paraphrase is equivalent.

The independent synthetic set contains 36 cases across multiple issuers. The separate 12-case disclosure set is grounded in [Microsoft FY2024](https://www.microsoft.com/investor/reports/ar24/) and [Apple FY2024 financial statements](https://www.apple.com/newsroom/pdfs/fy2024-q4/FY24_Q4_Consolidated_Financial_Statements.pdf), with authored paraphrases and explicitly counterfactual negative/contradiction mutations. Source facts were rechecked. They are not all quotations of real contradictory disclosures. These sets were initially frozen, but their failures are now visible during development; future validation must use a new untouched set.

## Retrieval independent of classification

CoreWeave retrieves all 5/5 positive pairs at frontier 0. Original challenge material recall at frontiers 0/1/2/4 is 4/6, 4/6, 5/6, 6/6, at 76/156/243/437 candidates (496 possible pairs). Both contradictions miss the initial embedding tail; neither misses NLI classification when evaluated directly. Wider frontiers reuse cached vectors and similarities (zero new embedding/similarity computations). There were no missed labeled paraphrases in either broader set: synthetic 17/17 material, disclosures 8/8. Increasing bands until the challenge fits would not establish production quality, so the adaptive policy remains unchanged.

Every labeled relationship has a similarity/cutoff trace. Every missed positive has a seven-category failure audit plus a separate restrictive-attribute-veto flag in [the full paired report](benchmarks/semantic-quality.json). Negative unretrieved pairs are not mislabeled as retrieval failures. Empty audit categories do not establish unknown context as agreement.

## Missed equivalence/entailment taxonomy

All baseline misses follow. Causes can coexist. “Threshold” identifies supportive scores below the provisional gate, not evidence that lowering it is safe. Explicit material-conflict flags are false on these reviewed positive labels; extra premise content is tracked as a directional veto, not an extraction error. Source ambiguity is retained for the supplier compression.

| Set/case | Baseline failure causes | After |
|---|---|---|
| coreweave: power-intro/power-execution | incorrect_nli_inference, missing_contextual_attributes, incorrectly_extracted_attributes | EQUIVALENT |
| coreweave: power-intro/power-presentation | overly_restrictive_decision_thresholds, missing_contextual_attributes, incorrectly_extracted_attributes | EQUIVALENT |
| coreweave: power-execution/power-presentation | incorrect_nli_inference, missing_contextual_attributes, incorrectly_extracted_attributes | EQUIVALENT |
| coreweave: centers-presentation/centers-transcript | incorrect_nli_inference, missing_contextual_attributes, incorrectly_extracted_attributes | EQUIVALENT |
| coreweave: suppliers-summary/suppliers-detail | incorrect_nli_inference, missing_contextual_attributes, incorrectly_extracted_attributes, genuine_source_ambiguity | UNRESOLVED |
| original_challenge: mutual | missing_contextual_attributes | EQUIVALENT |
| original_challenge: containment | missing_contextual_attributes, overly_restrictive_attribute_veto | ENTAILS |
| independent_heldout: revenue-notation | incorrect_nli_inference | UNRESOLVED |
| independent_heldout: count-year-end | incorrect_nli_inference, missing_contextual_attributes, incorrectly_extracted_attributes | EQUIVALENT |
| independent_heldout: power-units | incorrect_nli_inference, missing_contextual_attributes, incorrectly_extracted_attributes | EQUIVALENT |
| independent_heldout: capacity-wording | incorrect_nli_inference, missing_contextual_attributes, incorrectly_extracted_attributes | EQUIVALENT |
| independent_heldout: oneway-operations | missing_contextual_attributes, overly_restrictive_attribute_veto | ENTAILS |
| independent_heldout: oneway-financial | overly_restrictive_attribute_veto | ENTAILS |
| independent_heldout: oneway-qualification | overly_restrictive_decision_thresholds, overly_restrictive_attribute_veto | UNRESOLVED |
| independent_heldout: directional-detail | missing_contextual_attributes, overly_restrictive_attribute_veto | ENTAILS |
| disclosures_heldout: ms-revenue | incorrect_nli_inference | UNRESOLVED |
| disclosures_heldout: apple-sales | incorrect_nli_inference | UNRESOLVED |
| disclosures_heldout: apple-income | incorrect_nli_inference | UNRESOLVED |
| disclosures_heldout: ms-growth-containment | overly_restrictive_attribute_veto | ENTAILS |
| disclosures_heldout: apple-containment | overly_restrictive_attribute_veto | ENTAILS |

## Model evidence and costs

The pinned MiniLM model is accurate on several prose paraphrases and literal conjunct projections but is unreliable on date paraphrases and numeric scaling: equivalent revenue/net-sales/net-income million/billion expressions can receive very high contradiction probabilities despite compatible extracted quantities. A complete capacity grammar can prove some narrow facts independently; mere equality of extracted financial attributes is never a general proof. No alternate model was compared or installed; these results justify a future comparative evaluation, not a model replacement here.

The paired audit used 284 directional local predictions; resumed inference count is zero in all four sets. NLI initialization was 1.08s; NLI execution 15.46s; total paired evaluation 23.62s. Model scores and vectors were reused between policies and frontier bands, not recomputed for each policy.

The read-only real inventory contains 1,796 propositions plus 13 incoming fixture claims. Its candidate-run hash exactly matches the original benchmark: `44f81b922dc9d46cc39200756ccc2b90a90b1e977c54733556bef4dd0b15929e`. The same 22 candidates change from 22 UNRESOLVED to 4 EQUIVALENT / 18 UNRESOLVED. This inventory is unlabeled: merge precision and missed-merge count are undefined. Disposable inventory embedding work took 212.54s (1521 distinct uncached texts); NLI used 44 directional predictions in 1.65s wall time. Resume uses zero inference, embeddings or similarity calculations.

All semantic inference is local CPU work: zero remote/generative semantic requests and zero Cursor deduplication requests. Disposable Sort uses 10 recorded extraction/review requests, 186,888 prompt characters, zero authenticated requests, and no measured live token counts or monetary model bill. Do not interpret recorded requests as live extraction accuracy. Baseline replay wall time includes isolated model initialization/download overhead; it is not a speed comparison.

## Verification and remaining limits

Disposable end-to-end replay compares original commit and revised implementation on identical recorded source selections. Both retain all 13 independent evidence propositions and 22 exact citations; presentation entries change 13 → 10. Existing support anchors are asserted preserved. Resume makes zero requests and preserves passage rows. Manual direction, split suppression, context invalidation, complete-link grouping, immutable evidence coverage, stale/failed publication and transactional safeguards are covered by the suite. Regression tests explicitly cover note/text/recovered-date conflicts, fiscal-year ends, written quarters, amounts resembling years, missing issuer/period/scope, numbers/units, prospective tails, active/contracted state, geography and source restrictions.

Final verification: **440 tests passed** (`.venv/bin/python -m pytest -q --basetemp=.data/quality-full-verified-tmp`), 69 focused graph/policy tests passed, and the disposable original/revised Sort replay completed. Production SQLite checksum was unchanged during final verification. One earlier concurrent pytest invocation shared its configured temporary directory and produced a FileNotFoundError in `test_structured_source_context_changes_invalidate_graph` (431 passed, 1 setup error); subsequent verification uses separate directories. This was a test-run collision, not a silently ignored failure.

Remaining work before production rebuilding: resolve supplier-risk context with audited issuer identity and stronger paraphrase inference; compare models or bounded numeric reasoning on untouched financial disclosures; evaluate initial-frontier contradiction recall in realistic inventory; independently review the map-disclaimer interpretation and plus-sign bound convention. No production rebuild or PR merge is part of this delivery.
