"""NSE F&O universe loader."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List

import requests

from config.settings import NSE_FO_LOT_SIZE_URL, ROOT_DIR

logger = logging.getLogger(__name__)


@dataclass
class Stock:
    symbol: str
    name: str
    exchange: str
    lot_size: int
    fno: bool = True


_STATIC_FNO_FILE = ROOT_DIR / "data" / "fo_stocks.json"


def _load_static_fno() -> List[Stock]:
    try:
        symbols = json.loads(_STATIC_FNO_FILE.read_text())
        logger.info("Loaded %d F&O stocks from static file", len(symbols))
        return [
            Stock(symbol=s.strip().upper(), name=s.strip().upper(), exchange="NSE", lot_size=0)
            for s in symbols
        ]
    except Exception:
        logger.exception("Failed to load static F&O list")
        return []


def _normalize_symbol(sym: str) -> str:
    sym = sym.strip().upper()
    sym = sym.replace("&AMP;", "&")
    return sym


def _is_valid_fno_symbol(symbol: str) -> bool:
    """Heuristic: NSE symbols are short, uppercase alphanumeric, may contain & or -."""
    if not symbol:
        return False
    if len(symbol) > 25:
        return False
    if any(c.isspace() for c in symbol):
        return False
    if symbol.startswith("<") or symbol.startswith("("):
        return False
    return True


def _parse_nse_csv(text: str) -> List[Stock]:
    stocks: List[Stock] = []
    for line in text.splitlines():
        if not line.strip() or line.upper().startswith("SYMBOL"):
            continue
        row = [c.strip() for c in line.replace(",", " ").split()]
        if len(row) < 2:
            continue
        symbol = _normalize_symbol(row[0])
        lot = row[1].replace(",", "")
        if not lot.isdigit() or not _is_valid_fno_symbol(symbol):
            continue
        stocks.append(Stock(symbol=symbol, name=symbol, exchange="NSE", lot_size=int(lot)))
    return stocks


def _fetch_nse_fno() -> List[Stock]:
    if not NSE_FO_LOT_SIZE_URL:
        return []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/csv,text/plain,*/*",
    }
    resp = requests.get(NSE_FO_LOT_SIZE_URL, headers=headers, timeout=20)
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "").lower()
    if "pdf" in content_type:
        logger.warning("NSE F&O URL returned PDF, not CSV; using static list")
        return []
    stocks = _parse_nse_csv(resp.text)
    if not 150 <= len(stocks) <= 250:
        logger.warning("NSE F&O parse returned %d stocks (unexpected count); using static list", len(stocks))
        return []
    logger.info("Loaded %d F&O stocks from NSE", len(stocks))
    return stocks


def fetch_fno_universe() -> List[Stock]:
    """Return F&O universe. Try NSE CSV first, then static file."""
    try:
        stocks = _fetch_nse_fno()
        if stocks:
            return stocks
    except Exception:
        logger.debug("NSE F&O CSV fetch failed; falling back to static list", exc_info=True)

    stocks = _load_static_fno()
    if stocks:
        return stocks

    logger.error("Could not load any F&O watchlist")
    return []


def symbols() -> List[str]:
    return [s.symbol for s in fetch_fno_universe()]
