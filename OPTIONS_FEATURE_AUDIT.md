# VEXARIUM — Options Feature Audit (current state + backlog)

> **Purpose:** authoritative snapshot of the options workspace as of **Aug 2026**:
> what exists, what is broken, what is hardcoded, and what to build next.
> Written for AI agents taking over options work. Read
> `OPTIONS_PAGE_REWORK.md` first if you need the *history and design rationale*
> (that doc is the plan; this doc is the audit and the backlog).
>
> **STATUS UPDATE (Aug 22, 2026):** the first implementation round shipped.
> Bugs B1-B8 and hardcoded items H1, H3-H5, H10 are FIXED and live in
> production (BE commits `9f9cd29`, `d7e6c4e`; FE commit `ad418da` plus a
> style commit). Backlog P1 (header strip), P2 (chain polish), P3
> (save-to-portfolio), P4 (target-date slider) and P9 (banner removal) are
> DONE. Still open: P5 (multi-leg builder), P6 (strategy finder), P7 (IV
> rank), P8 (beginner layer), H6 (OCC parsing dedup), H9 (timeline model
> comment), H11 (PRO_FEATURE doc note). Read this doc's sections as the
> state BEFORE that round; the remaining work is the backlog minus the above.
>
> **TL;DR:** the data plumbing is done and correct enough (Alpaca indicative
> feed, free tier). The gaps are: 3 real FE bugs, a wrong strategy for bearish
> sentiment on the BE, several hardcoded/stub values, and a set of UX/feature
> upgrades. The marketdata.app integration question was evaluated and rejected
> (section 6).

---

## 1. Current state

### 1.1 Backend endpoints (all under `backend/app/api/`)

| Endpoint | File | Tier | Data source | Cache |
|---|---|---|---|---|
| `GET /options/{sym}/chain` | `api/options.py:31` | free | Alpaca market-data `get_option_chain` (INDICATIVE feed) | raw rows cached 15 min, key `options:{symbol}` (`cache.py:147`, `CACHE_TTL_OPTION_CHAIN`) |
| `GET /options/{sym}/payoff` | `api/options.py:161` | free | Alpaca `get_option_snapshot` | none |
| `POST /options/{sym}/matrix` | `api/options.py:198` | free | snapshot + Black-Scholes | none |
| `GET /options/{sym}/value` | `api/options.py:275` | free | snapshot + Black-Scholes | none |
| `GET /options/{sym}/chance` | `api/options.py:317` | **Pro** (`require_tier("pro")`, 403 otherwise) | snapshot + normal-model estimate | none |
| `GET /options/{sym}/strategies` | `api/strategies.py:12` | free | **trading** `get_option_contracts` + indicators | **none** (recomputes bars + all indicators every call) |

Rate limit: `settings.rate_limit_free = 30/min` (`config.py:65`) on all options
routes. `delayed: true` is hardcoded in the chain response (`api/options.py:145`)
and correct: the indicative feed is delayed by design, the FE shows a DELAYED
badge from it.

Chain response per contract: `symbol, strike_price, expiration_date, type,
bid, ask, last_price, implied_volatility (fraction, e.g. 0.1624),
greeks{delta,gamma,theta,vega,rho}` plus server-computed `days_to_expiry,
intrinsic_value, time_value, theoretical_value (Black-Scholes), spread,
distance_pct` (`api/options.py:90-140`, `schemas/options.py`).

### 1.2 Frontend widgets (`frontend/src/routes/options/[symbol]/+page.svelte`)

Widget defs in `lib/layout.svelte.ts:130` (`OPTIONS_WIDGETS`), layout persists
per-view in localStorage. Shared contract state in `lib/contract.svelte.ts`
(`store`): chain load → expiry chips → auto-select ATM contract → all widgets
react to `selectedSymbol`.

| Widget id | Component | What it renders | Data |
|---|---|---|---|
| `options-chain` | `OptionsChainWidget` → `OptionsChain` | expiry chips, two-sided CALLS \| STRIKE \| PUTS table | `/chain` |
| `payoff-explorer` | `PayoffWidget` → `PayoffExplorer` | intrinsic-at-expiry payoff SVG, click-to-set price, ±15% slider, timeline table | `/payoff`, `/value` |
| `greeks` | `GreeksWidget` | delta/gamma/theta/vega/rho + IV cards with InfoPopovers | `/payoff` |
| `probability` | `ProbabilityWidget` | prob-of-profit / prob-ITM bars, EV, breakeven; Pro-gated | `/chance` |
| `pl-matrix` | `MatrixWidget` → `OptionsMatrix` | strike × expiry P/L table + graph, range slider, 4 metric modes | `/matrix` |
| `strategies` | `StrategyWidget` → `StrategyCard` | strategy cards with mini payoff chart | `/strategies` |
| `watchlist` | `WatchlistWidget` | same as /s page | localStorage |

