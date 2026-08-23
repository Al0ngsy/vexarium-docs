# VEXARIUM — API Reference

> **Auto-generated from the FastAPI OpenAPI schema** (`app.openapi()`, 28 paths). Do not hand-edit the tables — regenerate with `docs/scripts/generate_api_md.py`. Editorial notes (gating, caching, gotchas) live in `docs/scripts/api_notes.md`.

## Health

| Method | Path | Params / body → Response | Notes |
|--------|------|---------------------------|-------|
| GET | `/api/v1/health/` | → `—` | Health |
| GET | `/api/v1/health/ready` | → `—` | Ready |

## Auth

| Method | Path | Params / body → Response | Notes |
|--------|------|---------------------------|-------|
| POST | `/api/v1/auth/login` | ``LoginRequest`` → `TokenResponse` | Login |
| GET | `/api/v1/auth/me` | ``?token`` → `—` | Me |
| POST | `/api/v1/auth/register` | ``RegisterRequest`` → `—` | Register |

## Analysis

| Method | Path | Params / body → Response | Notes |
|--------|------|---------------------------|-------|
| POST | `/api/v1/analysis` | ``AnalysisRequest`` → `AnalysisResponse` | Analyze |
| POST | `/api/v1/analysis/ai` | ``AnalysisRequest`` → `—` | Ai Analysis |
| POST | `/api/v1/analysis/ai/stream` | ``AnalysisRequest`` → `—` | Ai Analysis Stream |
| GET | `/api/v1/analysis/bars/{symbol}` | ``symbol` + `?timeframe` + `?limit`` → `—` | Bars |
| GET | `/api/v1/analysis/fear-greed` | → `—` | Fear Greed |
| GET | `/api/v1/analysis/finnhub/{symbol}` | ``symbol`` → `—` | Finnhub Data |
| GET | `/api/v1/analysis/market-news` | ``?limit`` → `—` | Market News |
| POST | `/api/v1/analysis/options-strategies` | ``AnalysisRequest`` → `—` | Ai Options Strategies |
| POST | `/api/v1/analysis/options-strategies/stream` | ``AnalysisRequest`` → `—` | Ai Options Strategies Stream |

## Assets

| Method | Path | Params / body → Response | Notes |
|--------|------|---------------------------|-------|
| GET | `/api/v1/assets/search` | ``?q`` → `—` | Search Assets |

## Options

| Method | Path | Params / body → Response | Notes |
|--------|------|---------------------------|-------|
| GET | `/api/v1/options/{symbol}/chain` | ``symbol` + `?expiration_gte` + `?expiration_lte` + `?strike_gte` + `?strike_lte` + `?contract_type` + `?max_expiries`` → `OptionsChainResponse` | Get Option Chain |
| GET | `/api/v1/options/{symbol}/chance` | ``symbol` + `?contract_symbol` + `?token`` → `OptionChanceResponse` | Get Option Chance |
| POST | `/api/v1/options/{symbol}/matrix` | ``symbol` + `MatrixRequest`` → `OptionsMatrixResponse` | Get Options Matrix |
| GET | `/api/v1/options/{symbol}/payoff` | ``symbol` + `?contract_symbol`` → `OptionsPayoffResponse` | Get Option Payoff |
| GET | `/api/v1/options/{symbol}/value` | ``symbol` + `?contract_symbol` + `?target_price` + `?target_date`` → `OptionValueAtPriceResponse` | Get Option Value At Price |

## Strategies

| Method | Path | Params / body → Response | Notes |
|--------|------|---------------------------|-------|
| GET | `/api/v1/options/{symbol}/strategies` | ``symbol` + `?sentiment` + `?strike` + `?expiration_gte` + `?expiration_lte`` → `StrategiesResponse` | Get Strategies |

## Portfolio

| Method | Path | Params / body → Response | Notes |
|--------|------|---------------------------|-------|
| POST | `/api/v1/portfolio/stance` | ``StanceRequest`` → `StanceResponse` | Get Stance |

