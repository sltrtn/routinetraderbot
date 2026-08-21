"""In-memory state cache for the bot."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set


@dataclass
class BotState:
    watchlist_symbols: Set[str] = field(default_factory=set)
    last_hashes: Set[str] = field(default_factory=set)
    source_health: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    pending_alerts: List[Dict[str, Any]] = field(default_factory=list)
    last_heartbeat: Optional[datetime] = None

    def is_duplicate(self, hash_hex: str) -> bool:
        if hash_hex in self.last_hashes:
            return True
        self.last_hashes.add(hash_hex)
        # Keep set bounded.
        if len(self.last_hashes) > 50_000:
            self.last_hashes = set(list(self.last_hashes)[-25_000:])
        return False
