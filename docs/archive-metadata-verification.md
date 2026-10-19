# Permanent Archive metadata verification — 2026-10-20

This supersedes the earlier Archive verification's description of manual metadata
entry and SEC dates. Imports ask for classification or conflicts only. The browser
keeps its existing compact expansion, with distinct dates and provenance.

- Full suite: `.venv/bin/pytest -q` — **132 passed**.
- New focused JSON regressions: **33 passed**. Coverage includes validation,
  contradictory hashes, content-only matching, same-name documents selected by
  hash, ambiguity, manual nulls/conflicts/remembered keep choices, idempotency,
  preservation of structured JSON dates on duplicate refresh, evidence export,
  offline/blocked/missing data, and transaction/file rollback.
- `git diff --check` — clean.
- `.venv/bin/stock archive --help` exposes permanent `--metadata JSON` alongside
  the existing ticker/file arguments. No repair command or new TUI screen.
- Real regression: `.venv/bin/python tests/verify_archive_metadata_real.py` read
  all four original PDFs from `~/Downloads/CoreWeave_Test`, copied the existing
  SQLite database and Research archive into `.data/metadata-real-verification`,
  and imported the missing presentation using the real installed pdfmd/Marker
  converter. All four supplied JSON records matched. Existing document IDs,
  original hashes and three conversions survived; Markdown/asset paths and hashes
  remained valid. SQLite integrity and foreign-key checks passed. Repeated JSON
  import changed zero records and performed zero SQLite writes. The live archive
  metadata and Downloads originals were not enriched or renamed.
- Real original SHA-256 values:

  | Original | SHA-256 |
  |---|---|
  | 2025-Annual-Report.pdf | `f660a7c2d181ceb77c27e9c58456fd11d08fdee4ff8d5826c71bd631facdee8d` |
  | CoreWeave-1Q26-10-Q.pdf | `b57cd2b889ba167744332230fd85303512aee21da832820cee805c6857a133da` |
  | CoreWeave-1Q26-Earnings-Presentation.pdf | `863706795708152ab65722e7b7b461c12dc9b72974a78abe21a35c2acbbaf8db` |
  | CoreWeave-Q1-2026-Transcript.pdf | `5e2306cfd4f4f732395049b2cdd3cdb2909a4e8c6712de3009c962b13de833ba` |

- Live issuer verification: downloaded all four `official_document_url` PDFs
  supplied in the JSON using verified TLS and the normal request user agent.
  Every remote PDF hash exactly matched its local original. This verifies document
  identity, not earliest publication. The Python installation required the same
  OS CA supplement already used for SEC requests; certificate verification was
  never disabled.
- Live SEC submissions returned **HTTP 403 Forbidden**. No alternate route or
  restriction workaround was attempted. SEC response matching is covered by
  controlled tests; this session does **not** independently verify the supplied
  filing dates against live regulatory records.

The enriched copied transcript has unknown publication, May 7 document/event
dates, and FactSet CallStreet publisher. The supplied annual and quarterly dates
are retained as filing dates; the presentation cover date is a document date.
All four publication dates remain unknown under the conservative normalization
of the supplied evidence. Their filenames consequently use `undated`.

Automatic discovery is bounded: document text/embedded metadata, embedded source
pages whose identified PDFs match by hash, SEC primary filing identity, and issuer
records corroborated by the cover. No general web search/crawler or LLM is used.
Without these identifiers, or when services are blocked, fields may remain unknown.
No routine manual date/publisher research prompts are added.

The live archive currently lacks the presentation. Import it before applying the
four-record JSON. Existing manually supplied transcript and quarterly publication
dates require explicit keep/JSON choices; Enter keeps the manual correction.
