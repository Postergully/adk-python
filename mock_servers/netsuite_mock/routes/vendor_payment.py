"""Vendor Payment record endpoints.

Implements:
    POST   /record/v1/vendorPayment
    GET    /record/v1/vendorPayment/{id}
    GET    /record/v1/vendorPayment?q=status='pendingApproval'
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from mock_servers.netsuite_mock.db import get_db
from mock_servers.netsuite_mock.models import VendorPaymentCreate

router = APIRouter(tags=["VendorPayment"])


@router.post("/vendorPayment", status_code=201)
async def create_vendor_payment(body: VendorPaymentCreate):
    db = get_db()
    record = db.insert("vendorPayment", body.model_dump(mode="json"))
    return record


@router.get("/vendorPayment")
async def list_or_search_vendor_payments(q: Optional[str] = Query(None)):
    db = get_db()
    if q:
        items = db.search("vendorPayment", q)
    else:
        items = db.list_all("vendorPayment")
    return {
        "items": items,
        "hasMore": False,
        "totalResults": len(items),
        "offset": 0,
        "count": len(items),
    }


@router.get("/vendorPayment/{payment_id}")
async def get_vendor_payment(payment_id: str):
    db = get_db()
    record = db.get("vendorPayment", payment_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "error.RecordNotFound",
                "title": "Record Not Found",
                "detail": f"VendorPayment with id '{payment_id}' not found",
            },
        )
    return record
