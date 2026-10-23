# Sort knowledge architecture: implementation and evidence

Current strategic-commentary contract and document-13 evaluation: [strategic commentary audit](strategic-commentary-audit.md). The `knowledge-2-strategic` refinement retains this architecture while prioritizing distinct strategy, corporate events, execution, source perspective and standalone readability. Its source-specific inventory accepts 24 human-corrected recorded propositions versus 17 surviving the observed live baseline; this does not establish fresh-model recall. Use `.venv/bin/python scripts/validate_knowledge.py` for safe offline validation. Detailed statements require `--show-statements`; another authenticated extraction requires explicit authorization.

The measurements and financial examples below document the original architecture delivery. They are historical evidence, not the current strategic coverage standard. In particular, the timeout below preceded the completed 650.6-second live run audited in the linked report.

Normal `stock sort TICKER` now uses document-level selection and factual reconstruction together, independently reviews batches of cited propositions, resolves uncertainty in one bounded follow-up wave, compares verified facts with plausible library neighbors, and publishes evidence and grouping atomically. A complete 31,048-character document-13 Markdown fixture fits one generation request. Large documents use bounded heading-aware sections and a shared outline; follow-up work can span multiple requests without discarding later claims to satisfy a request cap.

The architecture decision and stage-by-stage diagnosis are in [sort-knowledge.md](architecture/sort-knowledge.md). This supersedes the execution architecture described in `unified-sort.md`, `sort-efficiency.md`, and their historical section benchmark. Historical measurement files remain evidence about those older implementations.

## Replaced responsibilities

Removed runtime source-ID distillation, section-index checkpoint adoption, overlapping section context, per-statement citation repair/re-review loops, eager whole-PDF geometry preparation, and automatic exclusion pagers. Historical extraction and eager layout execution flows now live only in tests for provenance and failure reproduction; read-only legacy citation-validation helpers remain available for compatibility. The obsolete section benchmark was removed; use `scripts/benchmark_unified_sort.py` for the paired replacement replay.

`knowledge.py` owns the new control flow. SQLite separates exact anchors, reconstructed propositions, support edges, review judgments, operation artifacts and execution attempts. Artifact identity includes contract, hashes, source paths, document metadata, exact inputs and layout context. Checksums protect reuse; a generation cache hit never implies verification. No historical checkpoint is silently interpreted as current work. Completed operations survive interruption, including accepted review batches; failures record their type, reason and remaining operation. Only genuine protocol errors receive one retry, within the original request deadline.

`editorial.py` owns representation and independent support review. Decimal quantities normalize scales, currencies, signs, percentages, basis points and power/energy notation. Financial periods recognize explicit abbreviations, fiscal and spelled-out quarter forms; dates/period interpretations still require semantic support. Detached table scale headers supply possible numerical interpretations without rescaling unrelated counts. Matching quantities cannot prove metric/period/attribution/definition equivalence. Redundant but useful supported evidence reaches semantic consolidation rather than being discarded by review.

`source_layout.py` reads a cached original-page text index only when necessary and fetches geometry only for uniquely located requested pages. Pages carry original hashes and matched source IDs. Ambiguous multi-value tiles and damaged table relationships require layout tied to the claim’s own references; an unrelated neighboring page cannot authorize publication. Ordinary narrative does not require PDF geometry. Unlocatable visual relationships remain unpublished.

Existing complete-link grouping, cached judgments, bounded lexical retrieval, revision histories, Sources navigation, document filtering, member-specific topic edits and manual ungrouping remain. Unknown equivalence preserves separate facts. Replacement blocks when changed passage identities would erase manual splits or unmatched topic corrections. Retired passage rows, original topics, overrides and sort records are archived transactionally before replacement. Topic changes/reset also append reversible correction events. No model call or PDF work occurs inside publication transactions.

Normal processing uses one status line. Exclusions remain in structured audit/logs. Replacement shows a concise count/correction summary; `D` deliberately opens evidence, and only exact `REPLACE` authorizes replacement. Operator reading/approval suspends all processing deadlines, including nested pager waits. Review-only cannot publish or activate.

