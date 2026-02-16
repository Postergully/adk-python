"""Party (vendor) endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..auth import verify_api_key
from ..db import add_item, find_by_id, get_collection
from ..models import Party, PartyCreate

router = APIRouter(prefix="/parties", tags=["parties"])


@router.get("/", response_model=list[Party])
async def list_parties(_key: str = Depends(verify_api_key)) -> list[dict]:
    return get_collection("parties")


@router.get("/{party_id}/", response_model=Party)
async def get_party(party_id: str, _key: str = Depends(verify_api_key)) -> dict:
    party = find_by_id("parties", party_id)
    if party is None:
        raise HTTPException(status_code=404, detail="Party not found")
    return party


@router.post("/", response_model=Party, status_code=201)
async def create_party(
    body: PartyCreate, _key: str = Depends(verify_api_key)
) -> dict:
    party = body.model_dump()
    party["id"] = f"party_{uuid.uuid4().hex[:8]}"
    party["created_at"] = datetime.now(timezone.utc).isoformat()
    return add_item("parties", party)
