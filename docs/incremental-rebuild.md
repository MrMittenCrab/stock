# Incremental rebuild correction · 2026-10-24

Current implementation: [local directional proposition graph](semantic-map.md).
Cursor grouping and lexical retrieval described below are historical baselines.

This supersedes earlier requirements to type REPLACE or to publish before semantic
deduplication. Explicit `--rebuild DOCUMENT` authorizes replacement, but extraction,
independent factual review, semantic grouping and manual-correction reconciliation
remain mandatory. Implementation never replaced production document 13.

## Diagnosis on a disposable production backup

The production log `ac822e8041ae4366879398d4fd5a5444.jsonl` records four understanding
calls, independent review, targeted recovery and 17 semantic-grouping calls before
the 24-request safeguard paused processing. Those 17 grouping calls consumed
530.646 seconds; the whole run paused after 1,741.775 seconds.

Document 13 has 19 current knowledge artifacts: four understanding, one independent
verify, one uncertainty-resolution and 13 per-claim review artifacts. There are
13 persisted verified propositions/judgments. All 19 artifact IDs/checksums survive
this correction. Eight older `source_work_v3` section checkpoints also survive;
these are historical artifacts, not the current reconstruction engine.
The log covers 261 non-context source anchors, 113 selected and 37 marked verified;
these coverage flags do not claim that every source paragraph became a proposition.
The current accepted reconstruction has 59 references to 56 unique anchors, including
supporting context, for 13 propositions. Checkpoint-only extraction plus source
verification takes 0.132 seconds in this replay and makes zero model requests.

Production currently contains 1,796 published passages, including eight outgoing
passages from document 13. The proposal contains 1,801 passages: 1,788 unchanged
plus 13 replacements. SQLite has no active insight heads or revisions, no manual
splits, and no topic overrides. Protection of manual structure is therefore tested
with separate focused fixtures rather than claimed from this empty production state.

There are 166 semantic-cache entries: 44 actual judgments and 122 legacy entries
which recorded unreviewed/oversized uncertainty as negative decisions. The correction
retains actual judgments under their existing source fingerprints and contract,
and disregards those fabricated negative entries without deleting their audit data.

| Old retrieved workload | Pairs |
|---|---:|
| New–new | 5 |
| New–unchanged | 119 |
| Unchanged–unchanged | 9,993 |
| Total | 10,117 |
| Cache entries encountered | 166 (165 historical-only, one replacement-related) |

The old implementation rebuilt the full archive candidate graph with no active
revision to establish an unchanged baseline. A small 14k-character packing target,
full document provenance and statement support, and hash-based pair ordering made
most batches contain only one or two pairs. The original plan was **5,323 batches**.
Reconstructing that planner against the paused snapshot gives **5,306 remaining**,
exactly the original count minus 17 completed calls. Only **97 remaining mixed
batches** touch replacement evidence. Thus 5,226 of the original batches were
unrelated to the replacement. Under the old retrieval heuristic just 124 pairs
were replacement-related; a batch count is not an intrinsic semantic requirement.

## Complete replacement scope

The old top-eight retrieval is not a completeness guarantee. The replacement path
instead compares all incoming propositions internally and against all unchanged
published evidence, even if they share no words. Outgoing IDs are excluded. This
conservative scope does more relevant work than the old heuristic, while avoiding
historical-only model work entirely:

| Corrected workload | Measured |
|---|---:|
| New–new pairs | 78 |
| New–unchanged pairs | 23,244 |
| Total required pairs | 23,322 |
| Unchanged–unchanged model pairs | 0 |
| Valid replacement cache hits at initial replay | 0 |
| Valid historical judgments reused without model calls | 44 |
| Model batches planned | 329 |
| Serialized comparison characters | 20,826,967 |
| Offline synthetic replay | 48.854 seconds |
| Checkpointed resume | 3.248 seconds; zero requests; 23,322 replacement cache hits |
| Historical retrieval backlog | 9,949 unresolved pairs |

