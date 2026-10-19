# Stock

Minimal keyboard-only US and Hong Kong securities terminal. Python 3.11+ and Textual;
read-only market data through Longbridge CLI's supported JSON-RPC interface.

```sh
cd ~/Documents/Developer/stock
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
# Use the installed launcher, or activate this project's environment:
source .venv/bin/activate
stock price 700.HK
stock search Tencent
stock search coreweave
stock price CRWV.US
```

The current machine also has `~/.local/bin/stock` symlinked to the project's
`.venv/bin/stock`, so both commands work without activating the environment.
For another installation, put that directory on PATH and create the same symlink
only if no existing `stock` command occupies it.

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
before its public filing date is used; exhibits and annual-report booklets do not
inherit the parent filing's date. Earlier explicit publication evidence takes
precedence and retains its provenance. Event, period-end and PDF creation dates
are never used as publication dates. SEC fiscal-calendar metadata can establish
fiscal quarters; date-derived quarter/half labels otherwise remain suggestions.
Set `STOCK_SEC_USER_AGENT` to your identifying SEC request user agent if needed.
Blocked or unavailable lookups leave unresolved fields for clarification.

Interactive imports ask compact single-line questions only for unresolved fields:
type, period, date, title and publisher. Numbered choices offer the complete type
taxonomy and plausible periods; blank answers allow Unknown. No TUI opens during
import. Manual answers are marked user-supplied, including deliberate Unknowns.
Noninteractive imports retain unresolved metadata as Unknown; an unresolved type
requires an interactive import before any files are copied.

Identical bytes reuse the document ID. Incomplete metadata is identified again,
with clarification when needed, while manual corrections are preserved. Complete
metadata leaves the record and files unchanged. Metadata changes do not rerun a
completed PDF conversion. Ordinary schema upgrades add per-field provenance and
a separate SEC accession to existing records; existing archives remain editable.

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
O opens its original, M opens its Markdown, E edits metadata inline, and Esc exits.
The editor shows existing values: Tab moves between fields, Enter saves changed
fields, and Esc cancels. Blank/Unknown clears a field; dates use YYYY-MM-DD.
Corrections keep document/file IDs and original hashes, rename archived files and
assets together, and update Markdown links and registered paths. Collisions receive
a hash suffix, and failed updates roll back without replacing existing files. Unknown dates display
as `Unknown`. Narrow terminals wrap document identity and expanded metadata; PgUp/PgDn scroll
long expansions.
The original uses the system viewer; Markdown uses `STOCK_MARKDOWN_VIEWER` when
set (an executable and optional arguments, without shell expansion), otherwise
the system viewer. For example, `STOCK_MARKDOWN_VIEWER='open -a Typora'` on macOS.
Sort, Sources, and commentary topic classification are not implemented.
