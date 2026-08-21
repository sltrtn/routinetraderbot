"""Entry point for the trading bot."""

import asyncio
import logging
import sys
from datetime import datetime, timedelta

from config import settings, watchlist
from core.database import Database
from core.scheduler import TZ_INFO, get_current_window, is_trading_day, now_ist, sleep_until_next_window
from core.state import BotState
from engines import intraday, postmarket, premarket

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
# Keep httpx quiet so Telegram bot tokens are not logged.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def _send_heartbeat_if_needed(state: BotState) -> None:
    from alerts import telegram

    now = now_ist()
    if state.last_heartbeat is None or (now - state.last_heartbeat).total_seconds() >= 1800:
        await telegram.send_heartbeat()
        state.last_heartbeat = now


async def main() -> None:
    errors = settings.validate()
    if errors:
        for e in errors:
            logger.error(e)
        sys.exit(1)

    db = Database()
    await db.init()

    logger.info("Bot starting at %s", now_ist().isoformat())

    # Load watchlist into DB.
    stocks = watchlist.fetch_fno_universe()
    await db.save_watchlist([{"symbol": s.symbol, "name": s.name,
                              "exchange": s.exchange, "lot_size": s.lot_size,
                              "fno": s.fno} for s in stocks])
    logger.info("Watchlist ready with %d symbols", len(stocks))

    state = BotState(watchlist_symbols=set(watchlist.symbols()))

    while True:
        if not await is_trading_day(db):
            logger.info("Today is not a trading day. Sleeping until next pre-market.")
            await sleep_until_next_window()
            continue

        window = get_current_window()
        logger.info("Current window: %s", window)

        if window == "closed":
            await sleep_until_next_window()
            continue

        try:
            if window == "premarket":
                await premarket.run(db)
            elif window == "intraday":
                await intraday.run(db, state)
            elif window == "postmarket":
                await postmarket.run(db)
        except Exception:
            logger.exception("Engine %s failed", window)

        await _send_heartbeat_if_needed(state)

        # If an engine ran to completion (e.g., pre/post are one-shot), sleep to next window.
        # Intraday engine exits when market closes.
        if window in ("premarket", "postmarket"):
            await sleep_until_next_window()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down")
