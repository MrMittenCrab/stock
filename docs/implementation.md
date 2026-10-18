# Stock implementation
Approved scope: two CLI commands; Textual price terminal; Longbridge JSON-RPC;
project-local SQLite raw OHLCV cache and point annotations; no trading calls.

1. Verify RPC metadata, history, trading calendar and securities search live.
2. Test symbol validation, SQLite persistence, row navigation and anchored zoom.
3. Implement read-only RPC client, paced cache, domain state and chart rendering.
4. Implement Textual keyboard editing and CLI; test headlessly and live.
5. Install in project venv, document, commit and synchronize private stock repo.

Search must filter returned securities to HK and normalize numeric codes.
Failures must preserve cached data and identify stale/offline state. Plot only
observed closes, with explicit observation spacing and raw-price labeling.
