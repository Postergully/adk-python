"""Tests for Finny V1 Slack gateway."""

from __future__ import annotations

import hashlib
import hmac
import json as json_mod
import os
import time

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from p2p_agents.finny_v1.gateway.app import _verify_slack_signature, fastapi_app
from p2p_agents.finny_v1.gateway.event_handler import (
    is_duplicate,
    strip_bot_mention,
    _seen_events,
)
from p2p_agents.finny_v1.rate_limiter import RateLimiter


def _signed_post(client: TestClient, url: str, json_data: dict) -> Response:
    """POST with valid Slack signature headers."""
    body_str = json_mod.dumps(json_data)
    timestamp = str(int(time.time()))
    secret = os.environ.get("P2P_SLACK_SIGNING_SECRET", "mock-signing-secret")
    sig_basestring = f"v0:{timestamp}:{body_str}"
    signature = "v0=" + hmac.new(
        secret.encode("utf-8"),
        sig_basestring.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return client.post(
        url,
        content=body_str,
        headers={
            "Content-Type": "application/json",
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": signature,
        },
    )


@pytest.fixture
def gateway_client():
    return TestClient(fastapi_app)


@pytest.fixture(autouse=True)
def clear_dedup():
    """Clear dedup cache between tests."""
    _seen_events.clear()


# --- Signature verification ---


class TestSlackSignature:
    def test_valid_signature(self):
        secret = "test-signing-secret"
        timestamp = str(int(time.time()))
        body = b'{"type": "event_callback"}'

        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        expected_sig = (
            "v0="
            + hmac.new(
                secret.encode("utf-8"),
                sig_basestring.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
        )

        assert _verify_slack_signature(secret, timestamp, body, expected_sig)

    def test_invalid_signature(self):
        assert not _verify_slack_signature(
            "secret", str(int(time.time())), b"body", "v0=invalid"
        )

    def test_replay_attack_old_timestamp(self):
        secret = "test-signing-secret"
        old_timestamp = str(int(time.time()) - 600)  # 10 minutes old
        body = b"test"

        sig_basestring = f"v0:{old_timestamp}:{body.decode('utf-8')}"
        sig = (
            "v0="
            + hmac.new(
                secret.encode("utf-8"),
                sig_basestring.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
        )

        assert not _verify_slack_signature(secret, old_timestamp, body, sig)

    def test_empty_secret(self):
        assert not _verify_slack_signature("", "123", b"body", "v0=abc")

    def test_empty_signature(self):
        assert not _verify_slack_signature("secret", "123", b"body", "")


# --- URL verification ---


class TestUrlVerification:
    def test_challenge_response(self, gateway_client):
        resp = gateway_client.post(
            "/slack/events",
            json={
                "type": "url_verification",
                "challenge": "test-challenge-token",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["challenge"] == "test-challenge-token"


# --- Event parsing ---


class TestEventParsing:
    def test_app_mention_returns_200(self, gateway_client):
        resp = _signed_post(
            gateway_client,
            "/slack/events",
            {
                "type": "event_callback",
                "event_id": "Ev001",
                "event": {
                    "type": "app_mention",
                    "user": "U001",
                    "text": "<@U002> what is the status of INV-2024-001?",
                    "channel": "C001",
                    "ts": "1700000001.000001",
                },
            },
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_dm_message_returns_200(self, gateway_client):
        resp = _signed_post(
            gateway_client,
            "/slack/events",
            {
                "type": "event_callback",
                "event_id": "Ev002",
                "event": {
                    "type": "message",
                    "channel_type": "im",
                    "user": "U001",
                    "text": "status of INV-2024-001",
                    "channel": "D001",
                    "ts": "1700000002.000001",
                },
            },
        )
        assert resp.status_code == 200

    def test_bot_message_skipped(self, gateway_client):
        resp = _signed_post(
            gateway_client,
            "/slack/events",
            {
                "type": "event_callback",
                "event_id": "Ev003",
                "event": {
                    "type": "message",
                    "channel_type": "im",
                    "bot_id": "B001",
                    "text": "bot reply",
                    "channel": "D001",
                    "ts": "1700000003.000001",
                },
            },
        )
        assert resp.status_code == 200


# --- Idempotency ---


class TestIdempotency:
    def test_duplicate_event_detected(self):
        assert not is_duplicate("Ev100")
        assert is_duplicate("Ev100")  # second call is duplicate

    def test_different_events_not_duplicate(self):
        assert not is_duplicate("Ev200")
        assert not is_duplicate("Ev201")

    def test_dedup_on_retry(self, gateway_client):
        payload = {
            "type": "event_callback",
            "event_id": "Ev300",
            "event": {
                "type": "app_mention",
                "user": "U001",
                "text": "<@U002> test",
                "channel": "C001",
                "ts": "1700000010.000001",
            },
        }
        # First request
        resp1 = _signed_post(gateway_client, "/slack/events", payload)
        assert resp1.status_code == 200

        # Retry — should still return 200 but skip processing
        resp2 = _signed_post(gateway_client, "/slack/events", payload)
        assert resp2.status_code == 200


# --- Rate limiting ---


class TestRateLimiting:
    def test_allows_under_limit(self):
        rl = RateLimiter(max_requests=3, window_seconds=60)
        assert rl.is_allowed("user1")
        assert rl.is_allowed("user1")
        assert rl.is_allowed("user1")

    def test_blocks_over_limit(self):
        rl = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            rl.is_allowed("user1")
        assert not rl.is_allowed("user1")  # 4th request blocked

    def test_different_users_independent(self):
        rl = RateLimiter(max_requests=2, window_seconds=60)
        rl.is_allowed("user1")
        rl.is_allowed("user1")
        assert not rl.is_allowed("user1")
        assert rl.is_allowed("user2")  # different user, still allowed

    def test_remaining_count(self):
        rl = RateLimiter(max_requests=5, window_seconds=60)
        assert rl.remaining("user1") == 5
        rl.is_allowed("user1")
        assert rl.remaining("user1") == 4

    def test_cooldown_message(self):
        rl = RateLimiter()
        msg = rl.cooldown_message("user1")
        assert "rate limit" in msg.lower()

    def test_11th_request_rate_limited(self):
        """Simulates the 10 queries/user/minute rate limit."""
        rl = RateLimiter(max_requests=10, window_seconds=60)
        for _ in range(10):
            assert rl.is_allowed("billing_user")
        assert not rl.is_allowed("billing_user")  # 11th should fail


# --- Strip bot mention ---


class TestStripBotMention:
    def test_strips_mention(self):
        assert strip_bot_mention("<@U002> what is status?") == "what is status?"

    def test_no_mention(self):
        assert strip_bot_mention("what is status?") == "what is status?"

    def test_empty_text(self):
        assert strip_bot_mention("") == ""

    def test_only_mention(self):
        assert strip_bot_mention("<@U002>") == ""


# --- Health endpoint ---


class TestHealthEndpoint:
    def test_health(self, gateway_client):
        resp = gateway_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_root(self, gateway_client):
        resp = gateway_client.get("/")
        assert resp.status_code == 200
        assert "Finny" in resp.json()["name"]
