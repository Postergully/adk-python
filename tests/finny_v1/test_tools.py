"""Tests for Finny V1 tool functions."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from p2p_agents.finny_v1.contracts import (
    Confidence,
    PaymentStatus,
    PaymentStatusResponse,
    PendingStage,
)


# --- Helpers ---


def _make_response(**overrides) -> PaymentStatusResponse:
    defaults = dict(
        vendor_name="Google LLC",
        invoice_number="INV-2024-001",
        amount=1250000.0,
        currency="INR",
        due_date="2024-02-14",
        payment_status=PaymentStatus.PAID,
        approval_status="approved",
        pending_stage=PendingStage.NA,
        next_action="No action needed.",
        confidence=Confidence.HIGH,
    )
    defaults.update(overrides)
    return PaymentStatusResponse(**defaults)


# --- get_payment_status tests ---


class TestGetPaymentStatus:
    @patch("p2p_agents.finny_v1.tools._get_client")
    def test_by_invoice_number_found(self, mock_client_fn):
        from p2p_agents.finny_v1.tools import get_payment_status

        client = MagicMock()
        client.get_vendor_bill.return_value = _make_response()
        mock_client_fn.return_value = client

        result = get_payment_status(invoice_number="INV-2024-001")
        assert result["payment_status"] == "paid"
        assert result["vendor_name"] == "Google LLC"

    @patch("p2p_agents.finny_v1.tools._get_client")
    def test_by_invoice_number_not_found(self, mock_client_fn):
        from p2p_agents.finny_v1.tools import get_payment_status

        client = MagicMock()
        client.get_vendor_bill.return_value = None
        mock_client_fn.return_value = client

        result = get_payment_status(invoice_number="NONEXISTENT")
        assert result["status"] == "not_found"

    @patch("p2p_agents.finny_v1.tools._get_client")
    def test_by_vendor_name_single_match(self, mock_client_fn):
        from p2p_agents.finny_v1.tools import get_payment_status

        client = MagicMock()
        client.get_vendor_by_name.return_value = [
            {"id": "1", "companyName": "Google LLC"}
        ]
        client.get_vendor_bills_by_vendor_id.return_value = [
            {
                "id": "1001",
                "entity": {"id": "1", "refName": "Google LLC"},
                "tranId": "INV-2024-001",
                "tranDate": "2024-01-15",
                "dueDate": "2024-02-14",
                "amount": 1250000.0,
                "currency": {"id": "1", "refName": "INR"},
                "approvalStatus": "approved",
                "status": "paid",
                "memo": "GCP",
            }
        ]
        client._normalize_bill.return_value = _make_response()
        mock_client_fn.return_value = client

        result = get_payment_status(vendor_name="Google")
        assert result["vendor_name"] == "Google LLC"

    @patch("p2p_agents.finny_v1.tools._get_client")
    def test_by_vendor_name_disambiguation(self, mock_client_fn):
        from p2p_agents.finny_v1.tools import get_payment_status

        client = MagicMock()
        client.get_vendor_by_name.return_value = [
            {"id": "1", "companyName": "Google LLC"},
            {"id": "2", "companyName": "Google Cloud India"},
        ]
        mock_client_fn.return_value = client

        result = get_payment_status(vendor_name="Google")
        assert result["status"] == "disambiguation_needed"
        assert result["match_count"] == 2
        # PRIVACY: must not disclose actual vendor names
        assert "Google LLC" not in result["message"]
        assert "Google Cloud India" not in result["message"]

    @patch("p2p_agents.finny_v1.tools._get_client")
    def test_vendor_not_found(self, mock_client_fn):
        from p2p_agents.finny_v1.tools import get_payment_status

        client = MagicMock()
        client.get_vendor_by_name.return_value = []
        mock_client_fn.return_value = client

        result = get_payment_status(vendor_name="ZZZNonexistent")
        assert result["status"] == "not_found"

    def test_no_args_returns_error(self):
        from p2p_agents.finny_v1.tools import get_payment_status

        result = get_payment_status()
        assert result["status"] == "error"


# --- get_pending_approvals tests ---


class TestGetPendingApprovals:
    @patch("p2p_agents.finny_v1.tools._get_client")
    def test_no_pending(self, mock_client_fn):
        from p2p_agents.finny_v1.tools import get_pending_approvals

        client = MagicMock()
        client.search_suiteql.return_value = []
        mock_client_fn.return_value = client

        result = get_pending_approvals()
        assert result["status"] == "ok"
        assert "No pending" in result["message"]

    @patch("p2p_agents.finny_v1.tools._get_client")
    def test_grouped_by_stage(self, mock_client_fn):
        from p2p_agents.finny_v1.tools import get_pending_approvals

        client = MagicMock()
        client.search_suiteql.return_value = [
            {
                "entity": {"refName": "Vendor A"},
                "tranId": "INV-001",
                "amount": 100,
                "dueDate": "2024-01-01",
                "id": "1",
                "approvalStatus": "pendingApproval",
                "memo": "L1 pending",
            },
            {
                "entity": {"refName": "Vendor B"},
                "tranId": "INV-002",
                "amount": 200,
                "dueDate": "2024-02-01",
                "id": "2",
                "approvalStatus": "pendingApproval",
                "memo": "L2 review needed",
            },
            {
                "entity": {"refName": "Vendor C"},
                "tranId": "INV-003",
                "amount": 300,
                "dueDate": "2024-03-01",
                "id": "3",
                "approvalStatus": "pendingApproval",
                "memo": "Treasury sign-off",
            },
        ]
        mock_client_fn.return_value = client

        result = get_pending_approvals()
        assert result["total_pending"] == 3
        assert len(result["stages"]["L1"]) == 1
        assert len(result["stages"]["L2"]) == 1
        assert len(result["stages"]["Treasury"]) == 1


# --- send_approval_reminder tests ---


class TestSendApprovalReminder:
    def test_with_approver_and_ids(self):
        from p2p_agents.finny_v1.tools import send_approval_reminder

        result = send_approval_reminder(
            approver_name="Rahul", transaction_ids="1001,1002"
        )
        assert result["status"] == "confirmation_needed"
        assert "Rahul" in result["message"]
        assert "1001" in result["message"]

    def test_with_approver_no_ids(self):
        from p2p_agents.finny_v1.tools import send_approval_reminder

        result = send_approval_reminder(approver_name="Priya")
        assert result["status"] == "confirmation_needed"
        assert "all their pending" in result["message"]

    def test_no_approver(self):
        from p2p_agents.finny_v1.tools import send_approval_reminder

        result = send_approval_reminder(approver_name="")
        assert result["status"] == "error"
