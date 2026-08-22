# VEXARIUM - Stock/ETF Feature Audit (current state + backlog)

> **Purpose:** authoritative snapshot of the stock/ETF analysis workspace
> (`/s/{symbol}`) as of **Aug 2026**: what exists, what is broken, what is
> hardcoded, and what to build next. Written for AI agents taking over stock
> analysis work. The options workspace has its own audit
> (`OPTIONS_FEATURE_AUDIT.md`); this doc is the stock-side counterpart.
>
> **TL;DR:** the data plumbing is complete and correct enough (Alpaca paper +
> Yahoo + stockanalysis.com + Twelve Data + Finnhub + CNN, all free). The gaps
> are: 6 verified bugs (most small FE issues), ~20 hardcoded/stub values, a
> few widget sense problems (market-wide widgets on a symbol page, empty
> stock-only widgets on ETFs), and a backlog of screener/Bloomberg-style
> features that are buildable with today's data sources, no new paid data
> needed. The 16-indicator engine, the 24h-cached `/analysis` report, the
> SSE quote stream and the keyless Yahoo fundamentals are the raw material.

---

## 1. Current state

### 1.1 Backend endpoints the `/s` page actually calls (all free)

| Endpoint | File:line | Cache / TTL | Notes |
|---|---|---|---|
| `POST /analysis` | `api/analysis.py:109` | 24h per `(symbol, timeframe)` (`cache.py:145`, `analysis_key`) + single-flight lock | Full report: bars -> 16 indicators -> verdict -> news sentiment -> company profile. One response drives most widgets. |
| `GET /analysis/bars/{symbol}` | `api/analysis.py:221` | one bar duration (1m -> 60s, ..., 1d -> 6h cap, `cache.py:141`, `alpaca_client.py:190-195`) | Price chart data. Twelve Data first for intraday, then Alpaca, then Yahoo. |
| `GET /analysis/finnhub/{symbol}` | `api/analysis.py:171` | 12h per kind (`finnhub.py:46-48`) | insider / earnings / peers bundle. |
| `GET /analysis/market-news` | `api/analysis.py:189` | 12h global (`finnhub.py:140`) | Finnhub general news + VADER scores. |
| `GET /analysis/fear-greed` | `api/analysis.py:209` | 30 min (`fear_greed.py:112`) | CNN Fear & Greed. |
| `POST /analysis/ai` | `api/ai.py:78` | 24h per `(symbol, timeframe)` (`cache.py:144`) | LLM briefing, free for everyone, 10 req/min per IP. |
| `POST /analysis/ai/stream` | `api/ai.py:140` | same cache, replays cached text as chunks | SSE streaming used by the AI widget. |
| `GET /stream/quotes` | `api/stream.py:19` | none (live SSE) | Alpaca IEX trades+quotes fanned out; max 20 symbols (`quote_stream.py:32`). |
| `GET /assets/search` | `api/assets.py:157` | 60s Yahoo search cache + in-memory Alpaca asset list | TopBar symbol search. |
| `GET /health` | `main.py:87` | n/a | `wakeUp()` ping on load/focus (`+layout.svelte:14-21`). |

Rate limit: `settings.rate_limit_free = 30/min` (`config.py:70`) on all of the
above except `/analysis/ai*` (10/min, `config.py:74`). One page load fires
~10 requests: 5 analysis POSTs (main + quiet recompute + 1d/1w/1mo verdict
strip, `+page.svelte:217-308`), bars, finnhub, market-news, fear-greed,
AI stream. The `/s` page does **not** call `/portfolio/stance` or any
`/options/*` endpoint; "Save trade" writes localStorage only
(`SaveTradeModal.svelte:36`, `storage.ts:17-21`) and "Options →" is just a
link (`SymbolStrip.svelte:191-196`).

### 1.2 Frontend widgets (`frontend/src/routes/s/[symbol]/+page.svelte`)

