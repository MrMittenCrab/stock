# Proposition graph validation · 2026-10-24

**Architecture implemented; production rollout is not ready.** No production
CoreWeave replacement, index write or graph activation was used for validation.
The original draft PR remains a draft. This report separates actual model behavior
from injected workflow tests and historical Cursor measurements.

## Measured local execution

Pinned BGE-small and MiniLM2 NLI both executed through CPU ONNX Runtime on this
Apple Silicon Mac, Python 3.14.0. First downloads took roughly 10 seconds for
embedding initialization and 31 seconds for NLI initialization, including downloads.
Warm NLI initialization in the recorded inventory run took 1.12 seconds. Model
initialization and inference are not recurring paid requests. Initial indexing can
still be substantial on CPU; only subsequent unchanged vectors are free to reuse.

Artifacts:

- [Read-only inventory evaluation](benchmarks/proposition-graph.json)
- [Final labeled/model/refinement evaluation](benchmarks/proposition-graph-focused.json)
- [Complete recorded-extraction Sort regression](benchmarks/proposition-graph-e2e.json)

The inventory run preceded the final quantity-parser veto update (policy v2); the
final small-corpus/model/refinement and end-to-end runs use policy v3. The embedding
and NLI contracts are identical; the inventory has no gold relationship labels.

The inventory evaluation read 1,796 existing CoreWeave propositions with SQLite
`mode=ro`, added 13 committed incoming excerpt propositions in a disposable database,
and evaluated 1,809 total nodes. There were 1,521 unique text embeddings, all newly
computed in that disposable cold cache. It performed 23,348 incoming/historical and
78 incoming/incoming similarities, **23,426 local dot products** in total. Embedding
work took 243.78 seconds in this run, which overlapped regression testing; this is
not an isolated hardware throughput benchmark. Twenty-two candidate pairs selected
44 directional NLI predictions in 1.60 seconds. It deferred 23,404 pairs. All 22
relationships were UNRESOLVED; there were zero equivalence groups, zero entailment
edges and zero contradictions. The inventory has no exhaustive relationship labels,
so recall and precision on that entire inventory are unknown.

Repeating the identical inventory scope computed zero embeddings, zero similarities
and zero new NLI predictions, reusing all 1,521 embeddings and 22 completed pair
judgments. The historical-only backlog was outside this incoming-pair evaluation;
it is not certified distinct.

Compared with the historical **23,322 pairs / 329 Cursor deduplication requests**,
the new measured workload used **23,426 local similarities / 44 local directional
predictions / zero Cursor deduplication requests**. The inventories differ; the
numbers must not be presented as a controlled equal-quality speedup. There is no
claim of zero total Cursor usage: extraction and independent source verification
remain separate costs. No inference quality gain is inferred from the reduction.

## Retrieval and relationship quality

The committed 13-proposition CoreWeave excerpt fixture has nine hand-labeled
presentation groups. All original statements and exact citation anchors survived.
The initial retrieval checked 13 of 78 possible pairs, including all five directly
labeled equivalent pairs: candidate equivalence recall **5/5** on these excerpts.
The conservative final policy nevertheless produced **13 separate presentations**,
missing all four expected group reductions. It made no false merges; equivalence
precision is **undefined because there were no positive merges**, not 100%.
Financial date/notation differences, missing explicit scopes, attribution and model
uncertainty explain these false negatives. This is a real production-readiness
blocker, not successful deduplication disguised as a cost improvement.

One explicit refinement expanded to 29 checked pairs, leaving 49 deferred. It reused
all embeddings/similarities and the initial 13 pair decisions, computing 32 extra
directional predictions. Repeating that unactivated frontier reused all 29 pair
judgments and made zero new predictions. Candidate equivalent-pair recall remained
5/5. No exhaustive recall claim is made beyond the labeled fixture.

The final synthetic challenge set uses actual pinned models, separately from mocked
workflow tests. It includes generic equivalence, financial equivalence, one-way
containment, thematic relationships, contradiction, period, modality, capacity,
scope, definition, qualification, issuer, numeric and uncertainty challenges.
See the final JSON for each prediction, both score vectors and safeguard vetoes.
The final 16-case set retrieved four of six material gold relationships (66.7%);
retrieval missed both contradiction examples. The standalone NLI/policy evaluation
asserted three material relationships, all matching their labels (3/3); only two of
those were selected by the frontier (2/2 precision for retrieved assertions). Twelve
of 16 standalone classifications matched their labels. These tiny denominators
provide no reliable precision confidence bound. The set is small, hand-authored and not held out: reported precision/recall estimates
are descriptive fractions, not evidence of calibration or production accuracy.
The original difficult cases are retained even when additional explicitly scoped
cases demonstrate supported directional behavior; missed predictions remain visible.

## Evidence and workflow regression

The full recorded Sort replay used actual local semantic models with hand-recorded
extraction and independent source-review responses, through the actual Sort
transport/publication pipeline in a disposable database. It retained all 13 evidence
nodes and 22 exact citations, with 13 presentations versus nine original labeled
groups. Ten recorded Cursor extraction/review requests were exercised, zero Cursor
deduplication requests, and zero requests on resume. These are transport replays,
not authenticated Cursor calls or measurements of remote token usage/latency.

Pytest uses injected deterministic local encoders and NLI outputs to test workflow
invariants without downloads or authenticated services. Focused checks cover:
bidirectional scores, one-way retention, financial-conflict vetoes, jointly missing
attributes, unlisted counterparties, overlength refusal, uncertain outputs,
complete-link safety, cache identity/invalidation, cached inference resume, empirical
frontier expansion, manual correction/split persistence including retired evidence,
exact citation preservation, automatic rebuild publication, rollback, concurrent
snapshot/head checks and keyboard relation/member/source/topic navigation.
Final verification: `.venv/bin/python -m pytest -q` passed **402 tests** in
140.60 seconds. The focused graph/policy/rebuild run passed 49 tests before the
last policy-cache regression was added; the full run includes it. `pip check`,
Python compilation and `git diff --check` also passed.

An independent review identified missing-attribute agreement and lone-neighbor
retrieval bugs; both have failing-then-passing regression coverage. Additional review
caught policy/model freshness and retired split tombstones; those also have direct
regression coverage. Existing tests expecting rejected approval callbacks to stop
explicit rebuilds were corrected to use `review_only=True` for previews.

## Remaining readiness blockers

1. Improve financial equivalence recall without weakening safeguards: source-verified
   structured entity/period/scope and notation/qualification handling need a broader
   labeled financial evaluation. No production replacement should be used to tune it.
2. Calibrate or replace the conservative NLI decision policy on held-out financial
   pairs. MiniLM directional scores alone are not proof. Quantitative contradictions
   currently often remain unresolved rather than risking cross-period false conflict.
3. Validate the adaptive frontier on a larger labeled inventory, including distant
   paraphrases. Sparse observations and unrelated reference probes do not certify
   recall; historical-only deferred pairs remain backlog.
4. Evaluate alternative small NLI models if financial precision/recall remain poor.
   The present model ran successfully and cheaply, but general NLI benchmarks do not
   establish financial reliability.
5. The named `TERMINAL_RENDERING_HANDBOOK.md` was absent from the checkout and searched
   workspace. Existing grayscale terminal styling and keyboard tests were retained;
   a handbook-specific visual audit remains outstanding if an external copy exists.

Operational commands, pinned artifacts, graph schema and policy details are in
[semantic-map.md](semantic-map.md). The eventual `--rebuild 13` command is documented
there for use only after these blockers are resolved; it was not executed.
