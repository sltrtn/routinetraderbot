"""Deduplication: headline hashes and DB storage."""

import logging
from typing import Optional

from core.database import Database
from core.state import BotState
from sources.common import NewsItem

logger = logging.getLogger(__name__)


async def is_new(item: NewsItem, state: BotState, db: Database) -> bool:
    """Return True if this item has not been seen before."""
    if state.is_duplicate(item.hash):
        return False
    try:
        inserted = await db.insert_news(
            source=item.source,
            headline=item.headline,
            url=item.url,
            hash_hex=item.hash,
            source_type=item.source_type,
            published_at=item.published_at,
            raw_json=item.raw,
        )
        return inserted
    except Exception:
        logger.exception("DB insert failed for news item")
        # On DB failure, treat as duplicate to avoid spam.
        return False
