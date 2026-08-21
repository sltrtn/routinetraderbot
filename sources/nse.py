"""NSE corporate announcements source."""

import json
import logging
from typing import List

import aiohttp

from sources.common import NewsItem, clean_text, parse_iso_date

logger = logging.getLogger(__name__)

NSE_ANN_URL = "https://www.nseindia.com/api/corporate-announcements?index=equities"
NSE_HOME_URL = "https://www.nseindia.com"


class NSESession:
    """Maintains NSE session cookies. NSE blocks requests without cookies."""

    def __init__(self):
        self._cookies: dict = {}
        self._last_refresh: float = 0

    async def _refresh(self, session: aiohttp.ClientSession) -> None:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            async with session.get(NSE_HOME_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                self._cookies = {k: v.value for k, v in resp.cookies.items()}
                logger.debug("Refreshed NSE cookies: %s", list(self._cookies.keys()))
        except Exception as exc:
            logger.warning("Failed to refresh NSE cookies: %s", exc)

    async def fetch_announcements(self, session: aiohttp.ClientSession) -> List[NewsItem]:
        items: List[NewsItem] = []
        await self._refresh(session)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
        }
        try:
            async with session.get(
                NSE_ANN_URL,
                headers=headers,
                cookies=self._cookies,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                text = await resp.text()
                if resp.status != 200 or not text.strip():
                    logger.warning("NSE announcements returned status %s", resp.status)
                    return items
                data = json.loads(text)
        except Exception as exc:
            logger.warning("NSE announcements fetch failed: %s", exc)
            return items

        if not isinstance(data, list):
            logger.warning("Unexpected NSE response structure")
            return items

        for row in data:
            headline = clean_text(row.get("desc") or row.get("an_desc") or "")
            if not headline:
                continue
            url = row.get("attchmntFile") or ""
            if url and url.startswith("/"):
                url = f"https://www.nseindia.com{url}"
            dt = row.get("an_dt") or row.get("date")
            symbol = row.get("symbol") or row.get("sm_name")
            items.append(
                NewsItem(
                    source="nse_announcements",
                    headline=headline,
                    url=url,
                    published_at=parse_iso_date(dt),
                    source_type="regulatory",
                    symbol=symbol,
                    raw=row,
                )
            )
        logger.info("Fetched %d NSE announcements", len(items))
        return items


_nse_session = NSESession()


async def fetch_announcements(session: aiohttp.ClientSession) -> List[NewsItem]:
    return await _nse_session.fetch_announcements(session)
