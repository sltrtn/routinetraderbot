"""Shared source helpers and data models."""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    source: str
    headline: str
    url: str = ""
    published_at: Optional[str] = None
    source_type: str = "news"  # regulatory | news | social
    symbol: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def hash(self) -> str:
        text = f"{self.source}|{self.headline}|{self.url}"
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


def clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_iso_date(value: Optional[str]) -> Optional[str]:
    """Best-effort parse to ISO format."""
    if not value:
        return None
    try:
        dt = datetime.strptime(value, "%a, %d %b %Y %H:%M:%S %Z")
        return dt.isoformat()
    except ValueError:
        pass
    try:
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
        return dt.isoformat()
    except ValueError:
        pass
    try:
        dt = datetime.strptime(value, "%d-%b-%Y %H:%M:%S")
        return dt.isoformat()
    except ValueError:
        pass
    return value