Widget defs in `lib/layout.svelte.ts:27-128` (`ANALYSIS_WIDGETS`, 11
widgets), layout + visibility persist per view in localStorage
(`layout.svelte.ts:23-24`). The page's `{#if}` chain
(`+page.svelte:529-958`) is the component registry.

| Widget id | Rendered by | What it shows | Data |
|---|---|---|---|
| `price-chart` | `IndicatorChart` (inline) | Candlestick chart, timeframe select 1m..1mo, live last-candle tick, ~300 bars | `/analysis/bars` |
| `vitals` | inline (`+page.svelte:592-605`) | Price, 52-week range, ATR (volatility), RSI (momentum) | `/analysis` |
| `indicator-checks` | inline (`+page.svelte:606-734`) | 16 indicator chips with tooltips + mini series charts, multi-timeframe verdict strip (1d/1w/1mo), client-side exclusion via double-click | `/analysis` (3 timeframes) |
| `ai-opinion` | inline (`+page.svelte:735-759`) | Streamed LLM briefing, "Run AI analysis" button | `/analysis/ai/stream` |
| `company` | `CompanyProfile.svelte` | Wikipedia description, sector/industry, HQ, CEO, valuation (P/E, P/S, market cap), margins, ROE/ROA, growth, dividend yield, shares out, 52-week bar | `/analysis` (company payload) |
| `watchlist` | `WatchlistWidget.svelte` | localStorage watchlist with live prices + day change | `/stream/quotes` + localStorage |
| `news` | inline (`+page.svelte:760-847`) | Stock news (Alpaca + Google + Finnhub, VADER-scored, top 5) + broad market news (top 5) | `/analysis` + `/analysis/market-news` |
| `fear-greed` | inline SVG gauge (`+page.svelte:854-931`) | CNN fear-greed gauge + 1w/1m deltas + 3-month sparkline | `/analysis/fear-greed` |
| `insider` | `FinnhubWidget.svelte` | Insider transactions: name, buy/sell, shares, filing date | `/analysis/finnhub` |
| `earnings` | `FinnhubWidget.svelte` | Quarterly EPS estimates vs actuals bar chart | `/analysis/finnhub` |
| `peers` | `FinnhubWidget.svelte` | Comparator ticker chips linking to `/s/{symbol}` | `/analysis/finnhub` |

### 1.3 Widget sense-check (does it belong on a single-symbol page?)

| Widget | Verdict | Problem / adaptation |
|---|---|---|
| `price-chart` | Keep | Core. Lacks volume sub-chart and indicator overlays (series data already exists in `/analysis`, see P4/P1). |
| `vitals` | Trim | Partly duplicates `SymbolStrip` (price + 52-week range appear twice, `SymbolStrip.svelte:39,106-110,147-163`). Replace duplicates with day range, volume, market cap, % off 52-week high (all available, see P5). |
| `indicator-checks` | Keep | The strongest widget. 8 of 16 indicators have no mini series (`chart_series.py:34-68`), tooltips silently lack charts (H8). |
| `ai-opinion` | Keep | Sub label hardcodes "1D daily data" (`layout.svelte.ts:54`) and the AI call always uses `timeframe` default `1d` (`api.ts:241`), even when viewing 1w/1mo indicators. Either send `indicatorTf` or drop the sub. |
| `company` | Keep | For ETFs the "About" profile works (Yahoo longName + description), but valuation cells (P/E etc.) are empty for many ETFs (`CompanyProfile.svelte:177-228` shows "-"). Consider hiding valuation grid for `asset_type == "etf"` or labeling "n/a for funds". |
| `watchlist` | Keep, fix | Navigation value is real, but it competes with `SymbolStrip` for the SSE subscription (B2). On a symbol page it also renders the current symbol twice. |
| `news` | Keep, split labels | The "Market" block inside the stock news widget (`+page.svelte:823-841`) is market-wide; it is labeled ("broad market · score") but easy to misread as stock news. Consider a separate small widget or a header separator. |
| `fear-greed` | Questionable | Market-wide gauge on a symbol page. On its own it adds little to a stock decision; its best use is as a contrarian context panel vs the symbol verdict (P9). Consider moving to the home page and keeping only the contrast panel on `/s`. |
| `insider` | Keep for stocks only | Empty ("No insider filings") for every ETF/index, wasting grid space. Hide when `asset_type != "stock"` (the page already knows the type at `+page.svelte:169-171`). |
| `earnings` | Keep for stocks only | Empty for ETFs; also duplicates `company.next_earnings_date` in the About widget. Same asset-type gating as `insider`; add a countdown (P6). |
| `peers` | Keep | Finnhub peers are US-centric and often stale; a comparison table (P1/P5) is a better use of the slot. |

