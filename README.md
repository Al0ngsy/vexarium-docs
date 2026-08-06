# VEXARIUM — Project Documentation

**VEXARIUM** is a web-based **trading signal & options analysis** SaaS tool.
Free tier + Pro tier ($9/mo). FastAPI backend + SvelteKit frontend, Amber
Health Check visual design (cockpit dark + amber). **Analysis only — no trading.**

> ⚠ This is a technical handoff document set. Read `ARCHITECTURE.md` first,
> then the file relevant to whatever you are working on. The `vexarium-backend`
> and `vexarium-frontend` repos each contain a `README.md` with setup/run
> details; these docs are the higher-level overview for AI agents continuing work.

---

## Document map

| File | When to read it |
|------|-----------------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | **Start here.** System topology, components, data flow. |
| [BACKEND.md](./BACKEND.md) | Working on the FastAPI backend. |
| [FRONTEND.md](./FRONTEND.md) | Working on the SvelteKit frontend. |
| [API.md](./API.md) | Need the exact request/response shape of an endpoint. |
| [DATA_AND_INDICATORS.md](./DATA_AND_INDICATORS.md) | Data sources, caching, indicator registry, asset types. |
| [AI_ANALYSIS.md](./AI_ANALYSIS.md) | The AI pipeline, prompts, token budget, news feed. |
| [OPTIONS_PAGE_REWORK.md](./OPTIONS_PAGE_REWORK.md) | **Implemented options-page rework** (Aug 2026): Alpaca options capabilities audit + beginner-first page design + phased build plan. |
| [ENVIRONMENT.md](./ENVIRONMENT.md) | Env vars, setup, PYTHONPATH gotcha, dev tools. |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Docker, free-tier plan, Render/Neon, Hetzner migration. |
| [CONVENTIONS.md](./CONVENTIONS.md) | Coding conventions and non-obvious gotchas. |

---

## Quick facts (one-paragraph orientation)

- **Stack:** FastAPI (Python 3.11) · PostgreSQL · Redis ·
  SvelteKit + Tailwind v4 + Svelte 5 (runes) · TradingView Lightweight Charts v5.
- **Brand / design:** VEXARIUM, Amber Health Check — cockpit dark `#0b0e13`,
  amber `#f59e0b`, near-white `#e8edf5`, 14px radius, health-check vocabulary
  (grade ring, vitals, plain-language box, pass/watch/fail chips).
- **AI:** `deepseek-v4-flash:0731` via ollama-cloud (OpenAI-compatible at
  `https://ollama.com/v1`). Summarizes indicator verdicts + news sentiment.
- **Data:** Alpaca (paper trading keys) for daily OHLCV bars, quotes, news,
  options chains/Greeks.
- **Monetization:** **everything is free today** — all 10 indicators and the
  AI SECOND OPINION (per-IP 10 req/min + 24h per-symbol AI cache). Stripe is
  fully integrated (checkout + webhook) and ready for a future Pro tier;
  nothing is gated right now. Daily auto-update is a future Pro feature.
- **Auth:** minimal JWT login/register UI (backend + frontend) so Pro users
  can unlock AI. In dev, `DEV_FORCE_PRO=true` bypasses tier checks.
- **Tests:** backend `177 passed`. Frontend gates: `yarn check`
  (0 errors) + `yarn build`.

Read the per-topic docs for the details that will actually let you keep going
without re-discovering the project.
