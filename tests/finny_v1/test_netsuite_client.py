"""Tests for Finny V1 NetSuite client and auth strategies."""

from __future__ import annotations

import pytest

from p2p_agents.finny_v1.contracts import Confidence, PaymentStatus, PendingStage
from p2p_agents.finny_v1.netsuite_client import MockAuth, NetSuiteClient, OAuth2Auth


# --- Auth strategy tests ---


class TestMockAuth:
    def test_default_headers(self):
        auth = MockAuth()
        headers = auth.get_headers()
        assert headers["Authorization"] == "Bearer mock-netsuite-token-finny-dev"

    def test_custom_token_id(self):
        auth = MockAuth(token_id="test-123")
        headers = auth.get_headers()
        assert headers["Authorization"] == "Bearer mock-netsuite-token-test-123"


class TestOAuth2Auth:
    def test_placeholder_headers(self):
        auth = OAuth2Auth()
        headers = auth.get_headers()
        assert "Bearer" in headers["Authorization"]


# --- NetSuiteClient tests (require running mock server on :8081) ---


@pytest.fixture
def client():
    """Client configured to talk to the NetSuite mock server."""
    return NetSuiteClient(
        base_url="http://localhost:8081",
        auth=MockAuth(),
    )


@pytest.mark.skipif(
    True,
    reason="Requires running mock server: uvicorn mock_servers.netsuite_mock.app:app --port 8081",
)
class TestNetSuiteClientIntegration:
    """Integration tests — run with mock server active."""

    def test_get_vendor_bill_found(self, client):
        result = client.get_vendor_bill("INV-2024-001")
        assert result is not None
        assert result.invoice_number == "INV-2024-001"
        assert result.payment_status == PaymentStatus.PAID

    def test_get_vendor_bill_not_found(self, client):
        result = client.get_vendor_bill("NONEXISTENT-999")
        assert result is None

    def test_get_vendor_by_name_single(self, client):
        vendors = client.get_vendor_by_name("Google")
        assert len(vendors) >= 1
        assert any("Google" in v.get("companyName", "") for v in vendors)

    def test_get_vendor_by_name_no_match(self, client):
        vendors = client.get_vendor_by_name("ZZZNonexistentVendor999")
        assert len(vendors) == 0

    def test_normalize_bill_paid(self, client):
        bill = {
            "id": "1001",
            "entity": {"id": "1", "refName": "Google LLC"},
            "tranId": "INV-2024-001",
            "tranDate": "2024-01-15",
            "dueDate": "2024-02-14",
            "amount": 1250000.00,
            "currency": {"id": "1", "refName": "INR"},
            "approvalStatus": "approved",
            "status": "paid",
            "memo": "GCP Services",
        }
        result = client._normalize_bill(bill)
        assert result.payment_status == PaymentStatus.PAID
        assert result.vendor_name == "Google LLC"
        assert result.confidence == Confidence.HIGH

    def test_normalize_bill_pending_l1(self, client):
        bill = {
            "id": "5002",
            "entity": {"id": "202", "refName": "Tencent Cloud"},
            "tranId": "INV-2024-002",
            "tranDate": "2024-02-01",
            "dueDate": "2024-03-02",
            "amount": 675000.00,
            "currency": {"id": "1", "refName": "INR"},
            "approvalStatus": "pendingApproval",
            "status": "open",
            "memo": "Cloud Infra - L1 pending",
        }
        result = client._normalize_bill(bill)
        assert result.payment_status == PaymentStatus.PENDING_APPROVAL
        assert result.pending_stage == PendingStage.L1


# --- Unit tests for normalization (no server needed) ---


class TestNormalizeBill:
    """Unit tests for bill normalization logic."""

    @pytest.fixture
    def client(self):
        return NetSuiteClient(base_url="http://localhost:8081", auth=MockAuth())

    def test_paid_status(self, client):
        bill = {
            "entity": {"refName": "Test Vendor"},
            "tranId": "INV-001",
            "amount": 100.0,
            "currency": {"refName": "INR"},
            "dueDate": "2024-01-01",
            "approvalStatus": "approved",
            "status": "paid",
            "memo": "",
        }
        result = client._normalize_bill(bill)
        assert result.payment_status == PaymentStatus.PAID
        assert result.pending_stage == PendingStage.NA
        assert "No action" in result.next_action

    def test_pending_l2(self, client):
        bill = {
            "entity": {"refName": "Test Vendor"},
            "tranId": "INV-002",
            "amount": 200.0,
            "currency": {"refName": "INR"},
            "dueDate": "2024-02-01",
            "approvalStatus": "pendingApproval",
            "status": "open",
            "memo": "L2 approval needed",
        }
        result = client._normalize_bill(bill)
        assert result.payment_status == PaymentStatus.PENDING_APPROVAL
        assert result.pending_stage == PendingStage.L2

    def test_pending_treasury(self, client):
        bill = {
            "entity": {"refName": "Test Vendor"},
            "tranId": "INV-003",
            "amount": 300.0,
            "currency": {"refName": "INR"},
            "dueDate": "2024-03-01",
            "approvalStatus": "pendingApproval",
            "status": "open",
            "memo": "Treasury sign-off pending",
        }
        result = client._normalize_bill(bill)
        assert result.pending_stage == PendingStage.TREASURY

    def test_scheduled_status(self, client):
        bill = {
            "entity": {"refName": "Test Vendor"},
            "tranId": "INV-004",
            "amount": 400.0,
            "currency": {"refName": "INR"},
            "dueDate": "2024-04-01",
            "approvalStatus": "approved",
            "status": "scheduled",
            "memo": "",
        }
        result = client._normalize_bill(bill)
        assert result.payment_status == PaymentStatus.SCHEDULED

    def test_overdue_maps_to_processing(self, client):
        bill = {
            "entity": {"refName": "Test Vendor"},
            "tranId": "INV-005",
            "amount": 500.0,
            "currency": {"refName": "INR"},
            "dueDate": "2024-01-01",
            "approvalStatus": "approved",
            "status": "overdue",
            "memo": "",
        }
        result = client._normalize_bill(bill)
        assert result.payment_status == PaymentStatus.PROCESSING
