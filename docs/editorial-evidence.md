# Source-grounded editorial evidence (v4-editorial-1)

## Diagnosis and architecture

Useful source information and readable published wording are independent properties.
The previous v3-quality-1 repair rejected the first three frozen CoreWeave passages:
it screened numeric blocks before selection and required every publication to be an
exact contiguous Markdown slice. Its relevance prompt also excluded useful count
KPIs. Candidate construction omitted headings, tables and image pointers. Adjacency,
section boundaries and gap checks prevented a statement from citing separated
labels, values, periods and qualifications. There was no representation discriminator,
so publication could not safely contain editorial prose.

V3 had already solved source ownership, repeated-quotation ambiguity, stable IDs,
exact character anchors, original/Markdown hash checks, compact ID selection, bounded
protocol retries, staged resumable work, full rebuild preview and atomic replacement.
Those protections remain. The new change is an evidence representation and review
contract, rather than a prompt-only adjustment or another exception handler.

A separate relational representation/reference schema would require migrations and
duplicate the existing frozen record identity. Keeping only exact quotations would
preserve compatibility but cannot meet the reconstruction requirement. The chosen
minimal additive model retains the existing tables and puts the versioned evidence
envelope in `location` JSON:

- `text`: the published readable wording.
- `location.representation`: `verbatim`, `edited_quotation`, or
  `source_grounded_statement`.
- `location.references[]`: Stock-owned document ID, source ID, exact original
  Markdown text, Markdown hash/character offsets, original path/hash, section and
  speaker-turn context; page/visual provenance only when independently located.
- `location.review`: pending or separately model-reviewed state, factual fidelity,
  readability, investment relevance, reason, warnings and explicit limitations.
- `location.visual_context`: the original PDF line coordinates actually supplied
  for resolving layout; bound to the reviewed payload's fingerprint.
- `location.ambiguities`: unresolved contextual qualifications. Selections declaring
  unresolved ambiguity are retained in staging audit and excluded from publication.

For multi-reference records, legacy top-level offsets describe the **first** source
reference, never an invented continuous span. `references` is authoritative. Exact
whitespace gaps are retained only to reconcile equivalent legacy contiguous anchors
when transferring manual topics. Original evidence is never rewritten. Read-time
legacy records default to verbatim/legacy source verification; their stored JSON,
IDs, citations, wording and topics are unchanged.

Verbatim text is supplied exclusively by Stock and requires a contiguous exact span.
Edited quotations permit formatting cleanup, disclosed omissions and bracketed
clarifications. Words outside brackets must survive in source order, and omissions
must be disclosed. This lexical guard is deliberately conservative; semantic review
still checks meaning. Free paraphrase belongs in a source-grounded statement.

## Context and factual verification

Extraction retains numeric fragments, headings, table blocks, footnotes and visual
pointers rather than pre-screening their readability. Existing v3 text-atom IDs are
preserved. Source batches receive referenceable neighboring context. Stock optionally
opens the original PDF read-only and supplies text-line bounding boxes in PDF points.
Unique normalized text matching can locate a page; it does **not** verify a metric
association. Image filenames never establish page numbers, and converter-generated
chart descriptions are explicitly unverified visual summaries.

Cursor returns IDs, representation, optional editorial text, topics, category,
source-grounded individual speaker or null, and ambiguities. Stock validates protocol
shape and source membership/ordering, speaker turns/roles and exact slices. New
numbers, currency symbols, scales, percentages and common power-unit tokens absent
from the references are rejected deterministically. This lexical check neither
proves signs/units are attached to the correct metric nor understands semantic
identity. It conservatively rejects unsupported numeric conversions too.

Every new represented passage then receives a **separate fresh Cursor review call**
with its readable wording and exact supporting fragments. The review checks entity,
period/as-of date, values/signs, currency/scales/units, metric definitions, mapping,
comparative bases, material qualifications, attribution and fact versus interpretation.
A useful/clear/supported result is required; the three judgments are stored separately.
Required qualifications must be present in the selected references, not merely in
uncited surrounding context. Unsupported causal claims, valuations and management
intentions are evidence failures. Unknown visual mapping remains unresolved.

This is model judgment using the same service, not an independent human fact-check
or a mathematical equivalence proof. Fluent unsupported prose can still evade it.
Review reasons, warnings, exact evidence and supplied geometry remain inspectable.
A fingerprint binds wording, references, attribution, representation, visual context
and review; publication and checkpoint resume reject changed or unreviewed payloads.
The fingerprint detects accidental edits, not malicious rewriting of the local DB.

## Real CoreWeave evidence

Inspected production document 13 read-only and confirmed its eight frozen passages
against `document-13-live.json` and the exact archived Markdown. Markdown SHA-256:
`9f4f0f20f24a91c83adba7dfea851c61c0250629d8100c51d45682ad63aa84d4`.
Original PDF SHA-256:
`db716980ae8eb4eddda477d43ef2cead98419f6fa4fbec8e37ff643a98b6cbf6`.