Discoverability: the `/s/{symbol}` page has an "Options →" button in the
SymbolStrip (`SymbolStrip.svelte:191`). The `/options` page itself has **no
header strip** (no price/verdict/day change, no back link) and still shows the
"UNDER CONSTRUCTION" banner (`+page.svelte:47`).

---

## 2. Verified bugs (fix these first)

### B1 — Strategy card payoff charts are empty (FE, confirmed)
`StrategyCard.svelte:48-53` maps `p.estimated_option_price` / `p.estimated_pl`,
but the BE sends `PayoffPoint = {price, pl}` (`schemas/strategy.py:4-6`).
Every point is `NaN`, so the Lightweight-Charts mini chart renders nothing.
**Fix:** map `{price: p.price, pl: p.pl}` and correct the FE type
`StrategyCard.payoff_curve` in `lib/types.ts:308` (currently declared as
`PayoffRow[]`, which has the `estimated_*` fields; add a `PayoffPoint`
interface `{price, pl}` and use it).

### B2 — Greeks widget shows IV as a fraction of a percent (FE, confirmed)
`GreeksWidget.svelte:71` renders `payoff.implied_volatility.toFixed(1)%` →
IV 0.1624 displays as "0.2%" instead of "16.2%".
`OptionsChain.svelte:36` (`fmtIV`) already multiplies by 100; do the same here.

### B3 — Bearish sentiment recommends a bullish strategy (BE, confirmed)
`strategy_engine.py:172-174`: for `s == 'bearish'` the engine returns
`short_put`, which is a **bullish** strategy (profitable when price stays
above breakeven). This is a direction error, not a stub.
**Fix:** bearish → `long_put` (and optionally a bear put spread, mirroring
the bull call spread). Add a `_long_put` strategy to `compute_strategy`
(`strategy_engine.py:102`), wire it into `recommend_strategies`.

### B4 — Strategy engine prices legs from trading metadata, not market data (BE)
`api/strategies.py:18-33` builds the chain from `get_option_contracts`
(trading API), where `last_price` is frequently `0`/`None` (documented in
`alpaca_client.py:601` and verified in `OPTIONS_PAGE_REWORK.md` §3.5). The
bull call spread then uses leg-1's last price as the debit for **both** legs
(`api/strategies.py:167-168`), i.e. fabricated pricing.
**Fix:** switch the strategies endpoint to `get_option_chain` (market data,
bid/ask/IV/greeks, already cached 15 min) and use mid = (bid+ask)/2 per leg;
fetch a real premium for the second leg.

### B5 — `strike` query param is required but never used (BE)
`api/strategies.py:14` requires `strike: float`, but `recommend_strategies`
never receives it: it picks `calls[0]` / `puts[0]` (the first strike in the
fetched expiry range, not the ATM strike, not the selected contract).
**Fix:** pass `strike` into `recommend_strategies` and center leg selection
on it (nearest call/put to the requested strike), or drop the param from the
API contract. Note the FE already sends the selected contract's strike
(`contract.svelte.ts:95-97`).

### B6 — ATM row highlight in the matrix never fires (FE)
`OptionsMatrix.svelte:126`: `row.strike === matrix.current_price` is float
equality; it is virtually never true, so the highlight row never shows.
**Fix:** compare against the strike with `move_pct` closest to 0 (or have the
BE echo `atm_strike` in `OptionsMatrixResponse`).

### B7 — Payoff timeline computes a dead intrinsic value from the wrong price (BE, cosmetic)
`api/options.py:175` passes the **option's** `latest_trade_price` as
`current_price` into `build_payoff_timeline`; inside
`options_analyzer.py:188-193` that intrinsic is computed and then never used
(the timeline is pure linear theta decay). Harmless today, misleading
tomorrow.
**Fix:** drop the dead intrinsic block, or fetch the real underlying price
and use it. Decide one way, do not leave the mislabeled variable.

### B8 — Chain `mid` fallback logic is wrong (BE, edge case only)
`api/options.py:101`: `mid = bid if bid and ask and last else (last or bid or ask)`
sets mid = **bid** when all three exist. Mid should be `(bid + ask) / 2`.
Only matters when `current_price` is missing (then `theoretical = mid`).
**Fix:** one line.

