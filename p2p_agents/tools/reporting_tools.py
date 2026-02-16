"""Reporting agent tools — metrics, accruals, invoice/payment stats, report generation."""

from __future__ import annotations

from p2p_agents.config.constants import AGING_BUCKETS
from p2p_agents.tools.helpers import ns_get


# ── Tool 1 ───────────────────────────────────────────────────────────────────
def get_invoices_processed_count(start_date: str = "", end_date: str = "") -> dict:
    """Counts invoices (vendor bills) processed in a date range.

    Args:
        start_date: Start date in YYYY-MM-DD format. Defaults to current month.
        end_date: End date in YYYY-MM-DD format. Defaults to today.

    Returns:
        dict with invoice count and total amount for the period.
    """
    params = {}
    if start_date:
        params["q"] = f"tranDate >= '{start_date}'"
        if end_date:
            params["q"] += f" AND tranDate <= '{end_date}'"

    bills = ns_get("/record/v1/vendorBill", params=params or None)
    items = bills.get("items", []) if isinstance(bills, dict) else bills if isinstance(bills, list) else []
    total_amount = sum(b.get("amount", 0) for b in items)
    return {
        "count": len(items),
        "total_amount": total_amount,
        "period": {"start": start_date or "current_month", "end": end_date or "today"},
    }


# ── Tool 2 ───────────────────────────────────────────────────────────────────
def get_payments_made_count(start_date: str = "", end_date: str = "") -> dict:
    """Counts payments made in a date range.

    Args:
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.

    Returns:
        dict with payment count and total amount for the period.
    """
    params = {}
    if start_date:
        params["q"] = f"tranDate >= '{start_date}'"
        if end_date:
            params["q"] += f" AND tranDate <= '{end_date}'"

    payments = ns_get("/record/v1/vendorPayment", params=params or None)
    items = payments.get("items", []) if isinstance(payments, dict) else payments if isinstance(payments, list) else []
    total_amount = sum(p.get("amount", 0) for p in items)
    return {
        "count": len(items),
        "total_amount": total_amount,
        "period": {"start": start_date or "current_month", "end": end_date or "today"},
    }


# ── Tool 3 ───────────────────────────────────────────────────────────────────
def get_p2p_efficiency_metrics(start_date: str = "", end_date: str = "") -> dict:
    """Calculates P2P efficiency metrics: turnaround times, aging, error rates.

    Args:
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.

    Returns:
        dict with efficiency metrics: avg processing time, aging buckets, approval rate.
    """
    params = {}
    if start_date:
        params["q"] = f"tranDate >= '{start_date}'"
        if end_date:
            params["q"] += f" AND tranDate <= '{end_date}'"

    bills = ns_get("/record/v1/vendorBill", params=params or None)
    items = bills.get("items", []) if isinstance(bills, dict) else bills if isinstance(bills, list) else []

    total = len(items)
    approved = sum(1 for b in items if b.get("approvalStatus") == "approved")
    pending = sum(1 for b in items if b.get("approvalStatus") == "pendingApproval")
    rejected = sum(1 for b in items if b.get("approvalStatus") == "rejected")

    # Build aging bucket counts (mock: distribute evenly)
    aging = {}
    for low, high in AGING_BUCKETS:
        label = f"{low}-{high}" if high else f"{low}+"
        aging[label] = max(1, total // len(AGING_BUCKETS)) if total else 0

    return {
        "total_invoices": total,
        "approved": approved,
        "pending_approval": pending,
        "rejected": rejected,
        "approval_rate": f"{(approved / total * 100):.1f}%" if total else "N/A",
        "aging_buckets": aging,
        "avg_processing_days": 3.2,  # Mock average
        "period": {"start": start_date or "current_month", "end": end_date or "today"},
    }


# ── Tool 4 ───────────────────────────────────────────────────────────────────
def check_missed_accruals(month: str = "") -> dict:
    """Compares expected vs actual accruals for a period to find misses.

    Args:
        month: Month to check in YYYY-MM format. Defaults to current month.

    Returns:
        dict with missed accruals, expected vs actual comparison.
    """
    accruals = ns_get("/api/custom/accruals")
    items = accruals.get("items", []) if isinstance(accruals, dict) else accruals if isinstance(accruals, list) else []

    # Mock: compare expected accruals against actual records
    missed = []
    for accrual in items:
        expected = accrual.get("expectedAmount", 0)
        actual = accrual.get("actualAmount", 0)
        if abs(expected - actual) > 0.01:
            missed.append({
                "vendor": accrual.get("vendor", "Unknown"),
                "expected": expected,
                "actual": actual,
                "difference": round(expected - actual, 2),
            })

    return {
        "month": month or "current",
        "total_accruals": len(items),
        "missed_count": len(missed),
        "missed_accruals": missed,
        "status": "all_matched" if not missed else "discrepancies_found",
    }


# ── Tool 5 ───────────────────────────────────────────────────────────────────
def get_accrual_data(month: str = "") -> dict:
    """Fetches monthly accrual records from NetSuite.

    Args:
        month: Month to fetch in YYYY-MM format. Defaults to current month.

    Returns:
        dict with accrual records and summary totals.
    """
    accruals = ns_get("/api/custom/accruals")
    items = accruals.get("items", []) if isinstance(accruals, dict) else accruals if isinstance(accruals, list) else []

    total = sum(a.get("amount", 0) for a in items)
    return {
        "month": month or "current",
        "accruals": items,
        "total_amount": total,
        "count": len(items),
    }


# ── Tool 6 ───────────────────────────────────────────────────────────────────
def generate_p2p_report(report_type: str, params: dict | None = None) -> dict:
    """Generates a formatted P2P report based on the specified type.

    Args:
        report_type: Type of report: "payment_summary", "vendor_aging",
            "invoice_backlog", "monthly_dashboard", "accrual_report".
        params: Optional parameters like date_range, vendor_filter, etc.

    Returns:
        dict with the formatted report data.
    """
    params = params or {}
    start = params.get("start_date", "")
    end = params.get("end_date", "")

    if report_type == "payment_summary":
        payments = get_payments_made_count(start, end)
        invoices = get_invoices_processed_count(start, end)
        return {
            "report_type": "payment_summary",
            "payments": payments,
            "invoices": invoices,
        }

    elif report_type == "vendor_aging":
        metrics = get_p2p_efficiency_metrics(start, end)
        return {
            "report_type": "vendor_aging",
            "aging_buckets": metrics.get("aging_buckets", {}),
            "total_invoices": metrics.get("total_invoices", 0),
        }

    elif report_type == "invoice_backlog":
        bills = ns_get("/record/v1/vendorBill", params={"q": "approvalStatus='pendingApproval'"})
        items = bills.get("items", []) if isinstance(bills, dict) else bills if isinstance(bills, list) else []
        return {
            "report_type": "invoice_backlog",
            "pending_count": len(items),
            "pending_invoices": items[:20],
        }

    elif report_type == "monthly_dashboard":
        invoices = get_invoices_processed_count(start, end)
        payments = get_payments_made_count(start, end)
        metrics = get_p2p_efficiency_metrics(start, end)
        return {
            "report_type": "monthly_dashboard",
            "invoices": invoices,
            "payments": payments,
            "metrics": metrics,
        }

    elif report_type == "accrual_report":
        accruals = get_accrual_data(params.get("month", ""))
        missed = check_missed_accruals(params.get("month", ""))
        return {
            "report_type": "accrual_report",
            "accruals": accruals,
            "missed": missed,
        }

    return {"error": f"Unknown report type: {report_type}"}
