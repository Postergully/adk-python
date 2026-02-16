"""Pydantic models for Spotdraft API resources."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic import Field
from pydantic import HttpUrl
from pydantic import model_validator

_PAN_PATTERN = r"^[A-Z]{5}[0-9]{4}[A-Z]$"


class SpotdraftAddress(BaseModel):
  """Postal address for a Spotdraft party."""

  street: str
  city: str
  state: str
  country: str
  zipcode: str


class SpotdraftParty(BaseModel):
  """Spotdraft party record."""

  id: str | None = None
  name: str = Field(min_length=1)
  type: Literal["vendor", "customer", "partner"] = "vendor"
  email: str | None = Field(default=None, min_length=3)
  phone: str | None = None
  address: SpotdraftAddress | None = None
  tax_id: str | None = Field(default=None, pattern=_PAN_PATTERN)
  created_at: datetime | None = None


class SpotdraftContract(BaseModel):
  """Spotdraft contract record."""

  id: str | None = None
  name: str = Field(min_length=1)
  status: Literal["draft", "sent", "executed", "expired"] = "draft"
  party_ids: list[str] = Field(min_length=1)
  template_id: str | None = None
  contract_value: float | None = Field(default=None, ge=0)
  currency: str = "INR"
  start_date: date | None = None
  end_date: date | None = None
  created_at: datetime | None = None
  signed_at: datetime | None = None
  document_url: HttpUrl | None = None

  @model_validator(mode="after")
  def _validate_date_window(self) -> SpotdraftContract:
    if (
      self.start_date is not None
      and self.end_date is not None
      and self.end_date < self.start_date
    ):
      raise ValueError("end_date must be on or after start_date.")
    return self


class SpotdraftDocument(BaseModel):
  """Spotdraft document record."""

  id: str | None = None
  name: str = Field(min_length=1)
  type: str = Field(min_length=1)
  party_id: str = Field(min_length=1)
  uploaded_at: datetime | None = None
  status: Literal["pending", "verified", "rejected"] = "pending"
  file_url: HttpUrl | None = None


class SpotdraftOnboardingContract(BaseModel):
  """Contract summary used in onboarding status responses."""

  id: str
  status: Literal["draft", "sent", "executed", "expired"]
  type: str = Field(min_length=1)


class SpotdraftOnboardingStatus(BaseModel):
  """Custom onboarding status payload used by the mock API."""

  party_id: str = Field(min_length=1)
  party_name: str = Field(min_length=1)
  overall_status: Literal["pending", "in_progress", "complete", "blocked"]
  kyc_status: Literal["pending", "verified", "rejected"]
  documents_received: list[str] = Field(default_factory=list)
  documents_pending: list[str] = Field(default_factory=list)
  contracts: list[SpotdraftOnboardingContract] = Field(default_factory=list)


class SpotdraftSeedData(BaseModel):
  """Seed data container for Spotdraft mock server bootstrapping."""

  parties: list[SpotdraftParty] = Field(default_factory=list)
  contracts: list[SpotdraftContract] = Field(default_factory=list)
  documents: list[SpotdraftDocument] = Field(default_factory=list)
  onboarding: list[SpotdraftOnboardingStatus] = Field(default_factory=list)
