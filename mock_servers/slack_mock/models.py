"""Slack API models for the mock server.

Based on Slack Web API:
https://api.slack.com/methods
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# --- Message ---

class SlackMessage(BaseModel):
    channel: str
    user: str
    text: str
    ts: str
    thread_ts: Optional[str] = None
    type: str = "message"


# --- Channel ---

class SlackChannel(BaseModel):
    id: str
    name: str
    is_channel: bool = True
    is_im: bool = False


# --- User ---

class SlackUser(BaseModel):
    id: str
    name: str
    real_name: str
    is_bot: bool = False


# --- Request/Response models ---

class SlackPostMessageRequest(BaseModel):
    channel: str
    text: str
    thread_ts: Optional[str] = None


class SlackPostMessageResponse(BaseModel):
    ok: bool = True
    channel: str
    ts: str
    message: SlackMessage


class SlackUpdateMessageRequest(BaseModel):
    channel: str
    ts: str
    text: str


class SlackUpdateMessageResponse(BaseModel):
    ok: bool = True
    channel: str
    ts: str
    text: str


# --- Events ---

class SlackEvent(BaseModel):
    type: str
    event: Dict[str, Any] = Field(default_factory=dict)
    event_id: str
    event_time: int
    team_id: str = "T001"


# --- Auth ---

class SlackAuthTestResponse(BaseModel):
    ok: bool = True
    url: str = "https://mock-workspace.slack.com/"
    team: str = "Mock Workspace"
    user: str = "finny_bot"
    team_id: str = "T001"
    user_id: str = "U002"
    bot_id: str = "B001"
