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
