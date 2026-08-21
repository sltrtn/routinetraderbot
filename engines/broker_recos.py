"""Broker recommendation engine."""

import logging
from typing import List

import aiohttp

from alerts import telegram
from config import watchlist
from core.database import Database
from sources.broker_recos import BrokerReco, fetch_all

logger = logging.getLogger(__name__)


async def _is_in_watchlist(symbol: str) -> bool:
    return symbol in set(watchlist.symbols())


async def run(db: Database) -> None:
    logger.info("Broker recommendation engine started")
    async with aiohttp.ClientSession() as session:
        recos = await fetch_all(session)

    sent = 0
    for reco in recos:
        if not await _is_in_watchlist(reco.symbol):
            continue

        # Dedup via DB.
        inserted = await db.insert_broker_reco({
            "hash": reco.hash,
            "symbol": reco.symbol,
            "company_name": reco.company_name,
            "action": reco.action,
            "target": reco.target,
            "broker": reco.broker,
            "source": reco.source,
            "url": reco.url,
            "published_at": reco.published_at,
            "headline": reco.headline,
        })
        if not inserted:
            continue

        # Require at least one recent news item as backing.
        recent_news = await db.has_recent_news_for_symbol(reco.symbol, days=7)
        if not recent_news:
            logger.debug("Skipping broker reco for %s: no recent news backing", reco.symbol)
            continue

        await telegram.send_broker_reco(
            symbol=reco.symbol,
            action=reco.action,
            target=reco.target,
            broker=reco.broker,
            headline=reco.headline,
            news_backing=len(recent_news),
            url=reco.url,
        )
        await db.execute(
            "UPDATE broker_recos SET alerted = 1 WHERE hash = ?",
            (reco.hash,),
        )
        sent += 1
        logger.info("Sent broker reco: %s %s by %s", reco.action, reco.symbol, reco.broker)

    logger.info("Broker recommendation engine finished; sent %d recos", sent)
