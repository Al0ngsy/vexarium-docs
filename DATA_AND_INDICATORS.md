# VEXARIUM — Data & Indicators

How market data is fetched, cached, and turned into verdicts.

## Data source: Alpaca (+ Yahoo fallback)

Primary price data comes from **Alpaca** (paper-trading keys in
`backend/.env`). The wrapper is `backend/app/services/alpaca_client.py`
(`AlpacaClient`).

`get_stock_bars(symbol, timeframe="1d")` supports **daily AND intraday
timeframes**: `1m / 5m / 15m / 30m / 1h / 4h / 1d / 1w / 1mo` (the
`TIMEFRAMES` map in `alpaca_client.py`). `t` in every series is a **full ISO
timestamp** — date-only strings would collapse intraday bars onto one point.

**OTC / foreign ADRs are NOT on Alpaca's equity feed** (e.g. `SMERY`
Siemens Energy, `RNMBY` Rheinmetall — both trade on OTC Markets). For those
symbols Alpaca returns no bars, and `get_stock_bars` silently falls back to
**Yahoo Finance v8 chart** (keyless, same Windows-UA/query1→query2 strategy as
`company_info.py` — see `_fetch_yahoo_bars` in `alpaca_client.py`). The
fallback only fires when Alpaca returns zero bars or rejects the symbol, and
its result is cached under the same `bars:{symbol}:{timeframe}` key. Symbols
neither source knows still return 404.

Methods you'll use:
- `get_stock_bars(symbol, timeframe="1d")` → pandas DataFrame of OHLCV.
- `get_latest_quote(symbol)` → bid/ask/last price.
- `get_market_snapshot(symbol, df=None)` → live price, day change %, bid/ask,
  prev close + 52-week high/low + YTD change (from the bars). Fed to the
  AI as `market` context.
- `get_news(symbol, limit=10)` → list of article dicts (Alpaca news merged
  with Google News RSS). `news_service.fetch_news` adds Finnhub
  `/company-news`, then **dedupes** and **source-caps** (max 2/outlet) before
  VADER-scoring per article.
- `get_option_contracts(...)`, `get_option_snapshot(...)`,
  `get_option_chain(...)` — options market data (see below).

### What Alpaca can and cannot do (important)

- **Bars work** for stocks AND ETFs (e.g. `AAPL`, `SPY`), daily + intraday.
- **OTC / foreign ADRs** (e.g. `SMERY`, `RNMBY`) are NOT in Alpaca's universe —
  they fall back to **Yahoo Finance bars** (see above).
- **Indices (SPX, NDX, etc.) are NOT in the tradable / bar-data universe.**
  `POST /api/v1/analysis {symbol:"SPX"}` → **404 "No data found"**. This is
  expected, not a bug. Do not try to "fix" it by faking data.
- `asset_class` is always `"us_equity"` — it does **not** distinguish ETF from
  stock. ETF detection uses **name heuristics** (`"ETF"`/`"Trust"`/`"Fund"` in
  the name). See `assets.py::_detect_type`.

## Caching

Backend caching lives in `backend/app/services/cache.py`. It uses **Redis**
if `REDIS_URL` is set, otherwise an in-memory `TTLCache`. TTLs:

| Key | TTL | Notes |
|-----|-----|-------|
| `bars:{symbol}:{timeframe}` | bar duration (1m→60s … 4h→4h); daily+ 6h | Intraday bars: Twelve Data first (real-time, no 15-min delay) → Alpaca (delayed) → Yahoo. Daily bars change at most once/day. |
| `finnhub:{symbol}:{kind}` | 12h | Insider transactions / earnings history / peers (Finnhub enrichment widgets). |
| `quote:{symbol}` | 5s | Seconds during market hours. |
| `news:{symbol}` | 30 min | |
| `fear-greed` | 30 min | CNN Fear & Greed index (server-side proxy; see CONVENTIONS for the cookie handshake). |
| `optchain:{symbol}` | 15s | Options chain snapshot (indicative/delayed feed). |
| `company:v2:{symbol}` | 12h | Company/ETF profile + fundamentals (see below). |
| `ysearch:{q}` | 60s | Yahoo search autocomplete results (assets search). |
| `ai:{symbol}:{timeframe}:{date}` | 24h | AI analysis per symbol per timeframe per day. |
| `analysis:{symbol}:{timeframe}:{date}` | 24h | **Computed analysis result per symbol per day.** |

### Why daily caching is safe

Indicators are computed from **daily** bars. A daily bar for a given day is
fixed once the day closes. So the *computed analysis* only changes once a day
→ it's cached for 24h (keyed by symbol + timeframe + today's date). The bars
themselves are cached 6h to pick up the latest close intraday. Repeat analysis
of the same symbol on the same day is effectively free.

### Single-flight locks

`cache.py` also provides distributed single-flight locks (`lock_acquire` /
`lock_held` / `lock_release`, Redis `SET NX EX` with an in-memory `asyncio.Lock`
fallback). The AI endpoints use them so concurrent requests for the same symbol
wait for the in-flight LLM call instead of firing duplicates.

