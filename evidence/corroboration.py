"""Event fingerprinting, catalyst keyword classification, and corroboration."""

import json
import logging
import re
from datetime import datetime
from typing import List, Optional, Tuple

from core.database import Database
from sources.common import NewsItem

logger = logging.getLogger(__name__)

CATALYST_PATTERNS = [
    ("PROMOTER_PLEDGE", [r"promoter\s.*pledge", r"pledge\s.*shares?", r"share\s.*pledged"]),
    ("SEBI_WARNING", [r"sebi", r"show.?cause", r"regulatory\s.*action", r"penalty", r"settlement"]),
    ("AUDITOR_RESIGNATION", [r"auditor\s.*resign", r"statutory\s.*auditor", r"resign\s.*auditor"]),
    ("C_SUITE_RESIGNATION", [r"ceo\s.*resign", r"cfo\s.*resign", r"md\s.*resign", r"director\s.*resign",
                              r"resigns?\s.*ceo", r"resigns?\s.*cfo", r"resigns?\s.*md", r"steps\s.*down"]),
    ("MAJOR_LITIGATION", [r"nclt", r"supreme\s.*court", r"high\s.*court", r"arbitration",
                           r"lawsuit", r"legal\s.*dispute", r"class.?action"]),
    ("EARNINGS_MISS", [r"earnings?", r"quarterly\s.*result", r"quarterly\s.*profit", r"net\s.*profit\s.*fall",
                        r"net\s.*profit\s.*drop", r"profit\s.*fall", r"profit\s.*down", r"net\s.*loss",
                        r"misses?\s.*estimate", r"below\s.*estimate"]),
    ("CREDIT_RATING_CHANGE", [r"credit\s.*rating", r"downgrade", r"upgrade", r"icra", r"crisil", r"care\s.*rating"]),
    ("BOARD_MEETING", [r"board\s.*meet", r"board\s.*approve"]),
    ("ACQUISITION", [r"acquisition", r"acquires?", r"stake\s.*buy", r"buys?\s.*stake"]),
    ("OPEN_OFFER", [r"open\s.*offer"]),
]


def classify_catalyst(headline: str) -> Optional[str]:
    text = headline.lower()
    for catalyst, patterns in CATALYST_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, text):
                return catalyst
    return None


def extract_symbol(headline: str, watchlist: List[str]) -> Optional[str]:
    """Extract first matching watchlist symbol from headline (whole-word)."""
    text = f" {headline.upper()} "
    # Sort by length descending to match longer symbols first (e.g., TATASTEEL before TATA).
    for symbol in sorted(watchlist, key=len, reverse=True):
        # Whole word match; allow & in symbol.
        pattern = r"(?<![A-Z0-9&])" + re.escape(symbol) + r"(?![A-Z0-9&])"
        if re.search(pattern, text):
            return symbol
    return None


def event_fingerprint(symbol: Optional[str], catalyst: Optional[str], published_at: Optional[str]) -> str:
    date_part = ""
    if published_at:
        try:
            date_part = datetime.fromisoformat(published_at).strftime("%Y%m%d")
        except ValueError:
            pass
    if not date_part:
        date_part = datetime.now().strftime("%Y%m%d")
    sym = symbol or "_UNKNOWN_"
    cat = catalyst or "_GENERIC_"
    return f"{sym}|{cat}|{date_part}"


async def check_evidence(db: Database, fingerprint: str, item: NewsItem) -> Tuple[bool, int]:
    """Return (passes_evidence_rule, source_count)."""
    # Fetch existing event sources from DB.
    existing = await db.get_event(fingerprint)
    sources: set = set()
    if existing:
        try:
            evidence = json.loads(existing.get("evidence", "{}"))
            sources = set(evidence.get("sources", []))
        except Exception:
            pass

    sources.add(item.source)
    if item.source_type == "regulatory":
        return True, len(sources)
    return len(sources) >= 2, len(sources)
