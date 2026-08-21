"""Async SQLite database layer."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

from config.settings import DB_PATH

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    last_ok_at TEXT,
    last_error_at TEXT,
    last_error TEXT,
    success_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT UNIQUE NOT NULL,
    name TEXT,
    exchange TEXT,
    lot_size INTEGER,
    fno INTEGER DEFAULT 1,
    avg_volume_lakhs REAL,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS news_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_type TEXT,
    headline TEXT NOT NULL,
    url TEXT,
    published_at TEXT,
    fetched_at TEXT NOT NULL,
    hash TEXT UNIQUE NOT NULL,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT UNIQUE NOT NULL,
    symbol TEXT,
    catalyst TEXT,
    severity TEXT,
    confidence REAL,
    summary TEXT,
    evidence TEXT,
    status TEXT DEFAULT 'open',
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL,
    symbol TEXT,
    message TEXT NOT NULL,
    evidence TEXT,
    sent_at TEXT NOT NULL,
    telegram_message_id INTEGER
);

CREATE TABLE IF NOT EXISTS ipo_tracker (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    issue_dates TEXT,
    price_band TEXT,
    qib REAL,
    hni REAL,
    retail REAL,
    total REAL,
    gmp REAL,
    gmp_pct REAL,
    verdict TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS fundamentals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    quarter TEXT NOT NULL,
    revenue REAL,
    net_profit REAL,
    eps REAL,
    raw_text TEXT,
    updated_at TEXT,
    UNIQUE(symbol, quarter)
);

CREATE TABLE IF NOT EXISTS outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL,
    t0_price REAL,
    t1_price REAL,
    t5_price REAL,
    return_t1_pct REAL,
    return_t5_pct REAL,
    hit INTEGER,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS market_calendar (
    date TEXT PRIMARY KEY,
    is_trading INTEGER NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS broker_recos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hash TEXT UNIQUE NOT NULL,
    symbol TEXT NOT NULL,
    company_name TEXT,
    action TEXT NOT NULL,
    target REAL,
    broker TEXT NOT NULL,
    source TEXT NOT NULL,
    url TEXT,
    published_at TEXT,
    headline TEXT,
    alerted INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(SCHEMA)
            await db.commit()
        logger.info("Database initialized at %s", self.db_path)

    async def upsert_source_health(self, name: str, ok: bool, error: Optional[str] = None) -> None:
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO sources (name, last_ok_at, last_error_at, last_error, success_count, fail_count)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    last_ok_at = COALESCE(excluded.last_ok_at, sources.last_ok_at),
                    last_error_at = COALESCE(excluded.last_error_at, sources.last_error_at),
                    last_error = COALESCE(excluded.last_error, sources.last_error),
                    success_count = sources.success_count + COALESCE(excluded.success_count, 0),
                    fail_count = sources.fail_count + COALESCE(excluded.fail_count, 0)
                """,
                (
                    name,
                    now if ok else None,
                    now if not ok else None,
                    error,
                    1 if ok else 0,
                    1 if not ok else 0,
                ),
            )
            await db.commit()

    async def insert_news(self, source: str, headline: str, url: Optional[str], hash_hex: str,
                          source_type: str = "news", published_at: Optional[str] = None,
                          raw_json: Optional[Dict[str, Any]] = None) -> bool:
        now = datetime.now().isoformat()
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO news_items (source, source_type, headline, url, published_at, fetched_at, hash, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (source, source_type, headline, url, published_at, now, hash_hex,
                     json.dumps(raw_json) if raw_json else None),
                )
                await db.commit()
                return True
        except aiosqlite.IntegrityError:
            return False

    async def get_event(self, fingerprint: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM events WHERE fingerprint = ?", (fingerprint,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def upsert_event(self, fingerprint: str, symbol: Optional[str], catalyst: str,
                           severity: str, confidence: float, summary: str,
                           evidence: Dict[str, Any]) -> None:
        now = datetime.now().isoformat()
        evidence_json = json.dumps(evidence)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO events (fingerprint, symbol, catalyst, severity, confidence, summary, evidence, first_seen_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    severity = excluded.severity,
                    confidence = excluded.confidence,
                    summary = excluded.summary,
                    evidence = excluded.evidence,
                    last_seen_at = excluded.last_seen_at
                """,
                (fingerprint, symbol, catalyst, severity, confidence, summary, evidence_json, now, now),
            )
            await db.commit()

    async def insert_alert(self, alert_type: str, symbol: Optional[str], message: str,
                           evidence: Dict[str, Any]) -> int:
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO alerts (alert_type, symbol, message, evidence, sent_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (alert_type, symbol, message, json.dumps(evidence), now),
            )
            await db.commit()
            return cursor.lastrowid

    async def save_watchlist(self, stocks: List[Dict[str, Any]]) -> None:
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            for stock in stocks:
                await db.execute(
                    """
                    INSERT INTO watchlist (symbol, name, exchange, lot_size, fno, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol) DO UPDATE SET
                        name = excluded.name,
                        exchange = excluded.exchange,
                        lot_size = excluded.lot_size,
                        fno = excluded.fno,
                        updated_at = excluded.updated_at
                    """,
                    (stock["symbol"], stock.get("name"), stock.get("exchange", "NSE"),
                     stock.get("lot_size", 0), 1 if stock.get("fno") else 0, now),
                )
            await db.commit()

    async def execute(self, sql: str, params: tuple = ()) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(sql, params)
            await db.commit()

    async def fetch(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def insert_broker_reco(self, reco: Dict[str, Any]) -> bool:
        now = datetime.now().isoformat()
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO broker_recos (hash, symbol, company_name, action, target, broker, source, url, published_at, headline, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        reco["hash"], reco["symbol"], reco.get("company_name"), reco["action"],
                        reco.get("target"), reco["broker"], reco["source"], reco.get("url"),
                        reco.get("published_at"), reco.get("headline"), now,
                    ),
                )
                await db.commit()
                return True
        except aiosqlite.IntegrityError:
            return False

    async def has_recent_news_for_symbol(self, symbol: str, days: int = 7) -> List[Dict[str, Any]]:
        """Return recent news items for a symbol."""
        since = (datetime.now() - timedelta(days=days)).isoformat()
        return await self.fetch(
            """
            SELECT * FROM news_items
            WHERE headline LIKE ? AND fetched_at > ?
            ORDER BY fetched_at DESC
            LIMIT 5
            """,
            (f"%{symbol}%", since),
        )
