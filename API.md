# VEXARIUM — API Reference

All routes are mounted under `/api/v1`. Responses are JSON. Auth is
JWT-bearer via `token` query param (simple, self-built — not OAuth).
Rate limits are applied per-endpoint (free 30/min, pro 200/min).

## Health

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/health/` | Liveness |
| GET | `/api/v1/health/ready` | Readiness — checks Redis if configured, else 200. Degrades gracefully. |
| GET | `/health` | Root liveness (no prefix) |

## Auth

| Method | Path | Body | Notes |
|--------|------|------|-------|
| POST | `/api/v1/register` | `{email, password}` | 201. Password policy enforced. Rate limited. |
| POST | `/api/v1/login` | `{email, password}` | Returns `{access_token, token_type}`. |
| GET | `/api/v1/me` | `?token=` | Current user info. |

## Analysis

| Method | Path | Body | Notes |
|--------|------|------|-------|
| POST | `/api/v1/analysis` | `AnalysisRequest` | Returns **all 10 indicators** (indicators are free). Returns `AnalysisResponse`. |
| POST | `/api/v1/analysis/extended` | `AnalysisRequest` | Pro-gated but returns the same 10 indicators (kept for compat; indicators are no longer split). |
| POST | `/api/v1/analysis/ai` | `AnalysisRequest` | Runs LLM on indicators + news + fundamentals. **Free for everyone** — no token/tier gating. **Per-IP rate limit 10/min** (`RATE_LIMIT_AI`); result **cached per-symbol-per-day** (`ai:{symbol}:{date}`, 24h TTL) so repeat views never hit the LLM. |
| POST | `/api/v1/analysis/options-strategies` | `{symbol, strike}` | **Pro-only.** LLM explains the recommended options strategy for a symbol near a given strike (decision-impacting, no free preview). |

`AnalysisRequest`:
```json
{ "symbol": "AAPL", "asset_type": "stock", "options_enabled": false }
```

`AnalysisResponse` (free & extended; `news_articles` added for the dropdown):
```json
{
  "symbol": "AAPL",
  "asset_type": "stock",
  "current_price": 757.67,
  "analyzed_at": "2026-08-04T10:00:00+00:00",
  "overall": { "overall_verdict": "hold", "score": 0, "indicator_count": 5, "breakdown": [] },
  "indicators": [ { "name": "RSI(14)", "value": 41.2, "verdict": "hold", "tier": "free" } ],
  "price_series": [ { "t": "2026-01-05", "open": 100, "high": 101, "low": 99, "close": 100.5 } ],
  "indicator_series": [ { "name": "RSI(14)", "kind": "oscillator", "points": [ { "t": "2026-01-05", "v": 41.2 } ] } ],
  "news_sentiment": { "sentiment_score": 0.1, "article_count": 10, "summary": "Recent news sentiment is neutral." },
  "news_articles": [ { "id": "123", "headline": "...", "source": "benzinga", "url": "...", "created_at": "..." } ],
  "company": { "symbol": "AAPL", "name": "Apple Inc.", "exchange": "NasdaqGS", "high_52w": 344.57, "low_52w": 205.59, "currency": "USD", "sector": "Technology", "industry": "Consumer Electronics", "market_cap": 3000000000000, "pe_ratio": 32.5, "roe": 1.47, "employees": 150000, "ceo": "Tim Cook", "description": "Apple Inc. is an American multinational technology company..." }
}
```

`company.main_listing` (only present for **OTC/foreign ADRs** like `RNMBY`,
`SMERY`): the primary home-exchange listing, resolved keylessly via Yahoo
search — e.g. `RNMBY → {symbol: "RHM.DE", name: "Rheinmetall AG", exchange:
"XETRA"}`, `SMERY → {symbol: "ENR.DE", ...}`. The frontend shows a
"VIEW MAIN LISTING" button when this is present. Cache key `company:v2:{symbol}`
(12h TTL).

## Asset search (autocomplete)

| Method | Path | Params | Notes |
|--------|------|--------|-------|
| GET | `/api/v1/assets/search` | `?q=APPLE` or `?q=AAPL` (max 60 chars) | Returns `{assets:[{symbol,name,exchange,asset_type}]}`. Matches **symbol prefix, exact symbol, and company name** substring (e.g. "Apple" → AAPL), then merges **keyless Yahoo search results** so foreign main listings appear (e.g. "Rheinmetall" → `RHM.DE`/XETRA **before** the OTC ADR `RNMBY`). Yahoo results are cached ~60s (`ysearch:{q}`). |

`asset_type` is `"stock"` or `"etf"`, derived from the asset **name**
(Alpaca's `asset_class` is always `"us_equity"` and does not distinguish
ETF vs stock). Indices are NOT returned. The endpoint caches the full
Alpaca asset list in memory (~14k symbols) after the first load; Yahoo
results are appended on top (deduped by symbol).

## Options

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/options/{symbol}/chain` | **Full option chain** via Alpaca's market-data chain endpoint. Returns per-contract `symbol` (OCC), `strike_price`, `expiration_date`, `type`, `bid`, `ask`, `last_price`, `implied_volatility`, `greeks{delta,gamma,theta,vega,rho}`, plus computed `days_to_expiry`, `intrinsic_value`, `time_value`, `theoretical_value` (Black-Scholes), `spread`, `distance_pct`. `volume`/`open_interest` are `null` (Alpaca's free tier does not provide them — do not fabricate). Response also carries `current_price`, `day_change_pct`, and `delayed: true` (indicative feed). Skips same-day (0 DTE) expiries (they have no greeks). |
| GET | `/api/v1/options/{symbol}/payoff` | `?contract_symbol=` OCC code. Parses strike/type/expiry from OCC. |
| POST | `/api/v1/options/{symbol}/matrix` | `{contract_symbol, range_pct, quantity}` → **P/L matrix** (rows = strikes centered ±range_pct, columns = expiries, cells = Black-Scholes P/L). |
| GET | `/api/v1/options/{symbol}/value` | `?contract_symbol=&target_price=&target_date=` → **Black-Scholes** estimate of the option's worth if the underlying trades at `target_price`. |
| GET | `/api/v1/options/{symbol}/chance` | `?contract_symbol=&token=` → **Chance-of-profit estimate** (probability of profit, probability of ending ITM, expected value, breakeven) via a Black-Scholes normal model from implied volatility. **Pro-only — 403 for free/anonymous users.** All values are estimates. |