## Trades

| Method | Path | Params / body → Response | Notes |
|--------|------|---------------------------|-------|
| POST | `/api/v1/trades` | ``?token` + `TradeCreate`` → `—` | Create Trade |
| GET | `/api/v1/trades` | ``?token`` → `—` | List Trades |
| DELETE | `/api/v1/trades/{trade_id}` | ``trade_id` + `?token`` → `—` | Delete Trade |

## Billing

| Method | Path | Params / body → Response | Notes |
|--------|------|---------------------------|-------|
| POST | `/api/v1/billing/checkout` | ``?token`` → `—` | Checkout |
| POST | `/api/v1/billing/webhook` | → `—` | Webhook |

## Stream

| Method | Path | Params / body → Response | Notes |
|--------|------|---------------------------|-------|
| GET | `/api/v1/stream/quotes` | ``?symbols`` → `—` | Stream Quotes |

## Schemas

Compact JSON skeletons from the OpenAPI components (values are placeholder examples, not real data):

### `AnalysisRequest`

```json
{
  "symbol": "string",
  "asset_type": "string",
  "timeframe": "string",
  "options_enabled": false,
  "strike": "string",
  "strategy": "string"
}
```

### `AnalysisResponse`

```json
{
  "symbol": "string",
  "asset_type": "string",
  "timeframe": "string",
  "current_price": "string",
  "day_change_pct": "string",
  "ytd_change_pct": "string",
  "analyzed_at": "string",
  "overall": {
    "overall_verdict": "string",
    "score": 0,
    "indicator_count": 0,
    "breakdown": [
      {
        "name": "string",
        "value": "string",
        "verdict": "string"
      }
    ]
  },
  "indicators": [
    {
      "name": "string",
      "value": "string",
      "verdict": "string"
    }
  ],
  "price_series": [
    {
      "t": "string",
      "open": 0,
      "high": 0,
      "low": 0,
      "close": 0,
      "source": "string"
    }
  ],
  "indicator_series": [
    {
      "name": "string",
      "kind": "string",
      "points": [
        {
          "t": "string",
          "v": 0
        }
      ]
    }
  ],
  "news_sentiment": "string",
  "news_articles": [
    {
      "id": "string",
      "headline": "string",
      "source": "string",
      "url": "string",
      "summary": "string",
      "created_at": "string",
      "author": "string",
      "symbols": [
        "string"
      ],
      "sentiment": "string"
    }
  ],
  "company": "string"
}
```

### `CompanyInfo`

```json
{
  "symbol": "string",
  "name": "string",
  "short_name": "string",
  "exchange": "string",
  "currency": "string",
  "description": "string",
  "main_listing": "string",
  "sector": "string",
  "industry": "string",
  "website": "string",
  "headquarters": "string",
  "employees": "string",
  "founded": "string",
  "ceo": "string",
  "ceo_title": "string",
  "ceo_pay": "string",
  "market_cap": "string",
  "shares_outstanding": "string",
  "revenue_ttm": "string",
  "pe_ratio": "string",
  "forward_pe": "string",
  "ps_ratio": "string",
  "pb_ratio": "string",
  "high_52w": "string",
  "low_52w": "string",
  "dividend_yield": "string",
  "payout_ratio": "string",
  "revenue_growth": "string",
  "earnings_growth": "string",
  "profit_margin": "string",
  "gross_margin": "string",
  "roe": "string",
  "roa": "string",
  "next_earnings_date": "string"
}
```

### `GreeksSchema`

```json
{
  "delta": 0,
  "gamma": 0,
  "theta": 0,
  "vega": 0,
  "rho": 0
}
```

### `HTTPValidationError`

```json
{
  "detail": [
    {
      "loc": [
        "string"
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
```

### `IndicatorPoint`

```json
{
  "t": "string",
  "v": 0
}
```

### `IndicatorResult`

```json
{
  "name": "string",
  "value": "string",
  "verdict": "string"
}
```

