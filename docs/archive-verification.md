# Archive verification — 2026-10-19

Metadata identification/correction is part of ordinary import and the existing
Archive browser. No repair/redo command, import TUI, or extra detail screen was
added. Only this stock repository was changed.

## Validation

- `.venv/bin/pytest -q`: **94 passed**, including Price, Search, Archive and core
  regressions. Focused Archive coverage: **60 passed**.
- `git diff --check`: clean.
- Inspected the actual SQLite schema and all three existing CoreWeave records.
  Ordinary, idempotent schema upgrades add `metadata_provenance` and
  `sec_accession`; existing document/file IDs, source hashes and original metadata
  remain intact. Legacy-schema and existing-record reidentification tests pass.
- Read the actual CoreWeave 10-Q, annual-report and transcript PDFs through the
  installed PyMuPDF engine. The 10-Q reports March 31, 2026 separately from its
  accession and vendor filing-date subject; its title becomes `Form 10-Q`.
  The annual report stays FY2025. The transcript stays Q1-2026 and retains its
  transcript title despite a Form 10-Q reference in its body. No live archive or
  Downloads file was changed during these probes.
- PTY ordinary import showed only the unresolved fields, without Textual:

  ```text
  Period?  1 Q1-2026 · 2 Unknown · 3 Enter
  > 1
  Date?  YYYY-MM-DD · Enter Unknown
  >
  Archived  undated--quarterly--Q1-2026.md
  ```

- PTY Archive inspection confirmed `E Edit`, five labeled inline fields with
  existing values, Tab navigation, Enter save, and return to the same browser.
  Changed a date through actual terminal input and confirmed the saved SQLite
  value after exiting. Automated keyboard tests also cover editing only the
  focused field, cancellation, narrow input bounds and scrolling to later fields.
- Controlled SEC submissions fixtures verify accession, issuer/registrant, primary
  form and report-end matching, annual versus quarterly reports, fiscal calendars,
  earlier publication evidence and provenance, and rejection of conflicting
  registrants, report periods and report booklets. Live requests from this
  environment return SEC HTTP 403; they cannot verify a live publication date.
  This leaves fields unresolved for clarification. TLS verification stays enabled;
  the OS CA bundle handles this Python installation's missing default CA file.
- Tests cover English/Chinese HK terminology, presentations/transcripts, written
  quarter names, forward/reverse/mixed period ambiguity, Unknown titles and dates,
  minimal prompts and user provenance, all taxonomy choices, manually corrected
  and deliberately Unknown fields surviving repeat imports, and complete duplicate
  imports leaving SQLite unchanged.
- Correction tests verify exclusive filename collision handling, PDF/Markdown and
  nested assets moving together, Markdown asset references and hashes, unchanged
  source bytes, no reconversion after metadata edits, stable document/file IDs
  under foreign-key passage/annotation references, SQLite integrity, and rollback
  after document or mid-bundle asset-registration failures.

## Limits

Dates come from explicit exact-document publication evidence or reliably matched
SEC primary filing records. Event dates, vendor filing-date subjects, unrelated
filings, period-end dates and PDF creation/modification timestamps are not used as
publication dates. Date-derived quarter/half labels are suggestions until confirmed
by a user or a matched SEC fiscal calendar. Unknown metadata stays Unknown rather
than inheriting another document's date. Manual answers are user-supplied.

PDF reading/conversion continues to reuse installed PyMuPDF and pdfmd/Marker or
pymupdf4llm. No converter or model was installed; existing converted PDFs were not
reconverted. Scans without extractable text may require clarification. Sort and
Sources remain outside this change.

## Conversion recovery — 2026-10-20

- Removed elapsed-time deadlines from Marker and pymupdf4llm conversion calls.
  A one-second `communicate` polling interval updates liveness; it is not a
  conversion deadline. Explicit bounded probe callers retain their timeout.
- Verified the installed `pdfmd` wrapper accepts `PDF --zip-output ZIP` and invokes
  the existing `marker_single PDF --output_dir DIR --output_format markdown`.
  The wrapper waits without a deadline. Marker remains the first converter;
  failures fall back to installed pymupdf4llm, then labeled PyMuPDF text extraction.
  Marker images and table Markdown retain the existing asset handling.
- The timer begins after process creation, resets on each invocation, and writes
  one terminal row with carriage-return/erase-line updates. Captured converter
  logs do not scroll. No percentages or claims of measured progress are shown.
  Five minutes without captured output adds an activity-unmeasured notice; it
  never triggers termination. Noninteractive output has start/final events only.
- Simulated elapsed time beyond 600 seconds, converter/document timer resets,
  failure/fallback, text-only labeling, conversion-only retry and original
  preservation are covered by `tests/test_archive_conversion.py`. Real child and
  grandchild cancellation is tested as well. PTY inspection showed `00:00`,
  `00:01`, `00:02` replacing one row, then one completion newline; interruption
  similarly restored the row. The cursor is never hidden or moved vertically.
- Focused Archive tests: **108 passed**. Core, UI, data and US tests: **34 passed**.
  `git diff --check` passed. No dependencies were added.
- Read the actual CoreWeave prospectus cover and corrected local document **4**
  from `Table of Contents` to `CoreWeave, Inc. IPO Prospectus` using the existing
  transactional metadata editor. The original is now
  `undated--filing--CoreWeave-Inc.-IPO-Prospectus.pdf`. Document/file identities and
  SHA-256 `10f8088803d57c58c62e7ee885de27ad13717ead30b6859c8eeec487b4550d53`
  remain unchanged. Publication date remains unknown. SQLite was backed up under
  `.data/` before repair. Other archived originals and successful conversions were
  preserved. Retried only this document's missing conversion.
