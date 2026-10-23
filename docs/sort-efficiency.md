# Stock Sort workflow profile and repair

Measured on archived CoreWeave Q4-2025 presentation (document 13), against baseline
`b3b311d`. No production rebuild, authenticated Cursor invocation, publication or
archive conversion was performed. Document 13 still has its eight original published
passages. Hash comparisons confirm unchanged passage/topic records, all manual topic
overrides, historical staging, and archived document-13 files. The parent repository
was not modified.

## Demonstrated bottlenecks

The actual archived Markdown is 31,048 characters, with 135 canonical spans and a
24-page PDF. Baseline batching budgets serialized local provenance, rather than the
source data needed by the model. Nine primary batches of 14/18/12/24/19/17/14/13/4
spans become 199 transmitted spans after neighboring context is added: 64 repeated
span transmissions. Selection prompts alone total 367,974 characters, from 33,596
to 66,668 per section. Original paths, source hashes, offsets, and visual provenance
are repeated on every candidate. Review repeats provenance and exact source text
for every reference and receives the entire section's matched PDF pages again.

Normally the old path makes one selection and one independent review per nonempty
section: 18 analysis calls for nine sections, before any retries or clarification.
An empty selection requires no review. Each selection, deterministic clarification,
and review can make three protocol attempts, independently. Timeouts were also
misclassified as protocol errors, allowing three 600-second waits for one operation.
The constructor additionally runs help and authentication checks; it used to run
before completed staging could be inspected.

The persisted document-13 state contains three completed sections (23 accepted
statements and eight exclusions) plus one staged selection response. These imply
at least eight successful selection/clarification/review calls so far; the old code
retains neither attempt counts nor durations. It is impossible to reconstruct exact
historical call counts, token usage, selection-versus-review model latency, or total
live wall time from those checkpoints. No guessed latency is presented as a
measurement.

An initial combined PDF extraction/matching measurement was 2.53 seconds. The
repeatable paired benchmark below isolates parsing and normalization. Baseline
normalizes the same page text for every candidate/page comparison, reparses the PDF
on every resume, and only deduplicates editorial passages after reviewing them.
Completed sections are reusable under the same contract, but partial multi-statement
reviews and citation repairs previously had no granular resume state. Rejections
from semantic review had no missing-citation recovery at all.

## Changes

- Keep canonical document/hash/offset IDs and complete local provenance. Transport
  only IDs, exact text, roles, speaker/turn, section, page and selection scope. Review
  uses a source-ID dictionary, sending each shared exact reference once per call.
- Budget fresh batches by this compact transport. The actual document now plans
  four primary batches (37/41/41/16 spans), rather than nine. This is a measured
  deterministic partition change, not a claim that a whole document needs eight
  model calls: review batching depends on the amount of selected evidence.
- Cache original PDF extraction by source hash and extraction version, and unique
  page matches by source hash and candidate identity/text. Normalize each page once.
  Cache payloads have checksums; malformed caches are recomputed. Full source-file
  hashes are still verified before staging and publication.
- Reuse layout neighborhoods locally. Selection receives relevant lines with their
  unchanged coordinates, neighboring lines, headers, qualification lines and bottom
  notes. Review receives layouts relevant to its selected references. Partial scope
  is explicit; missing material context requires unresolved fidelity. Page matching
  is never treated as proof of label/value association or chart meaning.
- Keep independent semantic verification of every new editorial statement. Bound
  review batches, persist completed review batches, deduplicate exact duplicates,
  and reuse intact accepted fingerprints. Different statements over the same source
  still require judgment.
- Version staging as `v4-editorial-2`. Adopt compatible `v4-editorial-1` states into
  new records, retaining original partitions, accepted reviews, classifications and
  historical audit. Never reinterpret old section numbers using the new partition.
  For this already-staged document the next rebuild therefore retains nine sections
  and reuses completed work, rather than starting over with four fresh sections.
- Persist corrected selections before their review, and persist each repair outcome.
  An interrupted or protocol-failed repair review resumes from the corrected
  selection. It cannot mark unreviewed work complete. No completed accepted statement
  is reviewed again merely because another statement needs correction.
- Authenticate/start Cursor only when a model request is necessary. Only malformed
  JSON/schema errors receive bounded protocol retries; process errors/timeouts stop
  with staged work retained. Authentication and quota errors still stop immediately.
- Record every Cursor analysis attempt, including failures, in `source_model_calls`:
  document/section, operation, outcome, prompt characters/UTF-8 bytes, response
  characters, wall time, reported durations and native usage when supplied. Absent
  model durations/token usage remain null, never character-count estimates.
- Show document, section/total, stage elapsed, total elapsed and child state. A live
  child is explicitly waiting with progress unknown; liveness is not progress. Pause
  rendering for the keyboard pager and replacement approval. Ctrl+C still terminates
  the child process group and retains staging.

