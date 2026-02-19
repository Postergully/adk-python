"""SQLite audit logger for Finny V1."""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


class AuditLogger:
    """Logs queries and responses to SQLite for auditability."""

    def __init__(self, db_path: str = "./finny_audit.db"):
        self._db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    correlation_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    user_id TEXT,
                    query_type TEXT,
                    query_text TEXT,
                    response_status TEXT,
                    netsuite_records TEXT,
                    error_message TEXT
                )
            """)
            conn.commit()

    @staticmethod
    def new_correlation_id() -> str:
        return str(uuid.uuid4())

    def log_query(
        self,
        correlation_id: str,
        user_id: str,
        query_text: str,
        query_type: str = "payment_status",
    ) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO audit_log
                   (correlation_id, timestamp, user_id, query_type, query_text,
                    response_status, netsuite_records, error_message)
                   VALUES (?, ?, ?, ?, ?, '', '', '')""",
                (correlation_id, datetime.utcnow().isoformat(), user_id, query_type, query_text),
            )
            conn.commit()

    def log_response(
        self,
        correlation_id: str,
        response_status: str,
        netsuite_records: Optional[list[str]] = None,
        error_message: str = "",
    ) -> None:
        records_str = ",".join(netsuite_records or [])
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """UPDATE audit_log
                   SET response_status = ?, netsuite_records = ?, error_message = ?
                   WHERE correlation_id = ?""",
                (response_status, records_str, error_message, correlation_id),
            )
            conn.commit()

    def get_log(self, correlation_id: str) -> Optional[dict]:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM audit_log WHERE correlation_id = ?",
                (correlation_id,),
            ).fetchone()
            return dict(row) if row else None
