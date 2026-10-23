# Semantic insights implementation plan

Goal: distill material source content and display reversible distinct insights.
Architecture: cached source selection, bounded cached proposition judgments, append-only
insight revisions over immutable passages, member-scoped Sources controls.
Spec: docs/superpowers/specs/2026-10-23-semantic-insights-design.md
Constraints: preserve 17c710c, frozen sorts, citations, overrides; no production writes.
Execution: inline under the user's explicit implementation and commit/push request.

- [x] Add failing tests for staged semantic equivalence, non-equivalence, immutable
  activation/ungroup, topic/document visibility, selection planning, and cache reuse.
- [x] Implement stock/insights.py: bounded retrieval, strict model decisions, cached
  proposals, revision activation and audit, singleton compatibility.
- [x] Implement stock/distillation.py: cached hierarchical source-ID selection;
  wire fresh extraction and Cursor operation contracts without invalidating old work.
- [x] Wire CLI review/REPLACE and compact keyboard-only Sources member inspection.
- [x] Replay actual CoreWeave fixtures; measure retained information, false/missed
  merges, requests and resume. Run focused and full relevant regressions.
- [x] Review diff, document results/limits, commit and push origin/main.

Review focus: no transitive merges; no topic-edit propagation; filter canonical must
be supported by visible evidence; stale proposals fail atomically; historical
staging and every passage survive activation and ungrouping.

Rulings: no additional approval round was introduced because implementation,
commit and push were explicitly authorized by the user. Native inline work used
one independent reviewer as required by the code-review skill. Its topic-editor
binding and symmetric duplicate-omission findings were fixed with regression tests.
Target-only semantic groups are reviewed inside --rebuild before REPLACE, instead
of requiring a separate subsequent grouping pass. Cross-document grouping remains
explicitly staged. Dense complete-link fragmentation remains a documented limit.

Verification: full suite 305 passed; subsequent focused semantic rebuild rollback
regression 1 passed. Reviewer independently ran 28 semantic/distillation tests.
CoreWeave fixed-judgment replay: 13 passages, 9 insights, all evidence retained,
0 fixture false/missed merges, 4 replay requests, 0 resume requests.
