# Document 13 reconstruction timeout investigation

The 300-second request deadline expired as configured. The underlying provider
latency cause remains unknown. A timeout alone does not establish excessive input.
The smallest repair retains source coverage, reasoning instructions, batch planning,
independent verification, semantic grouping, publications and checkpoint identities.
No deadline defaults changed. No production rebuild or provider diagnostic ran.

## Evidence

Inspected `.data/sort-logs/27b823a891af44fd9d51b0d2f6f19330.jsonl`, the
production knowledge_attempts/artifacts/source_model_calls records, Archive evidence
versions and original successful `.data/knowledge-validation-ky0xq3ej/result.json`.
All extraction reconstruction used SQLite backups. Cursor's subprocess runner was
replaced with an offline recorder returning empty structured selections; no prompt
was sent to Cursor. Detailed prompts remain local under `.data/timeout-audit-*`.

Rebuild selects latest *candidate* evidence version 4, not the currently published
Markdown. Archive validation succeeded: 24 pages, 60 supplemental regions (58 native
PDF, two local OCR), prepared_with_visual_limitations. Original PDF SHA-256:
`db716980ae8eb4eddda477d43ef2cead98419f6fa4fbec8e37ff643a98b6cbf6`;
candidate Markdown SHA-256:
`076d1db0eedd0e4ca5e7d3c1f830576df8e07d92f7e80da638a39555e8219336`.

The first reconstructed operation matches the failed attempt's exact input identity
`87ad8a3da2ee6feaad20db5442fb6102769e6e09a9b0e4805bb83aa070bb4178`
and recorded 67,048 characters / 67,232 UTF-8 bytes. There is one failed understand
attempt, no successful document-13 knowledge artifacts in production for reuse.
Historical work remains untouched.

First request composition (original serialization):

| Component | Characters |
| --- | ---: |
| Instructions | 4,249 |
| Candidate array: 135 exact anchors, including metadata and primary flags | 35,060 |
| Context | 27,703 |
| Outer payload framing | 36 |
| Total | 67,048 |

The candidate text itself is 11,829 characters. Context comprises document metadata
2,150; outline 10,576 (99 distinct anchor identities); original PDF layout 14,781
(two distinct pages, 5 and 6); Archive quality 123; and JSON field/framing overhead.
Layout and outline occur once per request. Each of four batches shares the same
global context: 110,812 serialized context characters in aggregate, 83,109 beyond
the first copy. This is independent-request context, not demonstrated removable
redundancy. Some headings also occur as exact source anchors; outline identities
preserve global navigation and source anchors preserve exact evidence. Neither was
removed. No duplicate page objects exist in this first context.

The four batches contain 135 / 89 / 138 / 9 anchors (371 distinct, nonoverlapping
IDs), with source text lengths 11,829 / 12,572 / 8,873 / 1,556. The previously
successful knowledge-1 input had 135 anchors and 30,779 source characters in one
understanding request, without initial layout. The new candidate has 34,830 source
characters and more granular recovered regions. More anchors and metadata do not
imply proportionally more substantive information.

## Diagnosis and limits

The command reached selection after 2.09 seconds. Its Cursor call lasted 297.77
seconds and the command paused at 302.15 seconds. Request accounting begins before
lazy Cursor startup/authentication; that consumes part of the 300-second deadline.
This explains the slightly shorter model subprocess interval, not the long wait.
The stored response count is zero, but old instrumentation discarded partial
subprocess output on timeout. Zero therefore does not prove no generation occurred.
There is no provider timing, usage, queue or progress telemetry for the failed call.

The successful extraction took 650.57 seconds over five new requests; the first
understanding request took 205.71 seconds (58,140 characters). Another successful
request was 113,213 characters and took 199.23 seconds. Input size does not establish
latency or failure. Successful first-call usage included 25,408 cached tokens;
failed-call cache usage is unknown. Different contract, source recovery, model/cache
state and provider load confound any direct speed comparison.

Evidence supports increased total planned workload and a provider call that outlasted
its configured allowance. It does not distinguish queue/transport waiting from slow
or stalled model generation. Quick successful startup checks weigh against a gross
startup/authentication failure; they cannot rule out later transport trouble.
No subprocess timeout-control defect was reproduced. A bounded local subprocess
regression confirms timeout, partial-output accounting and process termination.
No live probe was necessary: a small successful probe would not explain this large
historical call, and replaying it would risk another expensive inconclusive timeout.

## Repair and measurements

JSON separators now omit formatting spaces outside string values. All four parsed
payloads, instructions, source strings and operation identities were compared for
exact equality before/after. Global context and batching remain intact.

| Batch | Before characters | After characters |
| --- | ---: | ---: |
| 1 | 67,048 | 64,131 |
| 2 | 64,925 | 62,288 |
| 3 | 65,871 | 62,978 |
| 4 | 35,220 | 33,869 |
| Total reconstruction | 233,064 | 223,266 |

This saves 9,798 characters (4.2%) of formatting overhead, with no demonstrated
live latency improvement. Full-document total previously included 339,426 input
characters across extraction, repair and review; comparing that total with only
new reconstruction would be misleading. New reconstruction requires four calls;
independent verification, uncertain-claim repair and semantic grouping add a
response-dependent number. No defensible total latency forecast or request-count
upper bound below the configured budget follows from these records. As a planning
scenario only, four calls at the old first-call latency plus the old remaining
verification/repair time would take about 21 minutes before additional grouping.
This is not an expected time estimate; current service latency may differ greatly.

Diagnostics now record prompt hash, instruction/component sizes and anchor count.
Timeout records add effective subprocess deadline, elapsed time, partial stdout /
stderr byte counts and termination return code, without output contents. Nonbudget
subprocess errors no longer interpolate the command (which contains the prompt).
Resume commands shell-quote document names and preserve all four configured budget
values, so an explicit 300-second request deadline no longer silently becomes 120.
Historical logs did not retain all invocation arguments; those cannot be recovered.

Strategic coverage remains unchanged by this repair, established through exact
payload equality and recorded regressions. Live semantic completeness of the newly
recovered Archive version still requires a successful extraction and independent
review; it is not claimed here.

## Validation and next rebuild

Focused command: `pytest -q tests/test_sort_efficiency.py tests/test_sort_budget.py
tests/test_knowledge.py tests/test_knowledge_inventory.py tests/test_strategic_commentary.py`
— initially 76 passed in 21.40 seconds. Review removed one redundant JSON
round-trip test and strengthened source-whitespace coverage. That test initially
used an incompatible claim fixture; after correcting the fixture, the final affected
file passed all 15 tests in 1.30 seconds; the other 60 focused tests passed in the
preceding run (75 distinct final tests covered). The original new compaction and
resume tests failed before the implementation fix. Offline `scripts/evaluate_strategic_commentary.py` retained all 24/24
recorded propositions with exact references and independent review; live recall
remains unmeasured. No full suite repeated. Machine measurements are in
[the benchmark](benchmarks/cursor-timeout.json).

For a deliberate next real rebuild, use explicit allowances and retain interactive
replacement review:

```sh
stock sort CRWV.US --rebuild 13 --request-seconds 600 --document-seconds 3600 --command-seconds 4800 --cursor-requests 24
```

These are opt-in operational allowances, not new defaults or a completion promise.
They allow the larger observed workload without altering the analytical task.
Inspect the complete proposed evidence before deciding whether to replace anything.
The investigation did not run this command or approve any replacement.
