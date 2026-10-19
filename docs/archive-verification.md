# Archive verification — 2026-10-19

Implementation follows the supplied Archive specification. The CLI branches before
constructing Market; Price and Search retain their existing behavior. Archive adds
three tables to the existing SQLite database and leaves cache/annotations intact.
No parent repository files or Git history were modified.

Validation:

- `.venv/bin/python -m pytest -q`: 64 passed, including existing regressions.
- `git diff --check`: clean.
- Generated a real one-page PDF using the installed PyMuPDF interpreter and imported
  it through CLI into an isolated `.data/archive-real` database/research root.
  The installed pdfmd/Marker produced matching PDF and Markdown basenames; document
  text supplied the annual classification, FY2025 period and publication evidence.
- PTY inspection at 80×24 and 30×18: header/ticker adjacency, grayscale aligned rows,
  in-place metadata expansion, selection and Esc. Narrow identity/metadata wrap;
  PgUp/PgDn provide keyboard scrolling for long expansions.
- PTY uncertain import: one inline type question, selecting Interim archived the
  file directly without starting Textual. Unknown noninteractive classification
  fails before copying; automated CLI coverage confirms no Market construction.
- Tested content/metadata recognition, historical-date exclusion, fiscal-period
  ambiguity, exact title retention, canonical symbols, stable basename collisions,
  hash deduplication and provenance persistence, conversion fallback, asset paths,
  failed conversion retry, source disappearance/change, database registration
  rollback, concurrent imports, unrelated database writes during conversion,
  converter timeout cleanup, O/M associations, and empty/narrow navigation.

Limitations: recognition is deliberately conservative and uses explicit publication
labels and period identifiers; unfamiliar formats can require manual type selection.
Unverified date/publisher/period remain unknown. PDF inspection requires local
PyMuPDF; conversion depends on existing pdfmd/Marker or local pymupdf4llm. The real
machine's pdfmd path was exercised; fallback behavior was tested with a controlled
external-converter boundary. Scanned documents without extractable text may have
incomplete metadata. No Sort or Sources implementation is included.
