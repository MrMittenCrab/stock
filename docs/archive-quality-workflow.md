# Archive preparation and interview evidence

Archive now checks PDF conversion before registering prepared evidence. It reads
native text blocks in their original content-stream order, compares normalized
meaningful words and short content anchors against Markdown, records individual
missing regions even when aggregate recall is high, and flags damaged numeric or
column ordering. Repeated short margin headers/footers are recorded separately.
Markdown formatting and footnote syntax are normalized before comparison.

Unpaginated legacy Markdown is aligned using unique native content anchors; pages
without sufficient anchors explicitly record an unresolved alignment and use the
whole output for a conservative omission check. The diagnostics are heuristics,
not a completeness or visual-fidelity certification. A page's reported word recall
is the **baseline before recovery**, not a post-repair score.

Missing native regions are appended verbatim to a new evidence Markdown version,
with explicit `native_pdf_region` references, PDF page, block identity and bounding
box. Original conversions and their offsets stay intact. Coordinates never create
an inferred label/value relationship. Transcript supplements do not inherit the
last Markdown speaker. The original PDF remains authoritative.

Only observed empty/image-only pages or damaged reading order request balanced,
forced local Marker/Surya OCR. Each preparation attempts at most three individual
pages, once each, with a 180-second / 8 GiB sampled-RSS bound per page. OCR is offline,
uses installed weights, blocks non-loopback inference in the worker, and disables
optional Marker LLM processors. Successfully completed per-page work can be reused
after interruption. Equivalent completed repair candidates are reused. No blanket
full-document forced OCR or cloud OCR is introduced. Ordinary digital transcript
numeric prose does not trigger layout OCR; missing native text is recovered first.

The versioned `stock.archive.evidence` manifest ties Markdown offsets and native/
OCR regions to the original hash, converter/runtime settings, OCR versions and
page-level diagnostics. Marker metadata/page statistics are retained when present.
Legacy baseline settings cannot be reconstructed if they were never recorded.
Visual diagrams and uncertain relationships remain explicitly unresolved evidence
in the preserved original PDF. Images alone do not justify an invented description.

Archive retains compatible `conversion_status` fields and adds evidence quality:
`prepared`, `prepared_with_visual_limitations`, or `needs_repair`; failed conversion
retains `failed`. The Archive terminal displays the quality status. Visual warnings
allow ordinary text extraction; missing unreadable pages retain a repair status.

Sort requests missing/failed preparation through Archive once. Prepared documents
are not reconverted on normal Sort execution. It consumes versioned Markdown plus
explicit native/OCR region types, passes original layout only for damaged evidence,
and retains the `knowledge-2-strategic` contract, verification checkpoints and atomic
publication/group activation. Source verification still reads the original PDF;
that is distinct from conversion. Model timing remains in `source_model_calls`;
Archive preparation timing is logged separately when the progress logger is active.

For an unsorted document, a usable repair candidate activates through registration.
For a sorted document, repair retains an inactive candidate. `--rebuild` selects that
candidate, stages extraction and semantic grouping, displays the review, and only
activates it in the approved replacement transaction. Existing manual-topic and
ungrouping reconciliation guards still apply. Metadata renaming retains the old
version's files and image links for historical citations.

## CoreWeave now

```sh
stock archive CRWV.US --repair 13
stock sort CRWV.US --rebuild 13 --request-seconds 300
stock sources CRWV.US
stock price CRWV.US
```

Document 13 is already sorted, so the explicit reviewed rebuild is necessary to
publish repaired-source extraction. Ordinary `stock sort CRWV.US` preserves its
existing publication and sorts other pending documents. The default request timeout
is 120 seconds; the command above allows 300 seconds after this session's timeout.
The existing per-document/command budgets still apply. Review/approve the completed
proposal in the terminal. Re-run the same command after interruption to resume its
completed extraction/review/grouping checkpoints. No production rebuild was run here.

For new documents, import with `stock archive CRWV.US FILE.pdf`, then use ordinary
`stock sort CRWV.US`. Bare `stock archive CRWV.US` opens the existing Archive browser.
Sources uses arrows for topics, Space for independently readable evidence, F for
document filtering, N/P for supporting members and O for the original source with
citation/verification details. Price retains the existing Longbridge engine.

## Verification and remaining blocker

Measured local results are in [archive-workflow-measurements.json](archive-workflow-measurements.json).
Original document-13 repair took **107.437 seconds**, with local OCR only on pages
5 and 6 (53.96 and 51.77 seconds). Final deterministic assessment reused these OCR
results in 1.794 seconds; an equivalent repair request reused the candidate in
0.008 seconds inside the process. The final candidate contains 58 native regions
and two OCR page regions. Native text explicitly recovers W&B Models, SUNK, CKS,
Cognition and Cursor. The fresh local page-5 OCR output preserves the separate
850MW+ active-power and 3.1GW+ contracted-power labels, and page 6 has four
separate commentary groups. These remain conversion outputs requiring claim-level
verification, not fresh-model extraction results. Page 4's diagram remains accessible in the original PDF;
its geometric relationships and visual chart series are not certified as prose.
Pages 14–15 retain backlog/investment explanations and original qualifications.
Their successful fresh-model strategic extraction has **not** been established.

An ordinary production transcript was assessed on a disposable output in 1.053
seconds with **zero OCR calls**. Existing `AI` text remained byte-preserved in the
baseline portion; additional exact native supplements account for increased term
counts. This is a conversion regression check, not a model extraction evaluation.

A keyboard-driven Sources probe on actual historical CoreWeave publications checked
topic navigation, document filtering, expanded evidence, original-opening routing
(the OS opener was intercepted), verification details and reopening. It left all
published passage rows unchanged. It exposed 1,796 existing published supports;
this does not imply 1,796 newly semantically grouped insights from this session.

The one authenticated, isolated fresh Cursor run timed out on its first selection
request at the 120-second limit, after **122.132 seconds** overall. It published
nothing. Its DB and log remain under `.data/archive-workflow/`; no further live
model campaign was run. Semantic grouping, resumed-model runtime and total time to
new published evidence consequently remain **unmeasured**. The one-hour acceptance
target is not established. A human-corrected fixture score is not used as proof.

The safe next action is the reviewed `--rebuild 13 --request-seconds 300` command
above. Existing evidence remains browsable until a complete verified replacement
is explicitly approved. Provider latency/fresh extraction remains the critical
unverified part of the end-to-end acceptance criterion.

Final validation: the full suite passed **378 tests in 156.65 seconds** using
`.venv/bin/python -m pytest -q --basetemp=.data/archive-workflow/final-test-tmp`.
The final integrity/preparation focused run passed **54 tests in 18.38 seconds**
with a separate temporary directory. These tests include mocked providers and
registration fixtures; they are distinct from the timed-out authenticated run.
`git diff --check` and Python compilation also passed.
