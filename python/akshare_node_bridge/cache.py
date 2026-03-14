from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CacheRecord:
    interface_name: str
    request_key: str
    payload: dict[str, Any]


class SqliteCache:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    interface_name TEXT NOT NULL,
                    request_key TEXT NOT NULL PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cache_entries_interface_name
                ON cache_entries(interface_name)
                """
            )

    def get(self, request_key: str) -> CacheRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT interface_name, request_key, payload_json FROM cache_entries WHERE request_key = ?",
                (request_key,),
            ).fetchone()
        if row is None:
            return None
        return CacheRecord(
            interface_name=row["interface_name"],
            request_key=row["request_key"],
            payload=json.loads(row["payload_json"]),
        )

    def set(self, interface_name: str, request_key: str, payload: dict[str, Any]) -> None:
        payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO cache_entries(interface_name, request_key, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(request_key) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (interface_name, request_key, payload_json),
            )

