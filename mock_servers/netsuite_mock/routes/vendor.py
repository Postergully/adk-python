"""Vendor record endpoints.

Implements:
    POST   /record/v1/vendor
    GET    /record/v1/vendor/{id}
    PUT    /record/v1/vendor/{id}
    DELETE /record/v1/vendor/{id}
    GET    /record/v1/vendor?q=companyName LIKE 'Google%'
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from mock_servers.netsuite_mock.db import get_db
from mock_servers.netsuite_mock.models import VendorCreate

router = APIRouter(tags=["Vendor"])


@router.post("/vendor", status_code=201)
async def create_vendor(body: VendorCreate):
    db = get_db()
    record = db.insert("vendor", body.model_dump(mode="json"))
    return record


@router.get("/vendor")
async def list_or_search_vendors(q: Optional[str] = Query(None)):
    db = get_db()
    if q:
        items = db.search("vendor", q)
    else:
        items = db.list_all("vendor")
    return {
        "items": items,
        "hasMore": False,
        "totalResults": len(items),
        "offset": 0,
        "count": len(items),
    }


@router.get("/vendor/{vendor_id}")
async def get_vendor(vendor_id: str):
    db = get_db()
    record = db.get("vendor", vendor_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "error.RecordNotFound",
                "title": "Record Not Found",
                "detail": f"Vendor with id '{vendor_id}' not found",
            },
        )
    return record


@router.put("/vendor/{vendor_id}")
async def update_vendor(vendor_id: str, body: dict):
    db = get_db()
    record = db.update("vendor", vendor_id, body)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "error.RecordNotFound",
                "title": "Record Not Found",
                "detail": f"Vendor with id '{vendor_id}' not found",
            },
        )
    return record


@router.delete("/vendor/{vendor_id}", status_code=204)
async def delete_vendor(vendor_id: str):
    db = get_db()
    if not db.delete("vendor", vendor_id):
        raise HTTPException(
            status_code=404,
            detail={
                "type": "error.RecordNotFound",
                "title": "Record Not Found",
                "detail": f"Vendor with id '{vendor_id}' not found",
            },
        )
    return None