---

## 2. Verified bugs (fix these first)

### B1 - Save-trade modal never prefills the entry price, keeps the previous symbol's value (FE, confirmed)
`SaveTradeModal.svelte:17` initializes `entry` from `entryPrice` exactly once
at component mount, but the modal is always mounted (`+page.svelte:971-976`)
with `entryPrice={analysis?.current_price ?? null}`, which is `null` on first
render. Result: the prefill never fires, and once the user types a price it
is carried over to the next symbol's modal (MSFT can be saved with AAPL's
price typed earlier).
**Fix:** react to prop changes, e.g. `$effect(() => { if (open) entry = entryPrice ? String(entryPrice) : ""; })`, or re-key the modal per symbol.

### B2 - Live-quote SSE subscription is replace-not-union; SymbolStrip and WatchlistWidget fight (FE, confirmed)
`setWatch` replaces the whole subscription set (`quotes.svelte.ts:66-77`).
Two writers call it on the same page: `SymbolStrip.svelte:33-35`
(`setWatch([symbol])`) and `WatchlistWidget.svelte:17-19`
(`setWatch(watchlist)`). Last effect run wins, so on a fresh load the
watchlist is live and the current symbol's strip price/chart tick is not, and
after navigating to a symbol the strip wins and the watchlist prices freeze.
Both can never be live simultaneously with the current API.
**Fix:** make `setWatch` additive (`[...wanted, ...symbols]` union) or give
the strip a separate subscription channel.

### B3 - `get_latest_quote` reports the bid as "last_price" (BE, confirmed)
`alpaca_client.py:290-292`: `last_price` is set to `bid_price` (falling back
to `ask_price`), not the actual last trade - the latest-quote endpoint has no
trade price. The fabricated bid then flows into `/portfolio/stance`
(`portfolio.py:18-19`, used by the portfolio page that Save-Trade feeds) and
the options chain's `current_price` (`api/options.py:59-60, 217, 342`). For a
widely-quoted stock the bid is a few cents off; the field is also wrongly
named. Same bug family as options B8.
**Fix:** rename to `mid` (midpoint) or fetch a real last trade, and update
the three consumers' fallback chains.

### B4 - AI stream is not cancelled or guarded on symbol change (FE, confirmed)
`runAI()` (`+page.svelte:239-256`) calls `streamAIAnalysis` without an
`AbortSignal` and the chunk callback appends unconditionally (`api.ts:243-256`
passes `signal` through but the page never creates one). Navigating to
another symbol mid-stream leaves the old stream running and its chunks are
appended to the new symbol's `aiMessage`; a second `runAI` fires concurrently
for the new symbol, interleaving two symbols' text.
**Fix:** create an `AbortController` per run, abort in a symbol-change effect,
and guard the callback (`if (symbol !== sym) return`).

