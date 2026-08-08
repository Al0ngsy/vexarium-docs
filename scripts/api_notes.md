---
# Hand-maintained editorial notes, appended verbatim to the generated API.md.
# Facts that change with code go in the generated tables above; judgment
# (gating, caching, gotchas) goes here. Keep it short and current.

All routes are mounted under `/api/v1`. Responses are JSON. Auth is
self-built JWT passed via `token` query param (not OAuth). Rate limits are
applied per-endpoint via slowapi (free 30/min, pro 200/min, AI 10/min —
per-IP; slowapi's in-memory storage, not Redis).

## Auth

> The frontend **login/register UI is currently removed**; the API stays live.
> `getToken()` in the FE still sends a token to the AI endpoints and the
> Pro-gated options chance endpoint.

## Analysis

`AnalysisRequest`:
```json
{ "symbol": "AAPL", "asset_type": "stock", "timeframe": "1d", "options_enabled": false, "strike": null }
```

- `POST /analysis` caches the full result per symbol per timeframe per day
  (`analysis:{symbol}:{timeframe}:{date}`, 24h TTL) — daily bars change at
  most once/day.
- `GET /analysis/bars/{symbol}` — `t` in every point is a **full ISO
  timestamp**; date-only strings collapse intraday timeframes onto one point.
- `POST /analysis/ai` and `/analysis/ai/stream` are **free for everyone** —
  no tier gating. Per-IP 10/min (`RATE_LIMIT_AI`); result cached per symbol
  per timeframe per day (`ai:{symbol}:{timeframe}:{date}`); single-flight
  locked so concurrent requests share one LLM call. The stream endpoint is
  SSE (`data: {"chunk":"..."}`) and replays cached answers chunk-by-chunk.
- `company.main_listing` (only present for **OTC/foreign ADRs** like `RNMBY`,
  `SMERY`): the primary home-exchange listing, resolved keylessly via Yahoo
  search — `RNMBY → RHM.DE/XETRA`. The frontend shows a "VIEW MAIN LISTING"
  button. Cache key `company:v2:{symbol}` (12h TTL).

## Assets

`asset_type` is `"stock"` or `"etf"`, derived from the asset **name**
(Alpaca's `asset_class` is always `"us_equity"`). Indices are NOT returned.
The Alpaca asset list (~14k symbols) is cached in memory after first load;
keyless Yahoo search results are merged on top (deduped, cached ~60s
`ysearch:{q}`), so "Rheinmetall" → `RHM.DE` before the OTC ADR `RNMBY`.

## Options

> **Frontend:** `options/[symbol]` is a **gridstack widget grid** (chain,
> payoff, Greeks, probability, P/L matrix, strategies, watchlist). A
> **DELAYED** badge flags the indicative (15-min delayed) feed. Volume/OI
> columns are omitted (not available on the free tier).
>
> **Gating:** `GET /options/{symbol}/chance` is **PRO-ONLY — 403 for
> free/anonymous users** (the only gated endpoint in the app).
> `DEV_FORCE_PRO=true` bypasses it in dev; never in production.

## Portfolio

`POST /portfolio/stance` thresholds come from `TAKE_PROFIT_THRESHOLD`
(default 0.10) / `CUT_LOSS_THRESHOLD` (default -0.08). `current_price` is
optional — the server fetches the live quote when omitted (the client only
stores entry prices).

## Trades

> ⚠ **In-memory persistence** — trades live in a module-level dict and are
> LOST on backend restart (Postgres store was never built). Fine for the
> prototype; ship a DB-backed store before treating trades as data.

## Billing

> **Stripe is fully integrated, not stubbed.** Real `STRIPE_SECRET_KEY`,
> `STRIPE_WEBHOOK_SECRET`, and a non-placeholder `STRIPE_PRICE_ID` are
> required for checkout to work (the service raises a clear ValueError on the
> placeholder `price_pro_monthly`). The webhook is the only path that unlocks
> Pro — register `<backend>/api/v1/billing/webhook` in the Stripe dashboard.

## Stream

SSE events: `data: {"symbol":"AAPL","price":213.44,"size":100,"ts":"..."}`,
heartbeat `: ping` comment every 20s. One upstream Alpaca IEX WebSocket is
fanned out to all subscribers (`services/quote_stream.py`); max 20 symbols.
