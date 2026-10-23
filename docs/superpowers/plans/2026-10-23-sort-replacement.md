# Sort knowledge replacement implementation plan

Goal: replace section-driven extraction with coherent document analysis and verified knowledge.
Architecture: one short-document generation, batched verification, one bounded uncertainty follow-up; exact anchor and operation storage; existing transactional publication projection.
Tech: Python, SQLite, existing authenticated read-only Cursor CLI.
Spec: docs/architecture/sort-knowledge.md.

Global constraints: production files/database unchanged; work only in stock; no new credentials; no automatic production document-13 rebuild; preserve REPLACE, preview, frozen records and manual corrections. User delegates implementation and commit/push; execute inline.

Review focus: incomplete artifacts cannot publish; notation normalization cannot establish semantic support; missing PDF must not reject narrative; manual split identities must survive or block replacement; approval waiting must not consume processing time.

- [x] Add contract tests for unified generation, exact multi-span citations, independent review, interruption/resume, legacy isolation and quiet failures. Run red.
- [x] Add Decimal numerical/period normalization with sign/currency/scale tests; replace lexical guards.
- [x] Replace evidence.extract orchestration with content-addressed generation/review/correction work. Separate source anchors, propositions, supports and judgments in additive versioned SQLite tables. Keep old tables audit-only. Test.
- [x] Add heading-aware long-document requests/global outline and selective original-page layout retrieval; cache by source hash; test missing layout/ambiguity.
- [x] Wire default Sort/rebuild, remove obsolete runtime distillation and per-claim repair, preserve semantic grouping/corrections and checked publication. Block replacement of manually split memberships without safe identity transfer.
- [x] Make diagnostics log-only, explicit keyboard detail at approval, suspend budgets during operator reading. Test rollback, review-only, frozen no-op and compact output.
- [x] Record expected-information inventory and replay old/new/baseline over actual source fixtures; report local and live evidence separately. Run final relevant suite, review and fix findings.
- [x] Verify production preservation, document limitations/safe validation command, commit and push origin/main.

Ruling: no worktree outside authorized directory; clean main checkout is isolated from production by disposable DBs, not a second filesystem checkout. Ruling: historical checkpoints retained but never execute old section flow. No unsupported auto-adoption.

Delivery ledger: 347 tests passed (126.21s), compilation and diff checks passed. Production tables and 197 archive files match the protected snapshot. Paired replay is docs/benchmarks/knowledge-sort.json; readable inventory and limits are docs/knowledge-sort.md. Runtime section extraction/distillation/eager layout/per-claim repair have been removed. Historical reproduction utilities are test-only.

Acceptance still blocked: the single authenticated extraction request returned no output before its 120s deadline. Fresh full-document quality/latency and naive baseline comparisons are not completed. No production evidence migrated. The isolated validation helper and retained failure directory permit deliberate follow-up without production publication.