### B5 - Dragged widget positions are reverted when any widget is toggled (FE, confirmed)
`WidgetGrid.svelte:39-51` snapshots saved positions once at first init
(`savedAtInit`), and re-inits the grid from that snapshot on every widget
enable/disable (`grid?.destroy(false)` + re-apply attributes, lines 80-97,
effect re-runs when `shown` changes). A drag saves to localStorage
(`onGridChange`, lines 107-125) but the re-init uses the stale snapshot, so
toggling any widget after dragging snaps every widget back and the stale
positions are then persisted again, permanently losing the drag.
**Fix:** re-read `loadPositions(view)` on each re-init (or diff only the
changed widget).

### B6 - Chart data-source hint disappears on cached bars (FE, cosmetic, confirmed)
`chartHint` (`+page.svelte:125-135`) reads `chartBars[last].source`, but the
source is set from `df.attrs["source"]` (`chart_series.py:15`), which is lost
when bars are cached and restored via `pd.read_json`
(`alpaca_client.py:196-203` - `DataFrame.to_json` does not serialize attrs).
So "Live bars" / "~15 min delay" / "Live price · bars ~15m" only show on the
first uncached fetch of a timeframe; every repeat load within the TTL shows
nothing.
**Fix:** persist the source in the cached payload (e.g. a `source` column or
a `bars:{sym}:{tf}:src` key) or have the FE fall back to `"unknown"` text.

---

## 3. Hardcoded values & stubs that need fleshing out

| # | Location | What is hardcoded | Recommendation |
|---|---|---|---|
| H1 | `+page.svelte:38-48` | `TIMEFRAMES` + `TF_MINUTES` poll table duplicated in FE | Single source of truth in `lib/` or the BE; drift risk when timeframes change. |
| H2 | `+page.svelte:58` | `mergeBars` cap of 600 bars | Document; fine while limit is 300. |
| H3 | `quotes.svelte.ts:24,60` | SSE reconnect backoff 1000ms base, 30s max | Fine; move to constants with a comment. |
| H4 | `+page.svelte:316-322` vs `verdicts.py:17-36` | `INDICATOR_SCORES` + `bucketScore` re-implement the BE aggregate | Currently identical; add a comment pointing at `verdicts.py` (drift risk on threshold changes). |
| H5 | `layout.svelte.ts:31,54` | `price-chart` sub "1D · 1y", `ai-opinion` sub "1D daily data" | The AI sub is wrong the moment the user switches to 1w/1mo indicators (AI always runs on 1d, `api.ts:241`). Either pass the timeframe or drop the sub. |
| H6 | `+page.svelte:861-870` vs `fear_greed.py:33-42` | Fear & Greed zone thresholds duplicated FE/BE; the BE `rating` field is ignored by the FE | Keep one source (BE `rating`) to avoid drift; the FE already receives it. |
| H7 | `verdicts.py` + `+page.svelte:323-329` | Verdict score buckets (`>=5` strong buy, `>=2` buy, etc.) | Document the thresholds next to the code; they are the product's grading curve. |
| H8 | `chart_series.py:34-68` | Only 8 of 16 indicators have a series (OBV, Ichimoku, CCI, Williams %R, MFI, ROC, PSAR, CMO return `[]`) | Add the missing series so every indicator tooltip has a mini chart; exact-name if-chain is fragile against renames. |
| H9 | `analysis.py:98` | Series filter `p["v"] is not None` keeps NaN warmup rows; FastAPI encodes them to `null` at render time | Works today (FE filters `null`), but the Redis cache receives literal `NaN` tokens (invalid JSON, `cache.py:123`) via `json.dumps`. Filter with `math.isnan` instead and cache clean JSON. |
| H10 | `cache.py:141-147` | TTLs: bars 6h max, analysis 24h, AI 24h, finnhub 12h, news 30min, quote 5s | Deliberate. Note the 24h analysis cache also freezes `day_change_pct` and `current_price` for the day; the strip's live price comes from the SSE tick, which is why it usually looks fresh. |
| H11 | `alpaca_client.py:252` | Swap to Yahoo bars whenever Alpaca returns < 201 rows | Fine for SMA(50)/EMA(200) coverage; comment already explains. |
| H12 | `alpaca_client.py:48` | `_TD_OUTPUTSIZE = 330`, FE limit 300 | Keep in sync if the FE window grows. |
| H13 | `news_service.py:95,143` | Dedupe similarity 0.85, max 2 articles per source | Deliberate; fine. |
| H14 | `ai_analyzer.py:138,175` | `max_tokens = 8192` | Comment exists (reasoning-heavy model). Keep. |
| H15 | `ai.py:161` | Cached AI replay: 24-char chunks, 30ms delay | Cosmetic; fine. |
| H16 | `config.py:61-62` | Take-profit 10%, cut-loss 8% | Env-overridable already. |
| H17 | `+page.svelte:143-146` | `aboutOpen`, `checksOpen`, `aiOpen`, `newsOpen` declared, never used | Dead code from the pre-grid design. Delete. |
| H18 | `extended.py:468-487` | Duplicate `create_pro_engine()` (the one used lives in `indicator_engine.py:391-424`) | Dead code; delete or make it the single factory. |
| H19 | `indicator_engine.py:391-396` | Docstring says "plus the 5 extended indicators" (it registers 11) | Fix the docstring. |
| H20 | `CompanyProfile.svelte:174,235,358`; `SymbolSearch.svelte:191,196,207`; `+page.svelte:490`; home `+page.svelte:127,162` | Em dashes in UI text (design rule: none) | Replace with commas/colons. Also `CompanyProfile` section labels are uppercase ("VALUATION - WHAT YOU PAY FOR THE STOCK") vs the sentence-case design rule. |
| H21 | `+page.svelte:152-199, 290-308` | Finnhub, market-news, fear-greed and the 1d/1w/1mo verdict strip fetch unconditionally, even when the widgets are disabled | Gate the fetches on `enabled` so disabling a widget actually saves requests. |
| H22 | `company_info.py:318-320` | `revenue_ttm` is fetched from stockanalysis.com but dropped (not in `CompanyInfo` schema, `schemas/analysis.py:77-118`) | Add the field and surface it, or drop the fetch. |

