"""Post-market engine: filings digest."""

import logging
from datetime import datetime
from typing import List

import aiohttp

from alerts import telegram
from core.database import Database
from sources import bse, nse
from sources.common import NewsItem

logger = logging.getLogger(__name__)


async def run(db: Database) -> None:
    logger.info("Post-market engine started")

    filings: List[NewsItem] = []
    async with aiohttp.ClientSession() as session:
        try:
            filings.extend(await nse.fetch_announcements(session))
        except Exception:
            logger.exception("NSE post-market fetch failed")
        try:
            filings.extend(await bse.fetch_announcements(session))
        except Exception:
            logger.exception("BSE post-market fetch failed")

    if not filings:
        await telegram.send_evening_wrap("No major filings this evening.")
        return

    lines = []
    for item in filings[:15]:
        symbol_tag = f" [{item.symbol}]" if item.symbol else ""
        lines.append(f"•{symbol_tag} {item.headline}")

    text = "\n".join(lines)
    await telegram.send_evening_wrap(text)
    logger.info("Post-market wrap sent with %d filings", len(filings))
