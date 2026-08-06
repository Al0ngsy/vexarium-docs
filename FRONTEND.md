# VEXARIUM — Frontend Guide

How to work in the SvelteKit frontend. Start with `ARCHITECTURE.md`; this file
is the day-to-day frontend cookbook.

## Stack

SvelteKit 2 + Svelte 5 (**runes**) · TypeScript · Tailwind v4 · TradingView
Lightweight Charts v5 · Yarn Berry 4.17.0. Deployed via
`@sveltejs/adapter-cloudflare`.

## Layout

```
src/
├── routes/
│   ├── +layout.svelte                # global shell + nav
│   ├── +page.svelte                  # home: symbol search + autocomplete + recent analyses
│   ├── analysis/[symbol]/+page.svelte  # technical analysis view
│   ├── options/[symbol]/+page.svelte   # options chain / Greeks / P/L matrix
│   ├── pricing/+page.svelte            # plans + Stripe checkout
│   ├── portfolio/+page.svelte          # saved trades
│   └── legal/*/                        # disclaimer, terms, privacy, impressum
├── components/       # IndicatorCard, IndicatorChart, PayoffChart, StrategyCard,
│                     # TradeCard, SaveTradeModal, VerdictBadge, InfoPopover, LegalLayout,
│                     # ContractPicker (expiry -> call/put -> strike builder),
│                     # PayoffExplorer (price slider + Black-Scholes value),
│                     # OptionsMatrix (strike×expiry P/L grid),
│                     # OptionsChain (two-sided chain table),
│                     # OptionGlossary (beginner glossary by experience level),
│                     # CompanyProfile (beginner company fundamentals card)
├── lib/
│   ├── api.ts        # typed fetch wrappers (analyze, getAIAnalysis, searchAssets, auth, options)
│   ├── types.ts      # TS types mirroring backend schemas
│   ├── storage.ts    # localStorage: recent analyses (key 'vexarium_recent')
│   ├── chart-theme.ts# Amber Health Check lightweight-charts options + colors
│   ├── verdict.ts    # verdict → color/label/icon
│   └── format.ts     # formatPrice, formatTimeAgo
└── app.css           # global Amber Health Check design tokens (CSS custom properties)
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

## Design system (Amber Health Check)

Defined in `src/app.css` as CSS custom properties:
`--surface`, `--surface-2`, `--surface-3`, `--panel-border`, `--grid-line`,
`--foreground`, `--foreground-muted`, `--foreground-subtle`, `--accent-primary`,
`--accent-white`, `--surface-active`. Base palette:
- cockpit dark `#0b0e13` backgrounds with a soft amber radial glow
- amber `#f59e0b` accents (instrument-light), hover `#fbbf24`
- near-white `#e8edf5` foreground
- 14px card radius, pill chips, UPPERCASE micro labels
- health-check vocabulary: grade ring, vitals row, plain-language box,
  pass/watch/fail chips (`chip-pass`/`chip-watch`/`chip-fail`), `section-title`
  with trailing rule, `stat-card` market tiles

Typography: Space Grotesk (display), Inter (body), JetBrains Mono
(prices/Greeks/P&L) via `@fontsource`.

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

## Data flow (single-page health check)

1. `+page.svelte` (home): debounced `searchAssets()` → grouped autocomplete
   (STOCK/ETF/INDEX sections, exact symbol match pinned first). Selecting an
   asset sets the symbol + derived `asset_type`. Recent analyses are read from
   localStorage on mount; **new analyses are recorded by the home page on
   success only** (a failed analysis like SPX is never added).
2. Running a check (`RUN CHECK`, Enter, or deep-link `/?symbol=AAPL`) calls
   `analyze(symbol, assetType)` (returns all 10 indicators — free) and renders
   the full health-check report **below the search on the same page**: verdict
   hero + grade ring, vitals row, plain-language box, price + RSI charts, a rich
   **"ABOUT {symbol}" company profile** (`CompanyProfile.svelte`: description,
   identity facts, valuation grid, profitability/growth metrics, 52-week range
   bar — every metric has a beginner tooltip; free keyless Yahoo+Wikipedia
   source), news sentiment + headlines dropdown, **THE CHECKS** table with
   pass/watch/fail chips, and save-to-portfolio.
   The **AI panel is Pro-gated**: shows a 🔒 PRO lock for non-Pro users and a
   "RUN AI ANALYSIS" button only when the logged-in user's tier is `pro`.