## Paired recorded replay

The same five committed CoreWeave excerpts cover presentation 13, IPO prospectus, quarterly filing and two earnings transcripts. Both implementations run actual serialization, provenance validation, independent review, SQLite checkpoints and publication against disposable databases. Decisions are hand recorded, not fresh model outputs. The baseline is `a076578`.

| Measurement | Before | Replacement |
|---|---:|---:|
| Model requests, complete workflow | 28 | 18 |
| Prompt characters | 336,241 | 241,903 |
| Selection/reconstruction requests | 16 | 5 |
| Selection/reconstruction prompt characters | 234,579 | 131,605 |
| Independent factual review requests | 5 | 5 |
| Semantic grouping requests | 7 | 8 |
| Recorded useful statements / distinct insights | 13 / 9 | 13 / 9 |
| Exact citations | 21 | 22 |
| Missing recorded propositions / incorrect golden merges | 0 / 0 | 0 / 0 |
| Resumed model requests | 0 | 0 |

Total calls fall **35.7%**, transmitted context **28.1%**; selection/reconstruction calls fall **68.8%** and their context **43.9%**. Grouping costs remain visible rather than being omitted from totals. An explicit reporting-quarter citation was added to the transcript evidence. All original exact supporting references survive.

Document-13 **excerpt**: eight → five requests, 102,670 → 83,965 prompt characters, with its four recorded propositions preserved. This supports the small-call design hypothesis on recorded material; it does not prove full-presentation recall or five-call live completion. Full document 13 is independently tested to fit one coherent generation request.

Cold local replay was 0.215 → 0.189 seconds; resumed 0.0024 → 0.0028 seconds. These exclude live model service and are too small/noisy to support latency conclusions. Machine-readable results, including per-document counts: [knowledge-sort.json](benchmarks/knowledge-sort.json).

A generation-only baseline would use the five recorded generation requests and transmit 131,605 characters; its answers have no independent verification or activated semantic library. The replacement adds five factual-review and eight grouping requests. This is a workload comparison with the first-pass answers, **not** a measured independent naive-model quality comparison. The requested fresh paired live baseline comparison could not be completed.

## Readable source-grounded results

The [expected-information inventory](../tests/fixtures/sort/knowledge-inventory.json) preserves exact original offsets, hashes, statements and qualifications. Six presentation propositions and one two-passage product proposition pass recorded independent-review tests. These are accepted **recorded test results**, not claims about a successful live extraction:

| Case | Accepted readable statement / result |
|---|---|
| FY revenue; previously rejected FY2025/B notation | CoreWeave reported FY2025 revenue of $5.1 billion, up 168% year over year. |
| FY EBITDA and correct margin | CoreWeave reported FY2025 adjusted EBITDA of $3.1 billion and an adjusted EBITDA margin of 60%, both non-GAAP measures. |
| Q4 EBITDA distinct from FY | CoreWeave reported Q4 2025 adjusted EBITDA of $898 million and an adjusted EBITDA margin of 57%, both non-GAAP measures. |
| Detached count plus reporting date | CoreWeave reported 43 active data centers as of December 31, 2025. |
| Qualified backlog | As of December 31, 2025, CoreWeave reported revenue backlog of $66.8 billion, including remaining performance obligations and other estimated future revenue under committed customer contracts, subject to delivery and service availability requirements. |
| Capex definition | CoreWeave reported Q4 2025 capital expenditures of $8.2 billion, defined as additions to property and equipment including assets acquired under finance leases, less changes in construction in progress. |
| Multi-citation products / speaker | CoreWeave said SUNK and Mission Control orchestrate layers of its cloud stack, and that select customers were licensing SUNK as their default research cluster management platform across multiple clouds. Attributed to Michael Intrator; both separate transcript passages remain attached. |

