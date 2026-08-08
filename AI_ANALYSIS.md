# VEXARIUM — AI Analysis

How the AI analysis feature works, its prompt, model chain, streaming, and
known quirks.

## Overview

`POST /api/v1/analysis/ai` and `POST /api/v1/analysis/ai/stream`
(`backend/app/api/ai.py`) run a DeepSeek model against the technical
indicators + news + fundamentals for a symbol and return a natural-language
briefing. **AI is free for everyone** — no token, tier, or featured-symbol
gating (the `_ai_access` dependency only reads the tier for logging; it never
403s). Abuse protection is three-layered:

- **Per-IP rate limit:** `RATE_LIMIT_AI` (default **10 requests/minute/IP**).
- **Heavy caching:** the result is cached per symbol per timeframe per day
  (`ai:{symbol}:{timeframe}:{date}`, 24h TTL), so repeat views are served from
  cache and never hit the LLM.
- **Single-flight lock:** concurrent requests for the same symbol wait for the
  in-flight LLM call (poll up to ~2 min) instead of firing duplicates
  (`ai_lock:{symbol}:{timeframe}:{date}`).

The frontend auto-runs the AI OPINION widget after every analysis and streams
the answer token-by-token; cached answers are replayed with the same
progressive effect.

## Provider & model chain

- Endpoint: `https://opencode.ai/zen/v1` (OpenAI-compatible `/chat/completions`,
  **free tier**). Do NOT use `/zen/go/v1` — it rejects `-free` model IDs.
- Primary model: `deepseek-v4-flash-free` (`LLM_MODEL`).
- **Fallback chain:** `LLM_FALLBACK_MODELS` (comma-separated free IDs, tried in
  order on rate limit / outage / empty completion) — see `_model_chain()` in
  `ai_analyzer.py`. Default:
  `big-pickle,mimo-v2.5-free,ling-3.0-tiny-free,laguna-s-2.1-free,longcat-2.0-free,north-mini-code-free,nemotron-3-ultra-free`.
- Config in `backend/.env`:
  - `LLM_BASE_URL=https://opencode.ai/zen/v1`
  - `LLM_API_KEY=<key>` (gitignored)
  - `LLM_MODEL=deepseek-v4-flash-free`
  - `LLM_FALLBACK_MODELS=...`

`backend/app/config.py` ships these as defaults; the local `.env` overrides
them. Keep `.env` as the source of truth.

## Prompt construction — `services/ai_analyzer.py`

- `SYSTEM_PROMPT`: instructs the model to produce a **structured briefing**
  with four sections — `## Summary`, `## The Setup`, `## Key Levels`,
  `## Risks & What to Watch` — referencing specific indicator values and
  prices, connecting fundamentals to the technical picture, and ending with
  the fixed disclaimer footer (`**This is not financial advice. AI can
  make/will make mistakes.**`).
- `build_prompt(indicator_results, overall_verdict, options_data=None,
  news_sentiment=None, news_articles=None, market_data=None,
  company_info=None)`:
  - Serializes indicators, overall verdict, options (if any), news
    sentiment, the **actual news articles** (capped at 8, summaries
    truncated to 400 chars), and **market context** into a JSON `context` block.
  - `market_data` (from `AlpacaClient.get_market_snapshot`) gives the model:
    live price, day change %, bid/ask, prev close, 52-week high/low, YTD change
    %. This lets the AI comment on where the price sits in its recent range.
  - **`key_levels`** are derived from the data (`_key_levels`): Bollinger
    bands, SMA/EMA levels, and the 52-week range become concrete support /
    resistance prices (nearest 3 each side) so the AI gives actionable levels,
    not percentages.
  - **`company_fundamentals`** (from `get_company_info`, free keyless Yahoo)
    are included when populated (P/E, margins, growth, market cap, sector…);
    empty/zero fields are filtered out.
- `analyze(prompt, skip_ai=False)`:
  - POSTs to `{llm_base_url}/chat/completions` with `max_tokens: 8192`.
  - Tries each model in the chain; on total failure returns the
    "temporarily unavailable" fallback string (never raises).
- `analyze_stream(prompt, skip_ai=False)`:
  - Same chain, `stream: true`; yields successive content strings.
  - **Skips `reasoning_content` deltas** (the model's hidden thinking) — only
    the actual answer is streamed.
  - Mid-stream errors propagate (a partial answer must not be silently swapped
    for another model's continuation — that bug cached a truncated briefing
    for 24h).

## The `max_tokens` gotcha (critical)

This model produces a **`reasoning` chain-of-thought** field _before_ the
`content` field. If `max_tokens` is too small (e.g. 300), the model spends the
entire budget on `reasoning` and `content` comes back **empty** → the feature
appears broken ("AI analysis temporarily unavailable").

**Do not lower `max_tokens` below ~8192.** It is intentionally generous so
that `reasoning` + `content` both fit (2000 was cutting deep analyses
mid-sentence). If you change the model, re-verify the budget against that
model's reasoning length.

## Request/response

Request body: `AnalysisRequest` (`{symbol, asset_type, timeframe,
options_enabled}`).

Response (non-streaming):

```json
{
  "symbol": "AAPL",
  "analysis": "## Summary\n**Recommendation: HOLD** ...\n\n----------------------------------------\n**This is not financial advice. AI can make/will make mistakes.**\n----------------------------------------",
  "model": "deepseek-v4-flash-free",
  "analyzed_at": "2026-08-04T10:00:00+00:00",
  "news_sentiment": { "...": "..." },
  "news_articles": [
    { "headline": "...", "source": "...", "url": "...", "summary": "..." }
  ],
  "market": {
    "price": 303.41,
    "day_change_pct": -1.72,
    "bid": 287.82,
    "ask": 318.73,
    "prev_close": 308.73,
    "high_52w": 340.08,
    "low_52w": 202.92,
    "ytd_change_pct": 11.96
  }
}
```

Streaming response: SSE events `data: {"chunk":"..."}` (each event is one
content delta; the client concatenates them). The frontend renders the
markdown with `lib/markdown.ts` (XSS-escaped mini-renderer — never inject the
AI text as raw HTML).

The frontend shows `analysis` text only (model name is intentionally NOT
displayed). On total backend failure the endpoint returns a 200 with the
fallback string — the frontend just renders it.

## Caching & failure semantics

- AI results are cached per symbol per timeframe per day
  (`ai:{symbol}:{timeframe}:{date}`, 24h TTL).
- **Never cache failure text**: a transient LLM outage must not poison the 24h
  cache — the "temporarily unavailable" fallback is excluded from caching so
  the next visitor retries the LLM.

## Future

- A per-user AI **daily limit** for the free tier is not yet enforced — today
  AI is unlimited (rate-limited per-IP only). The only Pro-gated endpoint is
  options chance-of-profit (`GET /options/{symbol}/chance`).
- **Pro auto-update** — a scheduled daily AI refresh for Pro users would live
  in a background worker (not yet implemented).
- Shorter-timeframe AI (e.g. every 4h/1h) is a planned extension — the cache
  keys already carry the timeframe.