3. `analysis/[symbol]/+page.svelte` is a **redirect** to `/?symbol=X` (kept so
   old links/bookmarks still work). Options mode routes to the same page with
   `/?symbol=X&mode=options`, which renders `OptionsWorkspace.svelte` (the full
   GUIDED / CHAIN / BUILDER options experience) **below the search on the same
   page**. `/options/[symbol]` is likewise a redirect to `/?symbol=X&mode=options`.

## Auth

- `lib/auth.svelte.ts`: Svelte 5 runes store persisting the JWT + user to
  localStorage (`vexarium_token`, `vexarium_user`). `initAuth`, `getToken`,
  `getUser`, `isPro`, `setSession`, `logout`. **Note the `.svelte.ts` suffix —
  runes in a plain `.ts` file are not compiled and break SSR.**
- `components/AuthModal.svelte`: login/register form wired to
  `/api/v1/auth/register` and `/api/v1/auth/login`.
- `routes/+layout.svelte` header: "LOGIN / SIGN UP" button (opens the modal)
  or a FREE/PRO badge + LOGOUT when signed in.

## Options pages

- `options/[symbol]/+page.svelte` — a **tabbed, beginner-first** options page:
  - **GUIDED** — explain-first "WHAT IS AN OPTION?" glossary (`OptionGlossary`)
    with an **EXPERIENCE** toggle (Novice/Intermediate/Advanced), a **YOUR VIEW**
    sentiment selector (Very Bearish…Very Bullish, pre-set from the indicator
    verdict), **TARGET PRICE** + **BUDGET** inputs, a `ContractPicker`, and
    **STRATEGIES** cards.
  - **CHAIN** — a two-sided TradingView-style options chain (`OptionsChain`):
    grouped by expiration, mirrored `CALLS | STRIKE + IV | PUTS` with bid/ask,
    last, theoretical (Black-Scholes), IV, and % distance. Click a row to load
    it in the BUILDER. Volume/OI columns are omitted (data not available).
  - **BUILDER** — `ContractPicker` + `PayoffExplorer` (draggable underlying-price
    slider), a **Pro-gated CHANCE OF PROFIT** panel (`getOptionChance`; shows an
    UPGRADE prompt for free users), the **GREEKS** panel, the **P/L MATRIX**
    (`OptionsMatrix`), and the **PAYOFF TIMELINE**.
  - A **DELAYED** badge in the header flags the indicative (15-min delayed) feed.

## Brand wordmark

The VEXARIUM wordmark is **two-tone**: `VEX` in near-white
(`var(--foreground)`) and `ARIUM` in amber (`var(--accent-primary)`), in
both the header (`+layout.svelte`) and the home hero (`+page.svelte`).

## Recent analyses (localStorage)

- `storage.ts`: `getRecentAnalyses()`, `addRecentAnalysis()`. Dedupes by
  symbol, newest first, cap 10. Key `vexarium_recent`.
- This is a **local** feature (not a pay feature). Daily auto-update is a
  future Pro feature.

## Gotchas

- **Lightweight Charts v5** is a major-version API change from v3/v4 — always
  match against how `PayoffChart.svelte`/`IndicatorChart.svelte` already call it.
- The **asset type is auto-derived** from the selected symbol (Alpaca can't
  distinguish ETF/stock, so it uses name heuristics on the backend). There is
  no manual asset-type selector on the home page anymore.
- Model name is intentionally NOT shown in the AI panel.
- Svelte 5 runes: use `$state`, `$derived`, `$props`, `$effect` — not the
  legacy `$:` reactive declarations.
