# Sort extraction diagnosis and repair

## Evidence and reproduction

Inspected `stock/sort.py`, `sources.py`, `sources_ui.py`, CLI, archive conversion,
existing Sources tests, all 13 archived CoreWeave Markdown documents, published
passages, and incomplete SQLite section checkpoints. Used SQLite's backup API to
create `.data/sort-diagnosis.sqlite3`; all diagnostic queries and authenticated
samples used this disposable copy. No full document or 13-document extraction ran.
Original PDFs/Markdown were not edited. Small source excerpts and checkpoint
reproduction cases are checked into `tests/fixtures/sort/` with source provenance.

At inspection, documents 2, 3, 5, 7, 8, 9, 10, 11 were frozen/completed. Documents
1, 4, 6, 12, 13 had 71, 1071, 422, 78, 0 accepted checkpoint passages respectively.
These are retained checkpoint counts, not published results.

| Demonstrated trigger | Consequence | Architectural correction | Regression |
| --- | --- | --- | --- |
| Prospectus section 29 repeats the derivative fair-value adjustment footnote inside one section | `Ambiguous quotation location`; document cannot finish despite 1071 accepted passages | Identity is document/hash/offset candidate ID, never a text search | `test_actual_checkpoint_failure_reproduction`, `test_repeated_identity_exact_offsets` |
| Q1 filing sections 13 and 16 select longer text overlapping previously accepted snippets | Whole document remains incomplete; retries ask for uncovered text and encourage fragments | Canonical candidate selections; duplicate IDs merge topics, overlapping contiguous groups reconstruct one exact interval | `test_actual_checkpoint_failure_reproduction`, `test_overlap_duplicate_distinct_claims` |
| Transcript Q&A mixes plain participant names, role lines, headings, images and page breaks | Last recognized heading belongs to another participant; valid Amit Daryanani questions fail | Whole-document name/role roster and explicit turn boundaries precede semantic classification; identity separate from category | `test_actual_checkpoint_failure_reproduction`, `test_turns_roles_unknown_and_page_heading`, `test_moderator_operator_and_unknown_identity` |
| Q4 presentation checkpoint records invalid JSON escape at character 1744, near a nested `passages` object after a Markdown heading | Protocol failure was retried through passage-error machinery; zero accepted | Compact ID-only response, strict JSON parser; protocol-only bounded retries, separate auth/quota exceptions | `test_cursor_compact_contract_and_invalid_escape`, `test_protocol_retry_resume_and_legacy_isolation`, `test_auth_not_retried` |
| Legacy prompt says “Include all substantive passages” and accepts financial footnotes, generic risk claims and isolated numbers | Hundreds of legally substantive snippets with low independent research value | Selective semantic criteria, deterministic exclusion of Markdown tables/images/role lines, coherent source groups | Real sample comparison below; `test_real_markdown_candidates`, `test_continuation_is_coherent_and_raw_table_excluded` |
| Published document 5 includes `Introduced                        \| Dedicated Inference` and `Introduced                        \| CoreWeave ARENA™` | Exact archived table fragments are unreadable in Sources | Exclude raw table candidates; preserve existing frozen evidence; no fabricated prose reconstruction | `unreadable-table.md`, `unreadable-evidence.json`, source-candidate regression |
| Prospectus page break separates `We` from `believe we are in the early stages...`; metric values can follow a separate bold/heading label | Valid source offsets alone do not guarantee readable evidence | Join directly contiguous unfinished paragraphs; bind metric labels to their adjacent values using exact original spans | `test_continuation_is_coherent_and_raw_table_excluded`, `test_metric_label_stays_with_value` |
| Legacy incomplete checkpoints have no new candidate protocol | Reusing them would mix text-search and source-ID work | Separate `source_work_v3`, explicit payload version, hash-bound resume; retain legacy rows | `test_protocol_retry_resume_and_legacy_isolation`, `test_checkpoint_integrity_failure` |
| Blocking subprocess collection and line-by-line document messages hide long waits | Liveness and progress indistinguishable; interruption handling implicit | Single terminal status line with stage/section/elapsed time and explicit child state; kill process group on interrupt/timeout | `test_status_timer_and_child_cancellation`, `test_interruption_preserves_completed_v3_section` |