## Indicator engine

`backend/app/services/indicator_engine.py` is a **pluggable registry**.

- `Indicator` dataclass: `name`, `compute(df)`, `verdict(value)`, `min_rows`.
  `evaluate(df)` handles edge cases (insufficient rows, compute errors, NaN) →
  always returns a valid `IndicatorResult` (never raises).
- `IndicatorResult`: `{name, value, verdict}`. Verdict is one of
  `strong_buy | buy | hold | sell | strong_sell` (or `none` when uncomputable).
- `create_default_engine()` → the **5 core** indicators.
- `create_pro_engine()` → **all 16** (core + 11 extended in
  `services/indicators/extended.py`). This is what every analysis uses.

### Free vs Pro

- **All 16 indicators are free** — every analysis uses `create_pro_engine()`.
  There is no free/pro indicator split.
- The **only Pro-gated endpoint** in the app is the options
  chance-of-profit estimate (`GET /options/{symbol}/chance`, see below).
- In dev, flip `DEV_FORCE_PRO=true` in `backend/.env` to bypass tier checks.

### Core indicators (5)

| Name | Kind | Meaning |
|------|------|---------|
| `RSI(14)` | oscillator | Momentum 0-100. >70 overbought, <30 oversold. |
| `SMA(50)/EMA(200)` | overlay | Golden/death cross proxy. |
| `MACD(12,26,9)` | oscillator | Trend momentum, signal crossovers. |
| `Bollinger(20,2)` | overlay | Volatility bands. |
| `Stochastic(14,3)` | oscillator | Close vs high/low range. |

### Extended indicators (11)

ATR(14), ADX(25), OBV, VWAP, Ichimoku, CCI(20), Williams %R(14), MFI(14),
ROC(12), PSAR, CMO(14). See `services/indicators/extended.py`. ATR/VWAP are
timeframe-aware; the AI briefings reference them by name.

### Adding a new indicator

```python
from app.services.indicator_engine import Indicator

MyIndicator = Indicator(
    name="MY_IND",
    compute=lambda df: float(df["close"].iloc[-1]),   # any pandas calc
    verdict=lambda v: "buy" if v > 0 else "sell",
    min_rows=10,
)
# register in create_default_engine() or create_pro_engine()
```

The `indicator_kind(name)` helper in `chart_series.py` decides whether a
chart series is `overlay` (price scale) or `oscillator` (own scale). Add new
indicator names there so their mini-charts render correctly.

## Chart series

`backend/app/services/chart_series.py`:
- `build_price_series(df, limit=120)` → last N OHLC `PricePoint`s (full ISO `t`).
- `compute_series_for(df, name)` → per-indicator line series.
- `indicator_kind(name)` → `"overlay"` or `"oscillator"`.

The `AnalysisResponse.indicator_series` drives the per-indicator mini-charts
on the frontend (`IndicatorChart.svelte`). The standalone bars endpoint
(`GET /analysis/bars/{symbol}`) serves the price chart at any timeframe.

## Verdict aggregation

`backend/app/services/verdicts.py::aggregate(indicator_results)` maps the list
of indicator verdicts to a single `OverallVerdict` (`{overall_verdict, score,
indicator_count, breakdown}`).

## Indicators → options strategies

`backend/app/services/strategy_engine.py` uses the computed indicators to
drive options strategy suggestions:
- `_direction_from_indicators(indicator_results)` — tallies bullish vs bearish
  verdicts to derive a direction (bullish/bearish/neutral), falling back to the
  endpoint's `sentiment` param when neutral.
- `_volatility_from_indicators(indicator_results)` — a high-volatility signal
  (e.g. ATR present) switches bullish suggestions from LONG CALL +
  CASH-SECURED PUT to a defined-risk BULL CALL SPREAD.
- `GET /api/v1/options/{symbol}/strategies` computes the indicators server-side
  and passes them in.

## Options chain (market-data)

`AlpacaClient.get_option_chain(underlying, ...)` calls Alpaca's **market-data
chain endpoint** (`OptionHistoricalDataClient.get_option_chain`) with the free
**indicative feed** (`OptionsFeed.INDICATIVE`). It returns, for every contract in
the requested expiry/strike window, the latest bid/ask, latest trade, implied
volatility and all 5 greeks — **in one paginated call** (unlike the trading
contracts endpoint, where volume/OI/last are `None`). Rows are enriched with
strike/expiry/type parsed from the OCC symbol.

Important data facts (verified against the live API):
- **`volume` and `open_interest` are NOT available** on Alpaca's free/paper tier.
  Do not fabricate them; the chain response omits them (null) and the UI drops
  those columns.
- **0 DTE (same-day) contracts have no greeks/IV** — the chain endpoint skips
  today's expiry so the default view stays meaningful.
- The **indicative feed is delayed ~15 min**; the chain response carries
  `delayed: true` and the frontend shows a "DELAYED" badge.
