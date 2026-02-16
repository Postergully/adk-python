"""Vendor agent tools — creation, onboarding, KYC, documents, status management."""

from __future__ import annotations

from p2p_agents.tools.helpers import ns_get, ns_post, ns_put, sd_get


# ── Tool 1 ───────────────────────────────────────────────────────────────────
def create_vendor(
    company_name: str,
    contact_email: str,
    payment_terms: str = "net_30",
    pan_number: str = "",
    gst_number: str = "",
    bank_account: str = "",
    contact_phone: str = "",
) -> dict:
    """Creates a new vendor record in NetSuite.

    Args:
        company_name: Legal entity name of the vendor.
        contact_email: Primary contact email.
        payment_terms: Payment terms code, e.g. "net_30", "net_60", "net_90".
        pan_number: PAN number for Indian vendors.
        gst_number: GST registration number.
        bank_account: Bank account number for payments.
        contact_phone: Contact phone number.

    Returns:
        dict with created vendor ID and confirmation.
    """
    from p2p_agents.config.constants import PAYMENT_TERMS

    terms_id = PAYMENT_TERMS.get(payment_terms, "5")
    result = ns_post(
        "/record/v1/vendor",
        json={
            "companyName": company_name,
            "email": contact_email,
            "phone": contact_phone,
            "terms": {"id": terms_id},
            "taxIdNum": pan_number,
            "gstNumber": gst_number,
            "bankAccount": bank_account,
        },
    )
    return {
        "status": "created",
        "vendor_id": result.get("id"),
        "company_name": company_name,
        "payment_terms": payment_terms,
    }


# ── Tool 2 ───────────────────────────────────────────────────────────────────
def get_vendor_onboarding_status(vendor_id: str = "", vendor_name: str = "") -> dict:
    """Checks the onboarding status of a vendor across NetSuite and Spotdraft.

    Args:
        vendor_id: NetSuite vendor ID to look up.
        vendor_name: Vendor name to search for (used if vendor_id not provided).

    Returns:
        dict with onboarding checklist: KYC, bank details, agreement, NetSuite record.
    """
    if not vendor_id and vendor_name:
        vendors = ns_get("/record/v1/vendor", params={"q": f"companyName LIKE '{vendor_name}%'"})
        items = vendors.get("items", []) if isinstance(vendors, dict) else vendors if isinstance(vendors, list) else []
        if not items:
            return {"error": f"No vendor found matching '{vendor_name}'"}
        vendor_id = items[0].get("id", "")

    if not vendor_id:
        return {"error": "Provide either vendor_id or vendor_name"}

    # Fetch NetSuite vendor record
    vendor = ns_get(f"/record/v1/vendor/{vendor_id}")

    # Fetch Spotdraft onboarding status
    try:
        onboarding = sd_get(f"/api/custom/onboarding/{vendor_id}/")
    except Exception:
        onboarding = {"overall_status": "unknown", "documents_pending": [], "documents_received": []}

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor.get("companyName", ""),
        "netsuite_record": "active" if vendor.get("id") else "missing",
        "kyc_status": onboarding.get("kyc_status", "unknown"),
        "overall_status": onboarding.get("overall_status", "unknown"),
        "documents_received": onboarding.get("documents_received", []),
        "documents_pending": onboarding.get("documents_pending", []),
        "contracts": onboarding.get("contracts", []),
    }


# ── Tool 3 ───────────────────────────────────────────────────────────────────
def run_kyc_check(
    vendor_name: str,
    pan_number: str = "",
    gst_number: str = "",
    bank_account: str = "",
) -> dict:
    """Validates vendor KYC documents (PAN, GST, bank details).

    In mock mode performs format validation. In production this would call
    a real KYC/verification service.

    Args:
        vendor_name: Vendor name for the check.
        pan_number: PAN number to validate.
        gst_number: GST registration number to validate.
        bank_account: Bank account number to validate.

    Returns:
        dict with KYC result: passed/failed and individual check results.
    """
    checks = {}
    if pan_number:
        checks["pan"] = {
            "value": pan_number,
            "valid": len(pan_number) == 10 and pan_number[:5].isalpha() and pan_number[5:9].isdigit() and pan_number[9].isalpha(),
        }
    else:
        checks["pan"] = {"value": "", "valid": False, "reason": "Not provided"}

    if gst_number:
        checks["gst"] = {
            "value": gst_number,
            "valid": len(gst_number) == 15,
        }
    else:
        checks["gst"] = {"value": "", "valid": False, "reason": "Not provided"}

    if bank_account:
        checks["bank_account"] = {
            "value": bank_account[-4:].rjust(len(bank_account), "*"),
            "valid": len(bank_account) >= 8,
        }
    else:
        checks["bank_account"] = {"value": "", "valid": False, "reason": "Not provided"}

    all_passed = all(c.get("valid", False) for c in checks.values())
    return {
        "vendor_name": vendor_name,
        "kyc_passed": all_passed,
        "checks": checks,
    }


# ── Tool 4 ───────────────────────────────────────────────────────────────────
def get_vendor_documents(vendor_id: str) -> dict:
    """Fetches vendor agreements and contracts from Spotdraft.

    Args:
        vendor_id: The vendor/party ID to fetch documents for.

    Returns:
        dict with contracts and documents for the vendor.
    """
    try:
        contracts = sd_get("/contracts/", params={"party_id": vendor_id})
    except Exception:
        contracts = []

    try:
        documents = sd_get("/documents/")
    except Exception:
        documents = []

    return {
        "vendor_id": vendor_id,
        "contracts": contracts if isinstance(contracts, list) else [],
        "documents": documents if isinstance(documents, list) else [],
        "total_contracts": len(contracts) if isinstance(contracts, list) else 0,
        "total_documents": len(documents) if isinstance(documents, list) else 0,
    }


# ── Tool 5 ───────────────────────────────────────────────────────────────────
def update_vendor_status(vendor_id: str, status: str) -> dict:
    """Updates a vendor's onboarding or active status in NetSuite.

    Args:
        vendor_id: NetSuite vendor ID.
        status: New status, e.g. "onboarding_complete", "active", "inactive", "blocked".

    Returns:
        dict confirming the status update.
    """
    result = ns_put(
        f"/record/v1/vendor/{vendor_id}",
        json={"entityStatus": status},
    )
    return {
        "vendor_id": vendor_id,
        "new_status": status,
        "updated": True,
        "vendor_name": result.get("companyName", ""),
    }


# ── Tool 6 ───────────────────────────────────────────────────────────────────
def generate_onboarding_report() -> dict:
    """Generates a status report of all vendors currently in onboarding.

    Returns:
        dict with summary counts and per-vendor status breakdown.
    """
    vendors = ns_get("/record/v1/vendor")
    items = vendors.get("items", []) if isinstance(vendors, dict) else vendors if isinstance(vendors, list) else []

    report = {"complete": [], "pending": [], "blocked": []}
    for vendor in items:
        vid = vendor.get("id", "")
        try:
            onboarding = sd_get(f"/api/custom/onboarding/{vid}/")
            status = onboarding.get("overall_status", "pending")
        except Exception:
            status = "pending"

        entry = {
            "vendor_id": vid,
            "vendor_name": vendor.get("companyName", ""),
            "status": status,
        }
        if status == "complete":
            report["complete"].append(entry)
        elif status == "blocked":
            report["blocked"].append(entry)
        else:
            report["pending"].append(entry)

    return {
        "total_vendors": len(items),
        "complete": len(report["complete"]),
        "pending": len(report["pending"]),
        "blocked": len(report["blocked"]),
        "details": report,
    }
