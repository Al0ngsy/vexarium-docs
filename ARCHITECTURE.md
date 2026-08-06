# VEXARIUM — Architecture

High-level system topology, component responsibilities, and data flow.

## System topology

```
Browser (SvelteKit SPA)
   │  /api/v1/*  (HTTP/JSON)
   ▼
FastAPI backend (modular monolith, port 8000)
   │
   │   ├── services/  ──  AlpacaClient (bars/quotes/news/options)
   │   │                 IndicatorEngine (10 free indicators)
   │                 AI analyzer (deepseek via ollama-cloud)
   │                 cache (Redis-or-in-memory)
   │                 news sentiment, options analyzer (Black-Scholes + P/L matrix), strategy engine
   │
   ├── PostgreSQL  ──  users, trades/portfolio (via repositories/)
   └── Redis       ──  rate-limit + cache (falls back to in-memory TTL cache)
```

**Modular monolith:** one FastAPI app + Postgres + Redis. Everything is under
`backend/app/` — no microservices.

## Backend layout

```
backend/app/
├── main.py             # FastAPI app, CORS, rate-limit wiring, route mounting
├── config.py           # pydantic-settings Settings (env + .env)
├── api/                # HTTP route modules (one router per resource)
│   ├── health.py auth.py analysis.py ai.py assets.py
│   ├── billing.py portfolio.py options.py strategies.py trades.py
├── services/           # business logic (no HTTP)
│   ├── alpaca_client.py indicator_engine.py ai_analyzer.py news_service.py
│   ├── cache.py chart_series.py options_analyzer.py stance.py
│   ├── strategy_engine.py stripe_service.py verdicts.py
│   └── indicators/extended.py     # the 5 additional indicators (all free now)
├── middleware/         # rate_limit.py validation.py tier_gating.py logging.py
├── models/  repositories/  schemas/   # persistence + DTOs
```

`main.py` mounts all routers under the `/api/v1` prefix. A router's routes
live in the matching `api/*.py` module.

## Frontend layout

```
frontend/src/
├── routes/             # SvelteKit routes
│   ├── +page.svelte                        # home: search + autocomplete + recent
│   ├── analysis/[symbol]/+page.svelte      # technical analysis view
│   ├── options/[symbol]/+page.svelte       # options chain / Greeks / P/L matrix
│   ├── pricing/+page.svelte                # plans + Stripe checkout
│   ├── portfolio/+page.svelte              # saved trades
│   └── legal/{disclaimer,terms,privacy,impressum}/   # legal pages
├── components/         # IndicatorCard, IndicatorChart, PayoffChart, StrategyCard,
│                       # TradeCard, SaveTradeModal, VerdictBadge, InfoPopover, LegalLayout,
│                       # ContractPicker, PayoffExplorer, OptionsMatrix
├── lib/
│   ├── api.ts          # typed fetch wrappers to the backend
│   ├── types.ts        # shared TypeScript types mirroring backend schemas
│   ├── storage.ts      # localStorage (recent analyses)
│   ├── chart-theme.ts  # Amber Health Check lightweight-charts options
│   ├── verdict.ts      # verdict → color/label/icon maps
│   └── format.ts       # formatPrice, formatTimeAgo
└── app.css             # global Amber Health Check design tokens (CSS vars)
```

## Request → response flow (analysis)

1. User types a symbol → home page debounced autocomplete calls
   `GET /api/v1/assets/search?q=...` (Alpaca `get_all_assets`, filtered).
2. User runs analysis → frontend navigates to `/analysis/[symbol]` →
   calls `POST /api/v1/analysis`.
3. Backend: `validate_symbol` → `AlpacaClient.get_stock_bars` (daily OHLCV,
   cached 6h) → `IndicatorEngine.compute_all(df)` → `aggregate` verdict →
   `_build_series_payload` (chart data) → fetch news sentiment + articles.
4. The **whole analysis result is cached per symbol per day** (daily bars →
   computed result changes at most once/day). Repeat lookups are nearly free.
5. Frontend renders: verdict hero → news sentiment + headlines dropdown →
   price chart → indicator cards (with mini-charts) → optional AI analysis.

## Key invariants

- **Analysis only.** No order placement anywhere. Always a "not financial
  advice" disclaimer.
- **Data source is Alpaca daily bars.** Indices (SPX, etc.) are NOT in the
  tradable-asset / bar-data universe → they return 404 "No data found".
- **All indicators are free.** The Pro tier gates **AI analysis only**
  (`middleware/tier_gating.py`). In dev, flip `DEV_FORCE_PRO=true` in
  `backend/.env` to treat everyone as Pro.
- **Caching is daily** for bars/news/analysis, seconds for quotes. See
  `DATA_AND_INDICATORS.md`.

See `API.md` for the full endpoint surface and `DATA_AND_INDICATORS.md` for
the caching + indicator model.
