# VEXARIUM — Project Documentation

**VEXARIUM** is a web-based **before-you-buy/sell decision-support** tool for
stocks, ETFs, indices and options. Free tier + Pro tier ($9/mo). FastAPI
backend + SvelteKit frontend, Professional Dashboard V2 visual design.
**Analysis only — no trading.**

> ⚠ This is a technical handoff document set. Read `ARCHITECTURE.md` first,
> then the file relevant to whatever you are working on. The `vexarium-backend`
> and `vexarium-frontend` repos each contain a `README.md` with setup/run
> details; these docs are the higher-level overview for AI agents continuing work.

---

## Document map

| File                                               | When to read it                                                                                                                     |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| [ARCHITECTURE.md](./ARCHITECTURE.md)               | **Start here.** System topology, components, data flow.                                                                             |
| [BACKEND.md](./BACKEND.md)                         | Working on the FastAPI backend.                                                                                                     |
| [FRONTEND.md](./FRONTEND.md)                       | Working on the SvelteKit frontend.                                                                                                  |
| [API.md](./API.md)                                 | Need the exact request/response shape of an endpoint. **Auto-generated** from the OpenAPI schema (`docs/scripts/generate_api_md.py`) — editorial notes live in `docs/scripts/api_notes.md`. |
| [DATA_AND_INDICATORS.md](./DATA_AND_INDICATORS.md) | Data sources, caching, indicator registry, asset types.                                                                             |
| [AI_ANALYSIS.md](./AI_ANALYSIS.md)                 | The AI pipeline, prompts, provider/model, streaming, news feed & sentiment. |
| [OPTIONS_PAGE_REWORK.md](./OPTIONS_PAGE_REWORK.md) | **Implemented options-page rework** (Aug 2026): Alpaca options capabilities audit + beginner-first page design + phased build plan. |
| [ENVIRONMENT.md](./ENVIRONMENT.md)                 | Env vars, setup, PYTHONPATH gotcha, dev tools.                                                                                      |
| [DEPLOYMENT.md](./DEPLOYMENT.md)                   | Render/Neon/Upstash/Cloudflare Pages, Stripe, the deploy script.                                                                    |
| [CONVENTIONS.md](./CONVENTIONS.md)                 | Coding conventions and non-obvious gotchas.                                                                                         |

---

## Quick facts (one-paragraph orientation)

- **Stack:** FastAPI (Python 3.11) · PostgreSQL (SQLAlchemy async + asyncpg) ·
  Redis · SvelteKit + Tailwind v4 + Svelte 5 (runes) ·
  TradingView Lightweight Charts v5 · gridstack.js · Yarn Berry 4.17.
- **Brand / design:** VEXARIUM, Professional Dashboard V2 — flat solid dark
  `#0a0c10`, blue accent `#3b82f6`, sentence case, 8–10px radius,
  full-width 12-column widget grid (gridstack), no metaphor vocabulary.
- **AI:** `mimo-v2.5` via **OpenCode Go** (`https://opencode.ai/zen/go/v1`,
  OpenAI-compatible, subscription — ~$10/mo). **Single model — free-tier
  fallback chain removed.** Usage limits: https://opencode.ai/docs/go/#usage-limits.
- **Data:** Alpaca (paper keys) for OHLCV bars (daily + intraday timeframes),
  quotes, news, options chains/Greeks. **Yahoo Finance** fallback for bars of
  OTC/foreign ADRs + company fundamentals; **stockanalysis.com** as a
  fundamentals fallback; **Wikipedia** for descriptions.
- **Monetization:** **everything is free today** — all 16 indicators, the AI
  analysis (per-IP 10 req/min + 24h per-symbol cache, streamed via SSE), and
  options analytics. The **only Pro-gated endpoint is the options
  chance-of-profit estimate** (`/options/{symbol}/chance`). Stripe is fully
  integrated (checkout + webhook) and ready for a future Pro tier.
- **Auth:** minimal self-built JWT auth (register/login/me). The frontend
  **login UI is currently removed** (getToken still feeds the AI stream); the
  backend auth API stays live. In dev, `DEV_FORCE_PRO=true` bypasses tier checks.
- **Tests:** backend `268 passed`. Frontend gates: `yarn check`
  (0 errors) + `yarn build`.

Read the per-topic docs for the details that will actually let you keep going
without re-discovering the project.