---

## 3. Hardcoded values & stubs that need fleshing out

| # | Location | What is hardcoded | Recommendation |
|---|---|---|---|
| H1 | `options_analyzer.py:12,58` | `risk_free = 0.04` (Black-Scholes + prob model), no dividend yield anywhere | Move to `settings` (`RISK_FREE_RATE`, env-overridable, default 0.04). Document that dividends are ignored (American-option simplification). Do not build a full term structure. |
| H2 | `api/options.py:195` | matrix `quantity` default 100; FE never sends it | Acceptable; add a quantity input to MatrixWidget only if users ask. |
| H3 | `strategy_engine.py:139-147` | `_volatility_from_indicators` returns `'high'` whenever any ATR indicator is present | Stub heuristic. Replace with an ATR% threshold (ATR / price) or leave but comment it as a placeholder with the upgrade path. |
| H4 | `contract.svelte.ts:53-54` | FE requests a **365-day** expiry window with `max_expiries=10`; BE `_spread_expiries` spreads evenly over the whole range → with a 1y window the chain shows ~monthly expiries and **no near-term weekly strikes** | If near-term is the default view (it should be), request a 60–90 day window, or change BE to pick the n nearest + a few far-dated. |
| H5 | `contract.svelte.ts:97` | FE calls `/strategies` with `sentiment='hold'` hardcoded | BE derives direction from indicators and ignores this unless neutral. Either drop the param or make it meaningful; do not leave dead weight. |
| H6 | `contract.svelte.ts:130-143` | `parseStrike` / `parseExpiration` re-implement OCC parsing client-side | BE already parses OCC (`_parse_occ`). Duplication is a drift risk; consider sending the parsed strike/expiry in the chain response instead. |
| H7 | `api/options.py:86-87` | 0DTE expiry silently excluded from the chain | Intentional (0DTE has no greeks/IV on the indicative feed). Keep, and keep the comment. |
| H8 | `api/options.py:145` | `delayed: true` hardcoded | Correct while on the indicative feed. If OPRA (paid) is ever enabled, make this reflect the feed. |
| H9 | `options_analyzer.py:186-201` | timeline = linear theta decay, floored at 0; ignores IV term structure and price moves | Deliberate simplification. Keep, but add a `# ponytail:`-style comment stating the model and the upgrade path (full BS re-pricing per day). |
| H10 | `PayoffExplorer.svelte:73-81` | payoff curve is intrinsic-at-expiry only (not Black-Scholes); slider fixed at ±15% | Fine for "at expiry" framing. Label it as such. |
| H11 | FE↔BE | `'PRO_FEATURE'` string is the FE convention for the `/chance` 403 (`api.ts:175`) | Works, but undocumented; note it in `docs/API.md` notes so agents don't "fix" it. |

Also note: the `/strategies` endpoint recomputes stock bars + the full
indicator engine on every call with no cache (`api/strategies.py:35-38`),
unlike the rest of the options stack. Cache it (reuse the `/analysis`
indicator results or add a short TTL).

---

## 4. Feature & UX backlog (prioritized)

### P1 — Header strip on the options page (high value, low effort)
The `/options` page has no price/verdict context. Cheapest path: reuse
`SymbolStrip`; it needs an `AnalysisResponse`, which `/analysis/{symbol}`
already serves 24h-cached. Fetch it once on mount and render the strip above
the grid (minus Save-trade, or keep it, see P3). This also gives the "back to
analysis" affordance and lets you remove the under-construction banner in the
same change.

### P2 — Chain UX (the widget is dense but raw)
- Strike filter chips: BE `/chain` already supports `strike_gte`/`strike_lte`
  and `contract_type` (`api/options.py:38-40`); the FE passes neither. Add
  ±N-around-ATM filter pills and an ITM/OTM toggle.
- Auto-scroll: on load, scroll the chain so the ATM strike row is visible.
- Table width: `min-width: 720px` + `overflow-x-auto`
  (`OptionsChain.svelte:106-107`) forces horizontal scrolling inside the
  widget on narrow layouts. Consider a responsive column reduction instead.
- Default expiry selection should prefer near-term after H4 is fixed.
- Swap hardcoded tints to the design tokens: `#4ade80`/`#fb923c`
  (`OptionsChain.svelte:50,60`) → semantic `#34d399`/`#f59e0b`; selected-row
  background `rgba(200,30,30,0.08)` (lines 120, 150) is a red tint leftover
  from the old design, use the blue accent. `moneynessColor` (line 48) is
  dead code, delete it.