## Citation recovery and publication quality

For a semantic `unsupported` or `unresolved` judgment, retain the reviewer's precise
missing-elements explanation. Deterministically retrieve original references,
neighboring spans and lexical matches from the same document/turn under a bounded
context budget. Make at most one targeted correction request for that statement.
The model must explicitly choose genuinely supporting IDs and correct or narrow the
text; retrieval never automatically adds a citation.

Resolve the correction against exact archived characters, numeric/unit guards and
attribution/turn rules, then independently review only that corrected statement.
Keep its supplied layout in the review fingerprint. Exclude a failed correction
with its reason, retrieved IDs, attempt count, rejected proposal and errors in the
audit. Protocol failure during review preserves pending corrected work rather than
accepting it. Readability/relevance-only rejections do not trigger citation searches.

The exact source-anchor and intact supported-review publication gates remain in
force. Atomic selective replacement, override transfer/blocking, lock protection,
source classifications and frozen legacy citations remain unchanged.

## Paired measurements

Reproduce from the project root:

```sh
.venv/bin/python scripts/benchmark_sort.py --baseline b3b311d
```

The script reads the production archive/checkpoints through a read-only connection,
extracts baseline code into a temporary directory, and stages both workers in
disposable databases. It never runs Cursor or publishes. Both paths cover the same
first two original primary sections (32 primary spans), using the same recorded
supported selections and independent review decisions. The new path combines the
selection workload into one batch while keeping two bounded review calls. It verifies
identical final statements, exact IDs/references and attribution, and validates every
publication gate. Deliberately unsupported evidence and recovery are evaluated by
separate deterministic regression tests, not rubber-stamped for this benchmark.

| Metric | Baseline | Optimized |
|---|---:|---:|
| Selection / review calls | 2 / 2 | 1 / 2 |
| Total model requests (replayed) | 4 | 3 |
| Prompt characters | 161,425 | 71,447 |
| Response characters | 24,540 | 16,593 |
| Accepted statements / exact citations | 17 / unchanged | 17 / unchanged |
| Cold local wall time | 3.292s | 3.243s |
| Cold PDF parsing time | 3.082s | 3.127s |
| Cold layout preparation incl. parsing | 3.209s | 3.140s |
| Normalization time incl. context preparation | 0.111s | 0.0067s |
| Resume local wall time | 3.261s | 0.040s |
| Resume PDF parsing | 3.108s | 0s |
| Resume model requests | 0 | 0 |
| Live model processing / total live wall time | Not measured | Not measured |
| Actual model tokens | Unavailable | Unavailable |

These demonstrate 25% fewer requests and 55.7% fewer prompt characters on identical
material, plus avoided parsing on resume. Cold local runtime is effectively unchanged
within ordinary timing variation. Local replay wall time includes actual PDF parsing,
matching, serialization and SQLite staging, with immediate deterministic responses.
It is **not** a measurement of live model speedup. Fewer requests and smaller prompts
should reduce service time/usage, but that remains an expectation until real attempts
are recorded. Full per-call volumes and timing fields are in
[the benchmark record](benchmarks/sort-efficiency.json).

Remaining limits: deterministic lexical retrieval can miss paraphrased support;
uncertain visual mapping still needs sufficient original PDF geometry; accepted
fingerprints reuse identical statements, not merely similar prose; bounded review
may require several calls for a dense section. Independent one-shot Cursor requests
still need their own factual source context; no cross-request context-cache hit or
semantic-quality improvement is assumed. The benchmark proves replay equivalence,
not that new live model judgments will be identical.

## Verification and next safe rebuild

Final verification: **278 tests passed**, including citation addition/narrowing gates,
unsupported exclusion, unit/currency errors, original chart geometry, transcript turns,
checkpoint adoption, interrupted batch/repair review, failed review protocols,
accepted-review reuse, deferred Cursor startup, child cancellation, atomic rollback,
manual corrections and Sources UI regressions. One earlier overlapping test invocation
collided with pytest's shared `.data/test-tmp`:
`tests/test_sources.py::test_strict_validation[change3]` lost a temporary source file.
The clean final suite used an isolated base directory and passed:

```sh
.venv/bin/python -m pytest -q --basetemp=.data/sort-efficiency/final-tests
```

The eight published passages were not rebuilt or changed. When ready to perform the
real staged rebuild in an interactive terminal:

```sh
.venv/bin/stock sort CRWV.US --rebuild 13
```

This adopts compatible staging, reuses accepted work, attempts bounded recovery of
existing factual exclusions, and continues remaining sections. Inspect the full
proposed evidence and unresolved audit. Published evidence changes only after typing
`REPLACE`; declining or cancelling retains the existing eight passages. Do not reset
or delete checkpoints first.
