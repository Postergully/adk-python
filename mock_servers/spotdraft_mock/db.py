"""In-memory database for the Spotdraft mock server.

Seed data is loaded from ``data/seed_data.json`` on first access.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_DATA_DIR = Path(__file__).parent / "data"

_store: dict[str, list[dict[str, Any]]] = {
    "parties": [],
    "contracts": [],
    "documents": [],
}

_loaded = False


def _load_seed() -> None:
    global _loaded
    if _loaded:
        return
    seed_path = _DATA_DIR / "seed_data.json"
    if seed_path.exists():
        with open(seed_path) as f:
            data = json.load(f)
        for key in _store:
            _store[key] = data.get(key, [])
    _loaded = True


def get_collection(name: str) -> list[dict[str, Any]]:
    _load_seed()
    return _store[name]


def add_item(collection: str, item: dict[str, Any]) -> dict[str, Any]:
    _load_seed()
    _store[collection].append(item)
    return item


def find_by_id(collection: str, item_id: str) -> dict[str, Any] | None:
    _load_seed()
    for item in _store[collection]:
        if item.get("id") == item_id:
            return item
    return None
