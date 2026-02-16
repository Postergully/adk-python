"""Expense (Reimbursement) record endpoints.

Implements:
    POST   /record/v1/expense
    GET    /record/v1/expense/{id}
    GET    /record/v1/expense?q=employee.id='789' AND approvalStatus='pendingApproval'
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from mock_servers.netsuite_mock.db import get_db
from mock_servers.netsuite_mock.models import ExpenseCreate

router = APIRouter(tags=["Expense"])


@router.post("/expense", status_code=201)
async def create_expense(body: ExpenseCreate):
    db = get_db()
    record = db.insert("expense", body.model_dump(mode="json"))
    return record


@router.get("/expense")
async def list_or_search_expenses(q: Optional[str] = Query(None)):
    db = get_db()
    if q:
        items = db.search("expense", q)
    else:
        items = db.list_all("expense")
    return {
        "items": items,
        "hasMore": False,
        "totalResults": len(items),
        "offset": 0,
        "count": len(items),
    }


@router.get("/expense/{expense_id}")
async def get_expense(expense_id: str):
    db = get_db()
    record = db.get("expense", expense_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "error.RecordNotFound",
                "title": "Record Not Found",
                "detail": f"Expense with id '{expense_id}' not found",
            },
        )
    return record
