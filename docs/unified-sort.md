# Unified Sort measurements and limits

Normal `stock sort TICKER` distills material source IDs, reconstructs statements,
independently verifies facts, compares propositions in batches, and publishes exact
evidence together with its complete semantic view. Frozen evidence receives reversible
view updates automatically. Current evidence/grouping performs no Cursor work and
creates no revision. `--review-only` previews all pending documents together without
publishing or activating; `--rebuild DOCUMENT` retains exact REPLACE approval.

The change extends origin/main `bbbcbac`; it adds no service or runtime dependency.
The second document shortlist assessment repeated materiality/distinctiveness work
already assigned to distillation, reconstruction and semantic grouping. Removing it
retains independently verified supporting evidence rather than deleting repetitions.
Cached pair judgments and direct complete-link grouping preserve period, forecast,
scope, qualification and contradictory-claim distinctions. Manual topic edits and
historical manual ungrouping survive updates. Unchanged evidence does not schedule
new uncached old-versus-old comparisons merely because another document arrived.

## Paired offline replay

Run `.venv/bin/python scripts/benchmark_unified_sort.py` from this repository.
Both workers use the same committed CoreWeave presentation, filing and transcript
excerpts, canonical paths, IDs, exact hashes, recorded materiality selections,
reconstructions, independent factual reviews and proposition judgments. Baseline
code is extracted into `.data`; databases and all publication are disposable.
The previous interface includes its separate cross-document grouping stage.
The replay exercises actual prompt serialization, validation, checkpoints and
transactional publication; it is not a measurement of live model latency/accuracy.

| Stage | Requests before / after | Prompt characters before / after |
|---|---:|---:|
| distillation | 16 / 11 | 153,017 / 130,965 |
| reconstruction | 5 / 5 | 103,614 / 103,614 |
| review | 5 / 5 | 21,980 / 21,980 |
| within-document grouping | 4 / 2 | 29,241 / 12,164 |
| cross-document grouping | 4 / 5 | 55,240 / 67,518 |
| citation recovery | 0 / 0 | 0 / 0 |
| Total | 34 / 28 | 363,092 / 336,241 |

This is 17.6% fewer requests and
7.4% fewer prompt characters.
Cross-document batches can also contain within-document pairs; a batch with any
cross-document pair is counted in that row. Reconstruction includes source selection.
Citation recovery requires zero calls on these supported fixtures; its rejection,
repair, re-review and interruption behavior is covered by focused recorded tests.

Cold local wall time: 0.350s → 0.246s.
Resumed local wall time: 0.0100s → 0.0026s;
both make **zero** resumed model requests. Local timing includes SQLite, source
parsing, validation, serialization and immediate replay responses. It excludes model
service time and does not establish a live speedup. Actual token usage and live
service latency are unavailable and remain null.

Both retain **13 useful recorded claims, nine distinct insights, four consolidated
duplicates and 21 exact citations**. Exact statement/reference text, offsets and
Markdown hashes match before/after. No golden claim is missing and no materially
different golden propositions merge. This cannot establish completeness for all
unselected source material or precision/recall of new live judgments.

## PDF and checkpoint regression

The existing presentation benchmark was rerun against `bbbcbac` using two identical
historical sections, a read-only production archive connection and disposable staging:

```sh
.venv/bin/python scripts/benchmark_sort.py --baseline bbbcbac
```

Both retain 17 statements with identical exact references and attribution. Both use
one selection and two factual-review calls cold (71,921 prompt characters), then
zero calls and zero PDF reparsing on resume. Cold local wall times were 3.200s / 3.441s,
including 3.085s / 3.316s PDF parsing; resume was 0.038s / 0.042s. This confirms the
completed efficiency repair remains intact; no additional PDF-speed gain is claimed.
Preparation caches remain keyed by original hashes and validated checksums. Full-page
provenance is retained locally; bounded relevant geometry is transported to reviews.

## Limits, diagnostics and safety

Defaults: 720 seconds/document, 1200 seconds/command, 12 Cursor requests/document,
120 seconds/request. CLI overrides: `--document-seconds`, `--command-seconds`,
`--cursor-requests`, `--request-seconds`. A grouping-only run uses one document-sized
Insights scope. Startup/probes, PDF children and model calls use the smaller remaining
deadline; protocol retries share their original request deadline and count toward
the request cap. No automatic timeout retry runs. Child process groups receive TERM,
with up to three seconds of cleanup before KILL. Publication and activation recheck
deadlines inside their transactions. Operator-controlled review waits suspend progress;
elapsed review time counts, and expiry blocks subsequent publication.

Limits retain completed plans, selections, accepted reviews, citation repairs and
semantic decisions; no partial evidence or grouping activates. Repeat the displayed
resume command. The terminal prints only compact middle-dot progress and a final
summary/log path; detailed events and native model usage, when supplied, stay in local
JSONL/SQLite diagnostics. No new font, colors, framing or mouse interaction was added.
`TERMINAL_RENDERING_HANDBOOK.md` was absent from this repository; the supplied rendering
rules and existing native terminal conventions were followed.

Retrieval is bounded to eight lexical neighbors per statement, using at most 12 terms
and 128 postings per term, plus previously verified group-member pairs. Comparison
payloads are batched under 14,000 characters and commands/documents impose request
caps. No globally repeated model analysis is required for unchanged archived evidence.
Lexical retrieval may miss paraphrases. Nonretrieved, oversized or otherwise uncertain
pairs remain separate; oversized/unchanged uncached candidate reasons are audited.
Dense archives may pause and need another invocation. No equivalence is inferred just
to fit a budget, and no arbitrary insight quota is imposed.

One disposable legacy transport test reached Cursor when the runner changed and its
old mock no longer intercepted it. The mock boundary is corrected. That response is
excluded from all benchmark measurements; no live service latency/token claim is made.
No complete live archive extraction or production evidence rebuild was performed.

Read-only preservation checks confirm all **1,796 published passages**, frozen topics,
manual overrides, sorts and historical checkpoints unchanged against existing protected
hashes/pre-repair snapshots. All **197 registered archive files** match their unchanged
registered hashes. Document 13 still has its original **eight** passages. Production
has no new semantic/cache tables, groups or revisions from this work. The parent
stockpile repository was not modified.

See [machine-readable measurements and preservation checks](benchmarks/unified-sort.json).

## Validation

Final focused run: **222 passed** (124.80 seconds). It covers unified extraction and
grouping, replay quality/citations, no-op completed Sort, combined review-only previews,
exact REPLACE approval, all budgets, PDF probe deadlines, child cancellation,
checkpoint/cache resume, historical manual splits, topic corrections, stale ticker-wide
rebuilds, transaction rollback and compact quiet terminal output. Relevant archive
and conversion regressions also passed.

```sh
.venv/bin/python -m pytest -q tests/test_sort_budget.py tests/test_distillation.py tests/test_sort_efficiency.py tests/test_insights.py tests/test_evidence.py tests/test_editorial.py tests/test_sources.py tests/test_archive.py tests/test_archive_conversion.py --basetemp=.data/unified-delivery-final
```

Next normal command: `.venv/bin/stock sort CRWV.US`.
