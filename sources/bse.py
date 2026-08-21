"""BSE corporate announcements source."""

import json
import logging
from datetime import datetime
from typing import List

import aiohttp

from sources.common import NewsItem, clean_text, parse_iso_date

logger = logging.getLogger(__name__)

BSE_ANN_URL = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"


def _today_str() -> str:
    return datetime.now().strftime("%Y%m%d")


async def fetch_announcements(session: aiohttp.ClientSession, lookback_days: int = 1) -> List[NewsItem]:
    items: List[NewsItem] = []
    today = datetime.now()
    start = today
    if lookback_days > 1:
        start = today  # BSE API can accept range; keeping simple for now

    payload = {
        "strCat": "Corporate Announcement",
        "strPrevDate": start.strftime("%Y%m%d"),
        "strCurDate": today.strftime("%Y%m%d"),
        "strScrip": "",
        "strSearch": "",
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "application/json, text/javascript, */*",
        "Origin": "https://www.bseindia.com",
        "Referer": "https://www.bseindia.com/",
    }
    try:
        async with session.get(
            BSE_ANN_URL,
            params=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            text = await resp.text()
            if not text.strip():
                return items
            data = json.loads(text)
    except Exception as exc:
        logger.warning("BSE announcements fetch failed: %s", exc)
        return items

    if isinstance(data, str):
        # Common response: "No Record Found!"
        if "no record" in data.lower():
            return items
        logger.warning("Unexpected BSE string response: %s", data[:100])
        return items

    if not isinstance(data, list):
        logger.warning("Unexpected BSE response structure")
        return items

    for row in data:
        headline = clean_text(row.get("HEADLINE") or row.get("SUBJECT") or "")
        if not headline:
            continue
        url = row.get("ATTACHMENTNAME", "")
        if url and not url.startswith("http"):
            url = f"https://www.bseindia.com{url}"
        dt = row.get("NEWS_DT") or row.get("DissemDT") or row.get("DT_TM")
        items.append(
            NewsItem(
                source="bse_announcements",
                headline=headline,
                url=url,
                published_at=parse_iso_date(dt),
                source_type="regulatory",
                symbol=row.get("SCRIP_CD"),
                raw=row,
            )
        )
    logger.info("Fetched %d BSE announcements", len(items))
    return items
