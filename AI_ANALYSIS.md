# VEXARIUM — AI Analysis

How the AI analysis feature works, its prompt, token budget, and known quirks.

## Overview

`POST /api/v1/analysis/ai` (`backend/app/api/ai.py`) runs a DeepSeek model
against the technical indicators + news + fundamentals for a symbol and
returns a natural-language recommendation. **AI is free for everyone** — no
token, tier, or featured-symbol gating (`is_preview` is always `false`).
Abuse protection is two-layered:

- **Per-IP rate limit:** `RATE_LIMIT_AI` (default **10 requests/minute/IP**,
  `config.py`) — tightened from the old 200/min Pro limit.
- **Heavy caching:** the result is cached per-symbol-per-day in Redis
  (`ai:{symbol}:{date}`, 24h TTL), so repeat views are served from cache and
  never hit the LLM. The LLM runs at most once per symbol per day.

The frontend auto-runs the AI SECOND OPINION after every health check; the
section is collapsible like the others.

## Provider

- Endpoint: `https://ollama.com/v1` (OpenAI-compatible `/chat/completions`)
- Model: `deepseek-v4-flash:0731`
- Config in `backend/.env`:
  - `LLM_BASE_URL=https://ollama.com/v1`
  - `LLM_API_KEY=<key>` (gitignored)
  - `LLM_MODEL=deepseek-v4-flash:0731`

`backend/app/config.py` defaults point at `api.deepseek.com` / `deepseek-chat`
— the local `.env` overrides them. Keep the `.env` values as the source of
truth.

## Prompt construction — `services/ai_analyzer.py`

- `SYSTEM_PROMPT`: instructs the model to produce a **structured briefing**
  with four sections — `## Summary`, `## The Setup`, `## Key Levels`,
  `## Risks & What to Watch` — referencing specific indicator values and
  prices, connecting fundamentals to the technical picture, and ending with
  the disclaimer.
- `build_prompt(indicator_results, overall_verdict, options_data=None,
news_sentiment=None, news_articles=None, market_data=None,
company_info=None)`:
  - Serializes the indicators, overall verdict, options (if any),
    news sentiment, the **actual news articles** (capped at 8, summary
    truncated to 400 chars), and **market context** into a JSON `context` block.
  - `market_data` (from `AlpacaClient.get_market_snapshot`) gives the model:
    live price, day change %, bid/ask, prev close, 52-week high/low, YTD change
    %. This lets the AI comment on where the price sits in its recent range —
    not just technicals + news.
  - **`key_levels`** are derived from the data (`_key_levels`): Bollinger
    bands, SMA/EMA levels, and the 52-week range become concrete support /
    resistance prices (nearest 3 each side) so the AI gives actionable levels,
    not percentages.
  - **`company_fundamentals`** (from `get_company_info`, free keyless Yahoo)
    are included when populated (P/E, margins, growth, market cap, sector…)
    so the AI can connect valuation to the technical setup. Empty/zero fields
    are filtered out.
  - Passes news **headlines/summaries**, not just the aggregate score, so the
    model can reason about the news itself.
- `analyze(prompt, skip_ai=False)`:
  - POSTs to `{llm_base_url}/chat/completions` with `max_tokens: 2000`.
  - **Retries once** on empty completion / exception; on second failure returns
    the "temporarily unavailable" fallback string.

## The `max_tokens` gotcha (critical)

This model produces a **`reasoning` chain-of-thought** field _before_ the
`content` field. If `max_tokens` is too small (e.g. 300), the model spends the
entire budget on `reasoning` and `content` comes back **empty** → the feature
appears broken ("AI analysis temporarily unavailable").

**Do not lower `max_tokens` below ~2000.** It is intentionally generous so
that `reasoning` + `content` both fit. If you change the model, re-verify the
budget against that model's reasoning length.

## Request/response

Request body: `AnalysisRequest` (`{symbol, asset_type, options_enabled}`).

Response:

```json
{
  "symbol": "AAPL",
  "analysis": "**Recommendation: HOLD** ... This is not financial advice. AI can make/will make mistakes.",
  "model": "deepseek-v4-flash:0731",
  "analyzed_at": "2026-08-04T10:00:00+00:00",
  "news_sentiment": { "...": "..." },
  "news_articles": [
    { "headline": "...", "source": "...", "url": "...", "summary": "..." }
  ],
  "market": {
    "price": 303.41,
    "day_change_pct": -1.72,
    "bid": 287.82,
    "ask": 318.75,
    "prev_close": 308.73,
    "high_52w": 340.08,
    "low_52w": 202.92,
    "ytd_change_pct": 11.96
  }
}
```

The frontend shows `analysis` text only (model name is intentionally NOT
displayed). On any backend exception the endpoint returns a 200 with the
fallback string — the frontend just renders it.

## Caching

AI results are cached per symbol per day (`ai:{symbol}:{date}`, 24h TTL in
`cache.py`). See `DATA_AND_INDICATORS.md`.

## Future

- **Pro tier** is unlocked by the **Stripe webhook** → `set_tier` (fully
  integrated, not stubbed) or `DEV_FORCE_PRO=true` in dev. A per-user AI
  **daily limit** for the free tier is not yet enforced — today non-Pro users
  are blocked entirely (403) and Pro is unlimited.
- **Pro auto-update** — a scheduled daily AI refresh for Pro users would live
  in a background worker (not yet implemented).
