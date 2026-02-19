"""Slack API Mock Server.

FastAPI application implementing a subset of the Slack Web API
for local development and testing of P2P ShareChat agents.

Start with:
    uvicorn mock_servers.slack_mock.app:app --port 8083
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mock_servers.slack_mock.auth import SlackAuthMiddleware
from mock_servers.slack_mock.db import get_db
from mock_servers.slack_mock.models import SlackAuthTestResponse
from mock_servers.slack_mock.routes.chat import router as chat_router
from mock_servers.slack_mock.routes.conversations import router as conversations_router
from mock_servers.slack_mock.routes.events import router as events_router

app = FastAPI(
    title="Slack API Mock",
    description="Mock implementation of Slack Web API for P2P agent development",
    version="1.0.0-mock",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth
app.add_middleware(SlackAuthMiddleware)

# Routes
app.include_router(chat_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")
app.include_router(events_router, prefix="/slack")


# auth.test lives under /api but is separate from the events router
@app.post("/api/auth.test")
async def auth_test():
    """Return mock bot identity."""
    return SlackAuthTestResponse()


@app.get("/")
async def root():
    return {
        "type": "mock",
        "name": "Slack API Mock",
        "version": "1.0.0",
        "endpoints": [
            "/api/chat.postMessage",
            "/api/chat.update",
            "/api/conversations.history",
            "/api/conversations.replies",
            "/api/auth.test",
            "/slack/events",
        ],
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
