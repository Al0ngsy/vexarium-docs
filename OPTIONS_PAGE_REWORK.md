# VEXARIUM — Options Page Rework: Analysis & Plan

> **Goal:** turn the current `options/[symbol]` page into a **beginner-first
> (but advanced-capable) stock/options analysis page**, inspired by TradingView's
> Options Chain and OptionStrat's builder, but **only using data Alpaca
> actually provides**. Everything must be explained for a complete newbie.
>
> **STATUS: IMPLEMENTED — SUPERSEDED BY WIDGET GRID (Aug 2026).** All of
> Phases 1–3 below are built and verified against the live Alpaca API:
> - Backend: `AlpacaClient.get_option_chain()` (market-data chain, indicative
>   feed), enriched `/chain` response (bid/ask/last/IV/greeks + computed DTE/
>   intrinsic/time/theoretical/spread/distance), Pro-gated `GET /options/{sym}/chance`.
> - Frontend: `OptionsChain.svelte` (two-sided chain), `OptionGlossary.svelte`,
>   and the tabbed **GUIDED / CHAIN / BUILDER** options page with an EXPERIENCE
>   toggle and a DELAYED badge.
> - **Aug 7 rework:** the tabbed options page was replaced by a **gridstack
>   widget grid** at `routes/options/[symbol]` (`OPTIONS_WIDGETS` in
>   `lib/layout.svelte.ts`; per-widget components: OptionsChainWidget, PayoffWidget,
>   GreeksWidget, ProbabilityWidget, MatrixWidget, StrategyWidget, WatchlistWidget).
>   The monolithic `OptionsWorkspace.svelte` (this doc's GUIDED/CHAIN/BUILDER
>   implementation), plus `ContractPicker.svelte`, `OptionGlossary.svelte` and
>   `VerdictBadge.svelte`, were **deleted** (zero importers). Widget layout
>   persists per-view in localStorage.
> - Gates: 248 backend tests pass; `yarn check` 0 errors; `yarn build` clean.
> This document records the analysis that drove the implementation.

---

## 1. What the reference apps do (from the provided screenshots)

### 1.1 TradingView Options Chain (`/options/chain/?symbol=SPY`)
A dense, two-sided **options chain table**:
- **Tabs:** Chain · Strategy builder · Strategy finder · Volatility · Volume.
- **Chain:** mirrored Calls | Strike + IV | Puts table. Columns include bid/ask,
  last trade, theoretical value, intrinsic value, time value, bid/ask %, spread,
  distance from underlying, % distance, volume.
- **Grouped by expiration** (0 DTE, 1 DTE, 2 DTE… each expandable).
- A **price banner** between ITM-call/OTM-put and OTM-call/ITM-put rows:
  `SPY 771.33 usd +13.66 +1.80%`.
- Per-strike **IV column** and **volume bars** (blue = calls, red = puts).
- Filter pills: expiration, ±strikes, spread, settings.
- Strategy builder = pick a template (Long Call, Covered Call, Bull Call
  Spread…), see a payoff graph + Greeks/metrics ribbon (max profit/loss, win
  rate, breakeven, delta/gamma/theta/vega/rho).

### 1.2 OptionStrat (`/build/long-call/SPY/.SPY260814C752`)
A **builder-first, beginner-labeled** tool:
- Experience levels (Novice / Intermediate / Advanced / Expert) with plain-English
  explanations — *"A call gives the buyer the right, but not the obligation, to
  buy the underlying stock at strike price A…"*
- **Sentiment selector** (Very Bearish … Very Bullish), **target price**,
  **budget**, **expiration** picker, **Max Return ↔ Max Chance** slider.
- **Strategy cards** (Long Call, Covered Call, Cash-Secured Put, Short Put,
  Bull Call Spread, Bull Put Spread…) each with a subtitle, **return on risk**,
  chance %, profit, risk/collateral, a mini payoff chart, and **"Open in Builder"**.
- A **strike slider tape** with the underlying marked (white triangle) and the
  chosen strike in a bubble.
