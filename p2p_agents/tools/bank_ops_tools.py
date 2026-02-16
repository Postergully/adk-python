"""Bank operations agent tools — statement parsing, entries, CC reconciliation."""

from __future__ import annotations

from p2p_agents.tools.helpers import ns_get, ns_post


# ── Tool 1 ───────────────────────────────────────────────────────────────────
def parse_bank_statement(file_content: str, bank_name: str = "HDFC") -> dict:
    """Extracts transactions from a bank statement (CSV/PDF).

    In mock mode returns sample transactions. In production this would parse
    real bank statement formats.

    Args:
        file_content: Raw content of the bank statement file.
        bank_name: Name of the bank for format-specific parsing.

    Returns:
        dict with list of parsed transactions and summary.
    """
    # Mock: return realistic parsed transactions
    transactions = [
        {"date": "2025-01-05", "description": "NEFT-Acme Technologies", "amount": 125000.00, "type": "debit", "reference": "NEFT0001"},
        {"date": "2025-01-07", "description": "RTGS-Google India", "amount": 450000.00, "type": "debit", "reference": "RTGS0002"},
        {"date": "2025-01-10", "description": "NEFT-Agora Services", "amount": 78000.00, "type": "debit", "reference": "NEFT0003"},
        {"date": "2025-01-12", "description": "CHQ DEP-Client Payment", "amount": 500000.00, "type": "credit", "reference": "CHQ0004"},
        {"date": "2025-01-15", "description": "NEFT-Office Supplies Co", "amount": 15000.00, "type": "debit", "reference": "NEFT0005"},
    ]
    total_debit = sum(t["amount"] for t in transactions if t["type"] == "debit")
    total_credit = sum(t["amount"] for t in transactions if t["type"] == "credit")
    return {
        "bank": bank_name,
        "transactions": transactions,
        "transaction_count": len(transactions),
        "total_debit": total_debit,
        "total_credit": total_credit,
        "net": total_credit - total_debit,
    }


# ── Tool 2 ───────────────────────────────────────────────────────────────────
def create_bank_entry(
    date: str,
    amount: float,
    memo: str,
    account_id: str = "1",
    entity_id: str = "",
) -> dict:
    """Creates a bank entry record in NetSuite.

    Args:
        date: Transaction date in YYYY-MM-DD format.
        amount: Transaction amount.
        memo: Description/memo for the entry.
        account_id: NetSuite account ID for the bank account.
        entity_id: Optional vendor/entity ID for the transaction.

    Returns:
        dict with created entry ID and confirmation.
    """
    payload: dict = {
        "tranDate": date,
        "amount": amount,
        "memo": memo,
        "account": {"id": account_id},
    }
    if entity_id:
        payload["entity"] = {"id": entity_id}

    result = ns_post("/api/custom/bank-entries", json=payload)
    return {
        "status": "created",
        "entry_id": result.get("id"),
        "amount": amount,
        "date": date,
    }


# ── Tool 3 ───────────────────────────────────────────────────────────────────
def get_credit_card_invoices(card_id: str = "", period: str = "") -> dict:
    """Fetches credit card invoices from NetSuite for reconciliation.

    Args:
        card_id: Optional credit card identifier to filter.
        period: Optional period in YYYY-MM format.

    Returns:
        dict with list of CC invoices and summary.
    """
    cc_invoices = ns_get("/api/custom/cc-invoices")
    items = cc_invoices.get("items", []) if isinstance(cc_invoices, dict) else cc_invoices if isinstance(cc_invoices, list) else []

    total = sum(inv.get("amount", 0) for inv in items)
    return {
        "card_id": card_id or "all",
        "period": period or "current",
        "invoices": items,
        "count": len(items),
        "total_amount": total,
    }