The overlap reproduction checks the rejected passage against accepted checkpoint
intervals. Validation of a rejected quote alone does **not** reproduce this failure:
the conflict depends on prior accepted state. Filing conflicts were 2 and 1 prior
intervals; the four Q4 transcript overlap cases intersected 1, 1, 2 and 2 intervals.
The transcript speaker errors and prospectus ambiguity reproduce through the
legacy validator against the original section/context.

The original complete malformed Cursor response was not retained in SQLite. The
checkpoint retains only its error and nearby characters. The invalid-escape class
is reproduced using that shape in a synthetic JSON envelope, not claimed as an
exact replay of a missing response. There is no speculative JSON repair.

## Source quality versus rendering

The document 5 table fragments match their archived Markdown offsets exactly.
The source table itself interleaves chart columns and visual labels. Extraction
selected partial rows; Sources then displays the stored string literally using
Rich `Text`. Rendering did not invent those words or columns. A cosmetic renderer
cannot recover missing prose or repair chart reading order. No archive conversion
was rerun: this repair excludes those source structures instead.

Some older evidence has PDF character offsets in `start/end` and separate
`markdown_start/markdown_end`; treating the former as Markdown offsets falsely
suggests corruption. The repair leaves those frozen citations intact. New records
always identify archived Markdown characters (UTF-8 BOM excluded, CRLF preserved),
with its byte SHA-256 and original archive reference. Repeated wording at different
locations stays distinct. No guessed PDF page is attached.

## New contract and state

Stock constructs nonoverlapping Markdown paragraph/sentence candidates globally,
including section, source hash, original reference and roster-backed turn identity.
Batches carry bounded source context. Cursor supplies `selections`, containing only
`ids`, fixed topic memberships, category and supported speaker name/null. It cannot
supply source quotations. Selected contiguous groups must share section/turn and
cannot jump excluded source blocks. Duplicate IDs union topic votes; overlapping
groups merge exact contiguous intervals. Adjacent independently selected claims
remain distinct. Conflicting speaker decisions receive a targeted ID decision.

Each response is checkpointed before targeted clarification. Protocol failures get
at most two retries; only rejected, known IDs are clarified. Unresolvable candidates
are excluded and recorded in audit state, without discarding valid evidence.
Completed sections are not requested again. Authentication and quota exceptions
stop further document calls. Transport failures and exhausted protocol retries
leave the section incomplete; source hash/offset/checkpoint integrity failures are
fatal. Resumed quotations are verified and reconstructed from archived text.

The legacy extraction/validation helpers remain for failure reproduction and the
existing citation tests; the CLI routes through the v3 implementation. Legacy
checkpoints are never consumed by v3 or deleted by ordinary publication.

Ordinary sort skips frozen completed documents before creating Cursor. Rebuild
stages v3 work while retaining published evidence and obtains a per-database,
per-document OS lock. The review prints old/new counts, basic readability indicators,
representative exact quotations, transferable overrides, and unmatched corrections.
These indicators are not semantic quality scores. Review output remains visible
while the terminal timer is suspended. Approval requires typing `REPLACE`.

Rejection, interruption and failure do not change published rows. Unmatched manual
corrections block replacement pending explicit reconciliation; the implementation
does not guess a semantic match or silently drop them. Exact source hash/offset/text
matches preserve overrides. After approval and re-verification, one SQLite
transaction replaces only the selected document's passages, original topics,
overrides and completion record. A failing insertion rolls back deletions as well.
Successful replacement clears that document's new staging checkpoints, allowing a
future rebuild to make fresh decisions. Other documents and legacy audit rows stay
unchanged. `--reset` still only removes overrides and restores frozen topics.