- A full **P/L table** (rows = future prices + % move, columns = dates) with
  green/red cell shading, plus a **P/L graph**, Greeks row (delta/theta/gamma/
  vega/rho), and metric tabs (Table / Graph / Profit-Loss $ / % / Contract Value /
  % of Max Risk).
- Note: the "Chance" and Greek values are **locked behind a subscription**.

### 1.3 The key insight for VEXARIUM
Both apps are fundamentally **analysis + education** tools, not just raw tables.
TradingView is *dense* (pro-oriented); OptionStrat is *beginner-layered*
(progressive disclosure). VEXARIUM's target user is explicitly a **newbie**, so
the OptionStrat model (sentiment → target → cards → builder, all explained) is
the better north star, while the TradingView chain is the better "advanced"
view. **We can offer both** — a beginner-friendly "Guided" view and a dense
"Chain" view — on one page.

---

## 2. What the current VEXARIUM options page already does

Verified by reading the code:

**Backend (`backend/app/services/alpaca_client.py`, `options_analyzer.py`,
`strategy_engine.py`; `api/options.py`, `api/strategies.py`):**
- `get_option_contracts(...)` — **Trading API** `GetOptionContractsRequest`
  (paginated, both CALL/PUT across expiries). Fields surfaced: OCC symbol,
  strike, expiration, type, `last_price`, `volume`, `open_interest`,
  `implied_volatility`.
- `get_option_snapshot(...)` — per-contract snapshot: greeks + IV + latest
  trade/quote (bid/ask).
- Black-Scholes pricing (`options_analyzer.py`) → `option_value_at_price`,
  `build_payoff_matrix`, `build_payoff_timeline`, breakeven.
- Strategy engine → `recommend_strategies` (LONG CALL, CASH-SECURED PUT,
  COVERED CALL, SHORT PUT, BULL CALL SPREAD) driven by indicator-derived
  sentiment.
- Endpoints: `GET /options/{sym}/chain`, `GET /options/{sym}/payoff`,
  `POST /options/{sym}/matrix`, `GET /options/{sym}/value`,
  `GET /options/{sym}/strategies`.

**Frontend (`options/[symbol]/+page.svelte` + components):**
- `ContractPicker` (expiry chips → call/put toggle → strike ladder with %
  distance + premium).
- `PayoffExplorer` (draggable underlying-price slider + Black-Scholes value).
- `OptionsMatrix` (strike × expiry P/L grid, color-coded, range slider + metric
  modes).
- Greeks panel (delta/gamma/theta/vega/rho with `InfoPopover` explanations —
  **already beginner-friendly**).
- Payoff timeline table; strategy cards; save-to-portfolio.

**What's missing vs. the references:**
- A real **two-sided options chain table** (the current "chain" is only a
  *picker*, not a dense chain view). The backend `/chain` endpoint does **not**
  return bid/ask per contract — only last_price/volume/OI/IV from the trading
  contract metadata, where **volume/OI/last_price are all `None`** (verified
  below).
- **No IV column** per strike, **no volume bars**, **no OI display**.
- **No bid/ask, spread, theoretical value, intrinsic/time value** columns.
- **No sentiment selector, target price, budget, or "chance"**.
- **No builder** for multi-leg strategies (the current engine only synthesizes a
  handful of single/2-leg strategies with made-up legs).
- **No beginner onboarding** (glossary, guided walkthrough, experience level).
- **Data correctness gap:** the current `/chain` returns contracts where
  `volume`, `open_interest`, `last_price`, `implied_volatility` are frequently
  `None`/0 because it uses the **trading contracts metadata** endpoint, not the
  market-data snapshot/chain endpoint.

---

## 3. What Alpaca actually provides (verified against live API + docs)

I verified these against `alpaca-py` **0.43.5** (the installed version) with the
live paper keys, and the official docs.

### 3.1 ✅ The big win: `OptionHistoricalDataClient.get_option_chain()`
Alpaca has a **dedicated option-chain market-data endpoint** that returns, in a
**single paginated call**, the latest trade + latest quote (bid/ask) + IV +
greeks for **every contract** of an underlying.

