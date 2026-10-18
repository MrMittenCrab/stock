# Stock

Minimal keyboard-only Hong Kong securities terminal. Python 3.11+ and Textual;
read-only market data through Longbridge CLI's supported JSON-RPC interface.

```sh
cd ~/Documents/Developer/stock
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
# Use the installed launcher, or activate this project's environment:
source .venv/bin/activate
stock price 700.HK
stock search Tencent
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
- Timeline ←/→ moves one actual observation; ▲ is selected, ● marks notes.
- Annotation Space toggles full text in place. → expands, then → edits.
- A adds/edits a point note at the selected historical timestamp.
- While editing, arrows move the cursor, Space inserts a space, Enter inserts
  a newline, and Esc saves and leaves editing. Esc outside editing exits Stock.
- Zoom ← widens and → narrows: 1Y, 6M, 3M, 1M, 1W, 1D, 1H. Only the selected
  zoom row shows directional arrows. The historical anchor survives zooming.

Use a monospace terminal; Stock uses the terminal's single font size, grayscale,
and no mouse reporting. 80×24 or larger is recommended. Expanded text pushes
following rows down; selected rows scroll into view in smaller terminals.

## Data behavior and limits

The chart plots **raw closes** from real OHLCV observations, with straight line
segments between them. It uses observation spacing, not elapsed wall-clock time:
weekends, holidays, lunch breaks and missing bars receive no invented points.
Intraday labels and dates use Asia/Hong_Kong. Month/year zooms are approximate
trading-observation windows (21/63/126/252 daily bars), not calendar durations.
The initial fetch contains up to 1,000 daily bars; navigation stops at its edges.

Stock probes 1m, 5m, 15m, 30m, then 1h history to find the finest resolution the
account actually returns. Intraday zoom is disabled if all probes fail. Moving
between daily and intraday bars retains the exact historical anchor; the triangle
uses the nearest returned bar on that HK date. Timeline movement then selects an
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

Search uses the supported **`quote.security_list` with market `HK`**, then matches
names (English and Chinese) or symbols locally. Both the catalogue shape and
Tencent → `700.HK` were verified against the authenticated API. A guessed
`/v1/search/stock` path returned 404 and is **not used**. Search includes other HK
securities returned by Longbridge, such as warrants and bonds; it never opens Price.
See the [RPC contract](https://open.longbridge.com/docs/cli/serve) and
[calendar API](https://open.longbridge.com/docs/market/trade-days).

## Verification

```sh
cd ~/Documents/Developer/stock
.venv/bin/python -m pytest -q
.venv/bin/python tests/smoke.py
```

The smoke script makes fresh authenticated, read-only requests for Tencent search,
metadata, daily and one-minute OHLCV, anchored minute history, and the HK calendar.
It fails if a stale cache fallback was used. Tests cover keyboard editing,
navigation, zoom anchoring across HK midnight, note persistence, validation,
calendar request limits, offline errors, and refusal of trading methods.
