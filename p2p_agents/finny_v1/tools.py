"""Finny V1 tools — payment status lookup, pending approvals, approval reminders."""
from __future__ import annotations

from p2p_agents.config.settings import get_settings
from p2p_agents.finny_v1.netsuite_client import NetSuiteClient, MockAuth


def _get_client() -> NetSuiteClient:
    settings = get_settings()
    return NetSuiteClient(
        base_url=settings.netsuite_base_url,
        auth=MockAuth(),
    )


def get_payment_status(invoice_number: str = "", vendor_name: str = "") -> dict:
    """Look up the payment status of an invoice or vendor.

    Provide either invoice_number OR vendor_name.
    If vendor_name matches multiple vendors, returns a disambiguation prompt
    WITHOUT disclosing other vendor names (privacy requirement).

    Args:
        invoice_number: The invoice/bill number (e.g. "INV-2024-001")
        vendor_name: The vendor/company name to search by

    Returns:
        dict with payment status details or disambiguation request
    """
    client = _get_client()

    if invoice_number:
        result = client.get_vendor_bill(invoice_number)
        if result is None:
            return {
                "status": "not_found",
                "message": f"No invoice found with number '{invoice_number}'. Please verify the invoice number.",
            }
        return result.model_dump()

    if vendor_name:
        vendors = client.get_vendor_by_name(vendor_name)
        if not vendors:
            return {
                "status": "not_found",
                "message": f"No vendor found matching '{vendor_name}'. Please check the name and try again.",
            }

        if len(vendors) > 1:
            # PRIVACY: never disclose other vendor names
            return {
                "status": "disambiguation_needed",
                "message": (
                    f"Multiple vendors match '{vendor_name}'. "
                    "Could you provide the invoice number instead, "
                    "or confirm the exact vendor name?"
                ),
                "match_count": len(vendors),
            }

        # Single vendor match — get their latest bills
        vendor = vendors[0]
        vendor_id = vendor.get("id", "")
        bills = client.get_vendor_bills_by_vendor_id(vendor_id)
        if not bills:
            return {
                "status": "no_bills",
                "message": f"No outstanding invoices found for {vendor.get('companyName', vendor_name)}.",
            }

        # Return the most recent bill's status
        latest = sorted(bills, key=lambda b: b.get("tranDate", ""), reverse=True)[0]
        result = client._normalize_bill(latest)
        return result.model_dump()

    return {"status": "error", "message": "Please provide an invoice number or vendor name."}


def get_pending_approvals() -> dict:
    """Get all vendor bills currently pending approval, grouped by approval stage.

    Returns:
        dict with pending bills grouped by stage (L1, L2, Treasury)
    """
    client = _get_client()

    # Query all pending bills
    bills = client.search_suiteql(
        "SELECT * FROM vendorBill WHERE approvalStatus = 'pendingApproval'"
    )

    if not bills:
        return {"status": "ok", "message": "No pending approvals found.", "stages": {}}

    stages: dict[str, list[dict]] = {"L1": [], "L2": [], "Treasury": []}

    for bill in bills:
        memo = (bill.get("memo") or "").lower()
        entity = bill.get("entity", {})
        vendor_name = entity.get("refName", "") if isinstance(entity, dict) else ""

        entry = {
            "invoice_number": bill.get("tranId", ""),
            "vendor_name": vendor_name,
            "amount": bill.get("amount", 0),
            "due_date": str(bill.get("dueDate", "")),
            "bill_id": bill.get("id", ""),
        }

        if "l2" in memo:
            stages["L2"].append(entry)
        elif "treasury" in memo:
            stages["Treasury"].append(entry)
        else:
            stages["L1"].append(entry)

    total = sum(len(v) for v in stages.values())
    return {
        "status": "ok",
        "total_pending": total,
        "stages": stages,
    }


def send_approval_reminder(approver_name: str, transaction_ids: str = "") -> dict:
    """Send an approval reminder for pending transactions.

    This is a text-based confirmation flow: the bot will ask the user to confirm
    before actually sending the reminder via Slack and email.

    Args:
        approver_name: Name of the approver to remind
        transaction_ids: Comma-separated list of bill/transaction IDs to remind about

    Returns:
        dict with confirmation prompt or result
    """
    if not approver_name:
        return {"status": "error", "message": "Please provide the approver's name."}

    ids = [t.strip() for t in transaction_ids.split(",") if t.strip()] if transaction_ids else []

    if not ids:
        return {
            "status": "confirmation_needed",
            "message": (
                f"I'll send a reminder to {approver_name} for all their pending approvals. "
                "Reply 'yes' to confirm or provide specific transaction IDs."
            ),
        }

    return {
        "status": "confirmation_needed",
        "message": (
            f"I'll send a reminder to {approver_name} for transactions: {', '.join(ids)}. "
            "Reply 'yes' to confirm."
        ),
        "approver_name": approver_name,
        "transaction_ids": ids,
    }
