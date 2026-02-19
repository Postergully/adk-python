"""Event and auth endpoints.

Implements:
    POST /slack/events   — inject test events
    GET  /slack/events   — retrieve injected events
    POST /api/auth.test  — mock bot identity
"""

from __future__ import annotations

from fastapi import APIRouter

from mock_servers.slack_mock.db import get_db
from mock_servers.slack_mock.models import SlackAuthTestResponse, SlackEvent

router = APIRouter(tags=["Events"])


@router.post("/events")
async def inject_event(body: SlackEvent):
    """Inject a test event for later retrieval."""
    db = get_db()
    event = db.store_event(body.model_dump())
    return {"ok": True, "event": event}


@router.get("/events")
async def list_events():
    """Return all injected events (for test assertions)."""
    db = get_db()
    return {"ok": True, "events": db.get_events()}