The following are regression reconstruction examples, not replacements published to
Sources. Offsets are zero-based half-open archived character ranges. Additional
periods/qualifications must be cited when included in the actual statement.

### Example 1: 4945–4979

Exact contributing source text (each paragraph can remain a separate reference):

```text
**11**

Data Centers Added in 2025
```

Source-grounded statement: CoreWeave added 11 data centers in 2025.

### Example 2: 4981–5029

Exact contributing source text (each paragraph can remain a separate reference):

```text
Active Power Contracted Power

**850MW+ 3.1GW+**
```

Source-grounded statement: CoreWeave reported active power of 850MW+ and contracted power of 3.1GW+.

### Example 3: 5333–5360

Exact contributing source text (each paragraph can remain a separate reference):

```text
**43**

Active Data Centers
```

Source-grounded statement: CoreWeave reported 43 active data centers.

### Example 4: 13569–13666

Exact contributing source text (each paragraph can remain a separate reference):

```text
**Revenue:** \$1.6 billion, up 110% YoY driven by strong demand for CoreWeave's AI Cloud Platform
```

Source-grounded statement: CoreWeave reported revenue of $1.6 billion, up 110% YoY, driven by strong demand for its AI Cloud Platform.

### Example 5: 14151–14266

Exact contributing source text (each paragraph can remain a separate reference):

```text
**Adjusted Net Loss:**

\$(284) million, compared to \$(36) million in Q4'24

**Adjusted Net Loss Margin:** 

(18)%
```

Source-grounded statement: Adjusted net loss was $(284) million, compared to $(36) million in Q4’24; the adjusted net loss margin was negative 18%.

### Example 6: 15222–15331

Exact contributing source text (each paragraph can remain a separate reference):

```text
#### **Adjusted EBITDA:**

\$898 million compared to \$486 million in Q4'24

**Adjusted EBITDA Margin:**

57%
```

Source-grounded statement: Adjusted EBITDA was $898 million compared to $486 million in Q4’24; the adjusted EBITDA margin was 57%.

### Example 7: 15473–15680

Exact contributing source text (each paragraph can remain a separate reference):

```text
#### **Revenue Backlog:**

\$66.8 billion, up 342% YoY driven by substantial growth from existing and new customers including large deals with AI labs, hyperscaler cloud customers, enterprises and AI natives
```

Source-grounded statement: Revenue backlog was $66.8 billion, up 342% YoY, driven by substantial growth from existing and new customers, including large deals with AI labs, hyperscaler cloud customers, enterprises and AI natives.

### Example 8: 16579–16673

Exact contributing source text (each paragraph can remain a separate reference):

```text
**Capital Expenditures:** \$8.2 billion driven by scaling our platform to meet customer demand
```

Source-grounded statement: Capital expenditures were $8.2 billion, driven by scaling the platform to meet customer demand.

### Material qualifying references

These are separate exact source spans, not text silently added to quotations.

Characters 4571–4761:

```text
Notes: Figures as of December 31, 2025. This graphic provides an illustrative representation of our infrastructure footprint and may not precisely reflect all current locations or capacities
```

Characters 14268–14437:

```text
1. Adjusted Net Loss and Adjusted Net Loss Margin are non-GAAP financial measures. Please see the reconciliation from GAAP to non-GAAP measures contained in the Appendix
```

Characters 15018–15183:

```text
1. Adjusted EBITDA and Adjusted EBITDA Margin are non-GAAP financial measures. Please see the reconciliation from GAAP to non-GAAP measures contained in the Appendix
```

Characters 15787–16385:

```text
1. Revenue backlog includes remaining performance obligations plus other amounts we estimate will be recognized as revenue in future periods under committed customer contracts, in each case, subject to the satisfaction of delivery and availability of service requirements. Revenue backlog is expected to fluctuate from period to period, given the nature of our committed contract business and the size of committed contracts. The percentages shown in the bar charts represent the percentage of revenue backlog we expect to recognize in the months following the end of the quarterly reporting period
```

Characters 16425–16577:

```text
1. Capital expenditures are additions to property and equipment including assets acquired under finance leases, less changes in construction in progress
```

Include non-GAAP status when publishing adjusted metrics. Backlog is not recognized
revenue: its definition includes estimated future amounts and delivery/availability
conditions. Capex includes finance leases and subtracts changes in construction in
progress. The extended financial/table/footnote tests preserve these references.

### Independently established power mapping

Original PDF page 5 was inspected as a rendered page and as text-line geometry.
The fixture `document-13-power-layout.json` preserves the extracted coordinates:

