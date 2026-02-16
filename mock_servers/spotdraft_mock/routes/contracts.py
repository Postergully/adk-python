"""Contract endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import verify_api_key
from ..db import add_item, find_by_id, get_collection
from ..models import Contract, ContractCreate

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.get("/", response_model=list[Contract])
async def list_contracts(
    party_id: Optional[str] = Query(None),
    _key: str = Depends(verify_api_key),
) -> list[dict]:
    contracts = get_collection("contracts")
    if party_id:
        contracts = [
            c for c in contracts if party_id in c.get("party_ids", [])
        ]
    return contracts


@router.get("/{contract_id}/", response_model=Contract)
async def get_contract(
    contract_id: str, _key: str = Depends(verify_api_key)
) -> dict:
    contract = find_by_id("contracts", contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


@router.post("/", response_model=Contract, status_code=201)
async def create_contract(
    body: ContractCreate, _key: str = Depends(verify_api_key)
) -> dict:
    contract = body.model_dump()
    contract["id"] = f"con_{uuid.uuid4().hex[:8]}"
    contract["created_at"] = datetime.now(timezone.utc).isoformat()
    contract["signed_at"] = None
    contract["document_url"] = None
    return add_item("contracts", contract)