Also note: the whole `/analysis` report is fine-grained but recomputed
per `(symbol, timeframe)` - visiting 10 symbols costs 30+ analysis computes
on cold cache (single-flight per pair helps only duplicates). The screener
ideas in section 4 must lean on the 24h cache, not on extra compute.

---

## 4. Feature & UX backlog (prioritized)

> Every item uses data sources that exist **today** (Alpaca paper, Yahoo
> keyless, stockanalysis.com, Twelve Data, Finnhub, CNN, the quote SSE).
> Nothing below needs a new paid provider. "easy" = FE-only or one small BE
> change; "moderate" = new endpoint or a small store/cron.

### P1 - Comparison widget: overlay current symbol vs a peer or SPY (high value, easy)
**What:** a "Compare" line in the price chart, or a small widget, overlaying
the normalized % return of the current symbol and one comparator
(peers from Finnhub already exist, plus SPY as the default benchmark).
**Why:** the single most Bloomberg-like request: "how is this stock doing
relative to the market / its peers?"
**Data:** `/analysis/bars/{symbol}` works for any symbol (SPY included; only
indices like SPX 404). Normalized %-change overlay is pure FE math on two
fetched series. `IndicatorChart` already handles a second line series
(`IndicatorChart.svelte:215-221`).
**Where today:** `alpaca_client.py:180-276` (bars), `finnhub.py:91-100`
(peers).
**Effort:** easy (FE-only v1; a `?vs=SPY` param on `/bars` is an optional
BE nicety).
**Lazy v1:** a comparator select inside the price-chart widget; normalize
both series to 100 at window start.

