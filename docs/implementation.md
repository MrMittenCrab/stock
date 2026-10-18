# Stock implementation
Approved scope: two CLI commands; Textual price terminal; Longbridge JSON-RPC;
project-local SQLite raw OHLCV cache and point annotations; no trading calls.

1. Verify RPC metadata, history, trading calendar and securities search live.
2. Test symbol validation, SQLite persistence, row navigation and anchored zoom.
3. Implement read-only RPC client, paced cache, domain state and chart rendering.
4. Implement Textual keyboard editing and CLI; test headlessly and live.
5. Install in project venv, document, commit and synchronize private stock repo.

US/HK extension: reuse the existing Market, State, and PriceApp; put currency,
timezone and regular-session length in stock/exchanges.py. Canonicalize ticker
keys at storage boundaries without migrating or removing existing HK records.
Search both documented CLI catalogues, deduplicate canonical tickers, rank exact
and close names/tickers, and print markets. Keep the UI layout unchanged.
Use exchange-local dates for chart labels, annotation markers and anchored
history requests; request calendars by market. Bound zoom by returned daily
history and probe available intraday resolution per ticker. Preserve upstream
errors in explicit history failures and cache fallback notices.

Verification: focused US tests followed by the full suite, fresh authenticated
US/HK smoke including independent holidays, real PTY Price inspection, then
review, commit and ordinary push to the existing private repository.
Failures must preserve cached data and identify stale/offline state. Plot only
observed closes, with explicit observation spacing and raw-price labeling.
