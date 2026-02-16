"""Invoice agent tools — OCR, NetSuite entry, format conversion, bank uploads."""

from __future__ import annotations

import json

from p2p_agents.tools.helpers import ns_get, ns_post, send_email


# ── Tool 1 ───────────────────────────────────────────────────────────────────
def extract_invoice_data_ocr(file_content: str) -> dict:
    """Extracts structured data from an invoice using OCR.

    In mock mode returns sample extracted data. In production this would call
    a real OCR service (Google Document AI, Textract, etc.).

    Args:
        file_content: The text content or base64 data of the invoice file.

    Returns:
        dict with extracted fields: vendor_name, invoice_number, amount, date, line_items.
    """
    # Mock OCR: return realistic extracted data
    return {
        "confidence": 0.92,
        "extracted": {
            "vendor_name": "Acme Technologies Pvt Ltd",
            "invoice_number": f"INV-{hash(file_content) % 10000:04d}",
            "amount": 125000.00,
            "currency": "INR",
            "date": "2025-01-10",
            "due_date": "2025-02-09",
            "line_items": [
                {"description": "Cloud Infrastructure Services - Jan 2025", "amount": 100000.00},
                {"description": "Support & Maintenance", "amount": 25000.00},
            ],
            "gst_number": "29AABCA1234E1ZF",
            "pan_number": "AABCA1234E",
        },
        "warnings": [],
    }


# ── Tool 2 ───────────────────────────────────────────────────────────────────
def create_netsuite_invoice(
    vendor_id: str,
    invoice_number: str,
    amount: float,
    date: str,
    due_date: str,
    line_items: list[dict],
) -> dict:
    """Creates a vendor bill (invoice) record in NetSuite.

    Args:
        vendor_id: NetSuite vendor ID.
        invoice_number: The invoice number from the document.
        amount: Total invoice amount.
        date: Invoice date in YYYY-MM-DD format.
        due_date: Due date in YYYY-MM-DD format.
        line_items: List of dicts with 'description' and 'amount' keys.

    Returns:
        dict with the created bill ID and confirmation.
    """
    ns_items = [
        {
            "item": {"id": "10"},
            "description": item.get("description", ""),
            "amount": item.get("amount", 0),
            "account": {"id": "500"},
        }
        for item in line_items
    ]
    result = ns_post(
        "/record/v1/vendorBill",
        json={
            "entity": {"id": vendor_id},
            "tranId": invoice_number,
            "tranDate": date,
            "dueDate": due_date,
            "amount": amount,
            "currency": {"id": "1"},
            "approvalStatus": "pendingApproval",
            "item": ns_items,
        },
    )
    return {
        "status": "created",
        "bill_id": result.get("id"),
        "invoice_number": invoice_number,
        "amount": amount,
    }


# ── Tool 3 ───────────────────────────────────────────────────────────────────
def validate_invoice_data(invoice_data: dict) -> dict:
    """Validates extracted invoice data before entry into NetSuite.

    Args:
        invoice_data: Dict with keys: vendor_name, invoice_number, amount, date, line_items.

    Returns:
        dict with is_valid flag and list of any validation errors.
    """
    errors = []
    required = ["vendor_name", "invoice_number", "amount", "date"]
    for field in required:
        if not invoice_data.get(field):
            errors.append(f"Missing required field: {field}")

    amount = invoice_data.get("amount", 0)
    if isinstance(amount, (int, float)) and amount <= 0:
        errors.append("Amount must be positive")

    line_items = invoice_data.get("line_items", [])
    if line_items:
        line_total = sum(item.get("amount", 0) for item in line_items)
        if abs(line_total - amount) > 0.01:
            errors.append(f"Line items total ({line_total}) does not match invoice amount ({amount})")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "data": invoice_data,
    }


# ── Tool 4 ───────────────────────────────────────────────────────────────────
def convert_document_format(file_content: str, target_format: str) -> dict:
    """Converts a document to the specified target format.

    In mock mode returns a confirmation. In production this would use
    a real conversion service.

    Args:
        file_content: The source document content.
        target_format: Target format, e.g. "pdf", "csv", "xlsx".

    Returns:
        dict with conversion status and output reference.
    """
    supported = {"pdf", "csv", "xlsx", "json", "xml"}
    if target_format.lower() not in supported:
        return {"status": "error", "message": f"Unsupported format: {target_format}. Supported: {supported}"}
    return {
        "status": "converted",
        "target_format": target_format,
        "output_file": f"converted_output.{target_format}",
        "size_bytes": len(file_content) if file_content else 0,
    }


# ── Tool 5 ───────────────────────────────────────────────────────────────────
def generate_bank_upload_file(bank_name: str, payment_ids: list[str] = None) -> dict:
    """Generates a bank-specific upload file for pending payments.

    Args:
        bank_name: Bank name, e.g. "HDFC", "ICICI", "SBI".
        payment_ids: Optional list of specific payment IDs. If empty, fetches all pending.

    Returns:
        dict with file content preview, payment count, and total amount.
    """
    payments = ns_get("/record/v1/vendorPayment")
    if not isinstance(payments, list):
        payments = []

    if payment_ids:
        payments = [p for p in payments if p.get("id") in payment_ids]

    total = sum(p.get("amount", 0) for p in payments)
    rows = []
    for p in payments:
        rows.append({
            "payment_id": p.get("id"),
            "vendor_id": p.get("entity", {}).get("id"),
            "amount": p.get("amount"),
            "date": p.get("tranDate"),
        })

    return {
        "status": "generated",
        "bank": bank_name,
        "format": f"{bank_name.upper()}_NEFT_FORMAT",
        "payment_count": len(rows),
        "total_amount": total,
        "file_preview": rows[:5],
    }


# ── Tool 6 ───────────────────────────────────────────────────────────────────
def get_invoice_from_email(email_subject: str = "", sender: str = "") -> dict:
    """Fetches an invoice attachment from email.

    In mock mode returns sample invoice data. In production this would
    connect to Gmail/Outlook API.

    Args:
        email_subject: Subject line to search for.
        sender: Sender email address to filter by.

    Returns:
        dict with email match details and extracted attachment info.
    """
    # Mock: return sample email + attachment info
    return {
        "found": True,
        "email": {
            "from": sender or "invoices@acmetech.com",
            "subject": email_subject or "Invoice #INV-2024-055 - January Services",
            "date": "2025-01-12",
            "attachment": {
                "filename": "INV-2024-055.pdf",
                "size_kb": 245,
                "content_type": "application/pdf",
            },
        },
        "file_content": "mock-pdf-content-base64",
    }
