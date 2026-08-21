"""Telegram alert sender."""

import logging
from typing import Any, Dict, Optional

from telegram import Bot

from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "\n\n<i>Personal tool only. Not investment advice. "
    "Do your own due diligence before trading.</i>"
)


def _bot() -> Optional[Bot]:
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram bot token not configured")
        return None
    return Bot(token=TELEGRAM_BOT_TOKEN)


def _format_urgent(symbol: Optional[str], catalyst: str, summary: str, evidence: Dict[str, Any]) -> str:
    sources = evidence.get("sources", [])
    source_links = "\n".join(f"• <a href='{url}'>{name}</a>" for name, url in sources if url) if sources else ""
    return (
        f"🚨 <b>URGENT SHORT WATCH</b>\n"
        f"<b>{symbol or 'UNKNOWN'}</b> — {catalyst}\n"
        f"{summary}\n\n"
        f"<b>Evidence:</b>\n{source_links}\n\n"
        f"Confidence: {evidence.get('confidence', 'N/A')}\n"
        f"Liquidity: {evidence.get('liquidity', 'N/A')}\n"
        f"Circuit: {evidence.get('circuit', 'N/A')}\n"
        f"Invalidation: {evidence.get('invalidation', 'N/A')}"
        f"{DISCLAIMER}"
    )


def _format_watch(symbol: Optional[str], catalyst: str, summary: str, evidence: Dict[str, Any]) -> str:
    return (
        f"⚠️ <b>WATCH</b>\n"
        f"<b>{symbol or 'UNKNOWN'}</b> — {catalyst}\n"
        f"{summary}\n"
        f"Sources: {len(evidence.get('sources', []))}"
        f"{DISCLAIMER}"
    )


def _format_ipo_verdict(ipo_name: str, verdict: str, context: str) -> str:
    return (
        f"📌 <b>IPO VERDICT: {ipo_name}</b>\n"
        f"Verdict: <b>{verdict}</b>\n\n"
        f"{context}"
        f"{DISCLAIMER}"
    )


def _format_morning_brief(cues: str, events: str) -> str:
    return (
        f"📊 <b>MORNING BRIEF</b>\n\n"
        f"<b>Global / Local Cues:</b>\n{cues}\n\n"
        f"<b>Overnight Events:</b>\n{events}"
        f"{DISCLAIMER}"
    )


def _format_evening_wrap(filings: str) -> str:
    return (
        f"🌙 <b>EVENING WRAP</b>\n\n"
        f"{filings}"
        f"{DISCLAIMER}"
    )


async def send_message(text: str, parse_mode: str = "HTML") -> Optional[int]:
    bot = _bot()
    if not bot or not TELEGRAM_CHAT_ID:
        logger.info("Telegram not configured; would send: %s", text[:200])
        return None
    try:
        chat_id = int(TELEGRAM_CHAT_ID)
        message = await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode, disable_web_page_preview=False)
        return message.message_id
    except Exception as exc:
        logger.warning("Telegram send failed: %s", exc)
        return None


async def send_urgent(symbol: Optional[str], catalyst: str, summary: str, evidence: Dict[str, Any]) -> Optional[int]:
    return await send_message(_format_urgent(symbol, catalyst, summary, evidence))


async def send_watch(symbol: Optional[str], catalyst: str, summary: str, evidence: Dict[str, Any]) -> Optional[int]:
    return await send_message(_format_watch(symbol, catalyst, summary, evidence))


async def send_ipo_verdict(ipo_name: str, verdict: str, context: str) -> Optional[int]:
    return await send_message(_format_ipo_verdict(ipo_name, verdict, context))


async def send_morning_brief(cues: str, events: str) -> Optional[int]:
    return await send_message(_format_morning_brief(cues, events))


async def send_evening_wrap(filings: str) -> Optional[int]:
    return await send_message(_format_evening_wrap(filings))


def _format_broker_reco(symbol: str, action: str, target: Optional[float], broker: str,
                        headline: str, news_backing: int, url: str) -> str:
    target_text = f"Target: Rs {target:,.0f}\n" if target else ""
    return (
        f"📈 <b>BROKER RECO</b>\n"
        f"<b>{symbol}</b> — {action} by {broker}\n"
        f"{target_text}"
        f"News backing: {news_backing} recent item(s)\n\n"
        f"<i>{headline}</i>\n"
        f"<a href='{url}'>Read more</a>"
        f"{DISCLAIMER}"
    )


async def send_broker_reco(symbol: str, action: str, target: Optional[float], broker: str,
                           headline: str, news_backing: int, url: str) -> Optional[int]:
    return await send_message(_format_broker_reco(symbol, action, target, broker, headline, news_backing, url))


async def send_heartbeat() -> Optional[int]:
    return await send_message("💓 Bot heartbeat: market monitor is running.")
