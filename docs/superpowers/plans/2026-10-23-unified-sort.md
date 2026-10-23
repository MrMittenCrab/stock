# Unified Sort implementation plan

Goal: make normal Sort build and publish distinct verified insights within predictable limits.
Architecture: extend existing extraction, caches and transactional semantic views; no evidence migrations.
Specification: user request in this session; origin/main bbbcbac.

- [x] Inspect extraction, source preparation, distillation, reviews, recovery and grouping.
- [x] Remove duplicate materiality reassessment; preserve factual review and old checkpoints.
- [x] Unify normal Sort and grouping; preview without activation; preserve REPLACE for rebuild.
- [x] Enforce shared monotonic document/command/request deadlines and request counts, including startup and PDF children.
- [x] Render compact status, suspend during review, and persist diagnostics locally.
- [x] Replay identical presentation, filing and transcript sources before/after using isolated databases; report model volumes and local times separately.
- [x] Test default grouping, idempotence, preview, replacement approval, limits, cancellation, resume, exact sources, topic overrides and material distinctions.
- [x] Review final diff, run focused regressions, document limits, commit and push main without rewriting history.

Constraints: work only in this repository; no live extraction, no production evidence changes, no automatic document-13 rebuild. Defaults: 720s/document, 1200s/command, 12 Cursor requests/document, 120s/request. Historical checkpoints and revisions remain intact.

Review focus: time exhausted after final response but before publication; timeout during retry; completed extraction awaiting grouping; topic edits and manual ungroup; incremental comparisons after a new document; preview with unpublished evidence.

Delivery evidence: 222 focused regressions passed; independent review findings fixed
and verified. Paired replay and preservation results are in `docs/unified-sort.md`
and `docs/benchmarks/unified-sort.json`. No production evidence rebuilt; document 13
retains eight frozen passages. Commit/push to main is explicitly authorized by the user.
