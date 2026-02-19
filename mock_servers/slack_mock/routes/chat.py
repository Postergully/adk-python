"""Chat method endpoints.

Implements:
    POST /api/chat.postMessage
    POST /api/chat.update
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from mock_servers.slack_mock.db import get_db
from mock_servers.slack_mock.models import (
    SlackMessage,
    SlackPostMessageRequest,
    SlackPostMessageResponse,
    SlackUpdateMessageRequest,
    SlackUpdateMessageResponse,
)

router = APIRouter(tags=["Chat"])


@router.post("/chat.postMessage")
async def post_message(body: SlackPostMessageRequest):
    db = get_db()

    # Verify channel exists
    channel = db.get_channel(body.channel)
    if channel is None:
        return {"ok": False, "error": "channel_not_found"}

    message = db.post_message(
        channel=body.channel,
        user="U002",  # Bot user by default
        text=body.text,
        thread_ts=body.thread_ts,
    )

    return SlackPostMessageResponse(
        ok=True,
        channel=message["channel"],
        ts=message["ts"],
        message=SlackMessage(**message),
    )


@router.post("/chat.update")
async def update_message(body: SlackUpdateMessageRequest):
    db = get_db()

    updated = db.update_message(
        channel=body.channel,
        ts=body.ts,
        text=body.text,
    )

    if updated is None:
        return {"ok": False, "error": "message_not_found"}

    return SlackUpdateMessageResponse(
        ok=True,
        channel=updated["channel"],
        ts=updated["ts"],
        text=updated["text"],
    )
