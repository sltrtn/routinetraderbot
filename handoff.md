# Trading & IPO Bot — Handoff

## Purpose
A personal, zero-cost Indian stock market monitor that runs 24/7 on an Oracle Cloud free VM. It sends Telegram alerts for:
- IPO apply/avoid verdicts (pre-market)
- Intraday short catalysts for liquid F&O stocks
- Post-market filings and results digest

## Stack
- Python 3.11+, asyncio, aiohttp
- SQLite (WAL mode) at `data/bot.db`
- Gemini API free tier (`google-genai` SDK)
- Telegram Bot API
- Hosted on Oracle Cloud Always Free ARM VM

## Quick Start (local)
```bash
cd /home/mad/trading-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys
python bot.py
```

## Watchlist
The intraday engine monitors the NSE F&O universe. The list is stored in `data/fo_stocks.json`. Update it monthly or when contract changes occur. If you find a working NSE F&O lot-size CSV endpoint, set `NSE_FO_LOT_SIZE_URL` in `.env`.

## Deployment (Oracle Cloud)
1. Create Always Free ARM VM (Ubuntu 24.04).
2. Clone/copy repo to `/home/ubuntu/trading-bot`.
3. Install deps and create `.env`.
4. Copy `systemd/trading-bot.service` to `/etc/systemd/system/`.
5. `systemctl enable --now trading-bot`
6. Watch Telegram heartbeat every 30 min.

## Secrets
Required in `.env`:
- `GEMINI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Architecture
Single async Python process:
- Pre-Market Engine (07:30–08:30 IST)
- Intraday Engine (09:15–15:30 IST)
- Post-Market Engine (18:00–20:00 IST)

## Evidence rule
URGENT alerts require either:
- One Tier-A source (NSE/BSE/SEBI filing), OR
- Two+ independent Tier-B news sources.

## Known limitations
- Market data is delayed.
- GMP is unofficial/gray-market sentiment only.
- NSE/BSE website endpoints can change without notice.
- Gemini free tier has rate limits; bot degrades to keyword rules if quota exhausted.

## Legal / compliance
Personal use only. All alerts carry a disclaimer. Do not sell signals or run public advisory channels without SEBI registration.