> **Frontend:** the options page (`/options/[symbol]`) is a **tabbed, beginner-first
> view**: **GUIDED** (plain-English glossary + experience level toggle + sentiment /
> target / budget + strategy cards), **CHAIN** (a two-sided TradingView-style
> CALLS | STRIKE+IV | PUTS table grouped by expiration, built from the enriched
> `/chain` response), and **BUILDER** (contract picker + payoff explorer +
> Pro-gated chance-of-profit + Greeks + P/L matrix + payoff timeline). A
> **DELAYED** badge flags the indicative (15-min delayed) feed. Volume/OI columns
> are intentionally omitted.

## Strategies & stance

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/strategies/{symbol}/strategies` | `?sentiment=&strike=&expiration_gte=&expiration_lte=`. Strategy selection is driven by **technical indicators** (computed server-side), falling back to the `sentiment` param. |
| POST | `/api/v1/portfolio/stance` | Compute take-profit/cut-loss stance. |

## Portfolio (trades)

| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/v1/trades` | `?token=` + body. Create trade. 201. |
| GET | `/api/v1/trades` | `?token=`. List current user's trades. |
| DELETE | `/api/v1/trades/{trade_id}` | `?token=`. 204. |
| POST | `/api/v1/trades/stance` | `?token=`. Batch stance. |

## Billing (Stripe)

| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/v1/billing/checkout` | `?token=` creates a Stripe Checkout **subscription** session (Pro). Returns `{checkout_url}`. |
| POST | `/api/v1/billing/webhook` | Stripe webhook → `checkout.session.completed` upgrades the user to Pro (and maps the Stripe customer id); `customer.subscription.deleted` downgrades back to free. |

> **Stripe is fully integrated, not stubbed.** Real `STRIPE_SECRET_KEY`,
> `STRIPE_WEBHOOK_SECRET`, and a non-placeholder `STRIPE_PRICE_ID` are required
> in the environment for checkout to work (the service raises a clear
> ValueError if `STRIPE_PRICE_ID` is empty or the placeholder
> `price_pro_monthly`). The webhook is the **only** path that unlocks Pro —
> ensure `<backend>/api/v1/billing/webhook` is registered in the Stripe
> dashboard. `DEV_FORCE_PRO=true` bypasses tier checks in dev.