### P3 — Save an option trade to the portfolio (medium)
`SaveTradeModal` and the portfolio stance logic already exist on the `/s`
page, and `POST /portfolio/stance` already accepts `trade_type` +
`contract: {expiration_date}` (`api.ts:194-208`). Wire a Save button into the
options workspace (e.g. in the payoff widget header) reusing the modal. No BE
work expected.

### P4 — Target-date slider in the payoff explorer (small, BE already ready)
`GET /options/{sym}/value` accepts `target_date` (`api/options.py:282`), but
the FE never sends it (`api.ts:145-146`). Add a date slider (today → expiry)
next to the price slider in `PayoffExplorer.svelte` and pass `target_date`.
This delivers the "value on a certain day" feature the user asked for.

### P5 — Real multi-leg builder (large; do after B3/B4)
Today `strategy_engine` synthesizes legs with fabricated premiums. A real
builder needs: (a) market-data mid prices for all legs (already available via
`get_option_chain` after B4), (b) a combo pricer (sum of per-leg Black-Scholes
is fine for a v1), (c) a FE flow to pick legs. Suggest: extend
`/strategies` to accept an explicit leg list (OCC symbols), or price combos
client-side from chain data + one `/value` call per leg. Do not build a
strategy DSL.

### P6 — Strategy finder / more strategies (deferred until P5)
Bear put spread, iron condor, straddle, strangle. Requires P5 leg pricing.
Also: `covered_call` exists in `compute_strategy` but is never emitted by
`recommend_strategies` (`strategy_engine.py:102-116`); either wire it in for
neutral/hold with an owned-shares note or delete it.

### P7 — IV rank / historical IV (deferred, needs a data store)
Alpaca provides no historical IV. Cheapest build: a daily cron that snapshots
per-underlying IV (ATM expiry from the chain) into Postgres; IV rank =
current IV vs. its own trailing window. This was already deferred in
`OPTIONS_PAGE_REWORK.md` Phase 4 and stays deferred.

### P8 — Beginner layer (optional)
The glossary/experience toggle from the rework plan was deleted in the Aug 7
widget-grid rework. Greeks InfoPopovers and the chain footnote remain. If the
newbie-first goal matters, re-add a small "What is an option" glossary widget
rather than a full guided flow.

### P9 — Remove the under-construction banner
`+page.svelte:44-50`. Remove once B1-B3 and P1 land; the page is functional
today.

---

## 5. Suggested execution order for the next agent

1. **Bug sweep (one PR):** B1, B2, B3, B8, B6 (all small, verified).
2. **Data correctness (one PR):** B4 + B5 (switch `/strategies` to market
   data, center on strike), H3 comment or threshold.
3. **FE polish (one PR):** P1 header, P2 chain UX, P9 banner removal, H4
   expiry window.
4. **Features:** P4 (target date), P3 (save to portfolio), then decide on P5.

---

## 6. Data provider note: marketdata.app (evaluated, rejected)

`marketdata.app` Free Forever was evaluated as an alternative/additional
options data source and **rejected**:
- It is redundant: Alpaca's free indicative feed already returns the chain
  (bid/ask/last/IV/greeks) and snapshots, also delayed, with **no daily
  credit cap**.
- Its free tier is strictly worse: 24h delayed (vs ~15 min indicative), 100
  API credits/day (one chain view would consume a large share), 1y history
  only.
- It does not solve the actual gaps (real-time OPRA, volume/OI, historical
  IV): those need a paid Alpaca subscription or an internal IV store, not a
  second free delayed provider.

Do not add it as a fallback. If a second provider is ever needed for
resilience, prefer one that covers a ticker universe Alpaca does not, and
treat the credit budget as a hard ceiling.

---

## 7. Verification gates (run before declaring done)

- Backend: `cd backend && env -u PYTHONPATH .venv/bin/python -m pytest tests/ -q`
  (expect **274 passed**; bump doc numbers if tests are added, see
  `CONVENTIONS.md`).
- Frontend: `cd frontend && yarn check && yarn build`.
- Endpoint shape changes: regenerate `docs/API.md`
  (`cd backend && .venv/bin/python ../docs/scripts/generate_api_md.py`) and
  update docs in the same commit (AGENTS.md golden rule).
- Live sanity check after deploy: open
  `https://vexarium.pages.dev/options/AAPL`, confirm the chain renders, the
  ATM contract auto-selects, strategy mini charts are not empty (B1), the IV
  card shows a plausible percent (B2), and the DELAYED badge shows.
