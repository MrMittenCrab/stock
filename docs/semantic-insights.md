# Distinct investment evidence

Implemented on top of `17c710c`. The completed transport, PDF/layout caching,
checkpoint adoption, review reuse, citation recovery, deferred Cursor startup,
process cancellation and metrics repair remain in place. No production CoreWeave
extraction, replacement, group activation or archived-file changes were performed.
All verification used disposable databases and fixed offline judgments.

## Root causes and architecture

Selection used compact sections without document-wide materiality assessment.
Final deduplication compared exact wording, references and attribution. Sources
read passage rows, making counts passage counts. Editorial fidelity review alone
could not establish whether two passages contributed the same proposition.

`stock/distillation.py` adds a source-ID selection plan before reconstruction.
`stock/insights.py` adds a reversible semantic view over immutable evidence.
`source_semantic_cache` stores contract/content-keyed pair judgments.
`source_insight_revisions` stores append-only staged group/membership revisions,
canonical member IDs, pair reasons, material differences, full member snapshots,
manual-edit disposition and parent revision. `source_insight_heads` selects the
active revision per ticker. A staged revision has no effect until activation.
Original passage rows are never overwritten/deleted to consolidate display.

This deliberately uses SQLite/JSON and an inverted token index, with no vector
service, agent framework or new runtime dependency. Existing archived documents,
passage hashes/offsets/references, review results and representation types remain
authoritative. Frozen legacy evidence falls back to singleton insights until
explicitly reviewed. Legacy exact-source status is shown; grouping does not
upgrade it to independently verified editorial fidelity.

## Document distillation

Fresh Sort first selects potentially distinct material source IDs from bounded
source batches. It evaluates materiality, specificity, incremental information,
distinctiveness, factual support and qualifications. It then reassesses the
collected shortlist across sections before expensive reconstruction and independent
factual review. Empty selection is valid; short KPIs and reconstructable chart/table
facts are expressly eligible. Hundreds/thousands of shortlisted items require a
substantive selection-quality assessment rather than count truncation.

There is no hard passage quota. Cross-batch duplicate context contains only claims
already retained by preceding assessments. Thus two batches cannot each discard a
fact in favor of the other future batch. Selection reasons and exact IDs are cached
in `source_distillation` under `distillation-2`. New editorial checkpoints retain the
whole document plan, so partially completed resumes preserve selection scope.
Old completed/partial editorial checkpoints retain their original selections,
partitions, review fingerprints and repair state; they are not reinterpreted under
the new planning contract. Accepted old statements are grouped after verification.
Older scripted extraction clients without the new capability retain compatibility;
the real Cursor adapter and its deferred factory enable the new planning path.

Reconstruction requests ask for one material proposition per statement with its
inseparable qualifications. Fidelity, readability and investment relevance still
have independent review fields. Distinctness and material information preservation
are separate grouping judgment fields. No reduction in count bypasses those gates.

## Semantic grouping and safeguards

Retrieve up to eight plausible neighbors per statement using informative shared
terms. Union these bounded neighbor pairs, then batch judgments under a compact
14k-character comparison-data budget. Shared documents, statements and exact source
fragments are dictionary encoded once per request. A single oversized pair is left
separate with a visible uncertainty reason, rather than truncating its evidence or
sending an unbounded request. Exact wording with identical document, attribution,
date and exact support anchors can merge deterministically. Exact wording across
different sources still requires contextual comparison.

Model judgments compare entity, property/event/metric, reporting/as-of period,
actual/forecast/intention/uncertainty, business/geographic scope, units/definitions,
values/direction/magnitude, material qualifications and viewpoint. Both
`dimensions_agree` and `information_preserved` must be true, with no material
differences, before equivalence is accepted. Contradictory/incomplete judgments
fail closed. Every member pair requires direct positive equivalence; there is no
transitive closure. Group canonical wording is an actual member, preferring a
reviewed clear and concise statement. It never synthesizes a stronger claim.

Pair judgments classify repeated assertions, independent corroboration, unknown
origin or different claims. Management repetition across documents/executives is
not independent observation. The prompt requires explicit source evidence for
independence; a second publication alone does not qualify. All exact member
citations remain inspectable, so independent support adds evidence, not a second
visible claim. Cache fingerprints include source anchors, statements, attribution,
review and document context plus the grouping contract, excluding topic edits and
derived display fields. Resuming unchanged evidence makes no new judgments.

## CoreWeave before/after replay

Run:

```sh
.venv/bin/python scripts/verify_semantic_insights.py
```

The committed fixture contains actual exact excerpts from the Q4-2025 presentation,
Q4-2025 and Q1-2026 transcripts, Q1-2025 quarterly filing and IPO final prospectus.
The presentation KPI label/value mapping uses the existing recorded original-layout
fixture. Editorial wording and judgment responses are **hand-recorded test fixtures**,
not authenticated model outputs. This evaluates the pipeline under fixed judgments,
not live model accuracy or full-library quality.

