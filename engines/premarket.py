"""Pre-market engine: morning brief and IPO verdicts."""

import logging
from datetime import datetime
from typing import Any, Dict, List

import aiohttp

from ai import gemini_client
from alerts import telegram
from config import settings
from core.database import Database
from sources import bse, ipo_gmp, nse
from sources.common import NewsItem
from sources.yfinance_client import get_global_cues

logger = logging.getLogger(__name__)


def _format_cues(cues: Dict[str, Any]) -> str:
    lines = []
    for name, data in cues.items():
        change = data.get("change_pct")
        change_str = f"{change:+.2f}%" if change is not None else "N/A"
        lines.append(f"• {name}: {data.get('last')} ({change_str})")
    return "\n".join(lines)


async def run(db: Database) -> None:
    logger.info("Pre-market engine started")

    cues = get_global_cues()
    cues_text = _format_cues(cues)

    # Fetch overnight regulatory announcements.
    overnight_items: List[NewsItem] = []
    async with aiohttp.ClientSession() as session:
        try:
            overnight_items.extend(await nse.fetch_announcements(session))
        except Exception:
            logger.exception("NSE overnight fetch failed")
        try:
            overnight_items.extend(await bse.fetch_announcements(session))
        except Exception:
            logger.exception("BSE overnight fetch failed")

    event_lines = []
    for item in overnight_items[:10]:
        event_lines.append(f"• {item.headline}")
    events_text = "\n".join(event_lines) if event_lines else "No major overnight filings."

    await telegram.send_morning_brief(cues_text, events_text)

    # IPO GMP and verdicts.
    async with aiohttp.ClientSession() as session:
        ipos = await ipo_gmp.fetch_all(session)

    for ipo in ipos[:5]:
        context = (
            f"Name: {ipo.name}\n"
            f"GMP: {ipo.gmp}\n"
            f"GMP %: {ipo.gmp_pct}\n"
            f"Price band: {ipo.price_band}\n"
            f"QIB: {ipo.qib}x, HNI: {ipo.hni}x, Retail: {ipo.retail}x, Total: {ipo.total}x"
        )
        analysis = gemini_client.deep_analyze_ipo(context)
        if analysis:
            verdict = analysis.get("verdict", "NEUTRAL")
            rationale = analysis.get("rationale", "")
            await telegram.send_ipo_verdict(ipo.name, verdict, f"{context}\n\n{rationale}")
            await db.execute(
                "INSERT INTO ipo_tracker (name, issue_dates, price_band, qib, hni, retail, total, gmp, gmp_pct, verdict, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET price_band=excluded.price_band, qib=excluded.qib, hni=excluded.hni, "
                "retail=excluded.retail, total=excluded.total, gmp=excluded.gmp, gmp_pct=excluded.gmp_pct, "
                "verdict=excluded.verdict, updated_at=excluded.updated_at",
                (ipo.name, "", ipo.price_band, ipo.qib, ipo.hni, ipo.retail, ipo.total, ipo.gmp, ipo.gmp_pct, verdict, datetime.now().isoformat()),
            )