| Original text | Left coordinate | Top coordinate |
| --- | ---: | ---: |
| 850MW+ | 586.75 | 489.824 |
| Active Power | 586.75 | 530.776 |
| 3.1GW+ | 779.600 | 489.824 |
| Contracted Power | 779.600 | 530.776 |

Each label sits immediately below its own value. Notably, original PDF text order
lists `3.1GW+` before `850MW+`, whereas flattened Markdown lists `850MW+ 3.1GW+`.
Neither text order establishes the pairing. Without layout or explicit reliable
context, the pending reconstruction cannot be published merely by resolving IDs.
A declared ambiguity or an unresolved semantic review leaves it in the audit trail.

### Small live Cursor demonstration

One authenticated selection call and one separate review call were run against
only the relevant archived KPI fragments, the dated footnote and original page 5
line geometry. No database was opened by this smoke script. Actual accepted text:

> As of December 31, 2025, CoreWeave reported 43 active data centers, 11 data centers added in 2025, 850MW+ of active power, and 3.1GW+ of contracted power. The infrastructure-footprint graphic is illustrative and may not precisely reflect all current locations or capacities.

It cited seven exact source IDs including the dated/illustrative qualification;
there were no resolution errors or review rejections. This is editorial text,
not a direct quotation. The raw selection and review response are frozen in
`document-13-editorial-live.json` and replayed in offline regressions. Full local
smoke diagnostics remain in `.data/editorial-live-smoke.json`. This narrow result
does not establish archive-wide selection quality, financial semantic performance,
or reliable behavior on arbitrary visual charts.

## Review, compatibility and operations

Sources remains a compact native-color keyboard-only terminal interface. `≈` marks
a source-grounded statement; `~` marks an edited quotation. Space expands the readable
text plus representation, verification reason/warnings and every exact fragment with
its citation/path/offsets. `O` retains the original-document opening behavior; topics,
file filtering and navigation remain. `TERMINAL_RENDERING_HANDBOOK.md` is not present
in this checkout; the existing `NATIVE_CSS` ANSI foreground/background behavior is
retained without adding colors, mouse controls or a GUI.

Ordinary Sort still skips completed documents. Selective rebuild stages results in
checkpoints, keeps frozen evidence visible, previews all proposed statements and
original fragments, and displays unpublished ambiguities/rejections too (including
on checkpoint reuse). Only explicit `REPLACE` approval can replace the selected
document. Source and concurrent-publication checks precede the atomic transaction.
Failure, cancellation or rejected approval retains the old evidence. Manual topics
transfer on unambiguous matching source anchors and attribution even if editorial
wording changes; unmatched or ambiguous corrections block replacement.

No table migrations or destructive archive operations are required. Frozen v1–v3
records remain readable; the active extraction version is 4. Checkpoints remain in
the historically named `source_work_v3` table, but keys include Markdown hash,
`v4-editorial-1` and a fingerprint of document/original identity and archived paths.
Earlier compatible/incompatible complete and interrupted rows remain for audit;
incompatible rows are never resumed. Exact reference provenance and review fingerprints
are rechecked before new publication.

To review a live selective rebuild (this has **not** been run):

```sh
stock sort CRWV.US --rebuild 13
```

Inspect the complete review, then type `REPLACE` only when satisfied. Adding a new
footnote/reference can intentionally prevent automatic topic transfer from an old
record; reconciliation is required rather than silent loss of the correction.

## Verification and remaining limits

Focused suites: `tests/test_editorial.py`, `tests/test_evidence.py`,
`tests/test_sources.py`. They cover the actual eight frozen spans, useful short KPIs,
verified and unresolved power layouts, headings, tables, visual pointers, footnotes,
financial comparisons, speaker turns, unsupported numbers/units/inferences, all three
representations, legacy reads, bounded protocol retries, interrupted review/resume,
review fingerprint integrity, original-identity checkpoint invalidation, override
transfer, rejected approval, rollback and document-specific replacement. Destructive
checks use disposable databases/copies. Final results are recorded in the delivery.

No production rebuild, full-archive extraction, or production database writes were
performed. The live Sources library still contains document 13's eight prior records.

Remaining risks: semantic review can misjudge signs, unit associations, omitted
caveats and relevance even when lexical checks pass. PDF line geometry is sufficient
for the demonstrated slide but does not decode every chart. Raster-only/complex
visuals require additional inspection and must remain unresolved when supplied
context cannot establish meaning. Neighbor context is bounded; distant definitions
may need an additional source selection. Duplicate text is deduplicated exactly,
not with a global semantic redundancy model. New numbers or unit conversions absent
from exact references are conservatively rejected. No passage-count reduction is
used as a quality score.

Final verification on 2026-10-23: the focused three-suite run completed with
**115 passed**. Python 3.11 grammar parsing and `git diff --check` passed. A final
read-only production query confirmed all eight frozen document 13 texts/anchors,
the original PDF and archived Markdown hashes, and zero v4 production checkpoints.
