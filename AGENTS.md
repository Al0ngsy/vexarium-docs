# AGENTS.md — Instructions for AI agents working on VEXARIUM

> This file is auto-read by agentic coding tools (Claude Code, Cursor, Codex,
> GitHub Copilot, etc.) **before every task**. If you are an AI about to modify
> this repository, follow these rules.

## Non-negotiable: keep documentation in sync with code

The **root-level documentation is the single source of truth for handoffs**
and must always reflect the actual codebase. Any change that alters observable
behavior **must** be reflected in the docs in the **same commit**.

**Read first, before writing code:**
- `README.md` — high-level orientation (stack, quick start, doc map).
- `docs/README.md` — document map + one-paragraph orientation.
- `docs/ARCHITECTURE.md` — system topology & data flow.
- `docs/API.md` — every endpoint, payload, and gating.
- `docs/CONVENTIONS.md` — non-obvious gotchas & foot-guns.
- Then the topic doc relevant to your work (`docs/BACKEND.md`, `docs/FRONTEND.md`,
  `docs/DATA_AND_INDICATORS.md`, `docs/AI_ANALYSIS.md`, `docs/ENVIRONMENT.md`,
  `docs/DEPLOYMENT.md`).

**Update in the same commit as your change when you touch:**
| If you change… | Also update… |
|---|---|
| An endpoint, request/response shape, auth, or gating | `docs/API.md` — then run `docs/scripts/generate_api_md.py` (it regenerates the tables from OpenAPI; `pytest` fails if they drift) |
| Architecture, containers, or component responsibilities | `docs/ARCHITECTURE.md` |
| Indicators, data sources, or caching | `docs/DATA_AND_INDICATORS.md` |
| The AI pipeline, prompt, or provider | `docs/AI_ANALYSIS.md` |
| Env vars, setup, or dev tooling | `docs/ENVIRONMENT.md` |
| Monetization / tier model / what's free vs Pro | `README.md`, `docs/README.md`, `docs/API.md`, `docs/AI_ANALYSIS.md`, `docs/DATA_AND_INDICATORS.md` |
| Deployment / Docker / CI | `docs/DEPLOYMENT.md`, `docs/ARCHITECTURE.md` |
| Stack, package manager, or design system | `README.md` |
| Any cross-cutting gotcha you discover | `docs/CONVENTIONS.md` |

**Golden rule:** a doc that says something that is no longer true is a bug.
If you find a doc already out of date, fix it even if you're not touching that
area — it's a cheap fix and prevents a future AI from trusting bad info.

## Quick facts (memorize these)

- **Stack:** FastAPI (Python 3.11) · PostgreSQL · Redis ·
  SvelteKit + Tailwind v4 + Svelte 5 (runes) · Lightweight Charts v5 ·
  gridstack.js · Yarn Berry 4.17.
- **Design:** Professional Dashboard V2 — flat solid dark `#0a0c10`,
  blue accent `#3b82f6`, sentence case, 8–10px radius, full-width 12-col
  widget grid. No amber, no radial glows, no UPPERCASE metaphor labels.
- **AI:** `mimo-v2.5` via **OpenCode Go** (`https://opencode.ai/zen/go/v1`,
  OpenAI-compatible, subscription — ~$10/mo). **Single model, no fallback
  chain** (the free tiers were removed). Usage limits:
  https://opencode.ai/docs/go/#usage-limits.
  (`muse-spark-1.2-contributor` has higher limits but is geo-blocked in DE.)
- **Data:** Alpaca paper-trading (bars for daily + intraday timeframes,
  quotes, news, option chains) with **Yahoo Finance fallback** for
  OTC/foreign ADRs outside Alpaca's universe (SMERY, RNMBY, …): daily bars
  (`_fetch_yahoo_bars`) + company profile + **main-listing mapping**
  (RNMBY → RHM.DE/XETRA, surfaced as `company.main_listing`, FE shows a
  "VIEW MAIN LISTING" button). Fundamentals fall back to stockanalysis.com.
  **Intraday bars (1m–4h) come from Twelve Data first** (`TWELVEDATA_API_KEY`,
  real-time, no 15-min delay — Alpaca/Yahoo historical bars lag 15 min by
  design).
  Assets search merges keyless Yahoo results, so "Rheinmetall" → RHM.DE
  before RNMBY. Indices (SPX) return 404 — expected.
- **News:** stock feed = Alpaca + Google + Finnhub `/company-news`, deduped
  + source-capped (max 2 per outlet) and **VADER**-scored per article
  (`news_articles[].sentiment`). Broad market = **market-news** and
  **Fear & Greed** widgets, fetched independently of `/analysis`.
- **Monetization:** **all 16 indicators are free**; **AI analysis is free for
  everyone** (per-IP 10 req/min + 24h per-symbol cache; `POST /analysis/ai`
  and `/analysis/ai/stream` are open, no 403). The **only Pro-gated endpoint
  is `GET /options/{symbol}/chance`**. **DEV NOTE (Aug 2026): all Pro gates are
  temporarily removed during development** — `GET /options/{symbol}/chance`
  and `POST /analysis/options-strategies` are open to everyone; the gates
  carry `# DEV:` markers (BE) and comments (FE) to be re-added before launch.
  Stripe billing is integrated for a future Pro tier.
- **Auth:** minimal self-built JWT register/login/me. The frontend **login UI
  is currently removed** (see git history); auth state lives in
  `frontend/src/lib/auth.svelte.ts` (rune store — must keep the `.svelte.ts`
  extension for SSR; a plain `.ts` throws `$state is not defined`).
- **Widget grid:** both `s/[symbol]` (analysis) and `options/[symbol]` pages
  are gridstack widget grids. Widget defs + persisted layout live in
  `frontend/src/lib/layout.svelte.ts` (`ANALYSIS_WIDGETS` /
  `OPTIONS_WIDGETS`); the page maps `def.id` → component inline. Do not
  reintroduce the old monolithic `OptionsWorkspace` page — it was deleted.

## Environment & commands (see `docs/ENVIRONMENT.md` for full detail)

- **PYTHONPATH gotcha:** this shell exports a `PYTHONPATH` that shadows the
  backend venv. Run ALL Python as
  `env -u PYTHONPATH .venv/bin/python ...` or `env -u PYTHONPATH .venv/bin/uvicorn ...`.
- **Yarn, never npm** for frontend commands: `yarn dev`, `yarn check`, `yarn build`.
- **Backend tests:** `cd backend && env -u PYTHONPATH .venv/bin/python -m pytest tests/ -q`
  (expect **279 passed**).
- **Frontend gates:** `yarn check` (0 errors) and `yarn build` (adapter-cloudflare).

## Workflow expectation

For any non-trivial change:
1. Read the relevant `docs/*.md` **first**.
2. Make the code change.
3. Update the affected docs **in the same commit** (see table above);
   API.md is auto-generated — run `cd backend && .venv/bin/python ../docs/scripts/generate_api_md.py`.
4. Run the gates: `pytest` (includes the docs-sync check `tests/test_docs_sync.py`),
   `yarn check`, `yarn build`.
5. If you hit a gotcha not already documented, add it to `docs/CONVENTIONS.md`.
