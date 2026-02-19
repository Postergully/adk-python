"""Tests for sandbox helper functions."""

from __future__ import annotations

import httpx
from unittest.mock import patch

from scripts.finny_sandbox import _get_messages, _get_thread_replies


def _make_response(status_code: int, json_data: dict) -> httpx.Response:
    """Build an httpx.Response with a dummy request so raise_for_status works."""
    resp = httpx.Response(status_code, json=json_data)
    resp._request = httpx.Request("GET", "http://test")
    return resp


class TestGetMessages:
    """Verify _get_messages calls conversations.history."""

    def test_returns_messages_from_history(self):
        mock_response = {"ok": True, "messages": [{"ts": "1.0", "text": "hello"}]}
        with httpx.Client() as client:
            with patch.object(client, "get") as mock_get:
                mock_get.return_value = _make_response(200, mock_response)
                result = _get_messages(client, "http://localhost:8083", "C001")
        assert result == [{"ts": "1.0", "text": "hello"}]

    def test_returns_empty_list_when_no_messages(self):
        mock_response = {"ok": True}
        with httpx.Client() as client:
            with patch.object(client, "get") as mock_get:
                mock_get.return_value = _make_response(200, mock_response)
                result = _get_messages(client, "http://localhost:8083", "C001")
        assert result == []


class TestGetThreadReplies:
    """Verify _get_thread_replies calls conversations.replies."""

    def test_returns_thread_messages(self):
        mock_response = {
            "ok": True,
            "messages": [
                {"ts": "1.0", "text": "parent", "thread_ts": None},
                {"ts": "1.1", "text": "reply", "thread_ts": "1.0"},
            ],
        }
        with httpx.Client() as client:
            with patch.object(client, "get") as mock_get:
                mock_get.return_value = _make_response(200, mock_response)
                result = _get_thread_replies(
                    client, "http://localhost:8083", "C001", "1.0",
                )
        assert len(result) == 2
        assert result[1]["text"] == "reply"

    def test_returns_empty_list_when_no_replies(self):
        mock_response = {"ok": True, "messages": []}
        with httpx.Client() as client:
            with patch.object(client, "get") as mock_get:
                mock_get.return_value = _make_response(200, mock_response)
                result = _get_thread_replies(
                    client, "http://localhost:8083", "C001", "1.0",
                )
        assert result == []
