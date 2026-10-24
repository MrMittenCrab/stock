# Incremental rebuild implementation plan

User specification: semantic grouping remains a publication prerequisite; explicit
rebuild authorizes replacement. Production evidence must remain untouched.

Design: scope replacement comparisons to all incoming/incoming and incoming/unchanged
pairs (no retrieval cutoff). Preserve validated unchanged groups and manual splits.
Keep historical-only unresolved work explicitly outside this scope. Reuse exact
contract/fingerprint caches, excluding legacy fabricated negative decisions. Batch
losslessly with shared dictionaries; oversized pairs must still be reviewed.
Reconcile manual decisions by unambiguous source anchors before staging. Commit
replacement and semantic head atomically. Allow rebuild with --review-only.

- [x] Diagnose log and SQLite snapshot; recover extraction/review with no live model.
- [x] Add regression tests for incremental completeness, preservation and unattended publication.
- [x] Implement scoped comparison, complete-link preservation and manual reconciliation.
- [x] Replay the real archive offline; record workload and checkpoint coverage.
- [x] Run focused tests, inspect diff, commit and push origin/main.

Review: independent review found normal archive staging incorrectly preserved
separate groups after new positive judgments. Preservation is now replacement-only;
a dedicated regression passes. Second review found no blocking issues.

Ruling: user supplied the complete implementation specification and explicitly
authorized commit/push, so no additional design or publishing permission was needed.
The request to avoid full-suite repetitions takes precedence over full-suite skill
defaults; verification targets the four affected semantic/rebuild/budget/efficiency
modules and the real-archive offline replay. No live Cursor calls or production
publication were performed.
