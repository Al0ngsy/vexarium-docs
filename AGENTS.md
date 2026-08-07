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
| An endpoint, request/response shape, auth, or gating | `docs/API.md` |
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
  SvelteKit + Tailwind v4 + Svelte 5 (runes) · Lightweight Charts v5 · Yarn Berry 4.17.
- **Design:** Amber Health Check — cockpit dark `#0b0e13`, amber `#f59e0b`,
  near-white `#e8edf5`, 14px radius, health-check vocabulary (grade ring,
  vitals, plain-language box, pass/watch/fail chips).
- **AI:** `deepseek-v4-flash` via OpenCode Go (`https://opencode.ai/zen/go/v1`).
- **Data:** Alpaca paper-trading (daily bars) with a **Yahoo Finance fallback**
  for OTC/foreign ADRs outside Alpaca's universe (SMERY, RNMBY, …): daily bars
  (`_fetch_yahoo_bars`) + company profile + **main-listing mapping**
  (RNMBY → RHM.DE/XETRA, surfaced as `company.main_listing`, FE shows a
  "VIEW MAIN LISTING" button). Assets search merges keyless Yahoo results, so
  "Rheinmetall" → RHM.DE before RNMBY. Indices (SPX) return 404 — expected.
- **Monetization:** **all 10 indicators are free**; **AI analysis is free for
  everyone** (per-IP 10 req/min + 24h per-symbol cache; `POST /analysis/ai` is
  open, no 403). `DEV_FORCE_PRO=true` in dev bypasses tier checks; never in
  production. Stripe billing exists for a future Pro tier but nothing is gated
  today.
- **Auth:** minimal JWT login/register (backend + frontend). Auth state lives in
  `frontend/src/lib/auth.svelte.ts` (rune store — must keep the `.svelte.ts`
  extension for SSR; a plain `.ts` throws `$state is not defined`).

## Environment & commands (see `docs/ENVIRONMENT.md` for full detail)

- **PYTHONPATH gotcha:** this shell exports a `PYTHONPATH` that shadows the
  backend venv. Run ALL Python as
  `env -u PYTHONPATH .venv/bin/python ...` or `env -u PYTHONPATH .venv/bin/uvicorn ...`.
- **Yarn, never npm** for frontend commands: `yarn dev`, `yarn check`, `yarn build`.
- **Backend tests:** `cd backend && env -u PYTHONPATH .venv/bin/python -m pytest tests/ -q`
  (expect ~137 passed, 1 skipped).
- **Frontend gates:** `yarn check` (0 errors) and `yarn build` (adapter-cloudflare).

## Workflow expectation

For any non-trivial change:
1. Read the relevant `docs/*.md` **first**.
2. Make the code change.
3. Update the affected docs **in the same commit** (see table above).
4. Run the gates (`pytest`, `yarn check`, `yarn build`).
5. If you hit a gotcha not already documented, add it to `docs/CONVENTIONS.md`.
