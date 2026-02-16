"""Custom bank operations endpoints (not part of standard NetSuite REST API).

Implements:
    POST   /api/custom/bank-entries
    POST   /api/custom/bank-entries/batch
    GET    /api/custom/cc-invoices
    GET    /api/custom/accruals
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter

from mock_servers.netsuite_mock.db import get_db
from mock_servers.netsuite_mock.models import BankEntry, CreditCardInvoice, Accrual

router = APIRouter(tags=["Bank Operations"])


@router.post("/bank-entries", status_code=201)
async def create_bank_entry(body: dict):
    db = get_db()
    record = db.insert("bankEntry", body)
    return record


@router.post("/bank-entries/batch", status_code=201)
async def batch_create_bank_entries(body: List[dict]):
    db = get_db()
    results = []
    for entry in body:
        record = db.insert("bankEntry", entry)
        results.append(record)
    return {"items": results, "count": len(results)}


@router.get("/bank-entries")
async def list_bank_entries():
    db = get_db()
    items = db.list_all("bankEntry")
    return {
        "items": items,
        "hasMore": False,
        "totalResults": len(items),
    }


@router.get("/cc-invoices")
async def list_cc_invoices():
    db = get_db()
    items = db.list_all("ccInvoice")
    return {
        "items": items,
        "hasMore": False,
        "totalResults": len(items),
    }


@router.get("/accruals")
async def list_accruals():
    db = get_db()
    items = db.list_all("accrual")
    return {
        "items": items,
        "hasMore": False,
        "totalResults": len(items),
    }
