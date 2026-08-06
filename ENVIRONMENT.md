# VEXARIUM — Environment & Local Setup

Everything you need to run the project locally and the gotchas that bite.

## Prerequisites

- Python 3.11
- Node.js + Yarn Berry 4.x (`corepack enable`)
- (Optional) Docker for the full stack

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .            # or: pip install -r requirements / pip install .
cp .env.example .env        # if present; otherwise create .env (see below)
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

`.env` is **gitignored**. Key values:

| Var | Purpose |
|-----|---------|
| `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` | Alpaca **paper** trading keys. |
| `ALPACA_PAPER=true` | Paper trading. |
| `LLM_BASE_URL=https://ollama.com/v1` | AI endpoint. |
| `LLM_API_KEY` | ollama-cloud key. |
| `LLM_MODEL=deepseek-v4-flash:0731` | AI model. |
| `JWT_SECRET` | Auth secret. Placeholder fails in production. |
| `DEV_FORCE_PRO=true` | Dev-only: unlock Pro tier for everyone. |
| `VEXARIUM_ENV` | `development` / `production`. Guards JWT secret + dev bypass. |
| `DATABASE_URL=postgresql://vexarium:vexarium_dev@localhost:5432/vexarium` | Postgres (local Docker, Neon, or Render). Empty → in-memory repos. |
| `REDIS_URL=redis://localhost:6379/0` | Redis cache. Empty → in-memory TTL cache. |
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | Stripe billing. Webhook endpoint must point at `<backend>/api/v1/billing/webhook`. |
| `STRIPE_PRICE_ID` | Pro subscription Price ID from the Stripe dashboard. |
| `STRIPE_SUCCESS_URL` / `STRIPE_CANCEL_URL` | Stripe Checkout redirect URLs (set to the prod frontend, e.g. `https://vexarium.pages.dev/pricing?...`). Defaults to localhost. |
| `CORS_ORIGINS=http://localhost:5173` | Allowed origins, comma-separated. |

### Local Postgres + Redis

Postgres (users, tier, Stripe customer mapping) and Redis (bars/news/analysis/
AI cache) run via Docker Compose. From the repo root:

```bash
docker compose up -d postgres redis   # postgres:5432, redis:6379
```

`backend/.env` already points `DATABASE_URL` and `REDIS_URL` at them. When
`DATABASE_URL` is set, the app auto-creates tables on startup and persists
users/subscriptions. Tests force empty URLs so they stay hermetic.

### `.env` gotcha

**Never put an inline comment on the same line as a value** in `.env`.
`pydantic-settings` reads the whole line, so `KEY=value # comment` includes
`# comment` as part of the value.

## Dev Pro toggle / auth

All **indicators are free** (no indicator Free/Pro split anymore). The **Pro
tier gates AI analysis only**. To test the AI paywall locally:

- Register/login via the header's "LOGIN / SIGN UP" button.
- Set `DEV_FORCE_PRO=true` in `backend/.env` to treat every user as Pro (bypass
  the tier check) and restart the backend. Without it, anonymous/free users
  get **403** from `/analysis/ai`.

> **Tests note:** `backend/tests/conftest.py` forces `dev_force_pro=False` so
> the tier-gating tests are deterministic regardless of your `.env`.

## Docker (full stack)

```bash
docker compose up --build
# api :8000, postgres:5432, redis:6379
```

See `docker-compose.yml` and `DEPLOYMENT.md`.

## Running the test suite

```bash
cd backend
env -u PYTHONPATH .venv/bin/python -m pytest tests/ -q
# expect: 134 passed, 1 skipped
```
