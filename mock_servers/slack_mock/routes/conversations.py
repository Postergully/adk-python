"""Conversations method endpoints.

Implements:
    GET /api/conversations.history
    GET /api/conversations.replies
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from mock_servers.slack_mock.db import get_db

router = APIRouter(tags=["Conversations"])


@router.get("/conversations.history")
async def conversations_history(
    channel: str = Query(..., description="Channel ID"),
    limit: int = Query(100, description="Max messages to return"),
):
    db = get_db()

    ch = db.get_channel(channel)
    if ch is None:
        return {"ok": False, "error": "channel_not_found"}

    messages = db.get_messages(channel, limit=limit)
    return {
        "ok": True,
        "messages": messages,
        "has_more": False,
    }


@router.get("/conversations.replies")
async def conversations_replies(
    channel: str = Query(..., description="Channel ID"),
    ts: str = Query(..., description="Thread parent timestamp"),
):
    db = get_db()

    ch = db.get_channel(channel)
    if ch is None:
        return {"ok": False, "error": "channel_not_found"}

    messages = db.get_thread_replies(channel, ts)
    return {
        "ok": True,
        "messages": messages,
        "has_more": False,
    }
