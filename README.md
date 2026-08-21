# RoutineTraderBot

A personal, zero-cost Indian stock market monitor that runs 24/7 and sends Telegram alerts.

## What it does

Three time-gated engines watch the market for you:

- **Pre-market (07:30–08:30 IST)** — IPO GMP/subscription verdict, global cues, overnight filings digest.
- **Intraday (09:15–15:30 IST)** — real-time catalyst alerts for NSE F&O stocks: promoter pledges, SEBI actions, resignations, litigation, earnings misses.
- **Post-market (18:00–20:00 IST)** — filings and quarterly results wrap.

Every alert is backed by a source-corroboration rule: one regulatory source or two independent news sources.

## Stack

- Python 3.11+ asyncio
- SQLite
- Gemini API free tier
- Telegram Bot API
- Oracle Cloud Always Free VM (optional)

## Quick start

```bash
git clone https://github.com/sltrtn/routinetraderbot.git
cd routinetraderbot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill in GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
python bot.py
```

## Deploy (Oracle Cloud Always Free VM)

Create an Ubuntu 24.04 ARM VM in the Oracle console, then:

```bash
./scripts/deploy-oracle.sh ubuntu@<VM_IP> ~/.ssh/id_rsa
scp -i ~/.ssh/id_rsa .env ubuntu@<VM_IP>:/home/ubuntu/routinetraderbot/.env
ssh -i ~/.ssh/id_rsa ubuntu@<VM_IP> sudo systemctl restart trading-bot
```

See `docs/oracle-setup.md` for the full guide.

## Disclaimer

Personal tool only. Not investment advice. Do your own due diligence.
