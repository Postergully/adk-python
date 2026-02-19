"""Tests for Slack mock server."""

from __future__ import annotations

import httpx
import pytest

# These tests require the Slack mock server running on :8083
# Start with: uvicorn mock_servers.slack_mock.app:app --port 8083

_skip_needs_server = pytest.mark.skipif(
    True,
    reason="Requires running Slack mock: uvicorn mock_servers.slack_mock.app:app --port 8083",
)


@_skip_needs_server
class TestSlackMockChatPostMessage:
    """Test chat.postMessage stores and returns messages."""

    def test_post_message(self):
        import httpx

        resp = httpx.post(
            "http://localhost:8083/api/chat.postMessage",
            json={"channel": "C001", "text": "Hello from test"},
            headers={"Authorization": "Bearer xoxb-mock-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["channel"] == "C001"
        assert "ts" in data

    def test_post_threaded_message(self):
        import httpx

        headers = {"Authorization": "Bearer xoxb-mock-token"}

        # Post parent
        parent = httpx.post(
            "http://localhost:8083/api/chat.postMessage",
            json={"channel": "C001", "text": "Parent message"},
            headers=headers,
        ).json()
        parent_ts = parent["ts"]

        # Post reply
        reply = httpx.post(
            "http://localhost:8083/api/chat.postMessage",
            json={
                "channel": "C001",
                "text": "Reply message",
                "thread_ts": parent_ts,
            },
            headers=headers,
        ).json()
        assert reply["ok"] is True


@_skip_needs_server
class TestSlackMockConversationsHistory:
    def test_get_history(self):
        import httpx

        headers = {"Authorization": "Bearer xoxb-mock-token"}
        resp = httpx.get(
            "http://localhost:8083/api/conversations.history",
            params={"channel": "C001"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "messages" in data


@_skip_needs_server
class TestSlackMockConversationsReplies:
    def test_get_thread(self):
        import httpx

        headers = {"Authorization": "Bearer xoxb-mock-token"}

        # First post a parent message
        parent = httpx.post(
            "http://localhost:8083/api/chat.postMessage",
            json={"channel": "C001", "text": "Thread parent"},
            headers=headers,
        ).json()

        resp = httpx.get(
            "http://localhost:8083/api/conversations.replies",
            params={"channel": "C001", "ts": parent["ts"]},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "messages" in data


# ---------------------------------------------------------------------------
# Tests that run without a live server (using ASGI transport)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestThreadReplyVisibility:
    """Threaded replies must appear in conversations.replies, not history.

    These tests use ASGI transport so they do not require a running Slack mock.
    """

    @pytest.fixture(autouse=True)
    async def _reset_db(self):
        from mock_servers.slack_mock.db import reset_db

        reset_db()
        yield
        reset_db()

    @pytest.fixture
    async def client(self):
        from mock_servers.slack_mock.app import app

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"Authorization": "Bearer xoxb-mock-token"},
        ) as c:
            yield c

    async def test_threaded_reply_excluded_from_history(self, client):
        # Post parent message
        parent = await client.post(
            "/api/chat.postMessage",
            json={"channel": "C001", "text": "user question"},
        )
        parent_ts = parent.json()["ts"]

        # Post threaded reply (simulates agent response)
        await client.post(
            "/api/chat.postMessage",
            json={"channel": "C001", "text": "agent answer", "thread_ts": parent_ts},
        )

        # conversations.history should NOT contain the threaded reply
        history = await client.get(
            "/api/conversations.history", params={"channel": "C001"}
        )
        history_texts = [m["text"] for m in history.json()["messages"]]
        assert "agent answer" not in history_texts
        assert "user question" in history_texts

    async def test_threaded_reply_included_in_conversations_replies(self, client):
        # Post parent message
        parent = await client.post(
            "/api/chat.postMessage",
            json={"channel": "C001", "text": "user question"},
        )
        parent_ts = parent.json()["ts"]

        # Post threaded reply
        await client.post(
            "/api/chat.postMessage",
            json={"channel": "C001", "text": "agent answer", "thread_ts": parent_ts},
        )

        # conversations.replies SHOULD contain the threaded reply
        replies = await client.get(
            "/api/conversations.replies",
            params={"channel": "C001", "ts": parent_ts},
        )
        reply_texts = [m["text"] for m in replies.json()["messages"]]
        assert "user question" in reply_texts  # parent included
        assert "agent answer" in reply_texts  # reply included
