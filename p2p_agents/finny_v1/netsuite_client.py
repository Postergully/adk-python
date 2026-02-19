"""NetSuite connector for Finny V1 with pluggable auth strategy."""
from __future__ import annotations

import httpx
from abc import ABC, abstractmethod
from typing import Optional

from p2p_agents.finny_v1.contracts import (
    PaymentStatusResponse, PaymentStatus, PendingStage, Confidence,
)


class AuthStrategy(ABC):
    @abstractmethod
    def get_headers(self) -> dict[str, str]: ...


class MockAuth(AuthStrategy):
    """Bearer mock-netsuite-token-* for development."""
    def __init__(self, token_id: str = "finny-dev"):
        self._token_id = token_id
    def get_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer mock-netsuite-token-{self._token_id}"}


class OAuth2Auth(AuthStrategy):
    """OAuth 2.0 for production NetSuite."""
    def __init__(self, client_id: str = "", client_secret: str = "", token_url: str = ""):
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_url = token_url
        self._access_token: str = ""

    def get_headers(self) -> dict[str, str]:
        # Production OAuth flow — placeholder for V1
        if not self._access_token:
            self._access_token = "oauth2-placeholder-token"
        return {"Authorization": f"Bearer {self._access_token}"}


class NetSuiteClient:
    def __init__(self, base_url: str, auth: AuthStrategy):
        self._base_url = base_url.rstrip("/")
        self._auth = auth

    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=15.0)

    def _get(self, path: str, params: dict | None = None) -> dict:
        with self._client() as c:
            r = c.get(f"{self._base_url}{path}", headers=self._auth.get_headers(), params=params)
            r.raise_for_status()
            return r.json()

    def _post(self, path: str, json_body: dict | None = None) -> dict:
        with self._client() as c:
            r = c.post(f"{self._base_url}{path}", headers=self._auth.get_headers(), json=json_body)
            r.raise_for_status()
            return r.json()

    def get_vendor_bill(self, invoice_number: str) -> Optional[PaymentStatusResponse]:
        """Look up a vendor bill by invoice number (tranId)."""
        data = self._get("/record/v1/vendorBill", params={"q": f"tranId='{invoice_number}'"})
        items = data.get("items", [])
        if not items:
            return None
        bill = items[0]
        return self._normalize_bill(bill)

    def get_vendor_by_name(self, name: str) -> list[dict]:
        """Search vendors by company name (LIKE match)."""
        data = self._get("/record/v1/vendor", params={"q": f"companyName LIKE '%{name}%'"})
        return data.get("items", [])

    def get_vendor_bills_by_vendor_id(self, vendor_id: str) -> list[dict]:
        """Get all bills for a vendor."""
        data = self._get("/record/v1/vendorBill", params={"q": f"entity.id='{vendor_id}'"})
        return data.get("items", [])

    def get_vendor_payments(self, vendor_id: str) -> list[dict]:
        """Get payment records for a vendor."""
        data = self._get("/record/v1/vendorPayment", params={"q": f"entity.id='{vendor_id}'"})
        return data.get("items", [])

    def search_suiteql(self, query: str) -> list[dict]:
        """Execute a SuiteQL query."""
        data = self._post("/query/v1/suiteql", json_body={"q": query})
        return data.get("items", [])

    def _normalize_bill(self, bill: dict) -> PaymentStatusResponse:
        """Convert a raw NetSuite vendor bill to PaymentStatusResponse."""
        status_raw = (bill.get("status") or "").lower()
        approval_raw = (bill.get("approvalStatus") or "").lower()

        # Map status
        if status_raw == "paid":
            payment_status = PaymentStatus.PAID
        elif status_raw in ("open", "pendingapproval"):
            payment_status = PaymentStatus.PENDING_APPROVAL
        elif "scheduled" in status_raw:
            payment_status = PaymentStatus.SCHEDULED
        elif "processing" in status_raw or status_raw == "overdue":
            payment_status = PaymentStatus.PROCESSING
        else:
            payment_status = PaymentStatus.NOT_FOUND

        # Map pending stage
        pending_stage = PendingStage.NA
        if payment_status == PaymentStatus.PENDING_APPROVAL:
            # Derive from approval status or memo
            memo = (bill.get("memo") or "").lower()
            if "l2" in memo or "l2" in approval_raw:
                pending_stage = PendingStage.L2
            elif "treasury" in memo:
                pending_stage = PendingStage.TREASURY
            else:
                pending_stage = PendingStage.L1

        entity = bill.get("entity", {})
        vendor_name = entity.get("refName", "") if isinstance(entity, dict) else ""

        return PaymentStatusResponse(
            vendor_name=vendor_name,
            invoice_number=bill.get("tranId", ""),
            amount=float(bill.get("amount", 0)),
            currency=bill.get("currency", {}).get("refName", "INR") if isinstance(bill.get("currency"), dict) else "INR",
            due_date=str(bill.get("dueDate", "")),
            payment_status=payment_status,
            approval_status=bill.get("approvalStatus", ""),
            pending_stage=pending_stage,
            next_action=self._derive_next_action(payment_status, pending_stage),
            confidence=Confidence.HIGH,
        )

    @staticmethod
    def _derive_next_action(status: PaymentStatus, stage: PendingStage) -> str:
        if status == PaymentStatus.PAID:
            return "No action needed — payment completed."
        if status == PaymentStatus.PENDING_APPROVAL:
            return f"Awaiting {stage.value} approval. You can send a reminder to the approver."
        if status == PaymentStatus.SCHEDULED:
            return "Payment is scheduled. It will be processed on the scheduled date."
        if status == PaymentStatus.PROCESSING:
            return "Payment is being processed. Check back later for confirmation."
        return "Invoice not found. Please verify the invoice number or vendor name."
