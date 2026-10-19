# Archive Metadata Implementation Plan

**Goal:** Permanent validated JSON enrichment and conservative automatic discovery.
**Architecture:** SQLite remains authoritative; a versioned JSON codec validates and matches records, then reuses Archive's in-place bundle updater. Distinct date fields and their evidence are stored together with field provenance.
**Spec:** User-approved design in this session.

- [x] Add failing JSON validation, matching, conflict, idempotency and distinct-date regression tests.
- [x] Implement codec/matcher and CLI option; extend existing transactional bundle updates.
- [x] Retain automatic SEC filing dates distinctly; inspect embedded content and retain source evidence without inventing unavailable metadata.
- [x] Verify four real CoreWeave originals in an isolated copied archive, offline and live source behavior, and full regression suite.
- [x] Document schema and commands, review, commit and push without rewriting existing work.

Review focus: filename-only false matches; contradictory identity; manual null corrections; rollback across PDF/Markdown/assets; publication versus filing/event dates. Preserve all current uncommitted changes and avoid parent repository changes.

Final independent review: corrected hash alias validation, content-only identity, reused-filename hash selection, and protection of structured JSON dates during duplicate refresh. Added regressions for each. No deferred findings.
