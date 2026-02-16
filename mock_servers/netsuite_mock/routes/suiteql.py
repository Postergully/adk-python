"""SuiteQL query endpoint.

Implements:
    POST   /query/v1/suiteql
"""

from __future__ import annotations

from fastapi import APIRouter

from mock_servers.netsuite_mock.db import get_db
from mock_servers.netsuite_mock.models import SuiteQLRequest

router = APIRouter(tags=["SuiteQL"])


@router.post("/suiteql")
async def execute_suiteql(body: SuiteQLRequest):
    db = get_db()
    items = db.execute_suiteql(body.q)
    return {
        "items": items,
        "hasMore": False,
        "totalResults": len(items),
    }
