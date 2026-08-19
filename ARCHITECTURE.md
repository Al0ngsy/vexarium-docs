# VEXARIUM — Architecture

High-level system topology, component responsibilities, and data flow.

## System topology

```
Browser (SvelteKit SPA, gridstack widget grids)
   │  /api/v1/*  (HTTP/JSON + SSE)
   ▼
FastAPI backend (modular monolith, port 8000)
   │
   │   ├── services/  ──  AlpacaClient (bars/quotes/news/options, Yahoo fallback)
   │   │                 IndicatorEngine (16 indicators)
   │   │                 AI analyzer (deepseek-v4-flash-free via OpenCode Zen,
   │   │                   fallback model chain, streaming)
   │   │                 cache (Redis-or-in-memory TTL), single-flight AI locks
   │   │                 news sentiment, options analyzer (Black-Scholes + P/L
   │   │                 matrix), strategy engine, company info (Yahoo/
   │   │                 stockanalysis.com/Wikipedia), quote stream (Alpaca IEX
   │   │                 WebSocket fanned out to SSE clients)
   │
   ├── PostgreSQL  ──  users/tiers/Stripe-customer mapping (SQLAlchemy async)
   └── Redis       ──  app cache (bars/news/analysis/AI/company) + single-flight
                       locks; falls back to in-memory TTLCache when unset
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
│   ├── billing.py portfolio.py options.py strategies.py stream.py trades.py
├── services/           # business logic (no HTTP)
│   ├── alpaca_client.py      # Alpaca data + Yahoo bars fallback
│   ├── company_info.py       # keyless company/ETF profile + fundamentals
│   ├── indicator_engine.py   # indicator registry, core 5 indicators
│   ├── indicators/extended.py# 11 more indicators (all free)
│   ├── ai_analyzer.py        # LLM prompt build + call (sync + stream), model chain
│   ├── cache.py              # Redis-or-TTL cache, key builders, single-flight locks
│   ├── news_service.py chart_series.py verdicts.py stance.py
│   ├── options_analyzer.py strategy_engine.py quote_stream.py
│   ├── auth.py stripe_service.py exceptions.py
├── middleware/         # rate_limit.py validation.py tier_gating.py logging.py
├── models/  repositories/  schemas/   # persistence + DTOs
```

`main.py` mounts all routers under the `/api/v1` prefix. A router's routes
live in the matching `api/*.py` module.

## Frontend layout

```
frontend/src/
├── routes/
│   ├── +layout.svelte                     # shell + TopBar nav
│   ├── +page.svelte                       # home: symbol search + recent analyses
│   ├── s/[symbol]/+page.svelte            # ANALYSIS view — gridstack widget grid
│   │                                      #   (price-chart, vitals, indicator-checks,
│   │                                      #    ai-opinion, news, company, watchlist)
│   ├── options/[symbol]/+page.svelte      # OPTIONS view — widget grid
│   │                                      #   (options-chain, payoff-explorer, greeks,
│   │                                      #    probability, pl-matrix, strategies, watchlist)
│   ├── pricing/+page.svelte               # plans + Stripe checkout
│   ├── portfolio/+page.svelte             # saved trades (in-memory backend)
│   └── legal/{disclaimer,terms,privacy,impressum}/   # legal pages
├── components/
│   ├── grid machinery: WidgetGrid, WidgetCard, WidgetLibrary
│   ├── analysis: IndicatorChart, CompanyProfile, SymbolStrip, WatchlistWidget,
│   │             SaveTradeModal, TradeCard, DisclaimerBanner
│   ├── options: OptionsChainWidget, OptionsChain, OptionsMatrix, MatrixWidget,
│   │            PayoffWidget, PayoffExplorer, PayoffChart, GreeksWidget,
│   │            ProbabilityWidget, StrategyWidget, StrategyCard
│   └── shared: TopBar, SymbolSearch, InfoPopover, LegalLayout, ConsentBanner
├── lib/
│   ├── api.ts              # typed fetch wrappers to the backend
│   ├── types.ts            # shared TypeScript types mirroring backend schemas
│   ├── layout.svelte.ts    # widget defs (ANALYSIS_WIDGETS/OPTIONS_WIDGETS),
│   │                       #   per-view localStorage layout persistence, liveSizes
│   ├── contract.svelte.ts  # options store: chain/expiries/payoff/strategies/greeks
│   ├── quotes.svelte.ts    # SSE quote stream for SymbolStrip/WatchlistWidget
│   ├── auth.svelte.ts      # JWT state (rune store, .svelte.ts required)
│   ├── storage.ts          # localStorage: recent analyses, trades, watchlist, consent
│   ├── markdown.ts         # safe (XSS-escaped) mini-markdown for AI output
│   ├── indicator-explain.ts# beginner explanations for the checks table
│   ├── chart-theme.ts      # lightweight-charts theme
│   ├── verdict.ts          # verdict → color/label maps
│   └── format.ts           # formatPrice, formatTimeAgo, …
└── app.css                 # Professional Dashboard V2 design tokens (CSS vars)
```

## Request → response flow (analysis)

1. User types a symbol → home page debounced autocomplete calls
   `GET /api/v1/assets/search?q=...` (Alpaca asset list + keyless Yahoo merge).
2. User opens a symbol → `s/[symbol]` → `POST /api/v1/analysis` (full report)
   + `GET /api/v1/analysis/bars/{symbol}?timeframe=` (chart data at a selectable
   resolution: 1m/5m/15m/30m/1h/4h/1d/1w/1mo), plus the independent fast loads
   `GET /analysis/finnhub/{symbol}`, `GET /analysis/market-news` and
   `GET /analysis/fear-greed` — separate from the slow report so widget
   content paints as it arrives.
3. Backend: `validate_symbol` → `AlpacaClient.get_stock_bars` (OHLCV, cached
   per `bars:{symbol}:{timeframe}`, TTL = bar duration for intraday, 6h for
   daily+; intraday source chain = Twelve Data real-time → Alpaca → Yahoo) →
   `IndicatorEngine.compute_all(df)` →
   `aggregate` verdict → chart series + news sentiment + company profile.
4. The **whole analysis result is cached per symbol per timeframe per day**
   (daily bars → computed result changes at most once/day).
5. Frontend renders the widget grid: price chart → vitals → indicator checks →
   AI opinion (SSE stream) → news → company → watchlist. Each widget can be
   toggled/dragged/resized (gridstack); layout persists in localStorage.
6. The AI opinion auto-runs via `POST /api/v1/analysis/ai/stream` (SSE),
   single-flight locked per symbol so only one LLM call happens at a time.

## Key invariants

- **Analysis only.** No order placement anywhere. Always a "not financial
  advice" disclaimer.
- **Data source is Alpaca + Yahoo fallback.** Indices (SPX, etc.) are NOT in
  the bar-data universe → they return 404 "No data found". OTC/foreign ADRs
  fall back to Yahoo bars.
- **Everything is free except options chance-of-profit.** All 16 indicators
  and the AI analysis are open (`middleware/tier_gating.py` gates only
  `GET /options/{symbol}/chance`). In dev, flip `DEV_FORCE_PRO=true` in
  `backend/.env` to treat everyone as Pro.
- **Caching is daily** for bars/news/analysis/AI, seconds for quotes. See
  `DATA_AND_INDICATORS.md`.

See `API.md` for the full endpoint surface and `DATA_AND_INDICATORS.md` for
the caching + indicator model.
