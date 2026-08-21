"""Application configuration loaded from environment."""

import os
from datetime import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "bot.db"

# Secrets
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Timezone
TZ = os.getenv("TZ", "Asia/Kolkata")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Market windows (IST)
def _parse_time(value: str, default: str) -> time:
    h, m = map(int, os.getenv(value, default).split(":"))
    return time(h, m)

PRE_MARKET_START = _parse_time("PRE_MARKET_START", "07:30")
PRE_MARKET_END = _parse_time("PRE_MARKET_END", "08:30")
INTRADAY_START = _parse_time("INTRADAY_START", "09:15")
INTRADAY_END = _parse_time("INTRADAY_END", "15:30")
POST_MARKET_START = _parse_time("POST_MARKET_START", "18:00")
POST_MARKET_END = _parse_time("POST_MARKET_END", "20:00")

# Polling intervals
INTRADAY_POLL_INTERVAL = int(os.getenv("INTRADAY_POLL_INTERVAL", "90"))
SOURCE_HEALTH_INTERVAL = int(os.getenv("SOURCE_HEALTH_INTERVAL", "300"))
GOOGLE_NEWS_MAX_PER_QUERY = int(os.getenv("GOOGLE_NEWS_MAX_PER_QUERY", "30"))

# Alert thresholds
MIN_AVG_VOLUME_LAKHS = float(os.getenv("MIN_AVG_VOLUME_LAKHS", "10"))
IPO_QIB_THRESHOLD = float(os.getenv("IPO_QIB_THRESHOLD", "5.0"))
IPO_GMP_PCT_THRESHOLD = float(os.getenv("IPO_GMP_PCT_THRESHOLD", "20.0"))

# Source URLs
# Leave empty to use the bundled static F&O list. NSE's official lot-size CSV
# endpoint is unreliable and often redirects to a PDF.
NSE_FO_LOT_SIZE_URL = ""
NSE_ANNOUNCEMENTS_URL = "https://www.nseindia.com/api/corporate-announcements?index=equities"
NSE_QUOTE_URL = "https://www.nseindia.com/api/quote-equity"
BSE_ANNOUNCEMENTS_URL = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"

# Sanity checks
def validate() -> list[str]:
    errors = []
    if not GEMINI_API_KEY:
        errors.append("GEMINI_API_KEY is missing")
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is missing")
    if not TELEGRAM_CHAT_ID:
        errors.append("TELEGRAM_CHAT_ID is missing")
    return errors
