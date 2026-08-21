"""IPO GMP and subscription scrapers."""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

CHITTORGARH_URL = "https://chittorgarh.com/report/ipo-grey-market-premium-latest-ipo-gmp/240/"
IPOWATCH_URL = "https://ipowatch.in/ipo-grey-market-premium-upcoming-ipo-gmp/"


@dataclass
class IPO:
    name: str
    gmp: Optional[float] = None
    gmp_pct: Optional[float] = None
    price_band: Optional[str] = None
    qib: Optional[float] = None
    hni: Optional[float] = None
    retail: Optional[float] = None
    total: Optional[float] = None
    source: str = ""


def _extract_float(text: str) -> Optional[float]:
    if not text:
        return None
    nums = re.findall(r"[\d,]+\.?\d*", text.replace(",", ""))
    if nums:
        try:
            return float(nums[0])
        except ValueError:
            pass
    return None


async def _fetch_chittorgarh(session: aiohttp.ClientSession) -> List[IPO]:
    ipos: List[IPO] = []
    try:
        async with session.get(CHITTORGARH_URL, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            html = await resp.text()
    except Exception as exc:
        logger.warning("Chittorgarh fetch failed: %s", exc)
        return ipos

    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", {"id": re.compile(r"table\d+", re.I)})
    if not table:
        logger.warning("Chittorgarh table not found")
        return ipos

    rows = table.find_all("tr")[1:]
    for row in rows:
        cells = row.find_all(["td", "th"])
        if len(cells) < 4:
            continue
        name = cells[0].get_text(strip=True)
        gmp = _extract_float(cells[1].get_text())
        price_text = cells[2].get_text(strip=True)
        price = _extract_float(price_text)
        gmp_pct = None
        if gmp and price:
            gmp_pct = round(gmp / price * 100, 2)
        ipos.append(IPO(name=name, gmp=gmp, gmp_pct=gmp_pct, price_band=price_text, source="chittorgarh"))
    return ipos


async def fetch_all(session: aiohttp.ClientSession) -> List[IPO]:
    """Fetch GMP data. Chittorgarh is primary; can extend with IPOWatch."""
    return await _fetch_chittorgarh(session)
