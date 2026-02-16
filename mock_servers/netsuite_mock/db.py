"""In-memory database for NetSuite mock server.

Loads seed data from JSON and provides CRUD operations for all record types.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class InMemoryDB:
    """Simple in-memory store keyed by record type."""

    def __init__(self) -> None:
        self.tables: Dict[str, Dict[str, dict]] = {
            "vendor": {},
            "vendorBill": {},
            "vendorPayment": {},
            "expense": {},
            "bankEntry": {},
            "ccInvoice": {},
            "accrual": {},
        }
        self._id_counters: Dict[str, int] = {}

    # --- ID generation ---

    def _next_id(self, table: str) -> str:
        counter = self._id_counters.get(table, 0) + 1
        self._id_counters[table] = counter
        return str(counter)

    # --- CRUD ---

    def insert(self, table: str, record: dict) -> dict:
        if "id" not in record or not record["id"]:
            record["id"] = self._next_id(table)
        else:
            # Update counter if seed data has higher IDs
            try:
                num = int(record["id"])
                if num >= self._id_counters.get(table, 0):
                    self._id_counters[table] = num
            except ValueError:
                pass
        self.tables[table][record["id"]] = record
        return record

    def get(self, table: str, record_id: str) -> Optional[dict]:
        return self.tables.get(table, {}).get(record_id)

    def update(self, table: str, record_id: str, data: dict) -> Optional[dict]:
        existing = self.get(table, record_id)
        if existing is None:
            return None
        existing.update(data)
        existing["id"] = record_id  # prevent id overwrite
        return existing

    def delete(self, table: str, record_id: str) -> bool:
        return self.tables.get(table, {}).pop(record_id, None) is not None

    def list_all(self, table: str) -> List[dict]:
        return list(self.tables.get(table, {}).values())

    def query(self, table: str, filters: Dict[str, Any]) -> List[dict]:
        """Simple field-value filter matching."""
        results = []
        for record in self.tables.get(table, {}).values():
            match = True
            for key, value in filters.items():
                record_val = _deep_get(record, key)
                if record_val is None:
                    match = False
                    break
                if isinstance(value, str) and "%" in value:
                    pattern = value.replace("%", ".*")
                    if not re.match(pattern, str(record_val), re.IGNORECASE):
                        match = False
                        break
                elif str(record_val) != str(value):
                    match = False
                    break
            if match:
                results.append(record)
        return results

    def search(self, table: str, q: str) -> List[dict]:
        """Parse simple NetSuite query strings like:
        companyName LIKE 'Google%'
        entity.id='123' AND status='pendingApproval'
        """
        filters = _parse_netsuite_query(q)
        return self.query(table, filters)

    # --- SuiteQL ---

    def execute_suiteql(self, sql: str) -> List[dict]:
        """Very basic SuiteQL parser for common patterns."""
        sql_lower = sql.strip().lower()

        # COUNT(*) FROM table WHERE ...
        count_match = re.match(
            r"select\s+count\(\*\)\s+(?:as\s+\w+\s+)?from\s+(\w+)(.*)",
            sql_lower,
        )
        if count_match:
            table = _normalize_table(count_match.group(1))
            where = count_match.group(2).strip()
            records = self._apply_where(table, where)
            return [{"count": len(records)}]

        # SUM(amount) FROM table WHERE ...
        sum_match = re.match(
            r"select\s+sum\((\w+)\)\s+(?:as\s+\w+\s+)?from\s+(\w+)(.*)",
            sql_lower,
        )
        if sum_match:
            field = sum_match.group(1)
            table = _normalize_table(sum_match.group(2))
            where = sum_match.group(3).strip()
            records = self._apply_where(table, where)
            total = sum(float(r.get(field, 0)) for r in records)
            return [{"sum": total}]

        # SELECT * FROM table WHERE ...
        select_match = re.match(
            r"select\s+\*\s+from\s+(\w+)(.*)",
            sql_lower,
        )
        if select_match:
            table = _normalize_table(select_match.group(1))
            where = select_match.group(2).strip()
            return self._apply_where(table, where)

        # SELECT field1, field2 FROM table WHERE ...
        fields_match = re.match(
            r"select\s+(.+?)\s+from\s+(\w+)(.*)",
            sql_lower,
        )
        if fields_match:
            fields = [f.strip() for f in fields_match.group(1).split(",")]
            table = _normalize_table(fields_match.group(2))
            where = fields_match.group(3).strip()
            records = self._apply_where(table, where)
            return [{f: r.get(f) for f in fields} for r in records]

        return []

    def _apply_where(self, table: str, where_clause: str) -> List[dict]:
        if not where_clause or not where_clause.startswith("where"):
            return self.list_all(table)
        where_body = where_clause[5:].strip()  # strip "where"
        filters = _parse_netsuite_query(where_body)
        return self.query(table, filters)

    # --- Seed data loading ---

    def load_seed_data(self, path: str | Path) -> None:
        path = Path(path)
        if not path.exists():
            return
        with open(path, "r") as f:
            data = json.load(f)

        table_mapping = {
            "vendors": "vendor",
            "vendorBills": "vendorBill",
            "vendorPayments": "vendorPayment",
            "expenses": "expense",
            "bankEntries": "bankEntry",
            "ccInvoices": "ccInvoice",
            "accruals": "accrual",
        }

        for json_key, table_name in table_mapping.items():
            for record in data.get(json_key, []):
                self.insert(table_name, record)


# --- Helpers ---

def _deep_get(record: dict, key: str) -> Any:
    """Support dotted paths like 'entity.id'."""
    parts = key.split(".")
    val = record
    for part in parts:
        if isinstance(val, dict):
            val = val.get(part)
        else:
            return None
    return val


def _normalize_table(name: str) -> str:
    """Map SuiteQL table names to our internal table names."""
    mapping = {
        "vendor": "vendor",
        "vendorbill": "vendorBill",
        "vendorpayment": "vendorPayment",
        "expense": "expense",
        "bankentry": "bankEntry",
        "ccinvoice": "ccInvoice",
        "accrual": "accrual",
    }
    return mapping.get(name.lower(), name)


def _parse_netsuite_query(q: str) -> Dict[str, Any]:
    """Parse simple query strings like:
    companyName LIKE 'Google%'
    entity.id='123' AND status='pendingApproval'
    """
    if not q:
        return {}

    filters = {}
    # Split on AND
    parts = re.split(r"\s+AND\s+", q, flags=re.IGNORECASE)
    for part in parts:
        part = part.strip()

        # LIKE pattern
        like_match = re.match(r"(\S+)\s+LIKE\s+'([^']*)'", part, re.IGNORECASE)
        if like_match:
            filters[like_match.group(1)] = like_match.group(2)
            continue

        # Equality: field='value' or field = 'value'
        eq_match = re.match(r"(\S+)\s*=\s*'([^']*)'", part)
        if eq_match:
            filters[eq_match.group(1)] = eq_match.group(2)
            continue

        # Date comparisons (simplified — just filter in)
        date_match = re.match(
            r"TRUNC\((\w+)\)\s*>=\s*'([^']*)'", part, re.IGNORECASE
        )
        if date_match:
            # We'll store this as a special filter that query() handles
            filters[f"_gte_{date_match.group(1)}"] = date_match.group(2)
            continue

    return filters


# --- Singleton ---

_db: Optional[InMemoryDB] = None


def get_db() -> InMemoryDB:
    global _db
    if _db is None:
        _db = InMemoryDB()
        seed_path = Path(__file__).parent / "data" / "seed_data.json"
        _db.load_seed_data(seed_path)
    return _db


def reset_db() -> InMemoryDB:
    """Reset the database (useful for testing)."""
    global _db
    _db = None
    return get_db()