### P2 - Watchlist screener table (high value, easy)
**What:** a screener row per watchlist symbol: price, day change, verdict
grade, score, 52-week position, RSI/ATR snapshot. Same data the `/s` page
shows, for every saved symbol.
**Why:** turns the flat watchlist into a monitor; users get the "what should
I look at today" view every screener has.
**Data:** one `POST /analysis` per symbol (24h cached, so repeat lookups are
cheap) + the already-live SSE quotes.
**Where today:** watchlist in localStorage (`storage.ts:59-89`), verdicts in
`/analysis` (`analysis.py:63-75`), quotes via `/stream/quotes`.
**Effort:** easy-moderate (new FE widget or a `/screener` route; optionally a
BE `/analysis/batch` that fans out the cached values server-side).
**Lazy v1:** a new `screener` widget on the `/s` page and home page that
maps over `getWatchlist()` and calls the existing `analyze()`; parallelize
with `Promise.all`, render a compact table.

### P3 - Price alerts (easy)
**What:** user sets a target price or % move per symbol; a toast fires when
the SSE quote crosses it.
**Why:** users leave the tab open; alerts make the live stream useful
instead of decorative.
**Data:** `/stream/quotes` already pushes ticks for up to 20 symbols
(`quote_stream.py:32`); the FE quotes store already receives them
(`quotes.svelte.ts:16`).
**Where today:** the same `quotes` store the strip and watchlist use.
**Effort:** easy (FE-only; localStorage persistence, checked in the quotes
store effect).
**Lazy v1:** `vexarium:alerts` localStorage list, one `$effect` in
`quotes.svelte.ts` that compares tick vs threshold, a transient toast. No
push/email (that would need a cron + notification infra: DEFERRED).

### P4 - Pattern flags from existing indicator series (easy)
**What:** a small "Patterns" strip: golden/death cross (SMA50 vs price),
MACD histogram flip, PSAR flip, price vs VWAP, RSI 30/70 crossing, 52-week
high/low breakout. Each flag = one dated event with a direction.
**Why:** turns the raw indicator tooltips into a scannable "what happened
this week" summary; beginner-friendly.
**Data:** `indicator_series` is already in every `/analysis` response
(`analysis.py:85-106`); the engine already computes all the inputs
(`indicator_engine.py:174-282`, `extended.py:30-52, 354-425`).
**Where today:** `chart_series.compute_series_for` builds the lines the FE
already renders in tooltips.
**Effort:** easy (FE-only; detect sign flips/crossovers client-side on the
series the FE already has).
**Lazy v1:** crossovers and flips on SMA, MACD hist, PSAR only; ignore
divergences (that is a moderate v2).

### P5 - Key-statistics widget (easy)
**What:** a Bloomberg-style stats block: market cap, P/E, forward P/E,
P/S, EPS (derived: market cap / shares out), dividend yield, % off 52-week
high, YTD change, volume.
**Why:** the About widget is buried mid-page; the strip + vitals duplicate
only price range. One glance at stats is the standard check.
**Data:** almost all fields already exist in the `/analysis` `company`
payload (`schemas/analysis.py:99-118`) and in `day_change_pct` /
`get_market_snapshot` (`alpaca_client.py:304-360`, YTD is computed but not
yet exposed in `AnalysisResponse`).
**Where today:** `company_info.py:121-149` (Yahoo quoteSummary).
**Effort:** easy (FE-only v1 from existing payload; add `ytd_change_pct` to
`AnalysisResponse` for completeness, one-line BE).
**Lazy v1:** a new `stats` widget rendering the fields already in
`analysis.company`, no BE change.

### P6 - Earnings/insider event context (easy-moderate)
**What:** a countdown to `next_earnings_date`, last quarter's surprise (from
the Finnhub earnings widget data), and N days since the last insider filing,
in the About or Earnings widget.
**Why:** earnings dates are top risk events; the AI prompt already asks the
model to mention them, the UI should too.
**Data:** `company.next_earnings_date` (`company_info.py:112-119`),
Finnhub earnings/insider bundles (`finnhub.py:51-100`) - both already
fetched.
**Where today:** `FinnhubWidget.svelte:88-158`, `CompanyProfile.svelte:156-168`.
**Effort:** easy (FE-only).
**Lazy v1:** a "next earnings in N days" line + surprise badge in the
earnings widget header.

