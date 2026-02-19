"""In-memory database for Slack mock server.

Loads seed data from JSON and provides operations for channels, messages, and users.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class InMemoryDB:
    """Simple in-memory store for Slack data."""

    def __init__(self) -> None:
        self.channels: Dict[str, dict] = {}
        self.users: Dict[str, dict] = {}
        self.messages: Dict[str, List[dict]] = {}  # channel_id -> [messages]
        self.events: List[dict] = []
        self._ts_counter: int = 0

    # --- Timestamp generation ---

    def _next_ts(self) -> str:
        """Generate a unique Slack-style timestamp string."""
        self._ts_counter += 1
        base = int(time.time())
        return f"{base}.{self._ts_counter:06d}"

    # --- Message operations ---

    def post_message(
        self,
        channel: str,
        user: str,
        text: str,
        thread_ts: Optional[str] = None,
    ) -> dict:
        """Store a message and return it with a generated ts."""
        ts = self._next_ts()
        message = {
            "channel": channel,
            "user": user,
            "text": text,
            "ts": ts,
            "thread_ts": thread_ts,
            "type": "message",
        }
        if channel not in self.messages:
            self.messages[channel] = []
        self.messages[channel].append(message)
        return message

    def update_message(
        self, channel: str, ts: str, text: str
    ) -> Optional[dict]:
        """Update an existing message by channel and ts."""
        for msg in self.messages.get(channel, []):
            if msg["ts"] == ts:
                msg["text"] = text
                return msg
        return None

    def get_messages(self, channel: str, limit: int = 100) -> List[dict]:
        """Return channel messages, most recent first."""
        msgs = self.messages.get(channel, [])
        # Return top-level messages only (not thread replies)
        top_level = [m for m in msgs if m.get("thread_ts") is None]
        return list(reversed(top_level[-limit:]))

    def get_thread_replies(
        self, channel: str, thread_ts: str
    ) -> List[dict]:
        """Return all messages in a thread, including the parent."""
        msgs = self.messages.get(channel, [])
        thread = [
            m
            for m in msgs
            if m["ts"] == thread_ts or m.get("thread_ts") == thread_ts
        ]
        return thread

    # --- Channel operations ---

    def get_channel(self, channel_id: str) -> Optional[dict]:
        return self.channels.get(channel_id)

    def list_channels(self) -> List[dict]:
        return list(self.channels.values())

    # --- User operations ---

    def get_user(self, user_id: str) -> Optional[dict]:
        return self.users.get(user_id)

    def list_users(self) -> List[dict]:
        return list(self.users.values())

    # --- Event operations ---

    def store_event(self, event: dict) -> dict:
        self.events.append(event)
        return event

    def get_events(self) -> List[dict]:
        return list(self.events)

    # --- Seed data loading ---

    def load_seed_data(self, path: str | Path) -> None:
        path = Path(path)
        if not path.exists():
            return
        with open(path, "r") as f:
            data = json.load(f)

        for channel in data.get("channels", []):
            self.channels[channel["id"]] = channel

        for user in data.get("users", []):
            self.users[user["id"]] = user

        for msg in data.get("messages", []):
            channel = msg["channel"]
            if channel not in self.messages:
                self.messages[channel] = []
            self.messages[channel].append({
                "channel": msg["channel"],
                "user": msg["user"],
                "text": msg["text"],
                "ts": msg["ts"],
                "thread_ts": msg.get("thread_ts"),
                "type": "message",
            })
            # Track ts counter to avoid collisions with seed data
            try:
                ts_parts = msg["ts"].split(".")
                counter = int(ts_parts[1]) if len(ts_parts) > 1 else 0
                if counter > self._ts_counter:
                    self._ts_counter = counter
            except (ValueError, IndexError):
                pass


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
