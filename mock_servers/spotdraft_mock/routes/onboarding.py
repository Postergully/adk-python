"""Custom onboarding-status endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import verify_api_key
from ..db import find_by_id, get_collection
from ..models import OnboardingResponse, OnboardingStatus

router = APIRouter(prefix="/api/custom", tags=["onboarding"])

# Documents required for a complete vendor onboarding.
_REQUIRED_DOCS = {"PAN", "GST", "Bank Details", "MSA"}


@router.get("/onboarding/{party_id}/", response_model=OnboardingResponse)
async def onboarding_status(
    party_id: str, _key: str = Depends(verify_api_key)
) -> dict:
    party = find_by_id("parties", party_id)
    if party is None:
        raise HTTPException(status_code=404, detail="Party not found")

    # Gather documents for this party.
    docs = [
        d
        for d in get_collection("documents")
        if d.get("party_id") == party_id
    ]
    received = set()
    has_rejected = False
    for d in docs:
        # Derive short label from document name (e.g. "Google - PAN Card.pdf" → "PAN")
        name_upper = d.get("name", "").upper()
        for label in _REQUIRED_DOCS:
            if label.upper() in name_upper:
                if d.get("status") != "rejected":
                    received.add(label)
                else:
                    has_rejected = True

    pending = sorted(_REQUIRED_DOCS - received)

    # Gather contracts.
    contracts = [
        c
        for c in get_collection("contracts")
        if party_id in c.get("party_ids", [])
    ]
    contract_summaries = [
        {
            "id": c["id"],
            "status": c.get("status", "draft"),
            "type": _infer_contract_type(c.get("name", "")),
        }
        for c in contracts
    ]

    # Determine KYC status.
    kyc_docs = [d for d in docs if d.get("type") == "kyc_document"]
    if not kyc_docs:
        kyc_status = "not_started"
    elif all(d.get("status") == "verified" for d in kyc_docs):
        kyc_status = "verified"
    elif any(d.get("status") == "rejected" for d in kyc_docs):
        kyc_status = "rejected"
    else:
        kyc_status = "pending"

    # Overall status.
    if has_rejected:
        overall = OnboardingStatus.blocked
    elif not pending and all(
        c.get("status") == "executed" for c in contracts
    ):
        overall = OnboardingStatus.complete
    elif received:
        overall = OnboardingStatus.in_progress
    else:
        overall = OnboardingStatus.pending

    return {
        "party_id": party_id,
        "party_name": party.get("name", ""),
        "overall_status": overall,
        "kyc_status": kyc_status,
        "documents_received": sorted(received),
        "documents_pending": pending,
        "contracts": contract_summaries,
    }


def _infer_contract_type(name: str) -> str:
    name_lower = name.lower()
    if "nda" in name_lower or "non-disclosure" in name_lower:
        return "NDA"
    if "sow" in name_lower or "statement of work" in name_lower:
        return "SOW"
    return "MSA"