# ── Tool 4 ───────────────────────────────────────────────────────────────────
def match_cc_transactions(cc_invoices: list[dict], bank_transactions: list[dict] | None = None) -> dict:
    """Matches credit card transactions against invoices.

    Args:
        cc_invoices: List of CC invoice dicts with 'amount' and 'description'.
        bank_transactions: Optional list of bank transaction dicts to match against.
            If not provided, uses a mock bank feed.

    Returns:
        dict with matched, unmatched, and summary.
    """
    if not bank_transactions:
        bank_transactions = [
            {"reference": "CC-001", "amount": 12500.00, "description": "AWS Services"},
            {"reference": "CC-002", "amount": 8900.00, "description": "Google Cloud"},
            {"reference": "CC-003", "amount": 3400.00, "description": "Office Supplies"},
        ]

    matched = []
    unmatched_invoices = []
    unmatched_bank = list(bank_transactions)

    for inv in cc_invoices:
        inv_amount = inv.get("amount", 0)
        found = False
        for i, txn in enumerate(unmatched_bank):
            if abs(txn.get("amount", 0) - inv_amount) < 0.01:
                matched.append({"invoice": inv, "bank_transaction": txn})
                unmatched_bank.pop(i)
                found = True
                break
        if not found:
            unmatched_invoices.append(inv)

    return {
        "matched": matched,
        "matched_count": len(matched),
        "unmatched_invoices": unmatched_invoices,
        "unmatched_bank_transactions": unmatched_bank,
        "match_rate": f"{(len(matched) / max(len(cc_invoices), 1) * 100):.1f}%",
    }


# ── Tool 5 ───────────────────────────────────────────────────────────────────
def flag_discrepancies(matched_transactions: list[dict], threshold: float = 100.0) -> dict:
    """Identifies unmatched or suspicious transactions for review.

    Args:
        matched_transactions: List of match result dicts from match_cc_transactions.
        threshold: Amount threshold for flagging discrepancies.

    Returns:
        dict with flagged items and severity levels.
    """
    flags = []
    for match in matched_transactions:
        inv = match.get("invoice", {})
        txn = match.get("bank_transaction", {})
        diff = abs(inv.get("amount", 0) - txn.get("amount", 0))
        if diff > threshold:
            flags.append({
                "invoice": inv,
                "bank_transaction": txn,
                "difference": round(diff, 2),
                "severity": "high" if diff > 1000 else "medium",
            })

    return {
        "flagged_count": len(flags),
        "flags": flags,
        "threshold": threshold,
    }


# ── Tool 6 ───────────────────────────────────────────────────────────────────
def generate_reconciliation_report(
    matched: list[dict],
    unmatched_invoices: list[dict],
    unmatched_bank: list[dict],
    flags: list[dict] | None = None,
) -> dict:
    """Generates a reconciliation summary report.

    Args:
        matched: List of matched transaction pairs.
        unmatched_invoices: List of CC invoices without a bank match.
        unmatched_bank: List of bank transactions without an invoice match.
        flags: Optional list of flagged discrepancies.

    Returns:
        dict with full reconciliation report.
    """
    total_matched_amount = sum(
        m.get("invoice", {}).get("amount", 0) for m in matched
    )
    total_unmatched_inv = sum(inv.get("amount", 0) for inv in unmatched_invoices)
    total_unmatched_bank = sum(txn.get("amount", 0) for txn in unmatched_bank)
    total_items = len(matched) + len(unmatched_invoices) + len(unmatched_bank)

    return {
        "report_type": "credit_card_reconciliation",
        "summary": {
            "total_items": total_items,
            "matched": len(matched),
            "unmatched_invoices": len(unmatched_invoices),
            "unmatched_bank": len(unmatched_bank),
            "flagged": len(flags) if flags else 0,
            "match_rate": f"{(len(matched) / max(total_items, 1) * 100):.1f}%",
        },
        "amounts": {
            "matched_total": total_matched_amount,
            "unmatched_invoice_total": total_unmatched_inv,
            "unmatched_bank_total": total_unmatched_bank,
        },
        "action_required": {
            "review_unmatched_invoices": unmatched_invoices,
            "review_unmatched_bank": unmatched_bank,
            "review_flags": flags or [],
        },
    }
