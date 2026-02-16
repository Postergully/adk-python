"""Vendor Bill (Invoice) record endpoints.

Implements:
    POST   /record/v1/vendorBill
    GET    /record/v1/vendorBill/{id}
    GET    /record/v1/vendorBill?q=entity.id='123' AND status='pendingApproval'
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from mock_servers.netsuite_mock.db import get_db
from mock_servers.netsuite_mock.models import VendorBillCreate

router = APIRouter(tags=["VendorBill"])


@router.post("/vendorBill", status_code=201)
async def create_vendor_bill(body: VendorBillCreate):
    db = get_db()
    record = db.insert("vendorBill", body.model_dump(mode="json"))
    return record


@router.get("/vendorBill")
async def list_or_search_vendor_bills(q: Optional[str] = Query(None)):
    db = get_db()
    if q:
        items = db.search("vendorBill", q)
    else:
        items = db.list_all("vendorBill")
    return {
        "items": items,
        "hasMore": False,
        "totalResults": len(items),
        "offset": 0,
        "count": len(items),
    }


@router.get("/vendorBill/{bill_id}")
async def get_vendor_bill(bill_id: str):
    db = get_db()
    record = db.get("vendorBill", bill_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "error.RecordNotFound",
                "title": "Record Not Found",
                "detail": f"VendorBill with id '{bill_id}' not found",
            },
        )
    return record
