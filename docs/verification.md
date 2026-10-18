# Verification · 18 October 2026

- Python 3.14, Textual 6.12.0, Longbridge CLI 0.30.0.
- 13 focused pytest tests passed.
- Fresh authenticated RPC smoke passed: Tencent catalogue search (700.HK among
  21 HK matches), HKD metadata, 1,000 raw daily bars, 1,000 one-minute bars,
  anchored one-minute history, and monthly-chunked HK trading calendar.
- Daily response range: 2022-09-20T16:00:00Z to 2026-10-15T16:00:00Z.
  These correspond to HK dates 21 September 2022 through 16 October 2026.
- Real `stock price 700.HK` rendered in an 80×24 PTY and exited with Esc.
- `stock search Tencent` and numeric search returned canonical tickers;
  `stock price Tencent` rejected the company name.
- Independent code review found no critical or important issues.

Limitations: tests simulate offline failure rather than changing system network
settings. Intraday entitlement fallback is tested with controlled responses;
this account actually returned 1m data. Older dates remain subject to Longbridge
retention and quota. No continuous refresh; zoom windows use trading-observation
counts. See README for cache, historical anchoring, and calendar behavior.

## US/HK extension · 18 October 2026

- Full suite: **34 passed**. Coverage includes US canonical/share-class symbols,
  separate annotation persistence, case-insensitive dual-market search, duplicate
  rank preservation, partial catalogue failures, New York DST/date boundaries,
  HK behavior, independent calendar parameters, short-history zoom limits,
  missing history, permission errors and visible stale-cache failure reasons.
- Fresh authenticated `tests/smoke.py` passed without cache reads:
  - CoreWeave resolves first to CRWV.US; metadata currency USD; 391 daily bars
    (2025-03-28T04:00:00Z through 2026-10-16T04:00:00Z), 1,000 minute bars,
    1,000 anchored minute bars and 21 current trading dates.
  - Tencent resolves first to 700.HK; metadata HKD; 1,000 daily bars
    (2022-09-20T16:00:00Z through 2026-10-15T16:00:00Z), 1,000 minute bars,
    1,000 anchored minute bars and 21 current trading dates.
  - July 1, 2026 is closed in HK and open in US; July 3 is open in HK and
    closed in US, verified with separate fresh trading_days requests.
- Installed CLI 0.30.0 `quote.security_list` returned 16,127 US and 17,142 HK
  records in direct authenticated probes. Official CLI catalogue/RPC docs
  support this route; the older SDK page describes a narrower overnight list.
  No guessed endpoint, scraping, dependency or alternate provider was added.
- `stock search coreweave` and `stock search tencent` displayed canonical
  symbols, company names and explicit market columns without opening Price.
- Actual `stock price CRWV.US` and `stock price 700.HK` inspected in 80×24 PTYs:
  correct headings/currencies, continuous grayscale chart, reserved marker row,
  aligned date/annotation/zoom rows, persistent zoom arrows. Down/Right selected
  zoom and changed 1M → 1W → 1D; anchors remained exchange-local midnight;
  Esc exited with status 0. Existing HK annotation markers remained visible.
- Independent code review found no blocking issues. Duplicate catalogue rank
  robustness and outdated documentation findings were addressed.
- `git diff --check` passed. GitHub API confirmed the existing repository
  MrMittenCrab/stock remains private. No parent repository files were changed.

Entitlements: this account returned real daily and one-minute history for both
requested tickers; no permission limitation was encountered for these requests.
Denied-access handling was verified with controlled failures, without changing
account permissions. Availability for other tickers/dates remains subject to
Longbridge entitlements and retention; unavailable anchored dates leave zoom
unchanged and show an error. Windows retain the existing observation-count
semantics (US regular day 390 minutes; HK 330), rather than synthetic calendar
bars or special half-day window lengths. Existing local caches/annotations and
SQLite schema were preserved; no database migration or data deletion was used.