Verified live:
```
req = OptionChainRequest(underlying_symbol='SPY', expiration_date_gte=today,
    expiration_date_lte=+35d, strike_price_gte=750, strike_price_lte=800,
    feed=OptionsFeed.INDICATIVE)
resp = client._option.get_option_chain(req)
→ dict keyed by OCC symbol, 1180 contracts
each: { symbol, latest_trade{price,size,...}, latest_quote{bid_price,ask_price,...},
        implied_volatility, greeks{delta,gamma,rho,theta,vega} }
sample: IV=0.1624, bid=12.96, ask=16.52, last_trade=14.07
```

**Implications:**
- We can build a **true TradingView-style chain** (bid/ask, last, IV per strike)
  with **one endpoint + pagination** — no N snapshot calls.
- `OptionChainRequest` supports filters: `type`, `strike_price_gte/lte`,
  `expiration_date`/`gte`/`lte`, `root_symbol`, `updated_since`, `feed`.
- `get_option_chain` exists in the installed SDK (confirmed via
  `hasattr(OptionHistoricalDataClient, 'get_option_chain')` → True).

### 3.2 ✅ Per-contract snapshots
`get_option_snapshot(symbol_or_symbols=[...])` — accepts **a list**, so you can
get greeks/IV/bid/ask for many contracts in one call (already used).

### 3.3 ✅ Historical option bars / trades / latest quote / latest trade
- `get_option_bars(OptionBarsRequest)` — historical OHLCV bars for a contract
  (any timeframe) **since Feb 2024**.
- `get_option_trades(OptionTradesRequest)`, `get_option_latest_quote`,
  `get_option_latest_trade`.
- All confirmed present on the installed SDK.

### 3.4 ✅/⚠️ Data feeds & delayed vs real-time
- **Indicative feed (free):** quotes are *indicative derivatives* (not true OPRA
  BBO), trades are **delayed 15 min**, modified quotes. This is the default for
  non-subscribed accounts (paper = free tier).
- **OPRA feed (paid):** true consolidated BBO, real-time. Only for subscribed
  users. `OptionsFeed.OPRA` vs `OptionsFeed.INDICATIVE`.
- **For VEXARIUM (paper, free tier):** all option data will be **indicative and
  delayed**. This is **fine for an analysis/education tool** — but the UI must
  say "DELAYED / INDICATIVE" (OptionStrat already shows "Delayed"; we should
  too).

### 3.5 ⚠️ `volume` / `open_interest` gotcha (important)
- The **trading** `GetOptionContractsRequest` returns `open_interest` /
  `volume` / `last_price` as fields, but **they come back `None`** in practice
  (verified live). OI/volume are **not** part of the market-data option-chain
  snapshot either.
