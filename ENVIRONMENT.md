# VEXARIUM — Environment & Local Setup

Everything you need to run the project locally and the gotchas that bite.

## Prerequisites

- Python 3.11
- Node.js + Yarn Berry 4.x (`corepack enable`)
- (Optional) Docker for Postgres + Redis locally (there is no
  docker-compose.yml in the repo anymore — start the services however you
  like, or run without them: the app falls back to in-memory stores)

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .            # or: pip install .
cp .env.example .env        # then fill in real values
```

Run (local, no Docker):

```bash
env -u PYTHONPATH .venv/bin/uvicorn app.main:app --reload
# → http://127.0.0.1:8000
```

### The PYTHONPATH gotcha (CRITICAL)

This Hermes session exports `PYTHONPATH` that **shadows the project venv**.
If imports fail or you get the wrong package versions, run Python with the
env var stripped:

```bash
env -u PYTHONPATH .venv/bin/python -m pytest tests/ -q
env -u PYTHONPATH .venv/bin/uvicorn app.main:app --reload
```

Alternatively add `unset PYTHONPATH` to `~/.zshrc`.

## Frontend

```bash
cd frontend
corepack enable            # once, if yarn not found
yarn install
yarn dev                   # → http://localhost:5173
```

Gates:

```bash
yarn check                 # svelte-check: expect 0 errors (some pre-existing warnings)
yarn build                 # adapter-cloudflare build
```

**Always use `yarn`, never `npm`** — this project is Yarn Berry 4.17.0
(node-modules linker, pinned release in `.yarn/releases/`).

## Environment variables (`backend/.env`)

`.env` is **gitignored**. Copy `.env.example` and fill in:

| Var | Purpose |
|-----|---------|
| `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` | Alpaca **paper** trading keys. |
| `ALPACA_PAPER=true` | Paper trading. |
| `LLM_BASE_URL=https://opencode.ai/zen/go/v1` | AI endpoint — **OpenCode Go subscription** (OpenAI-compatible). Not the free `/zen/v1` tier (no balance there). |
| `LLM_API_KEY` | OpenCode key (Go subscription). |
| `LLM_MODEL=mimo-v2.5` | AI model — highest-usage Go model usable in DE. |
| `TWELVEDATA_API_KEY` | Real-time intraday bars (free at twelvedata.com, 8 req/min, 800/day). Empty → intraday bars use Alpaca (15-min delayed) + Yahoo. |
| `FINNHUB_API_KEY` | Insider transactions / earnings / peers widgets (free at finnhub.io). Empty → those widgets show no data. |
| `CORS_ORIGINS=http://localhost:5173` | Allowed origins, comma-separated. |
| `REDIS_URL=redis://localhost:6379/0` | Redis cache + single-flight locks. Empty → in-memory TTL cache. |
| `SENTRY_DSN` | Optional error tracking; empty disables. |
| `DATABASE_URL=postgresql://vexarium:***@localhost:5432/vexarium` | Postgres (users/tiers/Stripe mapping). Empty → in-memory repos. Local Postgres needs `?ssl=disable` (no TLS); Neon/Render use TLS. |
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | Stripe billing. Webhook must point at `<backend>/api/v1/billing/webhook`. |
| `STRIPE_PRICE_ID` | Pro subscription Price ID (non-placeholder). |
| `STRIPE_SUCCESS_URL` / `STRIPE_CANCEL_URL` | Stripe Checkout redirect URLs (prod: `https://vexarium.pages.dev/pricing?...`). |
| `VEXARIUM_ENV` | `development` / `production`. Guards JWT secret + dev bypass. |
| `DEV_FORCE_PRO=true` | Dev-only: treat everyone as Pro. **Never in production.** |
| `JWT_SECRET` | Auth secret. Placeholder `change-me-in-production` refuses to boot in production. |
| `JWT_EXPIRY_HOURS=24` | Token lifetime. |
| `TAKE_PROFIT_THRESHOLD=0.10` / `CUT_LOSS_THRESHOLD=-0.08` | Portfolio stance thresholds. |
| `RATE_LIMIT_FREE=30` / `RATE_LIMIT_PRO=200` / `RATE_LIMIT_AI=10` | Per-IP requests/minute. |

### Local Postgres + Redis

Postgres (users, tier, Stripe customer mapping) and Redis (bars/news/analysis/
AI cache + single-flight locks) are managed services in production (Neon /
Upstash). For local dev, start them however you like — e.g.:

```bash
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=vexarium postgres:16-alpine
docker run -d -p 6379:6379 redis:7-alpine
```

`backend/.env` points `DATABASE_URL` and `REDIS_URL` at them. When
`DATABASE_URL` is set, the app auto-creates tables on startup and persists
users/subscriptions. Tests force empty URLs so they stay hermetic.

### `.env` gotcha

**Never put an inline comment on the same line as a value** in `.env`.
`pydantic-settings` reads the whole line, so `KEY=value # comment` includes
`# comment` as part of the value.

## Dev Pro toggle / auth

**Everything is free today** — all 16 indicators and the AI analysis are open
to everyone. The only Pro-gated endpoint is `GET /options/{symbol}/chance`
(403 for free/anonymous). To test the paywall locally:

- Set `DEV_FORCE_PRO=true` in `backend/.env` to treat every user as Pro
  (bypasses the tier check) and restart the backend. Without it,
  anonymous/free users get **403** from `/options/{symbol}/chance`.
- Register/login via the API (the frontend login UI is currently removed):
  ```bash
  curl -s -X POST localhost:8000/api/v1/auth/register -H 'Content-Type: application/json' \
    -d '{"email":"a@b.c","password":"supersecret"}'
  ```

> **Tests note:** `backend/tests/conftest.py` forces `dev_force_pro=False` so
> the tier-gating tests are deterministic regardless of your `.env`.

## Running the test suite

```bash
cd backend
env -u PYTHONPATH .venv/bin/python -m pytest tests/ -q
# expect: 268 passed
```

The suite includes `tests/test_docs_sync.py` — it regenerates `docs/API.md`
from the OpenAPI schema in memory and fails if the committed file drifted
(skipped when the docs repo isn't checked out next to backend). Fix with:

```bash
env -u PYTHONPATH .venv/bin/python ../docs/scripts/generate_api_md.py
```
