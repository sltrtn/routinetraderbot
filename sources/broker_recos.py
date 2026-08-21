"""Broker recommendation parser from RSS headlines."""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional

import aiohttp
import feedparser

from config.symbol_map import resolve_symbol
from sources.common import NewsItem, clean_text, parse_iso_date

logger = logging.getLogger(__name__)

# Credible brokers whose calls we surface.
CREDIBLE_BROKERS = {
    "icici securities", "hdfc securities", "motilal oswal", "edelweiss", "axis securities",
    "kotak securities", "jm financial", "clsa", "morgan stanley", "goldman sachs",
    "citi", "bofA securities", "bank of america", "jpmorgan", "ubs", "nomura",
    "ambit", "antique", "elara capital", "prabhudas lilladher", "sharekhan",
    "geojit", "anand rathi", "nuvama", "sbi securities", "yes securities",
    "pl capital", "dolat capital", "systematix", "lkp securities", "icici direct",
    "reliance securities", "sundaram mutual", "quant mutual fund",
}

ACTIONS = {"buy", "sell", "hold", "add", "accumulate", "reduce", "neutral", "overweight", "underperform"}

FEEDS = [
    ("moneycontrol_latest", "https://www.moneycontrol.com/rss/latestnews.xml"),
    ("moneycontrol_business", "https://www.moneycontrol.com/rss/business.xml"),
    ("et_markets", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    ("et_companies", "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"),
]


@dataclass
class BrokerReco:
    symbol: str
    company_name: str
    action: str
    target: Optional[float]
    broker: str
    source: str
    url: str
    published_at: Optional[str]
    headline: str
    hash: str


def _normalize_broker(name: str) -> str:
    name = name.strip()
    name = re.sub(r"\s+ltd\.?$", "", name, flags=re.I)
    name = re.sub(r"\s+limited\.?$", "", name, flags=re.I)
    return name


def _is_credible(broker: str) -> bool:
    normalized = _normalize_broker(broker).lower()
    return any(cred in normalized for cred in CREDIBLE_BROKERS)


def _extract_target(headline: str) -> Optional[float]:
    patterns = [
        r"target\s+(?:price\s+)?(?:of\s+)?Rs\.?\s*([\d,]+)",
        r"target\s+(?:price\s+)?(?:of\s+)?INR\s*([\d,]+)",
        r"target\s+(?:price\s+)?(?:of\s+)?Rs\s*([\d,]+)",
        r"TP\s+(?:of\s+)?Rs\.?\s*([\d,]+)",
    ]
    for p in patterns:
        m = re.search(p, headline, re.I)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def _extract_action(headline: str) -> Optional[str]:
    text = headline.lower()
    # Look for action words at the start or after "maintain"
    for action in sorted(ACTIONS, key=len, reverse=True):
        if re.search(rf"\b{action}\b", text):
            return action.upper()
    return None


def _extract_company_and_broker(headline: str, action: str) -> tuple[str, str]:
    """Parse 'Buy HDFC Bank; target of Rs 1,850: ICICI Securities' style."""
    # Split on colon to separate broker
    parts = headline.split(":", 1)
    broker = parts[1].strip() if len(parts) > 1 else ""
    left = parts[0].strip()

    # Remove action word from left
    text = re.sub(rf"\b{action}\b", "", left, flags=re.I).strip()
    # Remove target clause
    text = re.split(r"\s*;\s*", text)[0].strip()
    text = re.sub(r"\s+(?:with|at)\s+.*", "", text, flags=re.I).strip()
    return text, broker


def parse_reco(headline: str, source: str, url: str, published_at: Optional[str]) -> Optional[BrokerReco]:
    headline = clean_text(headline)
    action = _extract_action(headline)
    if not action:
        return None

    company_name, broker = _extract_company_and_broker(headline, action)
    if not broker or not _is_credible(broker):
        return None

    symbol = resolve_symbol(company_name)
    if not symbol:
        return None

    target = _extract_target(headline)
    hash_input = f"{symbol}|{action}|{target}|{broker}|{published_at or ''}"
    import hashlib
    hash_hex = hashlib.sha256(hash_input.encode()).hexdigest()

    return BrokerReco(
        symbol=symbol,
        company_name=company_name,
        action=action,
        target=target,
        broker=broker,
        source=source,
        url=url,
        published_at=published_at,
        headline=headline,
        hash=hash_hex,
    )


async def fetch_feed(session: aiohttp.ClientSession, name: str, url: str) -> List[BrokerReco]:
    recos: List[BrokerReco] = []
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            text = await resp.text()
    except Exception as exc:
        logger.warning("Broker reco feed fetch failed %s: %s", name, exc)
        return recos

    try:
        parsed = feedparser.parse(text)
    except Exception as exc:
        logger.warning("Broker reco feed parse failed %s: %s", name, exc)
        return recos

    for entry in parsed.entries:
        headline = clean_text(entry.get("title", ""))
        if not headline:
            continue
        reco = parse_reco(
            headline,
            source=name,
            url=entry.get("link", ""),
            published_at=parse_iso_date(entry.get("published") or entry.get("updated")),
        )
        if reco:
            recos.append(reco)
    logger.debug("Parsed %d broker recos from %s", len(recos), name)
    return recos


async def fetch_all(session: aiohttp.ClientSession) -> List[BrokerReco]:
    recos: List[BrokerReco] = []
    for name, url in FEEDS:
        try:
            recos.extend(await fetch_feed(session, name, url))
        except Exception:
            logger.exception("Broker reco fetch failed for %s", name)
    return recos
