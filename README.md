# VEXARIUM — Project Documentation

**VEXARIUM** is a web-based **trading signal & options analysis** SaaS tool.
Free tier + Pro tier ($9/mo). FastAPI backend + SvelteKit frontend, Arasaka
corpo visual design (Cyberpunk 2077). **Analysis only — no trading.**

> ⚠ This is a technical handoff document set. Read `ARCHITECTURE.md` first,
> then the file relevant to whatever you are working on. The existing
> `backend/README.md` and `frontend/README.md` contain setup/run details;
> these docs are the higher-level overview for AI agents continuing work.

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
| [OPTIONS_PAGE_REWORK.md](./OPTIONS_PAGE_REWORK.md) | **Planned options-page rework.** Alpaca options capabilities audit + beginner-first page design + phased build plan. |
| [ENVIRONMENT.md](./ENVIRONMENT.md) | Env vars, setup, PYTHONPATH gotcha, dev tools. |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Docker, free-tier plan, Render/Neon, Hetzner migration. |
| [CONVENTIONS.md](./CONVENTIONS.md) | Coding conventions and non-obvious gotchas. |

---

## Quick facts (one-paragraph orientation)

- **Stack:** FastAPI (Python 3.11) · PostgreSQL · Redis · ARQ worker ·
  SvelteKit + Tailwind v4 + Svelte 5 (runes) · TradingView Lightweight Charts v5.
- **Brand / design:** VEXARIUM, Arasaka corpo — deep blacks `#0a0a0c`,
  crimson `#c81e1e`, stark white `#f4f4f5`, 4px angular radius, uppercase labels.
- **AI:** `deepseek-v4-flash:0731` via ollama-cloud (OpenAI-compatible at
  `https://ollama.com/v1`). Summarizes indicator verdicts + news sentiment.
- **Data:** Alpaca (paper trading keys) for daily OHLCV bars, quotes, news,
  options chains/Greeks.
- **Monetization:** **all 10 indicators are free**; **AI analysis and the
  option "chance of profit" estimate are Pro features** (free tier 30 req/min,
  Pro 200 req/min). **Stripe is fully integrated** (checkout + webhook).
  Daily auto-update is a future Pro feature (ARQ worker).
- **Auth:** minimal JWT login/register UI (backend + frontend) so Pro users
  can unlock AI. In dev, `DEV_FORCE_PRO=true` bypasses tier checks.
- **Tests:** backend `154 passed, 1 skipped`. Frontend gates: `yarn check`
  (0 errors) + `yarn build`.

Read the per-topic docs for the details that will actually let you keep going
without re-discovering the project.
