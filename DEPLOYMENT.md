# VEXARIUM — Deployment

How VEXARIUM is (or will be) deployed. Start at $0, upgrade after first paying
user.

## Repo topology (split mirrors)

The **monorepo `Al0ngsy/vexarium` is the source of truth**. Backend and
frontend are mirrored to their own repos via `git subtree split`:

- **`Al0ngsy/vexarium-backend`** — Render **auto-deploys on push to `main`**.
- **`Al0ngsy/vexarium-frontend`** — mirror for standalone use; the live FE
  deploys via Cloudflare Pages from the monorepo.

To push code changes to the mirrors (and thus trigger a backend deploy), run
`./scripts/deploy.sh split` (or `all`). The script splits `backend/` and
`frontend/` into `split/backend` / `split/frontend` branches and pushes them to
the mirror repos.

## Deploying manual changes (runbook)

The exact commands live in **`scripts/deploy.sh`** (secrets auto-loaded from
`deploy-secrets.env`). Run it from the repo root:

```bash
./scripts/deploy.sh          # split+push BE & FE, then trigger BE redeploy
./scripts/deploy.sh split    # push subtree splits to both mirror repos
./scripts/deploy.sh fe       # frontend only (Cloudflare Pages)
./scripts/deploy.sh be       # backend redeploy only (Render)
./scripts/deploy.sh local    # start local Postgres + Redis (docker compose)
```

### Backend (Render) — `vexarium-api`
Render **auto-deploys from `Al0ngsy/vexarium-backend` `main`** on push. To
deploy backend changes:

```bash
cd /Users/lqat/Project/vexarium
git add -A && git commit -m "change" && git push origin main
./scripts/deploy.sh split    # pushes the backend subtree -> triggers Render
```

**Env-var changes do NOT auto-redeploy.** After changing a Render env var,
trigger a manual deploy:

```bash
curl -X POST "https://api.render.com/v1/services/srv-d9p51ovlk1mc73ad1t3g/deploys" \
  -H "Authorization: Bearer $RENDER_API_KEY" -H "Accept: application/json"
```

### Frontend (Cloudflare Pages) — `vexarium.pages.dev`
Manual deploy (build with the prod API URL, then push to Pages):

```bash
cd frontend
export CLOUDFLARE_API_TOKEN="$CLOUDFLARE_API_TOKEN"   # from deploy-secrets.env
export CLOUDFLARE_ACCOUNT_ID="6df45854487d44b5a40cf98b3309904e"
export VITE_API_URL="https://vexarium-api.onrender.com"
yarn build
yarn wrangler pages deploy .svelte-kit/cloudflare --project-name=vexarium --branch=main
```

### Redis + Postgres
- **Production:** both are **managed** (Upstash Redis, Neon Postgres) — nothing
  to deploy. The backend points at them via `REDIS_URL` / `DATABASE_URL` env
  vars on Render.
- **Local dev:** `./scripts/deploy.sh local` (or `docker compose up -d`) starts
  Postgres on 5432 + Redis on 6379.

## Container topology

`docker-compose.yml` runs 4 services:

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `api` | `./backend` (Dockerfile) | 8000 | FastAPI app |
| `worker` | `./backend` | — | ARQ worker (`python -m app.worker`) |
| `postgres` | `postgres:16-alpine` | 5432 | Database (volume `pgdata`) |
| `redis` | `redis:7-alpine` | 6379 | Cache + rate limit + ARQ broker |

Both `api` and `worker` build the same backend image; the worker overrides
the command. They read env from `backend/.env`.

## Phase 1 — $0 / free tier (current / live)

Live as of Aug 2026:
- **Backend** → Render free web service `vexarium-api` at `https://vexarium-api.onrender.com`
  (region **frankfurt**), auto-deploys from **`Al0ngsy/vexarium-backend`** `main`
  (pushed via `./scripts/deploy.sh split` from the monorepo).
- **Postgres** → **Neon** free tier, project **in Frankfurt (`aws-eu-central-1`)**.
- **Redis** → **Upstash** free (`rediss://...`).
- **Frontend** → **Cloudflare Pages** `vexarium` at `https://vexarium.pages.dev`
  (`@sveltejs/adapter-cloudflare`, `nodejs_compat` flag set).
- **Stripe** → live in test mode; product "VEXARIUM Pro" (€9/mo, `prod_V0rRUlFJkyA6Xj`),
  price `price_1U0pisJh8ojfoHZrQlkhWk75`, webhook registered at
  `https://vexarium-api.onrender.com/api/v1/billing/webhook`.

**Deploy gotchas (learned):**
- Render uses Python 3.14 by default → pin `PYTHON_VERSION=3.12.4` (pandas_ta_remake
  needs `pkg_resources`, removed in 3.14 / setuptools≥81 → pin `setuptools<81`).
- Neon DATABASE_URL has `channel_binding`/`sslmode` query params that **crash
  asyncpg** → `db._asyncpg_safe_url()` strips them and sets TLS via
  `connect_args={"ssl":"require"}`.
- Setting env vars via the Render API does **not** auto-redeploy — trigger
  `POST /services/{id}/deploys` after changing env vars.
- Stripe v15 returns `StripeObject` (no `.get()`) → webhook handler converts
  via `stripe_service._to_dict()`.

## Phase 2 — Hetzner VPS (after first paying user)

Migrate to a Hetzner VPS running the full `docker-compose.yml` stack
(api + worker + postgres + redis). This unlocks:
- Persistent Redis cache (no cold-start cache loss).
- The ARQ worker for Pro daily auto-update.
- Cheaper long-run costs once traffic grows past free-tier limits.

## Stripe setup (required for Pro to work)

Done in test mode on the live backend:
1. **Product + Price** created: "VEXARIUM Pro" recurring €9/month
   (`prod_V0rRUlFJkyA6Xj`, `price_1U0pisJh8ojfoHZrQlkhWk75`). Product has
   `tax_code=txcd_10000000` (electronically-supplied software) — required
   because the account has **Managed Payments** enabled.
2. `STRIPE_SECRET_KEY` / `STRIPE_PRICE_ID` set in the host env (Render).
3. **Webhook** registered at
   `https://vexarium-api.onrender.com/api/v1/billing/webhook`, subscribing to
   `checkout.session.completed` (→ Pro) and `customer.subscription.deleted`
   (→ free). `STRIPE_WEBHOOK_SECRET` set in the host env.
4. `STRIPE_SUCCESS_URL`/`STRIPE_CANCEL_URL` point at `https://vexarium.pages.dev/pricing`.

To add live (production) keys later: repeat steps 1–3 against the live-mode
keys and set them on Render. The code path is identical.

## Backend Dockerfile

The backend `Dockerfile` installs deps, then runs uvicorn. Set `ENV`/env vars
via `env_file` or build args. **Do not bake secrets into the image.**

## Frontend Cloudflare Pages

- Build: `yarn build` (adapter-cloudflare).
- The SvelteKit `load`/client code calls the backend at `http://localhost:5173`
  locally; set the production API base URL via env when deploying.

## Environment secrets

`.env` is gitignored and never committed. In production use the host's env /
platform secrets (Render env vars, Cloudflare secrets, VPS `.env`).

## Production safety

- `vexarium_env=production` + placeholder `JWT_SECRET` → app refuses to start
  (see `config.py::_check_production_jwt`).
- Set `DEV_FORCE_PRO=false` (it must never be true in production).
- Always a financial disclaimer; this is analysis-only, no trading.

## CI/CD

`.github/workflows/ci.yml` runs backend tests + frontend `yarn install
--immutable` + `yarn check`. Extend it for deploy steps when you pick a
platform.
