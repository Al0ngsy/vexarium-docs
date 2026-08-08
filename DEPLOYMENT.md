# VEXARIUM — Deployment

How VEXARIUM is deployed. Start at $0, upgrade after first paying user.

## Repo topology (3 standalone repos)

VEXARIUM is split into **three independent GitHub repos**, checked out
side-by-side in one local folder (`~/Project/vexarium/`):

- **`Al0ngsy/vexarium-backend`** — FastAPI backend. **Render auto-deploys on
  push to `main`**.
- **`Al0ngsy/vexarium-frontend`** — SvelteKit frontend. Deploys to Cloudflare
  Pages.
- **`Al0ngsy/vexarium-docs`** — documentation (this folder).

The former monorepo `Al0ngsy/vexarium` is **archived** (read-only) and no
longer used.

## Backend (Render) — `vexarium-api`

Render **auto-deploys from `Al0ngsy/vexarium-backend` `main`** on push. To
deploy backend changes:

```bash
cd backend
git add -A && git commit -m "change" && git push origin main
```

Render picks up the push and rebuilds automatically.

**Env-var changes do NOT auto-redeploy.** After changing a Render env var,
trigger a manual deploy:

```bash
curl -X POST "https://api.render.com/v1/services/srv-d9p51ovlk1mc73ad1t3g/deploys" \
  -H "Authorization: Bearer ***" -H "Accept: application/json"
```

## Frontend (Cloudflare Pages) — `vexarium.pages.dev`

One-command deploy (wrangler **direct upload** — the Pages project is not
git-connected):

```bash
cd frontend
yarn deploy          # → bash scripts/deploy.sh
```

`scripts/deploy.sh` builds with the production API URL, then uploads via
wrangler. Secrets are read from, in order: environment variables
(`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`) →
`../deploy-secrets.env` → `./.env`. Overridable: `VITE_API_URL` (default
`https://vexarium-api.onrender.com`) and `CF_PROJECT` (default `vexarium`).

## Redis + Postgres

- **Production:** both are **managed** (Upstash Redis, Neon Postgres) —
  nothing to deploy. The backend points at them via `REDIS_URL` /
  `DATABASE_URL` env vars on Render.
- **Local dev:** start Postgres (5432) + Redis (6379) yourself (see
  `ENVIRONMENT.md`); the app also runs without them (in-memory fallbacks).
  There is **no docker-compose.yml** in the repo anymore.

## Phase 1 — $0 / free tier (current / live)

Live as of Aug 2026:
- **Backend** → Render free web service `vexarium-api` at `https://vexarium-api.onrender.com`
  (region **frankfurt**), auto-deploys from **`Al0ngsy/vexarium-backend`** `main`.
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
  `connect_args={"ssl":"require"}`. Local Postgres (no TLS) needs
  `?ssl=disable` in the URL.
- Setting env vars via the Render API does **not** auto-redeploy — trigger
  `POST /services/{id}/deploys` after changing env vars.
- Stripe v15 returns `StripeObject` (no `.get()`) → webhook handler converts
  via `stripe_service._to_dict()`.
- The `-free` LLM model IDs only work on `https://opencode.ai/zen/v1` — the
  `/go/v1` path rejects them (401). Set `LLM_BASE_URL` accordingly on Render.

## Phase 2 — Hetzner VPS (after first paying user)

Optional migration to a Hetzner VPS running the backend Dockerfile + Postgres
+ Redis. This unlocks persistent Redis cache (no cold-start cache loss) and
cheaper long-run costs once traffic grows past free-tier limits. **Not started
yet.** The `frontend/Dockerfile` (self-host path) is optional infrastructure
for this migration; the primary FE target remains Cloudflare Pages.

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

The backend `Dockerfile` installs deps, then runs uvicorn. Set env vars via
the host (Render env vars / VPS `.env`). **Do not bake secrets into the image.**

## Environment secrets

`.env` is gitignored and never committed. In production use the host's env /
platform secrets (Render env vars, Cloudflare secrets, `deploy-secrets.env`
for local deploys).

## Production safety

- `vexarium_env=production` + placeholder `JWT_SECRET` → app refuses to start
  (see `config.py::_check_production_jwt`).
- Set `DEV_FORCE_PRO=false` (it must never be true in production).
- Always a financial disclaimer; this is analysis-only, no trading.
- There are **no CI workflows** in the repos today — deploy gates are
  `pytest` (backend) and `yarn check` + `yarn build` (frontend), run locally
  or by whoever pushes.