This is a 93.8% reduction in planned requests from 5,323, while exhaustively covering
the replacement. Historical cache judgments remain available even though no model
work is requested for those pairs. Historical backlog counts refer to the legacy
retrieval candidate set, not an exhaustive historical all-pairs graph. Revisions
record `grouping_scope` and `historical_backlog_pairs`; currentness does not silently
mark an unresolved historical backlog complete.

Shared document, evidence and statement dictionaries preserve every supplied field.
Ordering comparisons by historical document/statement lets many replacement claims
share support in each request. The 64k packing target is a batching boundary, never
a content quota: a single larger pair is still reviewed. No comparison is classified
negative merely because it is unchanged or large. The model contract still requires
bidirectional information preservation across entity, property, time, scope, values,
units, modality, perspective, qualifications and independent/repeated provenance.

Every merged member pair needs a direct positive judgment. Existing valid groups
are seeded before inserting replacements, so partial equivalence cannot steal a
member or create a transitive merge. Unreviewed historical pairs stay unresolved,
without fabricated judgments or a claim of global deduplication completeness.

## Publication and integrity

Source-identity reconciliation runs before grouping. Both outgoing and incoming
source anchor/category/speaker identities must be unique to transfer a manual topic
or split. Ambiguity or no match raises a specific error and retains old evidence.
Remapped manual split pairs override any cached model equivalence. Historical
revisions, retired evidence/topics/overrides and all extraction checkpoints survive.

After grouping, source files and the evidence/topic/head snapshot are checked again.
Replacement rows, transferred corrections, evidence-version activation and semantic
head activation share one SQLite transaction. Failure rolls everything back. A
budget interruption saves completed pair judgments but activates no partial view.
`--rebuild` never calls input or a pager. `--rebuild DOCUMENT --review-only` stages
the same checked proposal without replacing evidence or activating its groups.
Sources reads the active grouping and retains exact member citations and corrections.

## Reproduction and limits

```sh
.venv/bin/python -m scripts.benchmark_incremental_rebuild \
  --output docs/benchmarks/incremental-rebuild.json
```

The script opens production SQLite read-only solely to make a disposable backup.
It reuses real Archive files and verified checkpoints, forbids extraction/review
model requests, measures the old planner, exhaustively replays the new scope,
resumes without any model and automatically publishes only on the copy. Synthetic
negative answers measure workload and pair coverage; they do not measure live
semantic accuracy, latency or token usage. Focused semantic fixtures separately
exercise duplicate/nonduplicate decisions, complete-link safety and manual controls.
No thousands of live Cursor calls were made. The live completion time is unknown.

For an unattended run on the Mac, preventing idle sleep:

```sh
caffeinate -i stock sort CRWV.US --rebuild 13 \
  --request-seconds 600 --document-seconds 21600 \
  --command-seconds 21600 --cursor-requests 350
```

The request safeguard allows the measured 329 batches with modest headroom, not a
thousands-request historical regrouping. Wall-clock and request safeguards still
fail closed; on exhaustion the identical command resumes cached comparisons. Live
protocol/authentication/source-integrity failures still require resolution. Add
`--review-only` for a nonpublishing review. This implementation did not execute
either production command.

Final focused verification: **107 passed in 85.85 seconds**, using
`tests/test_insights.py`, `tests/test_evidence.py`, `tests/test_sort_budget.py` and
`tests/test_sort_efficiency.py`. This includes Sources UI grouping/member controls,
material distinctions, new-existing duplicates, complete-link safety, existing
structure, identity-based manual transfers/blocks, unattended CLI, nonpublishing
review, failure rollback, stale snapshots, interrupted grouping and resume.
Compilation and `git diff --check` also pass. An independent review caught and
verified the correction of an ordinary-sort regrouping regression; its second
review found no blocking integrity/publication issues.
