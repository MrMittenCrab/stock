# Proposition graph implementation plan

Goal: implement the supplied twelve-part specification on the existing draft branch.
Architecture: persistent exact embedding retrieval, bidirectional local NLI evidence,
conservative financial policy, and immutable relationship revisions activated with
existing evidence transactions. Presentation groups are complete-link views of nodes.

The supplied specification authorizes implementation now; routine design choices
are delegated to the implementer. No production rebuild or merge is authorized.

- [x] Add tests for directional decisions, financial conflicts, cache reuse,
  adaptive deferred discovery, complete-link safety and atomic graph activation.
- [x] Retain BGE vector cache and introduce explicit pinned artifact/preprocessing
  provenance; use empirical upper-tail neighborhoods with persisted deferred pairs.
- [x] Add a pinned small local NLI classifier with both directions, validated
  probability outputs and fail-closed overlength handling. Scores are uncalibrated.
- [x] Replace Cursor semantic staging with local graph staging; preserve source
  identity, corrections, manual splits, and historical revisions.
- [x] Extend `stock map` with `--refine`; reuse inference and vectors, activate
  only against unchanged evidence/head. Display links inline in Sources.
- [x] Run focused and offline regressions, real Mac model validation and disposable
  CoreWeave evaluation; document measured costs, gaps and exact operational commands.
- [x] Review, commit and push to the existing draft branch; preserve production.

Review focus: unknown financial attributes, cross-period apparent contradictions,
overlong propositions, interrupted cache checkpoints, and concurrent manual edits.

Validation ledger: focused workflow/policy run 49 passed before final added cases;
final full suite passed 402 tests in 140.60 seconds; real-model artifacts are in
docs/benchmarks/proposition-graph*.json and validation details in
docs/proposition-graph-validation.md.
Independent review findings (unknown attributes and lone-neighbor retrieval) fixed
with direct regressions. No production replacement or merge. Production quality
remains blocked: 13 real excerpt nodes retain four missed expected group reductions.
