# VEXARIUM — Backend Guide

How to work in the FastAPI backend. Start with `ARCHITECTURE.md` and
`DATA_AND_INDICATORS.md`; this file is the day-to-day backend cookbook.

## Stack

FastAPI · Pydantic v2 (pydantic-settings) · pandas · alpaca-py ·
pandas-ta-remake · slowapi (rate limiting) · cachetools (in-memory cache) ·
ARQ (worker). Python 3.11.

## Directory map

```
app/
├── main.py             # app factory: CORS, rate limiter, route mounting
├── config.py           # Settings (all env vars; settings is a module singleton)
├── api/                # one router per resource, thin HTTP layer
├── services/           # business logic, no HTTP
├── middleware/         # rate_limit, validation, tier_gating, logging
├── models/ + repositories/   # persistence (SQLAlchemy-adjacent; in-memory fallback)
├── schemas/            # pydantic request/response models
└── worker.py           # ARQ worker entrypoint
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
2. Add the pydantic model(s) in `app/schemas/*.py`.
3. Mount the router in `app/main.py`:
   ```python
   app.include_router(foo_router, prefix="/api/v1")
   ```
4. Add a test in `tests/`.

## Services you'll touch most

| Service | Responsibility |
|---------|----------------|
| `services/alpaca_client.py` | All Alpaca calls. **Never call Alpaca SDK directly in a route** — go through here (handles caching + errors). |
| `services/cache.py` | `cache_get/cache_set`, key builders, TTL constants. Redis-or-memory. |
| `services/indicator_engine.py` | Indicator registry + engines. |
| `services/ai_analyzer.py` | LLM prompt + call. |
| `services/news_service.py` | News sentiment scoring. |
| `services/verdicts.py` | Aggregate indicators → overall verdict. |
| `services/stance.py` | Take-profit / cut-loss stance (HOLD / TAKE_PROFIT / CUT_LOSS). |
| `services/options_analyzer.py`, `strategy_engine.py` | Options + strategies + P/L matrix + Black-Scholes. |

## Error handling conventions

- **Never return raw exceptions to the client.** Mask internals — the API
  layer catches `AlpacaError`/`SubscriptionRequiredError`/etc. and returns a
  clean status + message.
- `validate_symbol()` enforces the symbol regex `^[A-Z]{1,10}(\.[A-Z]{1,2})?$`.
- 404 for a symbol with no data; 502 for upstream (Alpaca) failures; 500 only
  for unexpected internal errors (logged).

## Rate limiting

`middleware/rate_limit.py` uses slowapi. Every public route should have a
`@limiter.limit(...)` decorator (free 30/min, pro 200/min). The limiter is
attached in `main.py` and uses Redis if configured, else memory.

## Tests

```bash
env -u PYTHONPATH .venv/bin/python -m pytest tests/ -q   # 147 passed, 1 skipped
```

- `tests/conftest.py` clears the cache and forces `dev_force_pro=False`
  (deterministic tier tests regardless of `.env`).
- Tests use FastAPI `TestClient` and mock `AlpacaClient` (no live network
  except a couple of explicit live calls).
- **Never run pytest without `env -u PYTHONPATH`** — the venv shadow breaks
  imports.

## Gotchas

- `env -u PYTHONPATH` for every Python command (see `ENVIRONMENT.md`).
- `.env` inline comments corrupt values.
- Indices (SPX) return 404 — expected.
- The analysis result is cached per symbol per day; if you change an indicator
  or verdict logic, bump the analysis cache TTL or clear the key while testing.
