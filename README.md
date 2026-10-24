# Stock — A Keyboard-First Market & Research Terminal

**A Python terminal application for market data, historical price analysis, and source-traceable investment research across US and Hong Kong securities.**

Stock brings a market terminal and a local research workflow into one keyboard-driven interface. It combines live read-only market data with historical charts and timestamped notes, then connects those observations to an archive of company filings, presentations, earnings calls, and research documents.

It was built around a practical research problem: investment work is not just finding a ticker or reading a document. It also means navigating market data, preserving context, tracking where claims came from, and keeping a durable record of the evidence behind an investment view.

## What it does

- **US and Hong Kong market lookup.** Search securities by ticker or English/Chinese name, inspect instrument metadata, and retrieve daily and available intraday price history.
- **Historical price exploration.** Navigate real OHLCV observations with time-based zoom and exchange-local dates. No synthetic prices are inserted for weekends, holidays, or missing bars.
- **Timestamped research notes.** Attach notes to specific historical observations and keep them in a local SQLite database.
- **Company research archive.** Import PDFs, Markdown, and text; organize them by canonical ticker; preserve source URLs, hashes, metadata, and conversion status.
- **Evidence-aware metadata.** Keep publication, filing, document, event, and reporting-period dates distinct. Unknown fields remain unknown rather than being guessed from filenames.
- **Source-linked commentary.** Extract and classify research passages by topic while retaining exact archived Markdown text, source anchors, and provenance. The optional Sort workflow uses the installed Cursor Agent CLI in read-only ask mode; it is not required for basic market-data use.
- **Offline resilience.** Cache read-only responses, display stale-cache/offline status, and surface upstream errors when no cached history is available.
- **Keyboard-first interface.** Designed for a monospace terminal, with no mouse interaction required.

## Why it is technically interesting

Stock sits at the intersection of market-data integration, terminal UI engineering, time-series navigation, local data modeling, document ingestion, metadata provenance, and validation of AI-assisted extraction.

A few design choices are deliberate:

- **Read-only by design:** Stock calls market-data/search methods only. It does not place orders or request trading permissions.
- **Source traceability over false precision:** It records evidence and distinguishes date types instead of treating a PDF cover date, earnings-call date, or filing date as proof of publication.
- **Deterministic storage:** SQLite is authoritative for local annotations, archived documents, and research metadata. JSON is an interchange format, not a second database.
- **Conservative failure behavior:** Failed lookups and unverifiable claims remain unresolved; incomplete extraction is not silently marked complete.
- **Explicit boundaries:** Market data depends on the connected Longbridge account and its entitlements; source extraction and classification still involve model judgment and are validated rather than treated as infallible.

## Quick start

**Requirements:** Python 3.11+, a terminal, and the official Longbridge CLI authenticated for read-only market-data access. Stock itself depends on Textual; test dependencies are optional.

```bash
git clone https://github.com/MrMittenCrab/stock.git
cd stock
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'

# Authenticate with Longbridge CLI (follow its official setup instructions).
longbridge auth login
longbridge check --format json

# Explore securities and prices.
.venv/bin/stock search CoreWeave
.venv/bin/stock price CRWV.US
.venv/bin/stock search Tencent
.venv/bin/stock price 700.HK
```

For the archive and research workflows, see the commands below and the detailed reference further down this page. Local market caches, annotations, and archived research are stored outside version control; they are not bundled with the repository.

## Main workflows

| Command | Purpose |
|---|---|
| `stock search TICKER_OR_NAME` | Search US/HK security catalogues |
| `stock price TICKER` | Open the interactive historical price view |
| `stock archive TICKER PATH` | Archive a local document under a security |
| `stock archive TICKER URL` | Import a directly linked source document |
| `stock sort TICKER` | Extract and classify source-grounded commentary |
| `stock sources TICKER` | Browse archived research passages and provenance |

## Verification