| Before: supporting statements | After: visible proposition |
|---|---|
| Presentation: 850MW+ active power at December 31, 2025; Q4 opening: more than 850MW as of December 31; Q4 execution: year-end active power exceeded 850MW | One year-end-2025 active-power insight, three exact supports; repeated management assertions |
| Presentation: 43 active data centers; Q4 execution: ended the year with 43 active data centers | One year-end-2025 data-center-count insight, two supports |
| Quarterly filing: supplier-disruption risk in summary; same risk in detailed heading | One component-supplier disruption-risk insight, both exact offsets retained |

These remain separate:

- 11 data centers **added during** 2025 versus 43 active **at year-end**.
- Q1-2026 actual active power above 1GW versus year-end-2025 above 850MW.
- Actual capacity versus the target above 1.7GW by end-2026.
- Contracted power at year-end versus contracted capacity **expected online by
  end-2027**: the additional timing qualification is retained separately.
- IPO prospectus: sales/marketing expense growth and personnel-cost contribution;
  it is not equivalent to any infrastructure-capacity fact.

Additional regression cases cover inference scope versus overall demand, geography,
contradictions, forecasts, different periods, added exceptions, short numeric claims,
independent-corroboration classification, legacy support, exact matching, oversized
context, nontransitive judgments, filters, member edits and ungrouping.

## Information retained and measured requests

[Recorded replay metrics](benchmarks/semantic-insights.json): **13 support passages →
9 insights**, with all 13 passage records/references intact. The fixture expects nine
propositions; observed false merges: **0**; missed merges: **0**. All expected
material information remains in the member evidence; canonical text comes from one
member. This is a small fixed oracle replay, not a statistical estimate of factual
fidelity or model precision/recall. It cannot prove that unselected source material
contains no valuable information. Real proposals require substantive review.

The actual retrieval produced 45 plausible pairs, judged in **4 replayed Cursor
requests**, with 51,604 comparison-payload characters excluding prompt boilerplate.
Repeat staging made **0** new requests and reused all **45** decisions. An initial
implementation repeated full source data per pair (10 requests, 128,946 payload
characters on this same replay); dictionary transport reduced that implementation
workload by 60% of requests and about 60% of payload characters. This is not a
comparison with a prior semantic feature: none existed. The new selection prepasses
also add requests for fresh documents; no net live extraction speedup is claimed.
No authenticated requests or live latency/token/quality measurements were made.

## Preservation, UI and safe review

Ordinary Sort still freezes on success. It only groups the newly sorted document,
in the same publication transaction. A failed semantic stage does not freeze an
incomplete publication. Selective `--rebuild DOCUMENT` stages its target's proposed
groups, evidence and override transfer report before the existing REPLACE approval;
evidence and target group changes commit/roll back together. It does not regroup
other frozen documents. Existing rebuild reconciliation still blocks unmatched
manual corrections; old staging remains available for audit.

For an existing ticker, preview cross-document grouping without activating:

```sh
.venv/bin/stock sort CRWV.US --insights --review-only
```

This analyzes **existing published evidence only**, stages an audited revision and
opens the keyboard review pager. It does not re-extract archived documents or change
active Sources groups. To review and optionally activate:

```sh
.venv/bin/stock sort CRWV.US --insights
```

Only typing `REPLACE` activates. Stale evidence, topic edits or a changed active head
block activation. Declining/cancelling retains active groups and every evidence row.
The existing extraction rebuild remains:

```sh
.venv/bin/stock sort CRWV.US --rebuild 13
```

Review shows passage/insight counts, equivalent members with exact sources,
material differences retained, potential information-loss limitations and manual
edits with their disposition. Original published CoreWeave evidence has not been
deduplicated by this implementation session.

Sources displays a distinct total and per-topic insight/support counts. Counts
within different topics are memberships, not an additive distinct total. A group's
effective topics are the union of effective member topics. Unclassified includes
groups with any unclassified member. Each topic/file view restricts support to its
own eligible members and chooses canonical wording from that visible support.
Space expands all visible statements/citations, dates and grouping reasons. N/P
selects the explicit member used by T (topic edits) and O (source opening). Topic
edits affect that member only, with no inherited consent to propagate changes.
U ungroups by creating/activating another audited revision; it removes no evidence
or overrides. Historical group revisions remain. Rebuilding a document retains
other active groups and replaces only the target's group memberships alongside the
explicitly approved evidence replacement.

## Known limits

Lexical retrieval can miss paraphrases without shared informative words. Bounded
retrieval and complete-link safety can fragment large duplicate sets; unknown edges
remain separate rather than inferring equivalence. Existing composite multi-fact
passages are not automatically split: partial overlap is not full equivalence.
A terse statement lacking recoverable period/scope remains separate when uncertain.
Independent-origin classification and all semantic equivalence remain fallible
model judgments. UI/source review and reversible groups are safeguards, not proof.
Old partial selections remain reusable rather than being retrospectively distilled;
reviewing their post-verification groups does not remove all low-information prose.

## Regression evidence

The full project suite passed **305 tests** with
`.venv/bin/python -m pytest -q --basetemp=.data/semantic-final`.
A subsequently added semantic-head failure during selective rebuild passed its
focused rollback test, preserving both prior passages and the active head.
The independent reviewer reran all **28** semantic/distillation tests successfully,
including that additional test. Existing archive, citation-repair, checkpoint,
Sources, editorial and performance regressions passed in the full run.
