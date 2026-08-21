"""Market data via yfinance (delayed, free)."""

import logging
from typing import Any, Dict, List, Optional

import yfinance as yf

logger = logging.getLogger(__name__)

TICKERS = {
    "gift_nifty": "^NSEI",       # Proxy; true GIFT Nifty ticker may differ
    "india_vix": "^INDIAVIX",
    "sp500": "^GSPC",
    "dow": "^DJI",
    "nasdaq": "^IXIC",
    "nikkei": "^N225",
    "hangseng": "^HSI",
}


def _safe_info(ticker: yf.Ticker) -> Dict[str, Any]:
    try:
        return ticker.info or {}
    except Exception as exc:
        logger.debug("yfinance info failed: %s", exc)
        return {}


def get_quote(symbol: str) -> Dict[str, Any]:
    """Return delayed quote info for an NSE symbol."""
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        info = _safe_info(ticker)
        hist = ticker.history(period="5d", interval="1d")
        avg_volume = hist["Volume"].mean() if not hist.empty else 0
        return {
            "symbol": symbol,
            "last_price": info.get("regularMarketPrice") or info.get("currentPrice"),
            "prev_close": info.get("regularMarketPreviousClose") or info.get("previousClose"),
            "change_pct": info.get("regularMarketChangePercent") or info.get("regularMarketChangePercent"),
            "avg_volume": avg_volume,
            "day_high": info.get("regularMarketDayHigh") or info.get("dayHigh"),
            "day_low": info.get("regularMarketDayLow") or info.get("dayLow"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        }
    except Exception as exc:
        logger.warning("yfinance quote failed for %s: %s", symbol, exc)
        return {"symbol": symbol}


def get_global_cues() -> Dict[str, Any]:
    cues: Dict[str, Any] = {}
    for name, ticker_str in TICKERS.items():
        try:
            ticker = yf.Ticker(ticker_str)
            info = _safe_info(ticker)
            hist = ticker.history(period="2d", interval="1d")
            prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
            last = info.get("regularMarketPrice") or info.get("currentPrice")
            change_pct = None
            if last and prev_close:
                change_pct = round((last - prev_close) / prev_close * 100, 2)
            cues[name] = {
                "last": last,
                "prev_close": prev_close,
                "change_pct": change_pct,
                "currency": info.get("currency"),
            }
        except Exception as exc:
            logger.warning("yfinance global cue failed for %s: %s", name, exc)
            cues[name] = {"error": str(exc)}
    return cues


def get_quotes(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """Batch fetch quotes. yfinance batch is flaky, so loop with short delay."""
    result: Dict[str, Dict[str, Any]] = {}
    for symbol in symbols:
        result[symbol] = get_quote(symbol)
    return result
