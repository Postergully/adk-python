"""Tests for Slack mock server."""

from __future__ import annotations

import pytest

# These tests require the Slack mock server running on :8083
# Start with: uvicorn mock_servers.slack_mock.app:app --port 8083

pytestmark = pytest.mark.skipif(
    True,
    reason="Requires running Slack mock: uvicorn mock_servers.slack_mock.app:app --port 8083",
)


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