### `IndicatorSeries`

```json
{
  "name": "string",
  "kind": "string",
  "points": [
    {
      "t": "string",
      "v": 0
    }
  ]
}
```

### `LoginRequest`

```json
{
  "email": "string",
  "password": "string"
}
```

### `MainListing`

```json
{
  "symbol": "string",
  "name": "string",
  "exchange": "string"
}
```

### `MatrixCell`

```json
{
  "expiry": "string",
  "days_to_expiry": 0,
  "option_value": 0,
  "pl": 0,
  "pl_pct": 0
}
```

### `MatrixRequest`

```json
{
  "contract_symbol": "string",
  "range_pct": 0,
  "quantity": 0,
  "dates": 0
}
```

### `MatrixRow`

```json
{
  "strike": 0,
  "move_pct": 0,
  "cells": [
    {
      "expiry": "string",
      "days_to_expiry": 0,
      "option_value": 0,
      "pl": 0,
      "pl_pct": 0
    }
  ]
}
```

### `NewsArticle`

```json
{
  "id": "string",
  "headline": "string",
  "source": "string",
  "url": "string",
  "summary": "string",
  "created_at": "string",
  "author": "string",
  "symbols": [
    "string"
  ],
  "sentiment": "string"
}
```

### `OptionChanceResponse`

```json
{
  "symbol": "string",
  "contract_symbol": "string",
  "is_call": false,
  "strike": 0,
  "premium": 0,
  "current_price": 0,
  "days_to_expiry": 0,
  "implied_volatility": 0,
  "prob_profit": 0,
  "prob_itm": 0,
  "expected_value": 0,
  "breakeven": 0
}
```

### `OptionContractSchema`

```json
{
  "symbol": "string",
  "strike_price": 0,
  "expiration_date": "string",
  "type": "string",
  "bid": 0,
  "ask": 0,
  "last_price": 0,
  "implied_volatility": 0,
  "greeks": {
    "delta": 0,
    "gamma": 0,
    "theta": 0,
    "vega": 0,
    "rho": 0
  },
  "days_to_expiry": 0,
  "intrinsic_value": 0,
  "time_value": 0,
  "theoretical_value": 0,
  "spread": 0,
  "distance_pct": 0
}
```

### `OptionValueAtPriceResponse`

```json
{
  "symbol": "string",
  "contract_symbol": "string",
  "strike": 0,
  "premium": 0,
  "is_call": false,
  "target_price": 0,
  "target_date": "string",
  "days_to_expiry": 0,
  "estimated_option_price": 0,
  "estimated_pl": 0,
  "pl_pct": 0
}
```

### `OptionsChainResponse`

```json
{
  "symbol": "string",
  "current_price": "string",
  "day_change_pct": "string",
  "delayed": false,
  "contracts": [
    {
      "symbol": "string",
      "strike_price": 0,
      "expiration_date": "string",
      "type": "string",
      "bid": 0,
      "ask": 0,
      "last_price": 0,
      "implied_volatility": 0,
      "greeks": {
        "delta": 0,
        "gamma": 0,
        "theta": 0,
        "vega": 0,
        "rho": 0
      },
      "days_to_expiry": 0,
      "intrinsic_value": 0,
      "time_value": 0,
      "theoretical_value": 0,
      "spread": 0,
      "distance_pct": 0
    }
  ]
}
```

### `OptionsMatrixResponse`

```json
{
  "symbol": "string",
  "contract_symbol": "string",
  "current_price": 0,
  "range_pct": 0,
  "premium": 0,
  "breakeven": 0,
  "expiries": [
    "string"
  ],
  "strikes": [
    {
      "strike": 0,
      "move_pct": 0,
      "cells": [
        {
          "expiry": "string",
          "days_to_expiry": 0,
          "option_value": 0,
          "pl": 0,
          "pl_pct": 0
        }
      ]
    }
  ]
}
```

### `OptionsPayoffResponse`

