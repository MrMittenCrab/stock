# Decision: document understanding → verified propositions → incremental knowledge

Status: selected for replacement, 2026-10-23. The user explicitly delegates architecture selection and implementation; no intermediate design approval is required. SQLite and authenticated Cursor CLI remain. No production rebuild is authorized.

## Product invariants

Publish selective, self-contained factual investment propositions in the eight existing topics. Each material assertion must be supported by its own exact archived Markdown anchors, including period, attribution, definitions and qualifications. Reconstruction is disclosed. No invented analysis. Preserve disagreements, forecasts versus actuals, periods and scope. Semantic equivalence is bidirectional information preservation; uncertainty leaves separate propositions. Archived files, frozen passages, topic overrides, manual splits and revision history survive. Normal Sort completes the workflow, no-op when current; replacement requires REPLACE; preview cannot activate. Model input is untrusted, with no tool access.

## Current system and actual failures

Trace: CLI → budgets/Status → sort_stock → evidence.extract → candidates → PDF attach → distillation.plan → sections with neighboring atoms → resolve_selection → editorial.review → per-claim recover_citations/review → insights.stage → transactional sources.publish. Rebuild runs extraction and grouping, then replaces inside a checked transaction. Sources projects active groups and edits individual supporting records.

| Stage | Input → output; purpose/invariant | Repetition, failure, cost, removal decision |
|---|---|---|
| Archive/read/hash | Registered files → exact Markdown and source identity | Necessary deterministic provenance. Reading 31k characters is trivial; no PDF needed. Retain. |
| Candidate grammar/roster | Markdown → offset IDs, headings, turns | Necessary stable references and speaker boundaries; segmentation must not decide insight boundaries. Retain as anchors, not selection units. |
| Eager PDF attach | Every anchor + entire PDF → every page geometry and matches | Resolves genuine layout questions, but runs before knowing questions; 3.3s local in recorded two-section benchmark. Replace with requested layout only. |
| Distillation | Repeated 14k source windows → selected ID set | Repeats reconstruction's materiality judgment and transmits source twice. 11 requests/130,965 characters in recorded five-document replay. Remove. |
| Section reconstruction | Shortlist + overlapping context → readable cited propositions | Useful model task; arbitrary windows hide global facts/footnotes. 5 requests/103,614 characters recorded. Replace with document request, heading-bounded hierarchy for long sources. |
| Lexical number/unit guard | Statement + selected spans → rejection | FY2025/FY'25 and billion/B reject harmless notation, yet coincident digits do not establish meaning. Replace with Decimal notation normalization, keep independent semantic check. |
| Clarification | Invalid candidates → repaired selections | Repairs problems created by segmentation/schema, can amplify deterministic rejection. Replace with one document-wide targeted follow-up for actual uncertain support. |
| Independent review | Claims + selected references/layout → fidelity/readability/relevance | Protects material semantic support; 5 calls/21,980 characters recorded. Retain batched, increase coherent request size; no per-statement call. |
| Citation recovery | Each failed statement + retrieved source → repair → another review | Genuine missing support can be repaired, but call fanout is unbounded in claim count. Replace with one bounded batch + independent batch review, cache each useful operation. |
| Deduplication | Verified propositions + plausible library neighbors → cached pair judgments → complete-link groups | Necessary semantic judgment distinct from support verification. Retain conservative incremental implementation; lexical retrieval can miss paraphrases. No exhaustive pair calls. |
| Checkpoints | Historical section indices → state/accepted/rejected/repair arrays | Keeps obsolete partitions executable and duplicates accepted state. Replace with content-addressed operation artifacts and normalized verified work. Historical tables remain audit only. |
| Publication/rebuild | Verified propositions + complete group revision → atomic activation | Essential; no model/PDF work inside transactions. Retain narrow projection to published legacy schema, preserve correction conflicts as blockers. |
| Terminal | Progress/rejections → status/pagers | Automatic rejection pager leaks internals; remove. Only explicit review opens details. Approval waiting must suspend deadlines. |
| Cursor transport | Prompt → new read-only subprocess → validated envelope | Startup/auth probes once per command, subprocess each analysis. Retain supported backend; no credential/service change. Instrument process and provider-reported duration separately; queue/transmission/inference cannot be separated reliably with CLI result JSON. |

Recorded a076578 replay: 28 calls, 336,241 prompt characters; 13 fixture claims, 9 groups, 21 citations. These are hand-recorded decisions, not live accuracy or full-document completeness. Document 13 is frozen with eight passages; older checkpoints partition it into nine sections. Published data cannot be silently regenerated.

## Alternatives

1. Preserve sequential extraction/repair: rejected because repeated source transmission and section contracts survive, and repairs remain the main readability mechanism.
2. One unverified holistic answer: useful baseline, rejected for publication because exact offsets, independent support, resume and manual corrections are absent.
3. Unified selection/reconstruction plus independent batched review (selected): full short-document understanding with explicit reference IDs; logical selection and reconstruction share one request. Targeted follow-up only for failed/ambiguous support, then independent review. Group verified facts incrementally.
4. Always one giant request: rejected for long prospectuses/context and output limits. Heading-aware bounded sections receive compact global document outline; all anchors stay referenceable in targeted retrieval. This is a hierarchy, with residual cross-section completeness risk evaluated explicitly.