Original PDF coordinates captured from pages 8, 13 and 18 establish that 60% belongs to FY EBITDA and 13% to adjusted operating income; captured layout includes the source PDF hash. The inventory rejects 13% as FY EBITDA margin despite its numerical presence, guaranteed backlog, a March 2026 date for the 43-center disclosure, and capex excluding finance leases. Unsupported $999 billion, wrong currencies/scales, missing qualifications and unverified flattened relationships also have contract tests. The pre-existing raw count/tile records remain frozen in production, unchanged.

Other representative recorded propositions retain supplier concentration and equipment availability risks from IPO/filing sources; transcript facts retain actual 2025 capacity separately from 2026 forecasts and period developments. Their exact citations and semantic distinctions are checked by the paired replay. This inventory is representative, not an exhaustive recall score for an entire prospectus or filing.

## Historical initial live timeout

One authenticated, extraction-only request used an isolated backup of document 13. It returned no model output before the configured request deadline: **120.08 seconds** total, approximately **2.57 seconds** startup/authentication and **117.51 seconds** inside the model subprocess. No timeout retry ran; no evidence was published anywhere. Retained failure state: `.data/knowledge-validation-1t_z9cqo`.

CLI envelope data did not expose separate queue, transmission or inference time, actual tokens or any model result. Those measurements remain unknown. This attempt preceded the final short-document boundary fix and targeted the first of two windows; the final implementation uses one whole-document request. There is **no demonstrated live speedup, fresh-model completeness improvement, or completed live baseline comparison**. Live acceptance is blocked pending a successful provider response. See [knowledge-live.json](benchmarks/knowledge-live.json).

## Preservation and migration

A protected SQLite backup plus file manifest was taken before implementation. Production comparison confirms all **13 tables**, **1,796 published passages**, document 13’s **eight passages**, and **197 archive files** unchanged. No production migration, extraction, replacement, conversion or ticker rebuild occurred. Parent stockpile was not modified. See [knowledge-preservation.json](benchmarks/knowledge-preservation.json).

The additive `knowledge_schema` version 1 is created when new analysis runs. It retains all old staging/revisions; new publication records carry extraction version 5. No old passage is rewritten by opening Sources or running current frozen Sort. Replacement is explicit and atomic, retaining retired records for audit; approval rejection or transaction failure retains active evidence. Disposable backups test the boundary. Restoring a complete protected SQLite backup reverses a disposable migration; do not delete historical tables as a rollback procedure.

## Validation and remaining limits

Final full suite: **347 passed in 126.21 seconds** (`.venv/bin/python -m pytest -q --basetemp=.data/knowledge-delivery-verified`). Compilation and `git diff --check` also passed. Tests cover notation, selected-only multi-span support, independent review, wrong labels/qualifications, ambiguous layout, cached page retrieval, interruption/resume, corruption, historical isolation, long bounded context, frozen no-op, topic edits/reset/audit, manual split preservation, rejected replacement, transactional rollback, review-only and quiet output. Most model decisions are deterministic fixtures. The one live timeout is reported separately.

Residual limits: semantic fidelity and materiality are model judgments; long-document global completeness is unproven; lexical equivalence retrieval can miss paraphrases; changed-anchor manual corrections/splits conservatively block replacement rather than guessing a transfer; some charts require visual interpretation beyond text geometry and remain excluded. Artifact contracts are versioned, so future prompt/schema changes must bump the contract rather than silently reuse old reasoning. Exactly-once provider calls cannot be guaranteed if a process dies between a response and its checkpoint commit.

Historical live-validation command (isolated database; no production publication). Run only with explicit authorization for another authenticated extraction:

```sh
.venv/bin/python scripts/validate_knowledge.py --live-document 13 --request-seconds 240
```

To resume an existing isolated run, add `--resume .data/knowledge-validation-<id>`. Normal user commands remain `stock sort TICKER`, `--review-only`, `--rebuild DOCUMENT`, `--reset DOCUMENT`, and `stock sources TICKER`. Do not run a production rebuild to test this migration.
