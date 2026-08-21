# AI Context: Trading & IPO Bot

## What this is
Personal zero-cost market monitor for Indian equities (NSE/BSE).
- Pre-market IPO verdicts and macro brief.
- Intraday catalyst alerts for NSE F&O stocks.
- Post-market filing and results processing.

## Stack
- Python 3.11+, asyncio, aiohttp
- SQLite (WAL mode)
- Gemini API free tier (`google-genai` SDK)
- Telegram alerts
- Oracle Cloud Always Free ARM VM for 24/7

## Architecture
Single async process with three time-gated engines.
See `handoff.md` for full details.

## Key rules
- Never commit `.env`.
- Always run inside project venv: `source .venv/bin/activate`
- Every URGENT alert must pass the evidence rule:
  1 Tier-A source, OR 2+ independent Tier-B sources.
- GMP is unofficial sentiment only.
- All alerts include disclaimers; personal use only.

## Watchlist
NSE F&O universe is in `data/fo_stocks.json`. Update monthly.

## Common commands
```bash
source .venv/bin/activate
python bot.py
```

## File conventions
- `config/` — settings and watchlist
- `core/` — DB, scheduler, state
- `sources/` — data fetchers
- `evidence/` — dedup + corroboration
- `ai/` — Gemini adapter and prompts
- `alerts/` — Telegram sender
- `engines/` — pre-market, intraday, post-market logic
