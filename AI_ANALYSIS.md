# VEXARIUM — AI Analysis

How the AI analysis feature works, its prompt, model chain, streaming, and
known quirks.

## Overview

`POST /api/v1/analysis/ai` and `POST /api/v1/analysis/ai/stream`
(`backend/app/api/ai.py`) run an OpenCode Go model (`mimo-v2.5`) against the
technical indicators + news + fundamentals for a symbol and return a
natural-language briefing. **AI is free for everyone** — no token, tier, or
featured-symbol gating (the `_ai_access` dependency only reads the tier for
logging; it never 403s). Abuse protection is three-layered:

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

## Provider & model

- Endpoint: `https://opencode.ai/zen/go/v1` (OpenAI-compatible
  `/chat/completions`, **OpenCode Go subscription** — ~$10/mo, flat model
  pricing; usage limits at https://opencode.ai/docs/go/#usage-limits).
- Model: `mimo-v2.5` (`LLM_MODEL`). It's the highest-usage Go model that works
  in DE; `muse-spark-1.2-contributor` has higher limits but returns a 403
  `RegionError` from Germany (Meta contributor-tier geo-block), and plain
  OpenCode Zen `/zen/v1` needs per-token balance (401 when empty).
- **No free tier / no fallback chain anymore.** The `-free` models plus the
  `LLM_FALLBACK_MODELS` / `LLM_PAID_FALLBACK` config were removed — a request
  failure surfaces as "temporarily unavailable" (never raises, never cached).
  The 24h per-symbol cache bounds API spend: at most one LLM call per symbol
  per day.
- Config in `backend/.env`:
  - `LLM_BASE_URL=https://opencode.ai/zen/go/v1`
  - `LLM_API_KEY=<key>` (gitignored)
  - `LLM_MODEL=mimo-v2.5`

`backend/app/config.py` ships these as defaults; the local `.env` overrides
them. Keep `.env` as the source of truth.

## News feed & sentiment (`services/news_service.py`)

The stock feed merges **Alpaca symbol news + Google News RSS** (via
`AlpacaClient.get_news`) with **Finnhub `/company-news`** as a second outlet,
then:

- **Dedupes** (`dedupe_articles`): identical headline or URL always; headline
  similarity ≥ 0.85 only on the same calendar day (stdlib `difflib`), so
  republishes collapse but real follow-ups survive.
- **Caps source dominance** (`cap_source`, max 2 per outlet, case-insensitive)
  so a busy wire (Benzinga) can't fill the visible list.
- **Scores each headline with VADER** (`compute_sentiment` → compound in
  [-1, 1], handles negation/caps). `news_articles[].sentiment` drives the
  widget's per-article chips AND is fed to the AI prompt context per article.
- Sorts newest-first, then returns to the caller.

Market-wide context is kept **separate** from the stock feed so it can't bias
the stock's sentiment:

- `GET /analysis/market-news` — Finnhub `news?category=general`, 12h cache,
  VADER-scored the same way.
- `GET /analysis/fear-greed` — CNN Fear & Greed index (unofficial dataviz
  endpoint, needs the page-cookie handshake), 30 min cache, `{}` on failure.

Both load independently of `/analysis` so they never block the slow report.

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
    truncated to 400 chars, each carrying its VADER `sentiment` score), and
    **market context** into a JSON `context` block.
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
  - On any failure returns the "temporarily unavailable" fallback string
    (never raises).
- `analyze_stream(prompt, skip_ai=False)`:
  - Single model, `stream: true`; yields successive content strings.
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
  "model": "mimo-v2.5",
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
  AI is unlimited (rate-limited per-IP only). **DEV (Aug 2026): Pro gates are temporarily removed during development**, so the options-strategies AI and `/options/{symbol}/chance` are open to everyone (`# DEV:` comments mark the re-add points for launch). Before that, the only Pro-gated endpoint was
  options chance-of-profit (`GET /options/{symbol}/chance`).
- **Pro auto-update** — a scheduled daily AI refresh for Pro users would live
  in a background worker (not yet implemented).
- Shorter-timeframe AI (e.g. every 4h/1h) is a planned extension — the cache
  keys already carry the timeframe.
