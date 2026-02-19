"""End-to-end integration test for Finny V1.

Requires both mock servers running:
  uvicorn mock_servers.netsuite_mock.app:app --port 8081
  uvicorn mock_servers.slack_mock.app:app --port 8083
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skipif(
    True,
    reason=(
        "Integration test requires both mock servers running:\n"
        "  uvicorn mock_servers.netsuite_mock.app:app --port 8081\n"
        "  uvicorn mock_servers.slack_mock.app:app --port 8083"
    ),
)


class TestFinnyEndToEnd:
    """Full pipeline: Slack event → agent → NetSuite → Slack reply."""

    def test_payment_status_by_invoice(self):
        """Inject a Slack event asking for payment status by invoice number.

        Expected flow:
        1. POST event to Slack mock's event injection endpoint
        2. Agent processes the query
        3. Agent calls NetSuite mock to look up invoice
        4. Agent posts threaded reply to Slack mock
        """
        import httpx

        headers = {"Authorization": "Bearer xoxb-mock-token"}

        # Simulate: user posts "@finny status of INV-2024-001" in #billing-support
        event_payload = {
            "type": "event_callback",
            "event_id": "Ev_integration_001",
            "event": {
                "type": "app_mention",
                "user": "U001",
                "text": "<@UFINNY> what is the status of INV-2024-001?",
                "channel": "C001",
                "ts": "1700100001.000001",
            },
        }

        # Post to Slack mock's event injection
        resp = httpx.post(
            "http://localhost:8083/slack/events",
            json=event_payload,
            headers=headers,
        )
        assert resp.status_code == 200

    def test_payment_status_by_vendor_name(self):
        """Test vendor name lookup triggers correct flow."""
        import httpx

        headers = {"Authorization": "Bearer xoxb-mock-token"}

        event_payload = {
            "type": "event_callback",
            "event_id": "Ev_integration_002",
            "event": {
                "type": "app_mention",
                "user": "U001",
                "text": "<@UFINNY> payment status for Google",
                "channel": "C001",
                "ts": "1700100002.000001",
            },
        }

        resp = httpx.post(
            "http://localhost:8083/slack/events",
            json=event_payload,
            headers=headers,
        )
        assert resp.status_code == 200

    def test_dm_query(self):
        """Test DM (direct message) query flow."""
        import httpx

        headers = {"Authorization": "Bearer xoxb-mock-token"}

        event_payload = {
            "type": "event_callback",
            "event_id": "Ev_integration_003",
            "event": {
                "type": "message",
                "channel_type": "im",
                "user": "U001",
                "text": "status of INV-2024-004",
                "channel": "D001",
                "ts": "1700100003.000001",
            },
        }

        resp = httpx.post(
            "http://localhost:8083/slack/events",
            json=event_payload,
            headers=headers,
        )
        assert resp.status_code == 200

    def test_pending_approvals_query(self):
        """Test 'show pending approvals' query."""
        import httpx

        headers = {"Authorization": "Bearer xoxb-mock-token"}

        event_payload = {
            "type": "event_callback",
            "event_id": "Ev_integration_004",
            "event": {
                "type": "app_mention",
                "user": "U003",
                "text": "<@UFINNY> show all pending approvals",
                "channel": "C001",
                "ts": "1700100004.000001",
            },
        }

        resp = httpx.post(
            "http://localhost:8083/slack/events",
            json=event_payload,
            headers=headers,
        )
        assert resp.status_code == 200