```sh
stock sort CRWV.US --rebuild 13
# or an unambiguous archived filename:
stock sort CRWV.US --rebuild 2026-02-26--presentation--Q4-2025.md
```

## Authenticated sample evaluation

`agent status` succeeded. Seven bounded calls tested four document types and then
rechecked presentation/prospectus quality findings. Responses and exact source spans
were inspected locally under `.data/sort-v3-smoke*.json`; nothing was published.

| Sample | Legacy checkpoint passages overlapping reviewed source range | New sample result | Assessment |
| --- | ---: | ---: | --- |
| Q4 presentation opening disclosures/positioning | 0 | Initially 2 of 12 candidates; tightened criteria: 0 of 6 | Initial generic leadership/platform claims were weak. Zero for disclosures and slogans is appropriate; it does not imply a zero-result presentation. |
| Q4 presentation financial results | 0 | 4 selections from 11 candidates | Revenue/demand and net-loss commentary recovered. Also exposed a value without its EBITDA label and chart residue. Metric-label segmentation subsequently fixed and regression-tested; chart contamination remains a source-quality concern. |
| Q1 SEC filing excerpt | 11 | 1 of 8 | Selected IPO-related stock-compensation expense, retained its qualifications; omitted surrounding stock-plan mechanics. |
| Q4 transcript prepared remarks | 8 | 5 of 8 | Named Michael Intrator correctly; retained older-GPU pricing/inference demand, capacity allocation, customer diversification and backlog context. Some repeated management positioning remains judgment-dependent. |
| IPO customer/growth sections | 35 initially, 34 in revised covered range | Initially 4 of 7; revised 2 of 4 | Source continuation fixed the customer-concentration quote. Revised output retained coherent customer concentration and growth qualifications. |

These are small, deliberately chosen samples, not recall/precision scores or full
document counts. IPO candidate filtering covers separated source sections; the
legacy count refers to the bounding reviewed range, so it is **not** an equal-input
reduction statistic. Fewer passages alone does not establish better quality.
The metric-label and moderator refinements after these calls have synthetic/real
fixture regressions, not another broad authenticated evaluation.

## Remaining limits

- Semantic relevance, redundancy across distant sections, and topic/category
  judgments still depend on Cursor. Stock can prove source identity, not usefulness.
- The Markdown reader deliberately uses a small paragraph/heading/role grammar,
  not a complete CommonMark parser. Unusual table formats, sentence abbreviations,
  very long indivisible sentences and novel transcript layouts need more fixtures.
- Batch boundaries can limit context grouping. No cross-document semantic dedupe
  occurs; repeated wording at separate locations is intentionally not collapsed.
- Identifiable non-transcript quoted individuals are conservatively left unnamed
  unless supported by Stock's context. Roster categories cover common executive,
  analyst and media roles; moderator category still requires contextual judgment.
- Strict override transfer can block a useful rebuild when legacy PDF-derived
  text differs from Markdown typography. Reconciliation is manual; no fuzzy match.
- A crash after Cursor has answered but before the response checkpoint commits can
  repeat that last call. Completed persisted sections are reused; exactly-once
  external calls cannot be guaranteed without provider request idempotency.
- The lock protects rebuilds made through Stock on the same filesystem. External
  direct database/file edits are detected where hashes/snapshots permit, not locked.
- Existing frozen poor evidence is preserved. The live archive has not been re-sorted.

## Validation and preservation result

Final command: `.venv/bin/pytest -q` — **210 passed in 51.52s**. This includes
legacy failure/citation tests (explicitly using the legacy extraction helper),
26 new contract/rebuild/process tests, and existing Archive, Sources, Price,
Search/core/UI tests. `git diff --check` and Python compilation also passed.
`stock sort --help` exposes both document rebuild and topic reset.

Compared every live database table's rows with the initial SQLite backup after
implementation and testing: unchanged. Rehashed every registered archive file:
all matched stored provenance. No live extraction, rebuild approval or publication
occurred. Diagnostic databases, account output and full smoke response logs remain
local and ignored by Git.
