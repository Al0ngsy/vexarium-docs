# VEXARIUM — Conventions & Gotchas

Non-obvious conventions and foot-guns that will otherwise waste time. **Read
this before changing anything.**

## The PYTHONPATH shadow (backend)

This dev environment exports a `PYTHONPATH` that shadows the project venv.
Every Python command must strip it:

```bash
env -u PYTHONPATH .venv/bin/python -m pytest tests/ -q
env -u PYTHONPATH .venv/bin/uvicorn app.main:app --reload
```

Or add `unset PYTHONPATH` to `~/.zshrc`. If you forget, imports resolve to the
wrong packages and tests behave differently.

## Yarn, never npm (frontend)

Frontend uses Yarn Berry 4.17.0 (node-modules linker, pinned in
`.yarn/releases/`). Always `yarn install` / `yarn dev` / `yarn check` /
`yarn build`. `npm` will fight the `.yarnrc.yml` config.

## `.env` inline comments corrupt values

`pydantic-settings` reads the **entire** line after `=`. `KEY=value # comment`
makes the value `"value # comment"`. No inline comments in `.env`.

## Indices return 404 — that's correct

Alpaca does not provide bar data for indices (SPX, NDX…). `POST /analysis
{symbol:"SPX"}` → 404 "No data found". This is expected. Do not synthesize
data. Stocks and ETFs (AAPL, SPY) work fine. OTC/foreign ADRs (SMERY, RNMBY)
fall back to Yahoo bars automatically.

## Options: volume / open interest / 0 DTE / delayed feed

- Alpaca's free/paper tier does **not** provide option **volume** or **open
  interest**. Do not fabricate. The chain response omits them and the UI drops
  those columns.
- **0 DTE (same-day) option contracts have no greeks/IV** on Alpaca. The `/chain`
  endpoint deliberately skips today's expiry so the default view stays
  meaningful.
- The free options feed is **indicative and ~15 min delayed**; responses carry
  `delayed: true` and the frontend shows a "DELAYED" badge.
- Market-data option endpoints and the Trading API have **separate** rate limits
  (each 200 req/min default on the free tier).

## Asset type detection is heuristic

Alpaca's `asset_class` is always `"us_equity"`. ETF vs stock is inferred from
the asset **name** (`"ETF"`/`"Trust"`/`"Fund"`). Indices are not in the
tradable-assets API at all. The frontend has no manual asset-type selector —
it's derived from the chosen symbol.

## Cache keys carry the timeframe

`bars:{symbol}:{timeframe}`, `analysis:{symbol}:{timeframe}:{date}`,
`ai:{symbol}:{timeframe}:{date}`. Don't drop the timeframe when building or
invalidating keys — intraday analysis would collide with daily otherwise.

## Daily caching means stale results within a day

Indicators are computed from **daily** bars, and the whole analysis is cached
per symbol per timeframe per day (24h). If you change indicator
logic/verdicts and want to see it immediately, clear that cache key (or bump
the TTL) while developing. Quotes are cached 5s; bars 6h; news 30m; AI 24h.

## Lightweight Charts v5 API

Major-version API change. Use `createChart` + `chart.addSeries(SeriesType, …)`
(not the old `chart.addCandlestickSeries()`). Match against existing
`IndicatorChart.svelte` / `PayoffChart.svelte` usage.

## Chart container must always render

The lightweight-charts container `<div bind:this={container}>` must be in the
DOM unconditionally. Do NOT wrap it in `{#if ... && container}` — the
`container` ref is only set after mount, so that gate deadlocks and renders
nothing ("NO CHART DATA"). Guard on the **data**, not the ref.

## Svelte 5 runes

Use `$state`, `$derived`, `$props`, `$effect`. Do not use legacy `$:`
reactive declarations. Rune stores MUST live in `.svelte.ts` files
(`lib/auth.svelte.ts`, `lib/layout.svelte.ts`, `lib/contract.svelte.ts`,
`lib/quotes.svelte.ts`) — a plain `.ts` throws `$state is not defined`.

## The widget `{#if}` chain is the component registry

Each grid page maps `def.id` → component in an inline `{#if}` chain. Adding a
widget = add a def in `lib/layout.svelte.ts` + a branch in the page snippet.
Keep the two in sync. Do NOT resurrect the old monolithic
`OptionsWorkspace` page — it was deleted (superseded by the widget grid).

## Recent-analyses history is success-only

The analysis page records a symbol into localStorage (`vexarium_recent`) only
after a successful analysis. This prevents failed lookups (e.g. SPX) from
polluting history.

## Tier gating

- `middleware/tier_gating.py` decides free vs pro (`require_tier` dependency).
- **All 16 indicators and the AI analysis are free** — no 403s on
  `/analysis`, `/analysis/ai`, or `/analysis/ai/stream`.
- The **only Pro-gated endpoint is `GET /options/{symbol}/chance`**
  (`require_tier("pro")` → 403 for free/anonymous).
- Dev: `DEV_FORCE_PRO=true` in `backend/.env` treats everyone as Pro.
- **Never** set `DEV_FORCE_PRO=true` in production.
- `tests/conftest.py` forces `dev_force_pro=False` so tests are deterministic.
- Frontend login/register UI is currently removed; `getToken()` still feeds
  the AI stream and the Pro-gated chance widget.

## AI model chain & token budget

`ai_analyzer.py` tries `LLM_MODEL` then each `LLM_FALLBACK_MODELS` entry on
rate-limit/outage/empty completion. Use `max_tokens: 8192` — this model emits
a `reasoning` field before `content`; a smaller budget (e.g. 300) yields empty
`content` and the feature looks broken (2000 cut briefings mid-sentence).
Streaming skips `reasoning_content` deltas; mid-stream failures propagate
(never swap a partial answer for another model's continuation).

## Error masking

Never leak internal error details to the API client. Map known failures
(`AlpacaError`, `SymbolNotFoundError`, `SubscriptionRequiredError`) to clean
statuses; log the rest and return a generic 500. No `eval`/`exec`/`pickle`;
all SQL is parameterized; symbols pass through `validate_symbol()`.

## In-memory trades (prototype ceiling)

`/api/v1/trades` persists to a module-level dict — data is lost on backend
restart. Marked `ponytail:` in `repositories/trades.py`. Ship the Postgres
store (`models/trade.py` already exists) before treating trades as real data.

## Testing discipline

Backend: extend the pytest suite when you change logic; run with
`env -u PYTHONPATH` (expect **248 passed**). Frontend: `yarn check`
(0 errors) + `yarn build` are the gates. Prefer focused tests over asserting
the whole suite every change.
