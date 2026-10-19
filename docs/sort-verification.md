# Sort prerequisite and passage verification

Verification uses database backups and temporary archive copies. The user's
CoreWeave database and original PDFs, Markdown, assets, frozen topics and manual
overrides are preserved. No completed document is rerun.

The original failure paths were mandatory original-PDF matching after Markdown
extraction, a 30-character quotation threshold, overly narrow speaker-evidence
matching, and document-wide failure on the first invalid candidate. Sort now uses
Markdown offsets and its SHA-256, with optional PDF page references only.
Transcript name/role adjacency can establish attribution even with Markdown
headshots between the name and role. Explicit transcript roles and turn headings
reject executive/analyst or speaker mismatches independently of exact text matches.

Focused and full tests cover PDF-only conversion prerequisites, successful reuse,
busy/failed conversion, missing successful conversion assets, conversion past ten
minutes, real converter interruption and descendant cleanup, short/unknown-speaker
passages, presentation recovery, substantive wording/number rejection, isolated
candidate failure, malformed section retries, checkpoint resumption, source
mutation, offsets/hashes, freeze-on-success, topic overrides/reset, and Sources TUI
interaction. Accepted passages are checkpointed; incomplete documents do not
receive a completion record or lose their verified work. Only unresolved
candidates/sections are retried on the next Sort invocation.

Commands:

```sh
.venv/bin/pytest -q
.venv/bin/python tests/verify_native_terminal.py
PYTHONPATH=. .venv/bin/python tests/verify_sort_real.py
```

The opt-in real check extracts actual CoreWeave transcript, quarterly management
discussion and annual narrative sections. It also converts a copied real Q4
presentation PDF before a complete authenticated sort. `--resume` revalidates
already captured authenticated section responses against the same source context;
the default always requests fresh responses. Verification responses stay in ignored
`.data`, outside Git. The final live-database dump must match the initial dump.
The terminal check backs up the database and exercises Price, Archive and Sources
in light and dark PTYs, rejecting explicit foreground/background color assignments.

## CoreWeave results (2026-10-20)

Authenticated extraction verified six transcript passages, twelve quarterly
management-discussion passages and eight annual narrative passages, with no
rejected candidates. Transcript coverage includes an unidentified Management
speaker, named executives and an Investor analyst. A table-only quarterly
section correctly returned no commentary; the narrative fixture targets the
management discussion rather than expecting tables to produce evidence.

Archive's Marker converter successfully converted the copied real Q4 presentation
PDF in 53 seconds. Original conversions were reused in all section checks.
Light and dark PTY checks passed for Price, Archive and Sources, including inline
manual topic editing. Simulated conversions exceeded ten minutes without a
conversion deadline; real interrupted converter tests confirmed child cleanup and
preservation of the archived original.

The complete automated suite passed 184 tests. A read-only integrity check also
confirmed all 154 registered files across the 13 live CoreWeave archive documents
still match their archived SHA-256 values; the three previously completed
classifications remain completed.

The final authenticated full sort of the previously failing Q4 presentation reused
its successful archived conversion and froze 31 passages in a database copy.
All 31 exact Markdown spans, hashes and citations were independently checked;
25 passages retained unique PDF page references and six kept unknown pages.
Repetition skipped Cursor, checkpoints were cleared only after success, existing
frozen records were unchanged, and the live database dump matched its baseline.

An earlier fresh-conversion trial exposed malformed Cursor JSON twice and correctly
left the document incomplete. Explicit JSON escaping guidance and trusted retry
instructions were added; the final current-code presentation run completed. No
failures remain in the final checks. This does not claim a full rerun of all 13
live documents: the three completed classifications were deliberately preserved.

For a later full-sort check that reuses the existing archive conversion, run
`PYTHONPATH=. .venv/bin/python tests/verify_sort_real.py --resume --reuse-conversion`.
The section-response cache is checked against the source context; the final full
presentation sort uses authenticated Cursor. Verification database copies are
retained under `.data/verify-sort-*` for inspection, including incomplete states.