```json
{
  "symbol": "string",
  "greeks": {
    "delta": 0,
    "gamma": 0,
    "theta": 0,
    "vega": 0,
    "rho": 0
  },
  "implied_volatility": 0,
  "premium": 0,
  "breakeven": 0,
  "payoff_timeline": [
    {
      "date": "string",
      "day": 0,
      "estimated_option_price": 0,
      "estimated_pl": 0,
      "pl_pct": 0
    }
  ]
}
```

### `OverallVerdict`

```json
{
  "overall_verdict": "string",
  "score": 0,
  "indicator_count": 0,
  "breakdown": [
    {
      "name": "string",
      "value": "string",
      "verdict": "string"
    }
  ]
}
```

### `PayoffPoint`

```json
{
  "price": 0,
  "pl": 0
}
```

### `PayoffRow`

```json
{
  "date": "string",
  "day": 0,
  "estimated_option_price": 0,
  "estimated_pl": 0,
  "pl_pct": 0
}
```

### `PricePoint`

```json
{
  "t": "string",
  "open": 0,
  "high": 0,
  "low": 0,
  "close": 0,
  "source": "string"
}
```

### `RegisterRequest`

```json
{
  "email": "string",
  "password": "string"
}
```

### `StanceRequest`

```json
{
  "symbol": "string",
  "entry_price": 0,
  "current_price": "string",
  "trade_type": "string",
  "contract": "string"
}
```

### `StanceResponse`

```json
{
  "stance": "string",
  "reason": "string",
  "pnl_pct": 0,
  "take_profit_at": 0,
  "cut_loss_at": 0
}
```

### `StrategiesResponse`

```json
{
  "symbol": "string",
  "sentiment": "string",
  "strategies": [
    {
      "name": "string",
      "subtitle": "string",
      "is_bullish": false,
      "max_profit": "string",
      "max_loss": "string",
      "breakeven": 0,
      "return_on_risk": "string",
      "payoff_curve": [
        {
          "price": 0,
          "pl": 0
        }
      ]
    }
  ]
}
```

### `StrategyCard`

```json
{
  "name": "string",
  "subtitle": "string",
  "is_bullish": false,
  "max_profit": "string",
  "max_loss": "string",
  "breakeven": 0,
  "return_on_risk": "string",
  "payoff_curve": [
    {
      "price": 0,
      "pl": 0
    }
  ]
}
```

### `TokenResponse`

```json
{
  "access_token": "string",
  "token_type": "string",
  "tier": "string"
}
```

### `TradeCreate`

```json
{
  "symbol": "string",
  "trade_type": "string",
  "entry_date": "string",
  "entry_price": 0,
  "quantity": 0,
  "contract": "string",
  "notes": "string"
}
```

### `ValidationError`

```json
{
  "loc": [
    "string"
  ],
  "msg": "string",
  "type": "string",
  "input": "string",
  "ctx": {}
}
```

---
# Hand-maintained editorial notes, appended verbatim to the generated API.md.
# Facts that change with code go in the generated tables above; judgment
# (gating, caching, gotchas) goes here. Keep it short and current.

