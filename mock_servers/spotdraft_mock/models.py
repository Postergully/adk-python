"""Pydantic models for the Spotdraft mock server."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# --- Enums ---


class ContractStatus(str, Enum):
    draft = "draft"
    sent = "sent"
    executed = "executed"
    expired = "expired"


class DocumentStatus(str, Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"


class OnboardingStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    complete = "complete"
    blocked = "blocked"


class PartyType(str, Enum):
    vendor = "vendor"
    customer = "customer"
    partner = "partner"


# --- Nested models ---


class Address(BaseModel):
    street: str
    city: str
    state: str
    country: str
    zipcode: str


# --- Core resources ---


class PartyBase(BaseModel):
    name: str
    type: PartyType = PartyType.vendor
    email: str
    phone: Optional[str] = None
    address: Optional[Address] = None
    tax_id: Optional[str] = None


class Party(PartyBase):
    id: str
    created_at: datetime


class PartyCreate(PartyBase):
    pass


class ContractBase(BaseModel):
    name: str
    status: ContractStatus = ContractStatus.draft
    party_ids: list[str] = Field(default_factory=list)
    template_id: Optional[str] = None
    contract_value: Optional[float] = None
    currency: str = "INR"
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class Contract(ContractBase):
    id: str
    created_at: datetime
    signed_at: Optional[datetime] = None
    document_url: Optional[str] = None


class ContractCreate(ContractBase):
    pass


class DocumentBase(BaseModel):
    name: str
    type: str  # e.g. kyc_document, agreement, nda
    party_id: str
    file_url: Optional[str] = None


class Document(DocumentBase):
    id: str
    uploaded_at: datetime
    status: DocumentStatus = DocumentStatus.pending


class DocumentCreate(DocumentBase):
    pass


# --- Custom endpoint responses ---


class OnboardingContractSummary(BaseModel):
    id: str
    status: ContractStatus
    type: str


class OnboardingResponse(BaseModel):
    party_id: str
    party_name: str
    overall_status: OnboardingStatus
    kyc_status: str
    documents_received: list[str]
    documents_pending: list[str]
    contracts: list[OnboardingContractSummary]
