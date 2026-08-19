# VEXARIUM — Frontend Guide

How to work in the SvelteKit frontend. Start with `ARCHITECTURE.md`; this file
is the day-to-day frontend cookbook.

## Stack

SvelteKit 2 + Svelte 5 (**runes**) · TypeScript · Tailwind v4 ·
TradingView Lightweight Charts v5 · **gridstack.js** (widget grid) ·
lucide-svelte (icons) · Yarn Berry 4.17.0. Deployed via
`@sveltejs/adapter-cloudflare`.

## Layout

```
src/
├── routes/
│   ├── +layout.svelte                # global shell + TopBar nav
│   ├── +page.svelte                  # home: symbol search (SymbolSearch) + recent analyses
│   ├── s/[symbol]/+page.svelte       # ANALYSIS view — gridstack widget grid
│   ├── options/[symbol]/+page.svelte # OPTIONS view — gridstack widget grid
│   ├── pricing/+page.svelte          # plans + Stripe checkout
│   ├── portfolio/+page.svelte        # saved trades (TradeCard, SaveTradeModal)
│   └── legal/*/                      # disclaimer, terms, privacy, impressum
├── components/
│   ├── WidgetGrid.svelte      # gridstack wrapper: init, drag/resize events, persist
│   ├── WidgetCard.svelte      # one grid item: drag handle, toggle, size readout
│   ├── WidgetLibrary.svelte   # bottom bar: re-add disabled widgets + reset layout
│   ├── analysis: IndicatorChart, CompanyProfile, SymbolStrip, WatchlistWidget,
│   │            SaveTradeModal, TradeCard, DisclaimerBanner
│   ├── options: OptionsChainWidget, OptionsChain, OptionsMatrix, MatrixWidget,
│   │            PayoffWidget, PayoffExplorer, PayoffChart, GreeksWidget,
│   │            ProbabilityWidget, StrategyWidget, StrategyCard
│   └── shared: TopBar, SymbolSearch, InfoPopover, LegalLayout, ConsentBanner
├── lib/
│   ├── api.ts        # typed fetch wrappers (analyze, getBars, streamAIAnalysis,
│   │                 #   getAIAnalysis, options, strategies, stance, auth, searchAssets)
│   ├── types.ts      # TS types mirroring backend schemas
│   ├── layout.svelte.ts # widget defs + per-view layout persistence + liveSizes
│   ├── contract.svelte.ts # options store: chain/expiries/payoff/strategies/greeks
│   ├── quotes.svelte.ts   # SSE quote stream for SymbolStrip/WatchlistWidget
│   ├── auth.svelte.ts     # JWT state (rune store)
│   ├── storage.ts    # localStorage: recent analyses, trades, watchlist, consent
│   ├── markdown.ts   # safe (XSS-escaped) mini-markdown for AI output
│   ├── indicator-explain.ts # beginner explanations for the checks table
│   ├── chart-theme.ts # lightweight-charts options + colors
│   ├── verdict.ts    # verdict → color/label maps
│   └── format.ts     # formatPrice, formatTimeAgo, …
└── app.css           # Professional Dashboard V2 design tokens (CSS custom properties)
```

## Key commands

```bash
cd frontend
corepack enable        # once
yarn install
yarn dev               # http://localhost:5173
yarn check             # svelte-check — gate (expect 0 errors)
yarn build             # adapter-cloudflare build — gate
```

**Use `yarn`, never `npm`.**

## Design system (Professional Dashboard V2)

Defined in `src/app.css` as CSS custom properties (`--background`,
`--surface`, `--surface-2`, `--surface-3`, `--panel-border`,
`--foreground`, `--foreground-muted`, `--accent-primary`, …). Base palette:

- flat solid dark `#0a0c10` background — **no gradients, no radial glows**
- blue `#3b82f6` accent (hover `#2563eb`)
- sentence case labels (no UPPERCASE micro-labels)
- 8–10px card radius
- full-width 12-column widget grid (gridstack.js)
- no health-check / cockpit / metaphor vocabulary

Typography: Space Grotesk (display), Inter (body), JetBrains Mono
(prices/Greeks/P&L) via `@fontsource`.

## Widget grid (the core UX)

Both `s/[symbol]` and `options/[symbol]` are **gridstack widget grids**:

- **Widget defs** live in `lib/layout.svelte.ts`: `ANALYSIS_WIDGETS`
  (price-chart, vitals, indicator-checks, ai-opinion, news, fear-greed,
  company, watchlist, insider, earnings, peers) and `OPTIONS_WIDGETS`
  (options-chain, payoff-explorer, greeks, probability, pl-matrix,
  strategies, watchlist) — each with id/title/x/y/w/h.
- **`WidgetGrid.svelte`** initializes gridstack on the `defs`, dispatches
  drag/resize changes into `liveSizes` (`lib/layout.svelte.ts`), and persists
  positions to localStorage (`vexarium:layout:{view}`).
- **Each page** renders `<WidgetGrid>` with a `{#snippet children({def})}`
  that maps `def.id` → the concrete widget component (an `{#if}` chain). The
  `{#if}` chain is the registry — add a widget by adding a def + a branch.
- **`WidgetCard.svelte`** is one grid item: drag handle, title + sub, live
  `W×H` size readout, and an eye toggle (hide/show widget; layout persists
  enabled-state per widget in `vexarium:layout:{view}:on`).