Run the local test suite and smoke checks:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python tests/smoke.py
```

The test suite covers keyboard interactions, chart alignment and navigation, exchange-local time handling, annotation isolation, symbol normalization, cache/error behavior, and safeguards against trading methods. The live smoke test makes authenticated read-only requests and therefore requires a working Longbridge CLI session.

## Data, credentials, and limitations

- Stock reuses the official Longbridge CLI's authentication; it does not copy or store brokerage credentials.
- Local SQLite state, research archives, virtual environments, and environment files are excluded from Git by the repository's ignore rules.
- Market-data availability and historical depth depend on Longbridge's API, account permissions, and retention limits.
- Cursor-assisted extraction requires the separately installed and authenticated Cursor Agent CLI. Model-assisted topic classification still involves judgment; Stock validates output structure and source text but cannot guarantee semantic correctness.
- This is a research and monitoring tool, **not an order-entry system or investment recommendation service**.

## Detailed technical reference

The sections below document implementation behavior, navigation controls, market-data limits, archive metadata rules, and source-extraction validation in detail.

## Longbridge authentication

Install the official [Longbridge CLI](https://open.longbridge.com/docs/cli)
(e.g. `brew install --cask longbridge/tap/longbridge-terminal`). Stock was
verified with CLI **0.30.0**, Python **3.14**, and Textual **6.12.0**.

```sh
longbridge auth login
longbridge check --format json
```

Stock reuses the CLI's existing authentication; it never copies credentials,
requests trading permissions, or calls trading methods. Longbridge manages its
own credentials outside this project. All Stock code, configuration and persistent
state live here. `.data/stock.sqlite3` contains cached market data and user point
annotations and is excluded from Git. Back it up to preserve notes.

## Price controls

- ↑/↓ selects timeline, annotation, or zoom (`>` marks the selected row).
- Timeline ←/→ moves one actual observation; ▼ is selected, ● marks notes.
- Annotation Space toggles full text in place. → expands, then → edits.
- A adds/edits a point note at the selected historical timestamp.
- While editing, ←/→ moves the caret, Space inserts a space, and Enter inserts
  a newline. ↑ saves and selects timeline; ↓ saves and selects zoom.
  Esc always saves pending edits and quits Stock.
- Zoom ← widens and → narrows: 1Y, 6M, 3M, 1M, 1W, 1D, 1H. Adjacent levels
  always show directional arrows (— marks unavailable levels).
  The historical anchor survives zooming.

Use a monospace terminal; Stock uses the terminal's single font size, grayscale,
and no mouse reporting. 80×24 or larger is recommended. Expanded text pushes
following rows down; selected rows scroll into view in smaller terminals.

## Data behavior and limits

The chart plots **raw closes** from real OHLCV observations, with straight line
segments between them. Chart segments, note markers, selection, and date ticks
share one elapsed-time scale. The reserved marker row sits immediately above the x-axis. No synthetic
price observations are added for weekends, holidays, lunch breaks, or missing bars.
Dates, annotation markers, anchored history requests, and intraday labels use the exchange timezone: Asia/Hong_Kong for HK and America/New_York for US (EST/EDT). Calendars are requested independently by market; only returned price observations are plotted. Month/year zooms are approximate
trading-observation windows (21/63/126/252 daily bars), not calendar durations.
The initial fetch contains up to 1,000 daily bars; navigation stops at its edges. Daily zooms longer than the returned history are unavailable (the shortest window remains usable for newly listed stocks).

Stock probes 1m, 5m, 15m, 30m, then 1h history to find the finest resolution the
account actually returns. Intraday zoom is disabled if all probes fail. Moving
between daily and intraday bars retains the exact historical anchor; the triangle
uses the nearest returned bar on that exchange-local date. Timeline movement then selects an
actual bar in the new resolution. No returned bar on that date means zoom stays
unchanged with an error. Intraday notes appear as date markers at daily zoom.
Historical availability remains subject to Longbridge retention and account quotas.

Responses are cached for one hour (metadata and catalogue: one day). Cache keys
include adjustment mode and resolution; Stock currently requests `adjust=none`,
so adjusted data cannot silently mix with raw data. Failed refreshes use cached
responses and show OFFLINE with the cache time. Without cached history Stock
reports the upstream error. There is no synthetic demo mode or automatic refresh.
Requests are serial and paced at least 1.1 seconds apart. Calendar requests are
split into ranges shorter than a month; startup retrieves the visible month.
Longbridge limits calendar history independently of price history; unavailable
calendar responses are reported while observed price timestamps remain usable.

Search uses the supported **`quote.security_list` with markets `US` and `HK`**,
then ranks names (English and Chinese) and tickers locally, case-insensitively.
Exact tickers and names precede prefixes, substrings, and close spelling matches.
Results retain canonical symbols and explicit markets, including duplicate company
names across listings. HK zero padding is normalized; US share-class punctuation
is retained. Catalogue failures identify which market could not be searched.
Search never opens Price. The catalogues may include funds, warrants and bonds
alongside equities; catalogue membership is not a guarantee of price entitlement.

The official [CLI catalogue documentation](https://open.longbridge.com/docs/cli/market-data/security-list)
and [RPC contract](https://open.longbridge.com/docs/cli/serve) document this route.
The older [SDK security-list page](https://open.longbridge.com/docs/quote/security/security_list)
describes a narrower overnight list; the installed CLI 0.30.0 RPC was separately
verified to return full US and HK catalogues, including CRWV.US and 700.HK.
No guessed REST endpoint, web scraping, alternate data provider, or CLI upgrade
is used. See also the [calendar API](https://open.longbridge.com/docs/market/trade-days).

## Verification

```sh
cd ~/Documents/Developer/stock
.venv/bin/python -m pytest -q
.venv/bin/python tests/smoke.py
```

The smoke script bypasses cached responses and makes fresh authenticated,
read-only requests for CoreWeave and Tencent search, metadata, daily and finest
available intraday OHLCV, anchored history, and each market's calendar. It also
checks independent July 2026 HK/US holidays. Tests cover keyboard editing,
chart continuity and alignment, navigation, exchange-local anchored zoom, DST,
annotation isolation, symbol normalization, short-history zoom limits, permission
errors, stale-cache notices, and refusal of trading methods.

## Archive

```sh
stock archive 700.HK                         # keyboard archive browser
stock archive 700.HK ~/Downloads/report.pdf # copy, identify and convert
stock archive CRWV.US ~/Downloads/note.md
```

Archive uses the existing `.data/stock.sqlite3`, independently of Longbridge.
Originals and converted Markdown live in `Research/<canonical ticker>/Archive/`
inside this project. This flat archive and its converter assets are excluded from
Git. Back up both `Research` and the database. Existing research directories,
market caches, and annotations are retained.

Names follow `YYYY-MM-DD--type--period-or-title.ext`, using `undated` when no
publication date is known. The database retains exact titles, original names,
source paths and metadata, publication-date evidence, SHA-256 hashes, import
history, conversion status, and an unsorted status reserved for future Sort.
Distinct documents with colliding names receive a stable hash suffix. Reimporting
identical bytes for a ticker reuses the same record and paths; a failed PDF
conversion is retried. Source files are never modified. Similar documents are
never merged. A PDF is committed before conversion, so a converter failure leaves
a usable archived original and returns exit status 1 with retry instructions.

Recognition uses front matter, headings, and PDF metadata, without an LLM or
filename-based guesses. US forms and English/Chinese HK reporting terminology
identify reports, presentations, earnings releases, transcripts and other types.
SEC accessions are stored separately from titles and periods. For primary SEC
reports, issuer, accession, form and reporting-end date must match the official
[SEC submissions record](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
before its filing date is retained as such; exhibits and annual-report booklets do not
inherit the parent filing's date. Explicit publication evidence remains separate and retains its provenance. Event, period-end and PDF creation dates
are never used as publication dates. SEC fiscal-calendar metadata can establish
fiscal quarters; date-derived quarter/half labels otherwise remain unknown.
Set `STOCK_SEC_USER_AGENT` to your identifying SEC request user agent if needed.
Blocked or unavailable lookups leave unresolved fields unknown.

Interactive imports ask only for unresolved document classification, preserving
numbered category choices, typed categories, and blank/Unknown selection. Other
metadata is extracted automatically or remains Unknown/absent. Noninteractive
imports require an established document type before any files are copied.

Use `stock archive TICKER URL` to import a direct PDF or a webpage with an explicit
`citation_pdf_url` or a single PDF link. Explicit citation/DC title and publisher
and publication-date tags fill document metadata gaps. Source and resolved document
URLs are retained; hosting names and download/modified dates are not publication
evidence. Pages requiring JavaScript, authentication, or a choice among multiple
PDFs require a direct PDF URL or a local download.

Identical bytes reuse the document ID. Incomplete metadata is identified again
without metadata questions, while prior manual corrections are preserved. Metadata
changes do not rerun a completed PDF conversion. Import source URLs are also
recorded when the same PDF was previously imported locally.

Supported originals are PDF, UTF-8 Markdown, and UTF-8 text. PDF inspection reuses
a locally installed PyMuPDF interpreter, discovered from Python or the `pymupdf`
launcher. Set `STOCK_PDF_PYTHON=/path/to/python` if needed. PDF conversion reuses
`pdfmd` and its existing Marker setup, with local `pymupdf4llm` as a fallback when
installed in the PDF interpreter. Neither conversion route requests an LLM.
Conversion output is quiet; Markdown and PDF share a basename. Image assets are
stored in a per-document `.assets` directory with updated Markdown links. No new
PDF engine or model is bundled. Scans without extractable text may require manual
type selection and retain an unknown title/period/date; OCR quality depends on
the installed converter. Conversion has a ten-minute limit for pdfmd and five
minutes for the fallback.

Browser controls: ↑/↓ selects a document, Space expands metadata in place,
O opens its original, M opens its Markdown, and Esc exits. Unknown dates display
as `Unknown`. Narrow terminals wrap document identity and expanded metadata;
PgUp/PgDn scroll long expansions.
The original uses the system viewer; Markdown uses `STOCK_MARKDOWN_VIEWER` when
set (an executable and optional arguments, without shell expansion), otherwise
the system viewer. For example, `STOCK_MARKDOWN_VIEWER='open -a Typora'` on macOS.
Sort, Sources, and commentary topic classification are not implemented.

### Portable metadata enrichment

```sh
stock archive CRWV.US https://example.com/report.pdf
stock archive CRWV.US --metadata ~/Downloads/CoreWeave_Archive_Metadata.json
```

`--metadata` permanently enriches **existing** archive records. It does not
import documents, duplicate them, or rerun conversion. Run ordinary file imports
first for documents that are not yet archived. The four supplied CoreWeave files
can be imported from `~/Downloads/CoreWeave_Test/`. An unmatched or ambiguous
record rejects the batch before updates. Conflicting manual corrections require
a one-line keep/JSON choice; Enter keeps the correction. Noninteractive conflicts
fail without changes. Keep decisions are remembered for the same incoming and retained values, so
repeated imports do not prompt again. Changed proposals require a new decision.

The versioned envelope and fields are defined in
[`docs/archive-metadata.schema.json`](docs/archive-metadata.schema.json). Example:

```json
{
  "schema_version": "stock.archive.metadata.v1",
  "ticker": "CRWV.US",
  "issuer": "CoreWeave, Inc.",
  "documents": [{
    "match": {
      "original_filename": "CoreWeave-Q1-2026-Transcript.pdf",
      "content_indicators": ["Corrected Transcript", "FactSet CallStreet", "Q1 2026 Earnings Call"]
    },
    "metadata": {
      "type": "Transcript",
      "period": "Q1-2026",
      "title": "CoreWeave Q1 2026 Earnings Call — Corrected Transcript",
      "publisher": "FactSet CallStreet, LLC",
      "publication_date": null,
      "publication_date_basis": "First public availability not established",
      "event_date": "2026-05-07",
      "document_date": "2026-05-07"
    }
  }]
}
```

Matching supports `original_filename`, `official_document_url`, `document_id`,
`sha256` (also `source_sha256`), and `content_indicators`. A filename or database ID
alone never authorizes enrichment. Supply an exact SHA-256 or at least two
substantive content indicators (25 normalized characters combined), with an optional known
filename, URL or ID to narrow candidates. All indicators must occur in the original content; detected
type, period, accession and claimed issuer must agree. Duplicate records, duplicate
JSON keys, invalid dates, unsupported versions and unknown fields are rejected.
Dates use ISO `YYYY-MM-DD` or `null`. Each date can have `_basis` and
`_evidence_url` fields. Other fields include `report_period_end`, `sec_cik`,
`sec_accession`, `sec_filing_type` and `publisher_evidence`.

Publication, filing, document, event and reporting-end dates remain distinct.
The supplied v1 example labels two SEC filing dates as publication dates; the
importer retains these as **filing dates** and leaves publication unknown. Its
presentation date based on a dated cover is retained as a **document date**.
The transcript's May 7 call date never establishes publication. Filenames use
`undated` when publication is unknown; expanded Archive rows show the other dates
with their meanings and evidence. Exact titles and publishers remain in SQLite.

Ordinary imports inspect text and embedded metadata, retain original URLs, and
reuse metadata on duplicate imports. Explicit embedded source-page URLs receive
a bounded lookup: page metadata is accepted only when the identified PDF's SHA-256
matches the local document. Primary SEC filings require issuer/accession/form/
report-end agreement; SEC filed-as-of dates remain filing dates. Missing issuer
publishers on annual/quarterly reports and presentations can be resolved from SEC
issuer records when the document cover independently identifies that issuer.
Third-party transcript publishers are recognized from the document itself.
Offline, blocked and missing-source results leave fields unknown without research
prompts. There is no crawler, LLM, or access-restriction workaround. Documents
without an identifying source link or SEC identity may remain unresolved.

SQLite is authoritative; JSON is portable interchange, never a parallel database.
The Python API `stock.archive.export_metadata(store, ticker)` returns a v1 envelope
from stored values for serialization with `json.dump`. Enrichment preserves document
and file IDs, original bytes/hashes and conversion status. PDF/Markdown/assets are
renamed together and Markdown asset links updated. Batch database updates and
file publication roll back together on failure; existing files are never overwritten.

## Sort and Sources

```sh
stock sort CRWV.US
stock sort CRWV.US --review-only
stock sources CRWV.US
stock sort CRWV.US --reset DOCUMENT
```

Sort builds distinct, material investment insights by default: source preparation →
materiality distillation → editorial reconstruction → factual verification → semantic
deduplication → insight publication. It uses existing archived Markdown. Convert or restore missing Markdown through Archive first. Stock assigns
stable document/hash/offset candidate IDs to coherent paragraphs and sentence groups.
Cursor judges relevance, fixed topics and supported speaker categories, returning
compact IDs rather than reproduced quotations. Stock reconstructs selected text
from verified source characters; repeated wording at different locations is distinct.
Tables and layout context can support explicit editorial reconstructions;
non-substantive operator turns are excluded.

The installed, authenticated Cursor Agent CLI runs in an empty disposable workspace
under `.data`, in read-only ask mode with shell, file, web and MCP permissions denied.
Source text is sent to Cursor's service using existing authentication (`agent login`).
Stock validates JSON, IDs, topics, roles and source hashes. JSON/schema errors receive
bounded retries; process timeouts retain staging without automatic retries, and
authentication/quota rejection stops further calls. A single in-place line shows
`Document · Progress · Stage · Total elapsed`. Diagnostics stay in `.data/sort-logs/*.jsonl`
and the local audit tables. Ctrl+C terminates active child process groups and preserves
completed checkpoints.

Successful documents publish atomically and freeze their original topics/citations.
Ordinary Sort preserves completed evidence and manual topic overrides. It automatically
builds missing or stale semantic groups as reversible audited revisions, using cached
equivalence judgments. When evidence and groups are current, it makes no Cursor calls
and creates no revision. Version 3 checkpoints are isolated from legacy checkpoints, which
remain available for audit. Rejected candidates are recorded independently; valid
selections survive. Source integrity failure prevents publication.

```sh
stock sort CRWV.US --rebuild 13
stock sort CRWV.US --rebuild 2026-02-26--presentation--Q4-2025.md
```

`--rebuild DOCUMENT` accepts an Archive ID or unambiguous archived filename for a
completed or incomplete document. It stages extraction while existing evidence
remains visible, then prints counts, quality indicators, representative quotations
and manual-override transfer results. `--rebuild DOCUMENT` authorizes atomic replacement
of only that document after extraction, independent verification and complete incremental
semantic grouping succeed. No keyboard confirmation is required. Interruption or failure
preserves published data. Add `--review-only` to preview a rebuild without publication.
Unmatched manual corrections block replacement until manually reconciled; Stock
does not guess matches or silently discard corrections. Concurrent rebuilds of the
same document are locked out. `--reset DOCUMENT` continues to restore frozen topic
assignments by removing overrides, without extraction or classification.

The eight fixed topics are **Market, Product, Operations, Financials, Capital,
Organization, Macro, Valuation**. Memberships may be multiple or empty. Categories
remain **Management, Investor, Media**. Stock constructs transcript turns from
name/role rosters, including plain name lines, before Cursor classifies evidence.
Unverified individual names stay null. Original PDFs and Markdown are unchanged;
new quotations carry exact Markdown offsets, its SHA-256, and original references.
Sources preserves frozen legacy citations, native terminal colors and topic editing.

`stock sort CRWV.US --review-only` previews proposed insights across pending documents
and frozen evidence without publishing evidence or activating groups. It may call Cursor
for uncached judgments. Normal Sort activates fully validated grouping revisions
automatically; `--rebuild DOCUMENT` also publishes automatically after all checks. `--insights` remains a hidden
compatibility alias. Manual topic corrections and explicit ungrouping remain intact.
For larger archives, rebuild first computes local embedding similarities,
then asks Cursor to verify only pairs passing a provisional high-similarity gate.
It reuses valid judgments and preserves unaffected groups. Small-library
compatibility still uses exhaustive comparison pending calibration. Large libraries require installing
`.venv/bin/python -m pip install -e '.[semantic]'` before rebuilding; no
unreviewed similarity score authorizes a merge. The index is a high-recall
candidate heuristic, not a complete equivalence proof. See
[the semantic-map architecture and validation limits](docs/semantic-map.md). Unresolved historical-only work is
reported separately; an incremental revision does not claim global completeness.
See [the measured rebuild correction](docs/incremental-rebuild.md).

Defaults are **12 minutes per document**, **20 minutes per command**, **12 Cursor
requests per document**, and **120 seconds per request**. Override with
`--document-seconds`, `--command-seconds`, `--cursor-requests`, and `--request-seconds`.
Preparation, startup, retries and grouping share monotonic deadlines. A grouping-only
run uses one document-sized Insights budget. Exhaustion cancels the child group,
retains staging and cached decisions, and prints the resume command and log path.
Incomplete evidence or semantic grouping is never activated; run the same command
to resume. Human review time counts against the deadline; publication rechecks it.

See [the unified replay measurements and limitations](docs/unified-sort.md) and
[semantic rules and the original CoreWeave replay](docs/semantic-insights.md).

See [the workflow profile, benchmark and resume behavior](docs/sort-efficiency.md)
for compact source transport, cached PDF preparation, independent review reuse and
bounded missing-citation repair.

See [the diagnosis and sample evaluation](docs/sort-diagnosis.md) for demonstrated
failures, regressions, quality findings and remaining limits. Archived user documents
remain excluded from Git; small regression excerpts are included under `tests/fixtures`.

Publication dates come only from archived provenance explicitly establishing public
availability with an evidence URL. Cover dates, call dates, bare user-supplied dates,
and filing dates without verified public-availability provenance show **Unknown**.
Stock does not invent earlier publication dates or ask Cursor to supply dates.
Passages appear newest verified public date first, followed by Unknown dates.

Sources controls:

- ↑/↓ navigates; → opens a topic; ← returns to the topic list; Esc quits Stock.
- Space expands/collapses the insight and its visible supporting statements/citations in place. Date/speaker columns stay
  fixed, and continuation text wraps at the passage column on resize.
- N/P selects a supporting member. T opens/closes its inline eight-topic checklist.
  ↑/↓ navigates topics; Space toggles membership and saves immediately to SQLite.
  A passage removed from the active filter stays visible while its checklist is
  open. Closing it selects the next available row. Speaker/date editing is excluded.
- F opens/closes an inline file selector containing All and archived filenames.
  ↑/↓ selects; →/Enter applies the filter within the current view.
- O opens the original document in the system viewer and displays its citation,
  physical page when available, Markdown section/character reference, speaker,
  verification basis, and date provenance inline. Page navigation in the external
  viewer is viewer-dependent.

U ungroups an insight in an audited revision; all evidence and topics remain.
Counts distinguish insights from supporting passages, with a distinct total. Topic
counts use effective member memberships and may overlap across topics. File/topic
filters restrict displayed support and canonical wording to eligible members.
**Unclassified** includes support with no effective topic; it is not a ninth topic.
Internal passage IDs are never displayed. Price, Archive, Sources, their scrolling
containers, and annotation editing use ANSI terminal-default foreground/background.
The editor caret and selection use reverse video, preserving light, dark, and
transparent terminal profiles without fixed RGB fills.

Run focused checks with `.venv/bin/pytest -q`. An opt-in real archive check,
`PYTHONPATH=. .venv/bin/python tests/verify_sort_real.py`, verifies the existing
CoreWeave transcript, quarterly and annual sections with fresh authenticated Cursor
extractions, then converts and sorts a copied real presentation PDF. It mutates
only disposable database/file copies and saves verification responses in `.data`.

For real terminal output verification,
`tests/verify_native_terminal.py` captures all three apps through a PTY using light
and dark terminal color responses, and rejects explicit foreground/background SGR
colors. Run the real archive check first to create its verified evidence fixture. The
terminal check copies the existing archive database into `.data`, adds that fixture
only to the copy, and leaves all captures under `.data`. Real Cursor calls are deliberately outside the ordinary test
suite to avoid repeated calls over full archived reports.

Local PDF fidelity review (staged and inactive):

```sh
.venv/bin/python -m stock.pdf_review SOURCE.pdf "$(mktemp -d /tmp/stock-pdf-review.XXXXXX)/conversion" --pages 4,5,6,14,15 --seconds 240
```

This explicit review mode uses balanced layout and forced local Surya OCR, with
Marker's optional LLM enhancements disabled. It leaves archive conversion defaults
and existing citations unchanged. Omit `--pages` for the entire PDF (default
30-minute bound); use `--profile current` for a fast/automatic comparison. It uses
the existing Marker Python at `~/.venvs/marker/bin/python` (`--python` overrides it)
and requires the installed weights and existing local Surya inference services;
it never starts or stops shared services. Output must be a new directory outside
Research, production data, and the source directory. It retains Markdown, images,
Marker page metadata, configuration, source/output hashes, versions and resource
metrics. Marker `{n}` page markers are zero-based: PDF page = n + 1. Diagrams and
chart relationships still require visual review; this is not verified investment
evidence. See [the measured comparison](docs/benchmarks/marker-ocr/report.md).

Selective Archive conversion repair is available with `stock archive CRWV.US --repair 13`.
It preserves published evidence and prepares an immutable candidate for the existing
reviewed Sort rebuild. See [Archive quality workflow](docs/archive-quality-workflow.md)
for commands, provenance, measured local results and the fresh-extraction limitation.
