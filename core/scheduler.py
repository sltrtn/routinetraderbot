"""Market-clock scheduler."""

import asyncio
import logging
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Optional

import aiosqlite
import pytz

from config.settings import (
    INTRADAY_END,
    INTRADAY_START,
    POST_MARKET_END,
    POST_MARKET_START,
    PRE_MARKET_END,
    PRE_MARKET_START,
    TZ,
)
from core.database import Database

logger = logging.getLogger(__name__)

TZ_INFO = pytz.timezone(TZ)


def now_ist() -> datetime:
    return datetime.now(TZ_INFO)


def today_ist() -> date:
    return now_ist().date()


def combine(dt: date, t: time) -> datetime:
    return TZ_INFO.localize(datetime.combine(dt, t))


async def is_trading_day(db: Database, dt: Optional[date] = None) -> bool:
    dt = dt or today_ist()
    try:
        async with aiosqlite.connect(str(db.db_path)) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT is_trading FROM market_calendar WHERE date = ?", (dt.isoformat(),)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return bool(row["is_trading"])
    except Exception:
        logger.exception("market_calendar lookup failed")
    return dt.weekday() < 5


def get_current_window(dt: Optional[datetime] = None) -> str:
    dt = dt or now_ist()
    t = dt.time()
    if PRE_MARKET_START <= t < PRE_MARKET_END:
        return "premarket"
    if INTRADAY_START <= t < INTRADAY_END:
        return "intraday"
    if POST_MARKET_START <= t < POST_MARKET_END:
        return "postmarket"
    return "closed"


def next_window_start(dt: Optional[datetime] = None) -> Optional[datetime]:
    """Return the next window start time from now."""
    dt = dt or now_ist()
    today = dt.date()
    candidates = [
        combine(today, PRE_MARKET_START),
        combine(today, INTRADAY_START),
        combine(today, POST_MARKET_START),
    ]
    for c in candidates:
        if c > dt:
            return c
    # Next day pre-market.
    return combine(today + timedelta(days=1), PRE_MARKET_START)


async def sleep_until_next_window() -> str:
    nxt = next_window_start()
    if nxt is None:
        return "closed"
    seconds = (nxt - now_ist()).total_seconds()
    window = get_current_window(nxt)
    logger.info("Sleeping %.0f seconds until %s window", seconds, window)
    await asyncio.sleep(max(1, seconds))
    return window
