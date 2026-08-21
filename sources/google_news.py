"""Google News RSS source."""

import logging
import urllib.parse
from typing import List

import aiohttp
import feedparser

from config.settings import GOOGLE_NEWS_MAX_PER_QUERY
from sources.common import NewsItem, clean_text, parse_iso_date

logger = logging.getLogger(__name__)

TOPIC_QUERIES = [
    "promoter pledge shares India",
    "SEBI warning notice company India",
    "auditor resignation India listed company",
    "CEO CFO resignation India company",
    "major litigation India company",
    "earnings miss India company",
    "credit rating downgrade India",
    "board meeting India company",
]

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"


def _build_url(query: str) -> str:
    params = {
        "q": query,
        "hl": "en-IN",
        "gl": "IN",
        "ceid": "IN:en",
    }
    return f"{GOOGLE_NEWS_RSS}?{urllib.parse.urlencode(params)}"


async def fetch_query(session: aiohttp.ClientSession, query: str) -> List[NewsItem]:
    items: List[NewsItem] = []
    url = _build_url(query)
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            text = await resp.text()
    except Exception as exc:
        logger.warning("Google News fetch failed for '%s': %s", query, exc)
        return items

    try:
        parsed = feedparser.parse(text)
    except Exception as exc:
        logger.warning("Google News parse failed for '%s': %s", query, exc)
        return items

    for entry in parsed.entries[:GOOGLE_NEWS_MAX_PER_QUERY]:
        headline = clean_text(entry.get("title", ""))
        link = entry.get("link", "")
        if not headline:
            continue
        items.append(
            NewsItem(
                source=f"google_news:{query}",
                headline=headline,
                url=link,
                published_at=parse_iso_date(entry.get("published") or entry.get("updated")),
                source_type="news",
                raw={"query": query, "summary": entry.get("summary", "")},
            )
        )
    logger.debug("Fetched %d items from Google News query '%s'", len(items), query)
    return items


async def fetch_all(session: aiohttp.ClientSession, queries: List[str] = None) -> List[NewsItem]:
    queries = queries or TOPIC_QUERIES
    items: List[NewsItem] = []
    for query in queries:
        try:
            items.extend(await fetch_query(session, query))
        except Exception:
            logger.exception("Unexpected error fetching Google News query %s", query)
    return items
