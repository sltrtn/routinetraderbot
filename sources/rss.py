"""RSS news source adapters."""

import logging
from typing import List

import aiohttp
import feedparser

from sources.common import NewsItem, clean_text, parse_iso_date

logger = logging.getLogger(__name__)

FEEDS = [
    ("moneycontrol_latest", "https://www.moneycontrol.com/rss/latestnews.xml"),
    ("moneycontrol_business", "https://www.moneycontrol.com/rss/business.xml"),
    ("et_markets", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    ("et_companies", "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"),
    ("livemint_markets", "https://www.livemint.com/rss/markets"),
    ("livemint_companies", "https://www.livemint.com/rss/companies"),
    ("bs_markets", "https://www.business-standard.com/rss/markets-106.rss"),
    ("bs_companies", "https://www.business-standard.com/rss/companies-101.rss"),
]


async def fetch_feed(session: aiohttp.ClientSession, name: str, url: str) -> List[NewsItem]:
    items: List[NewsItem] = []
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            text = await resp.text()
    except Exception as exc:
        logger.warning("RSS fetch failed for %s: %s", name, exc)
        return items

    try:
        parsed = feedparser.parse(text)
    except Exception as exc:
        logger.warning("RSS parse failed for %s: %s", name, exc)
        return items

    for entry in parsed.entries:
        headline = clean_text(entry.get("title", ""))
        link = entry.get("link", "")
        if not headline:
            continue
        items.append(
            NewsItem(
                source=name,
                headline=headline,
                url=link,
                published_at=parse_iso_date(entry.get("published") or entry.get("updated")),
                source_type="news",
                raw={"feed": name, "summary": entry.get("summary", "")},
            )
        )
    logger.debug("Fetched %d items from %s", len(items), name)
    return items


async def fetch_all(session: aiohttp.ClientSession) -> List[NewsItem]:
    items: List[NewsItem] = []
    for name, url in FEEDS:
        try:
            items.extend(await fetch_feed(session, name, url))
        except Exception:
            logger.exception("Unexpected error fetching %s", name)
    return items
