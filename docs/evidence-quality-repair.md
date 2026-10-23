> Historical v3-quality-1 diagnosis and repair. The active architectural repair is
> [Source-grounded editorial evidence](editorial-evidence.md); it supersedes the
> numeric-fragment exclusions and exact-quotation-only publication rules below.

# Evidence quality correction (v3-quality-1)

## Demonstrated failure

Inspected the production database read-only, document 13's full archived Markdown
(SHA-256 `9f4f0f20f24a91c83adba7dfea851c61c0250629d8100c51d45682ad63aa84d4`),
published source anchors, current candidates, extraction/selection/validation code,
and `.data/sort-v3-smoke*.json` Cursor response artifacts. The latter are earlier
smoke calls, not the successful live rebuild's response. The successful rebuild
removed its checkpoint; its complete raw response and internal relevance reasoning
cannot be recovered from those artifacts. Published `candidate_ids` establish the
selected groups, not the model's reasoning. Frozen regression fixtures contain the
full exact archived Markdown and all eight published quotations/anchors (without
local original-file paths).

| Source offsets | Published selection | Diagnosis |
| --- | --- | --- |
| 4945–4979 | 11 / Data Centers Added in 2025 | Understandable count tile; poor commentary selection, not necessarily unreadable source |
| 4981–5029 | Active Power Contracted Power / 850MW+ 3.1GW+ | Multiple labels and values with no explicit association; visual ordering cannot establish meaning |
| 5333–5360 | 43 / Active Data Centers | Understandable count tile; weak research contribution without commentary |
| 13569–13666 | Revenue, 110% YoY, demand explanation | Readable quantitative and causal claim |
| 14151–14266 | Adjusted net loss comparison and margin | Readable labeled values and prior-period comparison; check period/non-GAAP qualifications |
| 15222–15331 | Adjusted EBITDA comparison and margin | Readable labeled comparison; check period/non-GAAP qualifications |
| 15473–15680 | Revenue backlog growth and customer drivers | Readable quantitative and causal claim |
| 16579–16673 | Capex and scaling to customer demand | Readable quantitative and causal claim |

Segmentation emitted paragraph atoms, including numeric tiles and separate labels.
It associated colon labels with following values, but did not interpret slide columns.
Section headings reflected Markdown order, sometimes an earlier slide heading;
section metadata therefore cannot supply missing metric meaning. Cursor explicitly
grouped the first three pairs. The previous prompt said to reject fragments, but
also invited capacity/financial claims without clearly distinguishing KPI tiles
from independently useful commentary. It did not enforce the library's preference.

Candidate screening excluded tables/images/operator material, but let numeric-only
blocks through. Post-selection validation enforced IDs, adjacency, role, offsets,
and provenance, not readability or research usefulness. Exact source verification
succeeded correctly. It never established relevance. All eight passages had zero
table delimiters, so table counts missed the failure. Review showed only five,
hiding EBITDA, backlog and capex from the approval preview.

## Focused changes

- Preserve candidate IDs, source offsets, exact quotations, provenance and the v3
  publication schema. Screen detached numeric blocks deterministically. A single
  scalar directly following a colon label can remain eligible; multiple scalar
  tiles cannot establish a mapping merely by adding a colon. Apply the same guard
  to selected source spans. Never rewrite the source into invented prose.
- Strengthen semantic instructions for explanations, forecasts, risks, specific
  insights and useful quantitative comparisons. Omit raw KPI tiles, ambiguous
  columns, disclosures and chart residue. Short claims and numerical evidence
  remain eligible; no minimum word count is used.
- Display every proposed quotation, numbered, with advisory fragment/formatting/
  quantitative-context flags. Interactive terminals use the standard-library plain
  keyboard pager (Space, Enter, b, q); wrapped lines fit the terminal. Redirected
  output contains all passages. Approval remains a separate existing step.
- Report deterministic exclusions, model omissions and unresolved rejected
  selections separately. Omission is not evidence of unreadable source. Quality
  warnings are advisory and do not certify unflagged passages.
- Namespace checkpoints by Markdown digest plus `v3-quality-1`, and check the
  contract in payloads. Old complete and incomplete rows are ignored and retained.
  Keep raw selections in completed checkpoints; retain checkpoints after successful
  replacement. Future changes to screening, batching, segmentation or selection
  contracts require another contract bump.
- Preserve existing atomic replacement, concurrent-change guards and exact-match
  topic override transfers. Unmatched manual corrections still block replacement.

## Validation and limits

Regression tests replay all eight actual selections against the full archived
Markdown: the first three are rejected, the other five remain eligible. Tests cover
paired metrics (including colon ambiguity), clear quantitative claims, meaningful
short claims, label/section boundaries, all-passage review, keyboard pager routing,
both old checkpoint completion states, and frozen data preservation on a disposable
database copy. Existing representative presentation, filing and transcript fixtures
continue to exercise source anchors, role boundaries, retry/resume and rollback.
No live Cursor calls, full archive sorting, or document 13 rebuild were performed.
Production evidence and manual edits were not modified. Only this repository changed.

Deterministic screening deliberately covers reliable structural failures, not all
possible prose defects. Inline interleaved column text, misleading punctuation,
chart-axis tails embedded in prose, and context-dependent metrics still need Cursor
judgment and human review. Advisory checks can overflag valid short claims and
underflag fluent but irrelevant text. Colon syntax is an association cue, not proof
of substantive relevance. Shared slide qualifications may remain outside a useful
span; selection instructions require material adjacent context, but source order
can make grouping impossible. A readable source can still yield a poor selection.
A fresh live semantic assessment has not been claimed. Document 13 remains frozen
until a user explicitly runs and approves a rebuild.

Verification on 2026-10-23: full suite `228 passed`; final focused evidence suite
`44 passed` after a Python 3.11 syntax-compatible refactor of the exclusion count.
Python 3.11 grammar checks and `git diff --check` passed. A final read-only production
query confirmed document 13 still exactly matches all eight frozen quotations.