All routes are mounted under `/api/v1`. Responses are JSON. Auth is
self-built JWT passed via `token` query param (not OAuth). Rate limits are
applied per-endpoint via slowapi (free 30/min, pro 200/min, AI 10/min —
per-IP; slowapi's in-memory storage, not Redis).

## Auth

> The frontend **login/register UI is currently removed**; the API stays live.
> `getToken()` in the FE still sends a token to the AI endpoints and the
> Pro-gated options chance endpoint.

## Analysis

`AnalysisRequest`:
```json
{ "symbol": "AAPL", "asset_type": "stock", "timeframe": "1d", "options_enabled": false, "strike": null }
```

- `POST /analysis` caches the full result per symbol per timeframe per day
  (`analysis:{symbol}:{timeframe}:{date}`, 24h TTL) — daily bars change at
  most once/day.
- `GET /analysis/bars/{symbol}` — `t` in every point is a **full ISO
  timestamp**; date-only strings collapse intraday timeframes onto one point.
- `POST /analysis/ai` and `/analysis/ai/stream` are **free for everyone** —
  no tier gating. Per-IP 10/min (`RATE_LIMIT_AI`); result cached per symbol
  per timeframe per day (`ai:{symbol}:{timeframe}:{date}`); single-flight
  locked so concurrent requests share one LLM call. The stream endpoint is
  SSE (`data: {"chunk":"..."}`) and replays cached answers chunk-by-chunk.
- `company.main_listing` (only present for **OTC/foreign ADRs** like `RNMBY`,
  `SMERY`): the primary home-exchange listing, resolved keylessly via Yahoo
  search — `RNMBY → RHM.DE/XETRA`. The frontend shows a "VIEW MAIN LISTING"
  button. Cache key `company:v2:{symbol}` (12h TTL).
- `GET /analysis/market-news` (Finnhub general news, 12h cache) and
  `GET /analysis/fear-greed` (CNN Fear & Greed index, 30 min cache) are
  **loaded independently of `/analysis`** — the news widget and market gauge
  fetch them on their own so they never block the slow report. `fear-greed`
  proxies CNN's unofficial dataviz endpoint (needs the page-cookie handshake;
  plain requests get HTTP 418) and returns `{}` on failure. It also returns a
  `history` array (last ~90 daily scores) which the widget renders as a
  sparkline.
- News is **VADER**-scored per headline; `news_articles[].sentiment` carries
  each article's score. The stock feed merges Alpaca + Google + Finnhub
  `/company-news`, deduped (identical, or same-day ≥85% similar) with a
  per-source cap (max 2 per outlet).

## Assets

`asset_type` is `"stock"` or `"etf"`, derived from the asset **name**
(Alpaca's `asset_class` is always `"us_equity"`). Indices are NOT returned.
The Alpaca asset list (~14k symbols) is cached in memory after first load;
keyless Yahoo search results are merged on top (deduped, cached ~60s
`ysearch:{q}`), so "Rheinmetall" → `RHM.DE` before the OTC ADR `RNMBY`.

## Options

> **Frontend:** `options/[symbol]` is a **gridstack widget grid** (chain,
> payoff, Greeks, probability, P/L matrix, strategies, watchlist). A
> **DELAYED** badge flags the indicative (15-min delayed) feed. Volume/OI
> columns are omitted (not available on the free tier).
>
> **Gating:** `GET /options/{symbol}/chance` is **PRO-ONLY — 403 for
> free/anonymous users** (the only gated endpoint in the app).
> `DEV_FORCE_PRO=true` bypasses it in dev; never in production.

## Portfolio

`POST /portfolio/stance` thresholds come from `TAKE_PROFIT_THRESHOLD`
(default 0.10) / `CUT_LOSS_THRESHOLD` (default -0.08). `current_price` is
optional — the server fetches the live quote when omitted (the client only
stores entry prices).

## Trades

> ⚠ **In-memory persistence** — trades live in a module-level dict and are
> LOST on backend restart (Postgres store was never built). Fine for the
> prototype; ship a DB-backed store before treating trades as data.

## Billing

> **Stripe is fully integrated, not stubbed.** Real `STRIPE_SECRET_KEY`,
> `STRIPE_WEBHOOK_SECRET`, and a non-placeholder `STRIPE_PRICE_ID` are
> required for checkout to work (the service raises a clear ValueError on the
> placeholder `price_pro_monthly`). The webhook is the only path that unlocks
> Pro — register `<backend>/api/v1/billing/webhook` in the Stripe dashboard.

## Stream

SSE events: `data: {"symbol":"AAPL","price":213.44,"size":100,"ts":"..."}`,
heartbeat `: ping` comment every 20s. One upstream Alpaca IEX WebSocket is
fanned out to all subscribers (`services/quote_stream.py`); max 20 symbols.