## Selected flow and requests

Read/hash once → exact anchors/global outline → unified materiality, atomic reconstruction and citation selection → deterministic identity/notation checks → only uncertain layout retrieval → independent batch review → one batched targeted correction for rejected/uncertain facts → independent review of corrections → complete verified document → incremental cached equivalence → atomic publication.

Short documents use one generation request, one verification request and zero or more batched grouping requests. Ambiguity may add one targeted correction and one review. The 3–5 call hypothesis is evaluated, never used to suppress facts. Long documents use heading-aware nonoverlapping sections under a configurable code-level context bound and shared outline, with bounded review chunks. No insight quota. Original text is sent once for selection/reconstruction, and selected evidence only for review. Boundaries do not restrict citations retrieved in follow-up.

## Domain and grounding contract

Immutable archive registration stays authoritative. New versioned staging separates exact anchors (hash/offset/text), verified propositions (wording/representation/attribution), support edges, review judgments and content-addressed operation artifacts. Existing published passages remain a compatibility projection consumed by Sources and revision machinery; do not rewrite them during migration. Topic edits remain per-passage, not group authorization. Preserve unmatched edits by blocking replacement. Existing manual split pairs remain in historical revision lineage; replacing anchors needs conservative conflict handling rather than silently forgetting splits.

Every source ID is resolved against Stock-owned exact spans. Headings, tables and footnotes are independently citable. Numbers normalize notation, not meaning: matching values never bypass semantic verification of metric, period, currency, basis or definition. Visual pointers/converter descriptions alone cannot support a claim. Missing optional PDF does not reject ordinary narrative. Ambiguous claims stay unpublished until specific layout evidence and independent review support them.

## Checkpoints, migration, errors

Versioned additive SQLite schema; protected SQLite backup and file manifest created before changes. No legacy section adoption by index. New artifacts key on contract, document/hash/metadata, operation and exact input, with payload checksum. Reuse completed generation and reviewed batches regardless of historical sections. Interrupted responses repeat only unpersisted external calls; exactly-once provider calls are impossible without provider idempotency. Historical state is retained, never silently reinterpreted. Rollback: restore protected disposable snapshot; production schema remains untouched until command invocation. Fresh work is a new contract, never deletion of historical evidence.

Only protocol errors receive one bounded format retry, sharing request deadline. Authentication, quota, timeout and deterministic evidence rejection do not retry automatically. Preserve artifacts before follow-up. Unverified or incomplete document work never publishes. Publication rechecks hashes/deadlines/snapshots. Review-only stores audit but never activates. Operator review suspends budgets. Structured logs contain exclusions; terminal stays compact.

## Evaluation and acceptance

Use disposable databases and real archived presentation 13, IPO prospectus, filing and transcript fixtures. Maintain expected information with exact supporting spans, material qualifications, period/metric and accepted readable wording. Test revenue FY2025/$5.1B/168%, correct EBITDA/margin, 43 active centers/date, conditional backlog definition, capex definition and multi-span products. Separate genuinely ambiguous mappings from supported narrative. Record omissions, unsupported facts, incorrect merges, readability and selected exact support, not only counts.

Replay same hand-recorded source decisions through a076578 and replacement; report serialized model requests/characters and local wall times. Compare holistic generation-only baseline separately; no replay timing is live latency. Sparse authenticated evaluation only in disposable storage, never full ticker or production document 13. CLI gives aggregate process time and optional provider duration/usage; absent provider data stays unknown. Test cold/resume/no-op, legacy isolation, corrections/splits, atomic rollback, rejected replacement, timeout, long source and quiet output. Full relevant suite plus review before commit/push.

Risks: model completeness and independent verification remain judgments; lexical grouping retrieval misses paraphrases; long documents need cross-section follow-up; text coordinates cannot resolve all charts. Acceptance requires working default workflow, fewer redundant requests, readable supported final statements, intact data/corrections and explicit reporting of all unmeasured or incomplete validation. No claimed live speedup without paired observations.

## Implementation rulings after review

Independent review found and fixed: explicit quarter normalization; scale-header scope for unrelated counts; ambiguity across separate numeric tiles and damaged table headers; original layout must match both source hash and contributing anchors. Period headers in transcripts are neutral exact context anchors, not attributed utterances. Replacement archives historical publication rows and blocks loss of manual split IDs. Correction changes/reset append an audit event. The short-document packer first tests the complete serialized source size, avoiding premature half-budget cuts. Large targeted evidence continues in bounded request batches rather than truncating later claims. Historical eager PDF/extraction helpers are now test-only; their section benchmark is retired. A new replay wrapper restores recorded layout after in-process tests.

Live validation did not return a response within 120 seconds; the complete fresh-model quality/latency and naive baseline comparisons remain acceptance work, not achieved results. See docs/knowledge-sort.md for measurements and a safe isolated validation command.