### P7 - 52-week high/low and momentum scans over a curated universe (moderate)
**What:** scan N symbols for 52-week-high proximity, 52-week-low proximity,
52w momentum, and 20-day trend, ranked. Universe v1 = watchlist + saved
trades + recent analyses; v2 = a curated sector list.
**Why:** the classic screener entry point ("what is breaking out / washed
out right now").
**Data:** 52-week high/low is in every Yahoo v8 chart meta response
(`company_info.py:173-174`) and in `/analysis` bars; daily bars are cached
per bar-duration.
**Where today:** `_fetch_yahoo_meta` (one keyless call per symbol),
`/analysis/bars` for the momentum math.
**Effort:** moderate (a BE `/analysis/scan?symbols=...` endpoint that loops
the existing cached fetchers; the 24h analysis cache is not needed if only
52w/momentum metrics are scanned).
**Lazy v1:** limit to the watchlist (<= 20 symbols) and compute entirely
from the existing endpoints; no DB.
**Deferred:** full-market scanning (10k symbols) needs a daily cron that
snapshots Yahoo meta into Postgres; mark as the v2 of this item.

### P8 - Full technical screener page combining P2/P4/P7 (moderate, flagship)
**What:** a `/screener` route: filters (verdict grade, RSI bucket, 52w
position, ATR%, pattern flags, day change), run over the watchlist/recent
universe, each row expands into the `/s` page.
**Why:** the product's 16-indicator engine is currently only usable one
symbol at a time; a screener is the natural upgrade and a future Pro
candidate (only `/chance` is Pro today).
**Data:** everything in P2 + P4 + P7.
**Where today:** same endpoints.
**Effort:** moderate (reuses P2's table component and P4's flag code).
**Lazy v1:** P2's table + 4 filters + sortable columns, no saved scans.

### P9 - Fear & Greed as a market-context panel (easy)
**What:** replace (or augment) the standalone gauge with "market mood:
X (fear) vs THIS STOCK: Y (buy)" and a one-line contrarian note
("extreme greed historically precedes pullbacks").
**Why:** makes the market-wide widget decision-relevant on a symbol page.
**Data:** both values already loaded (`fearGreed`, `clientVerdict`).
**Where today:** `+page.svelte:854-931` (gauge), `+page.svelte:363` (verdict).
**Effort:** easy.

### P10 - ETF profile upgrade (moderate, free source)
**What:** expense ratio, fund AUM, holdings count, inception for ETFs, in
the About widget.
**Why:** the app claims ETF support; today the ETF card shows stock-style
valuation with most cells empty (section 1.3).
**Data:** expense ratio/AUM are scraped from stockanalysis.com in the
existing fallback path (`company_info.py:201-335` pattern, keyless);
Yahoo quoteSummary has none of them.
**Where today:** extend `_fetch_stockanalysis_fundamentals` with the ETF
statistics page.
**Effort:** moderate (scrape + model fields + widget branch).
**Lazy v1:** scrape only expense ratio and AUM; show a single "Fund facts"
card for `asset_type == "etf"`.

### P11 - Correlation / beta vs SPY (moderate)
**What:** 90-day rolling correlation and beta of the symbol vs SPY, shown as
a small number pair + mini chart.
**Why:** "is this stock moving with the market?" is a Bloomberg staple and a
decent risk gauge for beginners.
**Data:** daily bars for both symbols via the existing bar fetcher
(SPY works; only indices return 404).
**Where today:** `alpaca_client.py:180-276`; math is ~20 lines of pandas.
**Effort:** moderate (tiny BE endpoint `/analysis/correlation?symbols=A,SPY`
or FE-side math on two `/bars` calls; FE-side is fine for v1).
**Lazy v1:** FE-only, fixed 90-day window, no p-values.

### DEFERRED (need paid data or new infra)
- IV rank / historical volatility percentile (needs an internal IV snapshot
  store; see OPTIONS_FEATURE_AUDIT P7).
- Real-time push alerts (needs cron + email/push infra).
- Full-market 10k-symbol scans (needs the daily snapshot store in P7 v2).
- Analyst price targets / ratings (needs a paid provider, none exists today).

---

## 5. Suggested execution order for the next agent

1. **Bug sweep (one PR):** B1, B2, B4, B5, B6 (all FE, all small, all
   verified). B3 is BE and touches options consumers, do it in the same PR
   if convenient, else with the next BE PR.
2. **Quick wins (one PR):** P1 (comparison overlay), P4 (pattern flags),
   P5 (stats widget), P9 (fear-greed context), H17/H18/H19/H20 cleanup.
3. **Screener phase (one or two PRs):** P2 (watchlist screener), P3
   (alerts), then P7 and P8 on top (scan endpoint + filters).
4. **Moderate features:** P6 (event context), P10 (ETF facts), P11
   (correlation), and the sense-check fixes from 1.3 (asset-type gating for
   insider/earnings, vitals de-dup).

---

## 6. Data/provider notes

- **No new provider is needed for any P-item.** Alpaca paper covers bars,
  quotes, news and option chains; Yahoo covers the OTC/ADR universe, company
  profile and fundamentals; stockanalysis.com covers fundamentals fallback;
  Twelve Data covers real-time intraday; Finnhub covers insider/earnings/
  peers + company news; CNN covers market mood. Indices (SPX) 404 by
  design; SPY works and is the right benchmark symbol.
- **Monetization context:** all 16 indicators and the AI briefing are free;
  the only Pro-gated endpoint is `/options/{symbol}/chance`. The screener
  family (P2/P7/P8) is the natural next Pro candidate, but nothing in this
  doc requires gating to build.
- **`last_price` semantics are loose:** the fabricated bid-as-last-price
  (B3) and the options chain `mid` fallback (options audit B8) are the same
  family of "free-tier price approximation" issues; standardize on mid or
  snapshot trade price.
- **Doc staleness found (do not fix silently, update in the same commit as
  the code):** `docs/DATA_AND_INDICATORS.md:117` says "ROC(10)" but the
  indicator is `ROC(12)` (`extended.py:355-382`); `docs/AGENTS.md` and
  `OPTIONS_FEATURE_AUDIT.md` say 268 backend tests, the suite is at 274.
- **NaN handling quirk:** `/analysis` indicator series legitimately carry
  NaN warmup rows; FastAPI's encoder turns them into `null` for the FE, and
  the FE filters them, so nothing breaks. But the Redis cache stores raw
  `NaN` JSON tokens (`analysis.py:98` + `cache.py:123`), which is invalid
  JSON if anything non-Python ever reads those keys. Fix with an `isnan`
  filter when touching that code (H9).

---

## 7. Verification gates (run before declaring done)

- Backend: `cd backend && env -u PYTHONPATH .venv/bin/python -m pytest tests/ -q`
  (expect **274 passed** as of Aug 2026; the docs still say 268, bump them).
- Frontend: `cd frontend && yarn check && yarn build`.
- Endpoint shape changes: regenerate `docs/API.md`
  (`cd backend && .venv/bin/python ../docs/scripts/generate_api_md.py`) and
  update docs in the same commit (AGENTS.md golden rule).
- Live sanity check after deploy: open
  `https://vexarium.pages.dev/s/AAPL`, confirm the strip day-change + live
  price tick and the watchlist prices are BOTH live (B2), switching symbol
  mid-AI-stream does not mix text (B4), saving a trade prefills the current
  price (B1), dragging a widget then toggling another keeps the position
  (B5), and the chart "Live bars" hint survives a page reload within the
  bar TTL (B6).