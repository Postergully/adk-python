"""Payment agent tools — status lookups, approvals, reimbursements, notifications."""

from __future__ import annotations

from p2p_agents.config.constants import (
    APPROVAL_REMINDER_THRESHOLD_DAYS,
    PRIORITY_VENDORS,
    REIMBURSEMENT_AUTO_APPROVE_LIMIT,
)
from p2p_agents.tools.helpers import ns_get, ns_post, send_email, send_slack_message


# ── Tool 1 ───────────────────────────────────────────────────────────────────
def get_payment_status(invoice_number: str = "", vendor_name: str = "") -> dict:
    """Retrieves payment status from NetSuite by invoice number or vendor name.

    Args:
        invoice_number: Invoice number to look up, e.g. "INV-2024-001".
        vendor_name: Vendor name to search, e.g. "Google".

    Returns:
        dict with payment details including status, amount, dates, and vendor.
    """
    if invoice_number:
        bills = ns_get("/record/v1/vendorBill", params={"q": f"tranId='{invoice_number}'"})
        if isinstance(bills, list) and bills:
            bill = bills[0]
            payments = ns_get("/record/v1/vendorPayment", params={"q": f"entity.id='{bill.get('entity', {}).get('id', '')}'"})
            return {
                "invoice_number": bill.get("tranId"),
                "vendor_id": bill.get("entity", {}).get("id"),
                "amount": bill.get("amount"),
                "due_date": bill.get("dueDate"),
                "bill_status": bill.get("approvalStatus"),
                "payments": payments if isinstance(payments, list) else [],
            }
        return {"error": f"No invoice found with number {invoice_number}"}
    elif vendor_name:
        vendors = ns_get("/record/v1/vendor", params={"q": f"companyName LIKE '{vendor_name}%'"})
        if isinstance(vendors, list) and vendors:
            vendor = vendors[0]
            payments = ns_get("/record/v1/vendorPayment", params={"q": f"entity.id='{vendor.get('id', '')}'"})
            return {
                "vendor_name": vendor.get("companyName"),
                "vendor_id": vendor.get("id"),
                "payments": payments if isinstance(payments, list) else [],
            }
        return {"error": f"No vendor found matching '{vendor_name}'"}
    return {"error": "Provide either invoice_number or vendor_name"}


# ── Tool 2 ───────────────────────────────────────────────────────────────────
def get_pending_approvals() -> dict:
    """Retrieves all transactions pending approval from NetSuite.

    Returns:
        dict with lists of pending vendor bills, payments, and expenses.
    """
    bills = ns_get("/record/v1/vendorBill", params={"q": "approvalStatus='pendingApproval'"})
    payments = ns_get("/record/v1/vendorPayment", params={"q": "status='pendingApproval'"})
    expenses = ns_get("/record/v1/expense", params={"q": "approvalStatus='pendingApproval'"})
    return {
        "pending_bills": bills if isinstance(bills, list) else [],
        "pending_payments": payments if isinstance(payments, list) else [],
        "pending_expenses": expenses if isinstance(expenses, list) else [],
        "total_pending": (
            (len(bills) if isinstance(bills, list) else 0)
            + (len(payments) if isinstance(payments, list) else 0)
            + (len(expenses) if isinstance(expenses, list) else 0)
        ),
    }


# ── Tool 3 ───────────────────────────────────────────────────────────────────
def send_approval_reminder(approver_name: str, transaction_ids: list[str]) -> dict:
    """Sends a Slack/email reminder to an approver about pending transactions.

    Args:
        approver_name: Name of the person who needs to approve.
        transaction_ids: List of transaction IDs waiting for approval.

    Returns:
        dict confirming reminder was sent with count of transactions.
    """
    msg = (
        f"Reminder: {len(transaction_ids)} transactions are waiting for your approval: "
        f"{', '.join(transaction_ids)}. Please review in NetSuite."
    )
    slack_result = send_slack_message(f"@{approver_name}: {msg}")
    email_result = send_email(
        to=f"{approver_name.lower().replace(' ', '.')}@sharechat.com",
        subject=f"Action Required: {len(transaction_ids)} pending approvals",
        body=msg,
    )
    return {
        "approver": approver_name,
        "transactions_count": len(transaction_ids),
        "slack": slack_result,
        "email": email_result,
    }


