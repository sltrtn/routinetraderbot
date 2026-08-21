"""Intraday engine: poll sources and fire alerts."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

import aiohttp

from ai import gemini_client
from alerts import telegram
from config import settings, watchlist
from core.database import Database
from core.scheduler import TZ_INFO, get_current_window
from core.state import BotState
from evidence import corroboration, dedup
from sources import bse, google_news, nse, rss
from sources.common import NewsItem
from sources.yfinance_client import get_quote

logger = logging.getLogger(__name__)


def _is_liquid(quote: Dict[str, Any]) -> bool:
    avg_volume = quote.get("avg_volume") or 0
    # avg_volume is number of shares; threshold in lakhs (100k).
    return (avg_volume / 100_000) >= settings.MIN_AVG_VOLUME_LAKHS


def _circuit_status(quote: Dict[str, Any]) -> str:
    last = quote.get("last_price")
    prev = quote.get("prev_close")
    if not last or not prev:
        return "UNKNOWN"
    change_pct = (last - prev) / prev * 100
    if change_pct >= 4.9:
        return "UPPER_CIRCUIT_RISK"
    if change_pct <= -4.9:
        return "LOWER_CIRCUIT_RISK"
    return "OK"


async def _fetch_all_sources(session: aiohttp.ClientSession) -> List[NewsItem]:
    all_items: List[NewsItem] = []
    coros = [
        rss.fetch_all(session),
        google_news.fetch_all(session),
        nse.fetch_announcements(session),
        bse.fetch_announcements(session),
    ]
    results = await asyncio.gather(*coros, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            logger.warning("Source fetch failed: %s", result)
        else:
            all_items.extend(result)
    return all_items


async def _process_batch(
    session: aiohttp.ClientSession,
    db: Database,
    state: BotState,
    watchlist_symbols: List[str],
    items: List[NewsItem],
) -> None:
    # First pass: dedup and basic classification.
    candidates: List[NewsItem] = []
    classifications: List[Dict[str, Any]] = []
    for item in items:
        if not await dedup.is_new(item, state, db):
            continue
        catalyst = corroboration.classify_catalyst(item.headline)
        if not catalyst:
            continue
        symbol = item.symbol or corroboration.extract_symbol(item.headline, watchlist_symbols)
        item.symbol = symbol
        candidates.append(item)
        classifications.append({
            "headline": item.headline,
            "symbol": symbol,
            "catalyst": catalyst,
            "source": item.source,
            "source_type": item.source_type,
            "published_at": item.published_at,
        })

    if not candidates:
        return

    # Optional Gemini Fast-mode confirmation in batches.
    gemini_results: List[Dict[str, Any]] = []
    if settings.GEMINI_API_KEY:
        batch_size = 10
        for i in range(0, len(candidates), batch_size):
            batch = candidates[i : i + batch_size]
            results = gemini_client.fast_classify([c.headline for c in batch])
            gemini_results.extend(results)
            await asyncio.sleep(0.5)

    # Second pass: evidence check and alerting.
    for idx, item in enumerate(candidates):
        gemini = gemini_results[idx] if idx < len(gemini_results) else {}
        catalyst = gemini.get("catalyst") or classifications[idx]["catalyst"]
        symbol = gemini.get("symbol") or item.symbol
        severity = gemini.get("severity", "MEDIUM")
        confidence = gemini.get("confidence", 0.7)
        summary = gemini.get("summary") or item.headline

        fingerprint = corroboration.event_fingerprint(symbol, catalyst, item.published_at)
        passes, source_count = await corroboration.check_evidence(db, fingerprint, item)

        evidence = {
            "sources": [(item.source, item.url)],
            "confidence": confidence,
            "gemini": gemini,
        }

        # Update event in DB.
        await db.upsert_event(
            fingerprint=fingerprint,
            symbol=symbol,
            catalyst=catalyst,
            severity=severity,
            confidence=confidence,
            summary=summary,
            evidence=evidence,
        )

        if not passes:
            continue

        # Liquidity / circuit check for short alerts.
        liquidity = "UNKNOWN"
        circuit = "UNKNOWN"
        if symbol:
            quote = get_quote(symbol)
            liquid = _is_liquid(quote)
            circuit = _circuit_status(quote)
            liquidity = f"{'PASS' if liquid else 'FAIL'} (avg volume {quote.get('avg_volume', 0):.0f})"
            if not liquid or circuit != "OK":
                logger.info("Skipping alert for %s: liquid=%s circuit=%s", symbol, liquid, circuit)
                continue

        if severity == "HIGH" and catalyst in (
            "PROMOTER_PLEDGE", "SEBI_WARNING", "AUDITOR_RESIGNATION",
            "C_SUITE_RESIGNATION", "MAJOR_LITIGATION", "EARNINGS_MISS",
        ):
            alert_id = await db.insert_alert(
                alert_type="URGENT_SHORT",
                symbol=symbol,
                message=summary,
                evidence=evidence,
            )
            await telegram.send_urgent(
                symbol=symbol,
                catalyst=catalyst,
                summary=summary,
                evidence={
                    **evidence,
                    "liquidity": liquidity,
                    "circuit": circuit,
                    "invalidation": "Price reclaims VWAP / catalyst disproved",
                },
            )
            logger.info("URGENT alert sent for %s: %s", symbol, catalyst)
        else:
            alert_id = await db.insert_alert(
                alert_type="WATCH",
                symbol=symbol,
                message=summary,
                evidence=evidence,
            )
            await telegram.send_watch(symbol=symbol, catalyst=catalyst, summary=summary, evidence=evidence)
            logger.info("WATCH alert sent for %s: %s", symbol, catalyst)


async def run(db: Database, state: BotState) -> None:
    logger.info("Intraday engine started")
    watchlist_symbols = watchlist.symbols()
    state.watchlist_symbols = set(watchlist_symbols)

    async with aiohttp.ClientSession() as session:
        while True:
            now = datetime.now(TZ_INFO)
            # Safety: break if market closed.
            if get_current_window(now) != "intraday":
                logger.info("Intraday window closed; exiting engine")
                break

            try:
                items = await _fetch_all_sources(session)
                await _process_batch(session, db, state, watchlist_symbols, items)
            except Exception:
                logger.exception("Intraday iteration failed")

            await asyncio.sleep(settings.INTRADAY_POLL_INTERVAL)
