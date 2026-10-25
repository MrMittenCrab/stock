# Semantic correctness continuation

Authorized scope: user requirements 1–10, starting at 0893253 on the existing feature branch. No production writes, document 13 rebuild, merge or ready-for-review transition.

Design: retain raw embedding/NLI contracts and current MiniLM. Compare pinned DistilRoBERTa and DeBERTa-small CPU ONNX alternatives on a newly frozen authored financial set, before examining predictions. Report raw directional accuracy and conservative policy results separately. No tuning on this set. Existing fixtures remain unchanged; supplier disagreement receives a separate adjudication, never a score-driven relabel.

A full-consumption money-fact grammar can prove equivalence only with the same explicit issuer, metric/definition, fiscal period, assertion, issuer scope, currency and exact Decimal value. Reject residual clauses, missing fiscal basis, rounding, forecasts, ranges and restrictions. Existing provenance, context and attribution vetoes remain active. Attribute equality alone cannot prove equivalence. Alternatives considered: lowering NLI cutoffs (unjustified risk); model replacement (requires comparative evidence); bounded symbolic proof (selected for inspectability).

Add a separate deterministic compatibility-index retrieval channel with a fixed per-incoming budget. Index issuer/metric/period/scope and material definition/modality/state compatibility, allowing numerical/polarity disagreement. Preserve empirical similarity retrieval and caches. No new remote inference or all-pairs NLI.

Sequence:
1. Freeze new test labels and hash before inference; inspect source failures and supplier wording.
2. Add failing safety/recovery and structured retrieval tests.
3. Implement bounded parser and retrieval; run focused tests.
4. Run paired baseline/current policies and three models; preserve raw predictions and timings.
5. Replay complete Sort in disposable databases; verify evidence, citations, cache, manual and publication invariants.
6. Audit results and limitations, commit/push, verify draft PR and production checksum.


Verification ledger:
- Tasks 1–5 complete: frozen 40-case fixture and pinned local models, reproduced failures, bounded full-fact proof and structured retrieval, raw-score paired audit, 195 focused tests and complete disposable Sort replay. Independent review findings were reproduced and fixed. All old gold fixtures remain unchanged.
- Ruling: work in the existing requested feature checkout; the user explicitly selected this branch and starting commit. No worktree/merge/ready-for-review menu is needed because integration was already specified.
- Ruling: unknown issuer identity abstains, even though this reduces bare-text holdout accuracy. Unknown words cannot safely establish financial issuer identity. The cost is missed relationships without audited context; documented as a production blocker.
- Ruling: possible rounding overlap withholds numeric contradiction; interval overlap never proves equivalence. The cost is conservative contradiction recall.
- Task 6: final evidence and blockers in docs/semantic-correctness.md; commit/push verification follows. PR #1 must remain draft and production checksum must remain unchanged.
