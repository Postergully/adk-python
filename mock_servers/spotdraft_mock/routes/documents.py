"""Document endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..auth import verify_api_key
from ..db import add_item, find_by_id, get_collection
from ..models import Document, DocumentCreate

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/", response_model=list[Document])
async def list_documents(_key: str = Depends(verify_api_key)) -> list[dict]:
    return get_collection("documents")


@router.get("/{doc_id}/", response_model=Document)
async def get_document(
    doc_id: str, _key: str = Depends(verify_api_key)
) -> dict:
    doc = find_by_id("documents", doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/", response_model=Document, status_code=201)
async def create_document(
    body: DocumentCreate, _key: str = Depends(verify_api_key)
) -> dict:
    doc = body.model_dump()
    doc["id"] = f"doc_{uuid.uuid4().hex[:8]}"
    doc["uploaded_at"] = datetime.now(timezone.utc).isoformat()
    doc["status"] = "pending"
    return add_item("documents", doc)