- **`WidgetLibrary.svelte`** (bottom bar) re-adds disabled widgets and resets
  the layout.
- **`ALL_WIDGETS`** in `layout.svelte.ts` groups the two def lists by view
  (`analysis` | `options`); the enabled-state and grid key come from the same
  module. The actual component mapping is the page's snippet.

## Charts (Lightweight Charts v5)

- `chart-theme.ts` exports `CHART_THEME` (shared layout, includes
  `attributionLogo: false` to hide the TradingView watermark) and
  `PROFIT_COLOR`/`LOSS_COLOR`/`BREAKEVEN_COLOR`.
- `IndicatorChart.svelte`: renders a mini chart from an `IndicatorSeries`
  (+ optional `priceSeries` for overlays). **v5 API:** `createChart` +
  `chart.addSeries(CandlestickSeries, ...)` / `chart.addSeries(LineSeries, ...)`.
- `PayoffChart.svelte`: uses `createOptionsChart` (price-based x-axis).
- The container div must render **unconditionally** (the chart mounts into
  `bind:this`); a `#if ... && container` gate deadlocks it and shows nothing.

## Data flow (analysis page)

1. `+page.svelte` (home): debounced `searchAssets()` → grouped autocomplete
   (STOCK/ETF sections, exact symbol match pinned first). Selecting an asset
   navigates to `s/[symbol]`. Recent analyses are read from localStorage on
   mount; **new analyses are recorded on success only** (a failed analysis
   like SPX is never added).
2. `s/[symbol]/+page.svelte` renders the analysis widget grid:
   - `price-chart`: `getBars(symbol, timeframe)` (any of
     1m/5m/15m/30m/1h/4h/1d/1w/1mo) → candlestick chart.
   - `vitals`: current price, day change, 52w range.
   - `indicator-checks`: the indicator verdicts table with PASS/WATCH/FAIL
     chips + beginner explanations (`indicator-explain.ts`).
   - `ai-opinion`: `streamAIAnalysis(...)` (SSE) → markdown rendered via
     `lib/markdown.ts`; cached answers replay with the same progressive effect.
   - `news`: news sentiment + headlines dropdown.
   - `company`: `CompanyProfile.svelte` — identity facts, valuation grid,
     profitability/growth metrics, 52-week position bar, each metric with a
     beginner tooltip; "VIEW MAIN LISTING" button when `main_listing` present.
   - `watchlist`: saved symbols with live prices via the SSE quote stream.
3. `options/[symbol]/+page.svelte` renders the options widget grid:
   options chain (two-sided CALLS | STRIKE+IV | PUTS, grouped by expiry),
   payoff explorer, Greeks, probability, P/L matrix, strategy suggestions,
   watchlist. A **DELAYED** badge flags the indicative (15-min delayed) feed.
   Volume/OI columns are omitted (data not available).

## Options store

`lib/contract.svelte.ts` is the shared options state (Svelte runes):
`store.symbol`, `loadChain()`, `getExpiries()`, `getSelectedChain()`,
`currentPrice`, `payoff`, `strategies`, `selectedSymbol`, plus loading/error
flags. All options widgets read from it. Widgets keyed on `store.symbol`
reload automatically when the symbol changes (runes `$derived`/`$effect`).

## Auth

- `lib/auth.svelte.ts`: Svelte 5 runes store persisting the JWT + user to
  localStorage (`vexarium_token`, `vexarium_user`). `initAuth`, `getToken`,
  `getUser`, `isPro`, `setSession`, `logout`. **Note the `.svelte.ts` suffix —
  runes in a plain `.ts` file are not compiled and break SSR.**
- The login/register UI is currently **removed** — the backend auth API stays
  live and `getToken()` still feeds the AI stream and Pro-gated options
  chance; restore the UI from git history when login is re-enabled.

## Brand wordmark

The VEXARIUM wordmark is **two-tone**: `VEX` in foreground and `ARIUM` in the
blue accent, in the `TopBar` header.

## Recent analyses / watchlist (localStorage)

- `storage.ts`: `getRecentAnalyses()`, `addRecentAnalysis()`, saved trades,
  watchlist, consent. Dedupes by symbol, newest first, cap 10. Key
  `vexarium_recent`.
- `SymbolStrip` has a **watchlist toggle** (☆ Add to watchlist / ★ Watchlisted)
  that saves the current symbol (with company name) to `vexarium_watchlist`;
  the landing page renders a WATCHLIST section from the same key.
- These are **local** features (not pay features). Daily auto-update is a
  future Pro feature.

## Gotchas

- **Lightweight Charts v5** is a major-version API change from v3/v4 — always
  match against how `PayoffChart.svelte`/`IndicatorChart.svelte` already call it.
- The **asset type is auto-derived** from the selected symbol (Alpaca can't
  distinguish ETF/stock, so it uses name heuristics on the backend). There is
  no manual asset-type selector.
- Model name is intentionally NOT shown in the AI panel.
- Svelte 5 runes: use `$state`, `$derived`, `$props`, `$effect` — not the
  legacy `$:` reactive declarations.
- `lib/layout.svelte.ts` and `lib/contract.svelte.ts` / `lib/quotes.svelte.ts`
  / `lib/auth.svelte.ts` MUST keep the `.svelte.ts` extension (runes).
- The `s/[symbol]` page's widget `{#if}` chain is the component registry —
  keep it in sync with the defs in `layout.svelte.ts`.