- So the **TradingView "volume bars" and "open interest" columns are NOT
  reliably available from Alpaca's free/paper tier.** There is an open Alpaca
  GitHub issue about OI availability (issue #261) confirming it's limited.
- **Mitigation:** we can estimate *relative* interest using the option **bars**
  (`get_option_bars`, daily volume per contract) — but that's an extra call per
  contract and heavy. Better: **drop true OI/volume columns**, or show volume
  only where bars are cheaply available (or behind a toggle). Do not fabricate
  these numbers.

### 3.6 ⚠️ No server-side "theoretical price", "intrinsic/time value", "IV rank", or "chance"
- Alpaca snapshots give greeks + IV + latest trade/quote — **not** theoretical
  price. We already compute theoretical value ourselves via **Black-Scholes**
  (`options_analyzer.py`) — keep that; it's the source of "theoretical" and
  "intrinsic/time value" columns.
- **IV rank / IV percentile / historical IV / IV skew:** Alpaca does **not**
  provide these directly. IV rank needs a **history of IV per underlying**,
  which we'd have to build from `get_option_bars` or by storing daily IV — a
  larger effort. **Defer.**
- **"Chance of profit" / "win rate":** not provided. Must be **estimated** via a
  probability model (e.g., from the option's delta → normal CDF approximation,
  or an implied-vol-normal model). This is the OptionStrat-locked premium
  feature; for VEXARIUM it's a natural **Pro** upsell we compute ourselves.

### 3.7 ✅ OCC symbol format
Alpaca uses standard **OCC**: `ROOT + YYMMDD + C/P + 8-digit strike`. Verified:
`SPY260814C00752000`. Note SPY's OCC root can be `SPY` (3-char) — the existing
`_parse_occ` in `api/options.py` handles this (it uses last-9 char = C/P and
last-8 = strike). Good.

### 3.8 ✅ Multi-leg strategies
No special endpoint — strategies are built client-side by **combining
contracts** from the chain (each leg priced via snapshot/chain + Black-Scholes).
Fully feasible.

### 3.9 ✅ Underlying price
We already have `get_stock_snapshot` / `get_latest_quote` for the underlying's
live price + day-change %. OptionStrat's header (price + % + $ change) is easy.

### 3.10 Rate limits / subscription
- Paper = free Alpaca tier: **indicative feed**, REST rate-limited (typically
  200 req/min for market data; VEXARIUM's own endpoint rate-limits at
  free=30/min, pro=200/min). **Options data does not require a paid subscription
  for the indicative feed** — but real-time OPRA does.
- `GetOptionContractsRequest.limit` max is **10,000** per page (default 100) —
  a single `get_option_chain` can return a full expiry in one call, which keeps
  request count low.

### 3.11 Trading
Alpaca supports option **trading** (place orders, positions) on live accounts.
VEXARIUM is analysis-only ("no trading" per docs), so we **won't** wire trading
now, but it's a future option.

---

## 4. Feasibility verdict — build / defer / skip

| Reference feature | Feasible now? | How | Notes |
|---|---|---|---|
| Underlying price + day change | ✅ | `get_stock_snapshot` (have it) | add $ and % |
| **Two-sided options chain** (bid/ask/last/IV per strike) | ✅ | **`get_option_chain`** | **replaces current picker-only chain**; key build |
| IV column per strike | ✅ | from `get_option_chain` | |
- **Theoretical / intrinsic / time value** | ✅ | Black-Scholes (have it) | compute per row |
- **Bid/ask spread** | ✅ | bid/ask from chain | |
| Expiration grouping / DTE badges | ✅ | derive from expiry | |
| Sentiment selector | ✅ | indicator verdict (have it) | map to Very Bearish…Very Bullish |
| Target price + budget | ✅ | own calc (Black-Scholes) | |
| Strategy cards (return on risk, profit, risk, mini payoff) | ✅ | strategy_engine (extend) | multi-leg combining chain contracts |
| "Open in Builder" → payoff graph + Greeks ribbon | ✅ | PayoffExplorer + Greeks (have it) | combine into one builder |
| **Chance of profit / win rate** | ⚠️ estimate | delta→normal-CDF model | **Pro upsell**; label "estimate" |
| Beginner explanations / experience levels / glossary | ✅ | content, no data needed | **must-do for the newbie goal** |
| **Volume bars** | ⚠️ partial | option bars (heavy) | drop or make optional; **don't fake** |
| **Open interest** | ❌ | not in free/paper data | omit; explain why |
| **IV rank / historical IV / IV skew** | ❌ (later) | build from daily IV history | defer to Phase 3 |
| "Strategy finder" (scan whole chain for best setup) | ⚠️ later | needs prob model | defer |
| Real-time data | ❌ | needs OPRA paid sub | show "DELAYED" label |
| Trading/ordering | ❌ | out of scope (analysis-only) | future |

**Bottom line:** the **chain + builder + education** core is fully feasible with
Alpaca today (especially thanks to `get_option_chain`). The main things we
**cannot** honestly show are real-time data, true open interest, volume, and
IV-rank — and we must never fabricate them.

---

## 5. Design assessment: does the current page fit?

**No — it needs a real make-over, but the Arasaka visual system stays.**

Current issues:
1. **Information architecture is wrong for the goal.** It's a stack of
   vertically stacked panels (BUILD CONTRACT / P/L MATRIX / GREEKS / PAYOFF
   TIMELINE / STRATEGIES) with no narrative and no beginner guidance. A newbie
   has no idea what to do first.
2. **No true options chain.** The page's "contract picker" is a builder, not a
   chain. There's no way to see the whole bid/ask surface at a glance.
3. **Data correctness gap** (section 2/3.5): the `/chain` endpoint returns
   contracts whose last_price/volume/OI/IV are often `None`/0, so premiums in
   the picker are unreliable. Must switch to `get_option_chain`.
4. **No explanation layer.** Greeks have tooltips, but strike/delta/IV/breakeven/
   time-decay/the underlying are unexplained. The whole tool assumes options
   literacy.
5. **No sentiment→target→strategy flow** (the OptionStrat onboarding that makes
   options approachable for beginners).
6. **The vertical stack wastes space** — a pro chain needs horizontal density.

**Recommendation: keep the Arasaka brand (black/crimson/white, 4px angular,
uppercase), but restructure the page.** A comprehensive rework of the **layout**
(not the design system) is warranted. Concretely:
- Reuse the design tokens (`app.css`), fonts, `.panel`, `.label`, `.data`,
  `InfoPopover`, `PayoffChart` (Lightweight Charts), `VerdictBadge`. These all
  fit.
- Introduce a **tabbed page**: **Guided** (beginner flow) / **Chain** (dense
  pro view) / **Builder** (payoff + Greeks), mirroring TradingView's Chain·
  Builder tabs and OptionStrat's layered approach.
- Introduce a **beginner glossary + "first 60 seconds" explainer** and an
  **experience toggle** (Novice/Intermediate/Advanced) that progressively shows
  more columns/jargon — the OptionStrat model.
- Add a persistent **"DELAYED / INDICATIVE DATA"** badge (honesty, and it's the
  legal reality).

---

## 6. Proposed page structure (target)

**Route:** `options/[symbol]` (keep URL; add tabs).

```
Header strip:   SYMBOL  |  VERDICT badge  |  price  +$x.x (+x.xx%)  |  DELAYED badge
Tabs:           [ GUIDED ] [ CHAIN ] [ BUILDER ]
────────────────────────────────────────────────────────────
GUIDED (beginner):
  1. Explain-this-first card: "What is an option?" (glossary expander)
  2. Sentiment selector (Very Bearish … Very Bullish) — presets from verdict
  3. Target price input (+ computed % move) + Budget
  4. Expiration picker (chips with DTE)
  5. Strategy cards grid (Long Call / Covered Call / Cash-Secured Put /
     Bull Call Spread…) each: plain-English subtitle, return on risk,
     profit, risk, mini payoff chart, "OPEN IN BUILDER" → jumps to BUILDER tab
  6. "Chance of profit" on cards — PRO-gated (estimate), 🔒 for free users

CHAIN (advanced, TradingView-style):
  - Two-sided table: CALLS | STRIKE + IV | PUTS
  - Columns: bid, ask, last, theoretical, intrinsic, time value, spread,
    distance %, DTE (grouped by expiration, expandable)
  - Current-price banner row between ITM-call/OTM-put and OTM-call/ITM-put
  - Click a row → selects contract → "OPEN IN BUILDER"
  - Filter pills: expiration window, ±strikes
  - NOTE: no volume/OI columns (data not available) — a small footnote explains.

BUILDER (both levels):
  - Strike slider tape (underlying marked, chosen strike bubble) — OptionStrat
  - Greeks ribbon (delta/gamma/theta/vega/rho) each with InfoPopover
  - Payoff P/L graph (expiration vs. current, profit/loss shading, breakeven)
  - Max profit / max loss / breakeven / return-on-risk readouts
  - Optional: P/L table (rows = prices+%move, columns = dates) — the matrix
    we already have, exposed here
  - "ESTIMATE — NOT GUARANTEED" footer on all computed values
```

---

## 7. Phased implementation plan

### Phase 1 — Correct the data layer (small, high value)
Backend:
- Add `AlpacaClient.get_option_chain(underlying, ...)` wrapping
  `OptionHistoricalDataClient.get_option_chain` with pagination +
  `OptionsFeed.INDICATIVE`.
- Rework `GET /options/{sym}/chain` to return, per contract: `symbol, strike,
  expiration, type, bid, ask, last_price, implied_volatility, greeks` (+ DTE,
  computed). Keep backward-compatible fields where cheap.
- Fix the current bug where the trading-contracts endpoint yields
  None volume/OI/last_price. Drop `volume`/`open_interest` from the response
  (or mark them null) rather than returning 0s.
- Add `intrinsic` / `time_value` / `theoretical` / `spread` (compute via
  Black-Scholes + chain quote) per row — either backend or frontend.
- Add a `feed`/`delayed: true` flag to responses.
- Add tests; update `docs/API.md`, `docs/DATA_AND_INDICATORS.md`,
  `docs/CONVENTIONS.md` (the OI/volume gap).

### Phase 2 — Two-sided Chain view (the visual centerpiece)
Frontend:
- New `OptionsChain.svelte` component: grouped-by-expiration, mirrored
  CALLS|STRIKE+IV|PUTS table, price banner row, click-to-select, filter pills.
- Wire it as the CHAIN tab. Reuse Arasaka tokens; `PayoffChart`/`InfoPopover`.
- Replace the picker-only `ContractPicker` usage: the chain now drives contract
  selection; keep `ContractPicker` for the Guided/Builder flow if useful.
- `yarn check` + `yarn build` gates; update `docs/FRONTEND.md`.

### Phase 3 — Guided beginner flow + Builder
Frontend:
- Sentiment selector, target price/budget inputs (front-end state; compute via
  existing `/value` Black-Scholes endpoint).
- Strategy cards: extend `StrategyCard` with return-on-risk, chance (Pro), and
  an "Open in Builder" that loads the BUILDER tab with that contract.
- **Builder tab:** combine `PayoffExplorer` + Greeks panel + `OptionsMatrix`
  into one view with a strike tape.
- **Chance-of-profit** estimate: add a backend helper (delta→normal-CDF or
  IV-normal probability). Gate behind Pro (like AI) — `require_tier("pro")`.
- Beginner content: glossary component + experience toggle + "first 60 seconds".
- Add `DELAYED / INDICATIVE DATA` badge globally on the options page.
- Update `docs/API.md` (new chance endpoint + gating), `docs/FRONTEND.md`,
  `README.md` (monetization: chance-of-profit is Pro).

### Phase 4 (deferred, optional)
- IV rank / historical IV / IV skew (build a daily IV history store).
- Strategy finder (scan chain for best risk/reward using the chance model).
- Real-time OPRA feed (requires paid Alpaca sub — not now).

---

## 8. Honesty & legal guardrails (important)
- **Never fabricate** volume, open interest, real-time prices, or IV rank —
  Alpaca's free/paper tier doesn't provide them. Omit, or label clearly.
- **Greeks/IV are absent on 0DTE contracts** (same-day expiry) — a chain that
  spans today's expiry will have missing greeks for those rows. Handle with a
  "—"/"N/A" (do not fabricate), and prefer defaulting to the next expiry.
- **Rate-limit note:** market-data option endpoints and the Trading API each
  have their own separate 200 req/min default cap (free tier). The chain call
  counts against market data; the contracts call against Trading. Keep both in
  mind when paginating.
- **Every computed number** (theoretical value, breakeven, chance, P/L) is an
  **estimate** and must carry the "ESTIMATE — NOT GUARANTEED" treatment the
  codebase already uses.
- All option data on the free tier is **indicative + delayed** → surface a
  "DELAYED" badge.
- VEXARIUM is **analysis-only** (docs: "Analysis only — no trading"). Do not add
  order placement.
- Keep the existing global disclaimer ("This is not financial advice").

---

## 9. Open questions for the owner before building
1. Confirm the two-tab or three-tab approach (Guided / Chain / Builder) — or
   keep single scroll with anchors?
2. Is **Chance-of-Profit** the next Pro monetization point (behind Stripe Pro),
   matching the current "AI-only Pro" model? Recommended: yes.
3. For the Chain view, do we paginate **all** expiries or cap at ~6 spread
   expiries (the current behavior) to keep request count low? Recommended: cap.
4. Paper vs live data: keep paper/indicative for now (recommended) — real-time
   requires the paid Alpaca OPRA plan.