- Market-data option endpoints and the Trading API have **separate** rate limits
  (each 200 req/min default on the free tier).

## Chance-of-profit (the one Pro feature)

`options_analyzer.prob_profit(strike, premium, current_price, days_to_expiry,
implied_vol, is_call)` estimates probability of profit / probability of ending
ITM / expected value / breakeven via a **Black-Scholes normal model** from the
contract's implied volatility. Served by `GET /options/{sym}/chance`, which is
**Pro-gated** (403 for free/anonymous) — the frontend shows an upgrade prompt.
`DEV_FORCE_PRO=true` bypasses the gate in dev.

## Options pricing (Black-Scholes + P/L matrix)

`backend/app/services/options_analyzer.py`:
- `black_scholes_price(strike, price, days_to_expiry, implied_vol, ...)` —
  Black-Scholes option price for a hypothetical underlying price (0 DTE →
  intrinsic value).
- `option_value_at_price(...)` — what an option is worth if the underlying
  trades at `target_price`, optionally at a future `target_date` (time decay).
- `build_payoff_matrix(strike, premium, current_price, expiry, implied_vol,
  is_call, ...)` — builds a **strike × expiry P/L grid**: rows are strikes
  centered ±`range_pct` around current price (each labeled with its % move),
  columns are expiry dates, and every cell is the projected P/L for holding to
  that expiry (priced via Black-Scholes, × `quantity`). Powers the
  OptionStrat-inspired `POST /api/v1/options/{symbol}/matrix` endpoint and the
  `MatrixWidget`/`OptionsMatrix` frontend components.
- `prob_profit(...)` — see the "Chance-of-profit" section above.

## Company / ETF profile (free, keyless)

`backend/app/services/company_info.py::get_company_info(symbol)` enriches the
Analysis page with a **plain-English, beginner-explained** company/fund profile
and fundamentals using free, keyless sources:

- **Yahoo Finance v10 quoteSummary** (the primary source) — rich fundamentals
  for stocks AND ETFs: name, exchange, currency, sector, industry, website,
  headquarters, employees, CEO + total pay, market cap, shares outstanding,
  P/E, forward P/E, P/S, P/B, dividend yield, payout ratio, revenue/earnings
  growth, profit margin, gross margin, ROE, ROA, and next earnings date. Uses a
  session cookie + crumb obtained programmatically.
- **stockanalysis.com fundamentals** — a secondary keyless source filling any
  fields Yahoo didn't return (`_fetch_stockanalysis_fundamentals`).
- **Yahoo Finance v8 chart meta** — 52-week high/low (falls back to filling any
  identity fields the summary didn't return). No auth.
- **Wikipedia REST summary** — a one-paragraph plain-English `description`. The
  article title is derived from the Yahoo name (legal suffix kept, e.g.
  `Apple_Inc.`), with a curated `SYMBOL_WIKI_TITLES` map for tricky ETF names
  (SPY, QQQ, GLD…).

Cached under `company:v2:{symbol}` (Redis or in-memory). **Never raises** — on any
fetch failure the missing fields are simply omitted so the UI degrades
gracefully. Surfaced as `AnalysisResponse.company` and rendered in the "About"
widget (`CompanyProfile.svelte`) with identity facts, a valuation grid,
profitability/growth metrics and a 52-week position bar — each metric has a
beginner plain-English tooltip.

**OTC ADR → main listing:** when the symbol's exchange contains "OTC" (e.g.
`RNMBY`, `SMERY` — foreign ADRs not on Alpaca's feed), `get_company_info`
also resolves the **primary home-exchange listing** via keyless Yahoo search
(`find_main_listing`, exchange preference XETRA/GER → FRA → other) and adds
`main_listing: {symbol, name, exchange}` — e.g. `RNMBY → RHM.DE/XETRA`,
`SMERY → ENR.DE/XETRA`. The frontend uses it for the "VIEW MAIN LISTING"
button.

> **Rate-limit note:** Yahoo rate-limits aggressive polling (429). In production
> the analysis + company info are cached (24h analysis / 12h company), so this
> is at most one company fetch per symbol per day — not an issue. The service
> degrades gracefully (fields omitted) if it ever does hit the limit.

## Data sources

- **Alpaca (paper trading)** supplies most market data: OHLCV bars (daily +
  intraday timeframes), quotes, news, and option chains/Greeks.
- **Yahoo Finance v8 chart (keyless)** is the **fallback for bars of
  symbols outside Alpaca's universe** — OTC/foreign ADRs like `SMERY`,
  `RNMBY` (no bars from Alpaca). See `_fetch_yahoo_bars` in
  `alpaca_client.py`. Company profiles use Yahoo too (`company_info.py`).
- **stockanalysis.com (keyless)** fills company fundamentals Yahoo misses.
- **Wikipedia REST** provides the plain-English company description.
- **Google News RSS** is the news fallback when Alpaca news is down.
- No other external data feed is used.
