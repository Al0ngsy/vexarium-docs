# VEXARIUM — Data & Indicators

How market data is fetched, cached, and turned into verdicts.

## Data source: Alpaca

All price data comes from **Alpaca** (paper-trading keys in `backend/.env`).
The wrapper is `backend/app/services/alpaca_client.py` (`AlpacaClient`).

Methods you'll use:
- `get_stock_bars(symbol, days=365)` → pandas DataFrame of **daily** OHLCV.
- `get_latest_quote(symbol)` → bid/ask/last price.
- `get_market_snapshot(symbol, df=None)` → live price, day change %, bid/ask,
  prev close + 52-week high/low + YTD change (from the daily bars). Fed to the
  AI as `market` context.
- `get_news(symbol, limit=10)` → list of article dicts.
- `get_option_contracts(...)`, `get_option_snapshot(...)`, `get_market_calendar()`.

### What Alpaca can and cannot do (important)

- **Daily bars** work for stocks AND ETFs (e.g. `AAPL`, `SPY`).
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
| `bars:{symbol}` | 6h | Daily bars change at most once/day. |
| `quote:{symbol}` | 5s | Seconds during market hours. |
| `news:{symbol}` | 30 min | |
| `ai:{symbol}:{date}` | 24h | AI analysis per symbol per day. |
| `analysis:{symbol}:{date}` (and `analysis:pro:{symbol}:{date}`) | 24h | **Computed analysis result per symbol per day.** |

### Why daily caching is safe

Indicators are computed from **daily** bars. A daily bar for a given day is
fixed once the day closes. So the *computed analysis* only changes once a day
→ it's cached for 24h (keyed by symbol + today's date). The bars themselves
are cached 6h to pick up the latest close intraday. Repeat analysis of the
same symbol on the same day is effectively free.

## Indicator engine

`backend/app/services/indicator_engine.py` is a **pluggable registry**.

- `Indicator` dataclass: `name`, `compute(df)`, `verdict(value)`, `tier`,
  `min_rows`. `evaluate(df)` handles edge cases (insufficient rows, compute
  errors, NaN) → always returns a valid `IndicatorResult` (never raises).
- `IndicatorResult`: `{name, value, verdict, tier, note}`. Verdict is one of
  `strong_buy | buy | hold | sell | strong_sell`.
- `create_default_engine()` → the **5 core** indicators.
- `create_pro_engine()` → **all 10** (core + ATR, ADX, OBV, VWAP, Ichimoku in
  `services/indicators/extended.py`). This is what every analysis uses.

### Free vs Pro

- **`create_pro_engine()`** (all 10 indicators) is what **every** analysis
  uses — indicators are all free. There is no longer a free(5)/pro(10)
  indicator split.
- The **Pro tier now gates AI analysis only** (`POST /analysis/ai` requires
  `require_tier("pro")` → 403 for free). See `AI_ANALYSIS.md`.
- In dev, flip `DEV_FORCE_PRO=true` in `backend/.env` to bypass tier checks.

### Core indicators

| Name | Kind | Meaning |
|------|------|---------|
| `RSI(14)` | oscillator | Momentum 0-100. >70 overbought, <30 oversold. |
| `SMA(50)/EMA(200)` | overlay | Golden/death cross proxy. |
| `MACD(12,26,9)` | oscillator | Trend momentum, signal crossovers. |
| `Bollinger(20,2)` | overlay | Volatility bands. |
| `Stochastic(14,3)` | oscillator | Close vs high/low range. |

### Pro indicators

ATR, ADX, OBV, VWAP, Ichimoku. See `services/indicators/extended.py`.

### Adding a new indicator

```python
from app.services.indicator_engine import Indicator

MyIndicator = Indicator(
    name="MY_IND",
    compute=lambda df: float(df["close"].iloc[-1]),   # any pandas calc
    verdict=lambda v: "buy" if v > 0 else "sell",
    tier="free",   # or "pro"
    min_rows=10,
)
# register in create_default_engine() or create_pro_engine()
```

The `indicator_kind(name)` helper in `chart_series.py` decides whether a
chart series is `overlay` (price scale) or `oscillator` (own scale). Add new
indicator names there so their mini-charts render correctly.

## Chart series

`backend/app/services/chart_series.py`:
- `build_price_series(df)` → last ~120 OHLC `PricePoint`s.
- `compute_series_for(df, name)` → per-indicator line series.
- `indicator_kind(name)` → `"overlay"` or `"oscillator"`.

The `AnalysisResponse.indicator_series` drives the per-indicator mini-charts
on the frontend (`IndicatorChart.svelte`).

## Verdict aggregation

`backend/app/services/verdicts.py::aggregate(indicator_results)` maps the list
of indicator verdicts to a single `OverallVerdict` (`{overall_verdict, score,
indicator_count, breakdown}`).

## Indicators → options strategies

`backend/app/services/strategy_engine.py` now uses the computed indicators to
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

## Chance-of-profit (Pro)

`options_analyzer.prob_profit(strike, premium, current_price, days_to_expiry,
implied_vol, is_call)` estimates probability of profit / probability of ending
ITM / expected value / breakeven via a **Black-Scholes normal model** from the
contract's implied volatility. Served by `GET /options/{sym}/chance`, which is
**Pro-gated** (403 for free/anonymous) — the frontend shows an upgrade prompt.

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
  `OptionsMatrix` frontend component.
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
- **Yahoo Finance v8 chart meta** — 52-week high/low (falls back to filling any
  identity fields the summary didn't return). No auth.
- **Wikipedia REST summary** — a one-paragraph plain-English `description`. The
  article title is derived from the Yahoo name (legal suffix kept, e.g.
  `Apple_Inc.`), with a curated `SYMBOL_WIKI_TITLES` map for tricky ETF names
  (SPY, QQQ, GLD…).

Cached under `company:{symbol}` (Redis or in-memory). **Never raises** — on any
fetch failure the missing fields are simply omitted so the UI degrades
gracefully. Surfaced as `AnalysisResponse.company` and rendered in an "ABOUT
{symbol}" card (`CompanyProfile.svelte`) with identity facts, a valuation grid,
profitability/growth metrics and a 52-week position bar — each metric has a
beginner plain-English tooltip.

> **Rate-limit note:** Yahoo rate-limits aggressive polling (429). In production
> the analysis + company info are cached (24h analysis / 12h company), so this
> is at most one company fetch per symbol per day — not an issue. The service
> degrades gracefully (fields omitted) if it ever does hit the limit.

## Data sources

- **Alpaca (paper trading)** supplies all market data: daily OHLCV bars, quotes,
  news sentiment, and option chains/Greeks. No other external data feed is used.
