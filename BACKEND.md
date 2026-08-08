# VEXARIUM — Backend Guide

How to work in the FastAPI backend. Start with `ARCHITECTURE.md` and
`DATA_AND_INDICATORS.md`; this file is the day-to-day backend cookbook.

## Stack

FastAPI · Pydantic v2 (pydantic-settings) · pandas · alpaca-py ·
pandas-ta-remake · slowapi (rate limiting) · cachetools (in-memory cache) ·
Redis (async) · SQLAlchemy 2 async + asyncpg · python-jose (JWT) ·
passlib/bcrypt · stripe · httpx · websockets · sentry-sdk (optional).
Python 3.11.

## Directory map

```
app/
├── main.py             # app factory: CORS, rate limiter, route mounting, Sentry
├── config.py           # Settings (all env vars; settings is a module singleton)
├── api/                # one router per resource, thin HTTP layer
├── services/           # business logic, no HTTP
├── middleware/         # rate_limit, validation, tier_gating, logging
├── models/ + repositories/   # persistence (Postgres when DATABASE_URL set,
│                            #   in-memory fallback for hermetic tests)
├── schemas/            # pydantic request/response models
tests/                  # pytest suite
```

## Adding a new endpoint

1. Create/edit a router in `app/api/*.py`:
   ```python
   router = APIRouter(prefix="/analysis", tags=["analysis"])

   @router.post("/foo", response_model=FooResponse)
   @limiter.limit(f"{settings.rate_limit_free}/minute")
   async def foo(request: Request, body: FooRequest):
       ...
   ```
   **Every public route needs the `@limiter.limit(...)` decorator** (first arg
   of the handler must be `request: Request` for slowapi).
2. Add the pydantic model(s) in `app/schemas/*.py`.
3. Mount the router in `app/main.py`:
   ```python
   app.include_router(foo_router, prefix="/api/v1")
   ```
4. Add a test in `tests/`.

## Services you'll touch most

| Service | Responsibility |
|---------|----------------|
| `services/alpaca_client.py` | All Alpaca calls + Yahoo bars fallback. **Never call the Alpaca SDK directly in a route** — go through here (handles caching + errors). |
| `services/cache.py` | `cache_get/cache_set/cache_delete`, key builders, TTL constants, single-flight locks. Redis-or-memory. |
| `services/indicator_engine.py` + `indicators/extended.py` | Indicator registry + all 16 indicators. |
| `services/ai_analyzer.py` | LLM prompt build + call (sync `analyze`, stream `analyze_stream`), fallback model chain. |
| `services/company_info.py` | Free keyless company/ETF profile (Yahoo + stockanalysis.com + Wikipedia). |
| `services/news_service.py` | News sentiment scoring. |
| `services/verdicts.py` | Aggregate indicators → overall verdict. |
| `services/stance.py` | Take-profit / cut-loss stance (HOLD / TAKE_PROFIT / CUT_LOSS). |
| `services/options_analyzer.py`, `strategy_engine.py` | Options + strategies + P/L matrix + Black-Scholes. |
| `services/quote_stream.py` | One Alpaca IEX WebSocket fanned out to N SSE subscribers. |
| `services/auth.py` | JWT encode/decode. |
| `services/stripe_service.py` | Stripe checkout session + webhook handling. |

## Error handling conventions

- **Never return raw exceptions to the client.** Mask internals — the API
  layer catches `AlpacaError` / `SymbolNotFoundError` /
  `SubscriptionRequiredError` (all in `services/exceptions.py`) and returns a
  clean status + message.
- `validate_symbol()` (middleware/validation.py) enforces the symbol regex
  `^[A-Z]{1,10}(\.[A-Z]{1,2})?$`.
- 404 for a symbol with no data; 502 for upstream (Alpaca) failures; 500 only
  for unexpected internal errors (logged). AI endpoints return the fallback
  string (200) instead of failing.

## Rate limiting

`middleware/rate_limit.py` uses slowapi (`Limiter(key_func=get_remote_address)`).
Every public route carries a `@limiter.limit(...)` decorator (free 30/min,
pro 200/min, AI 10/min). The limiter is attached in `main.py` with the
`RateLimitExceeded` handler. **Note: slowapi storage is in-memory** — Redis is
used for the app cache (bars/news/analysis/AI/company), not for rate-limit
counters.

## Tests

```bash
env -u PYTHONPATH .venv/bin/python -m pytest tests/ -q   # 248 passed
```

- `tests/conftest.py` clears the cache and forces `dev_force_pro=False`
  (deterministic tier tests regardless of `.env`).
- Tests use FastAPI `TestClient` and mock `AlpacaClient` (no live network
  except a couple of explicit live calls).
- **Never run pytest without `env -u PYTHONPATH`** — the venv shadow breaks
  imports (see `ENVIRONMENT.md`).

## Gotchas

- `env -u PYTHONPATH` for every Python command (see `ENVIRONMENT.md`).
- `.env` inline comments corrupt values.
- Indices (SPX) return 404 — expected.
- The analysis result is cached per symbol per timeframe per day; if you
  change an indicator or verdict logic, bump the analysis cache TTL or clear
  the key while testing.
- Cache keys carry the timeframe (`bars:{symbol}:{timeframe}`,
  `analysis:{symbol}:{timeframe}:{date}`) — don't drop it when building keys.
- Trades are in-memory only (lost on restart) — see `API.md`.