# ── Tool 4 ───────────────────────────────────────────────────────────────────
def send_payment_delay_email(
    vendor_name: str, vendor_type: str, amount: float, days_overdue: int
) -> dict:
    """Sends a payment delay notification email to a vendor.

    Args:
        vendor_name: Name of the vendor to notify.
        vendor_type: Either "MSME" or "foreign" to select the right template.
        amount: Outstanding payment amount.
        days_overdue: Number of days the payment is overdue.

    Returns:
        dict confirming email was sent with vendor and amount details.
    """
    if vendor_type.upper() == "MSME":
        subject = f"Payment Update - {vendor_name}"
        body = (
            f"Dear {vendor_name},\n\n"
            f"We acknowledge the pending payment of INR {amount:,.2f} which is "
            f"{days_overdue} days past due. We are processing this on priority "
            f"as per MSME guidelines. Expected resolution within 5 business days.\n\n"
            f"Regards,\nShareChat Finance Team"
        )
    else:
        subject = f"Payment Status Update - {vendor_name}"
        body = (
            f"Dear {vendor_name},\n\n"
            f"This is to inform you that the payment of {amount:,.2f} is currently "
            f"being processed. We expect completion within 7-10 business days.\n\n"
            f"Regards,\nShareChat Finance Team"
        )
    return send_email(to=f"ap@{vendor_name.lower().replace(' ', '')}.com", subject=subject, body=body)


# ── Tool 5 ───────────────────────────────────────────────────────────────────
def get_priority_vendor_list() -> dict:
    """Returns the list of priority vendors for ShareChat.

    Returns:
        dict with the list of priority vendor names.
    """
    return {"priority_vendors": list(PRIORITY_VENDORS)}


# ── Tool 6 ───────────────────────────────────────────────────────────────────
def send_holding_reply(vendor_name: str, invoice_number: str) -> dict:
    """Sends an auto-reply to a priority vendor confirming payment is being processed.

    Args:
        vendor_name: Name of the priority vendor.
        invoice_number: The invoice number they are asking about.

    Returns:
        dict confirming holding reply was sent.
    """
    return send_email(
        to=f"ap@{vendor_name.lower().replace(' ', '')}.com",
        subject=f"Re: Payment Status - {invoice_number}",
        body=(
            f"Dear {vendor_name} Team,\n\n"
            f"Thank you for reaching out regarding invoice {invoice_number}. "
            f"We confirm this is in our payment pipeline and is being processed. "
            f"We will update you within 2 business days.\n\n"
            f"Regards,\nShareChat Finance Team"
        ),
    )


# ── Tool 7 ───────────────────────────────────────────────────────────────────
def get_reimbursement_claims(employee_id: str = "") -> dict:
    """Fetches pending employee reimbursement claims from NetSuite.

    Args:
        employee_id: Optional employee ID to filter claims. Returns all if empty.

    Returns:
        dict with list of reimbursement claims and total count.
    """
    if employee_id:
        params = {"q": f"employee.id='{employee_id}'"}
    else:
        params = {"q": "approvalStatus='pendingApproval'"}
    expenses = ns_get("/record/v1/expense", params=params)
    items = expenses if isinstance(expenses, list) else []
    return {"claims": items, "total": len(items)}


# ── Tool 8 ───────────────────────────────────────────────────────────────────
def process_reimbursement(
    employee_id: str, amount: float, category: str, description: str
) -> dict:
    """Verifies a reimbursement claim against policy and submits it to NetSuite.

    Args:
        employee_id: The employee ID submitting the claim.
        amount: Reimbursement amount in INR.
        category: Expense category, e.g. "travel", "meals", "office_supplies".
        description: Description of the expense.

    Returns:
        dict with approval status and any policy violations.
    """
    violations = []
    if amount <= 0:
        violations.append("Amount must be positive")
    if not description.strip():
        violations.append("Description is required")

    if violations:
        return {"status": "rejected", "violations": violations}

    auto_approved = amount <= REIMBURSEMENT_AUTO_APPROVE_LIMIT
    approval_status = "approved" if auto_approved else "pendingApproval"

    result = ns_post(
        "/record/v1/expense",
        json={
            "employee": {"id": employee_id},
            "tranDate": "2025-01-15",
            "amount": amount,
            "memo": description,
            "category": {"id": category},
            "approvalStatus": approval_status,
            "expenseList": [{"category": {"id": category}, "amount": amount}],
        },
    )
    return {
        "status": approval_status,
        "auto_approved": auto_approved,
        "expense_id": result.get("id"),
        "message": (
            "Approved automatically — within policy limit."
            if auto_approved
            else "Routed to manager for approval — exceeds auto-approve limit."
        ),
    }
