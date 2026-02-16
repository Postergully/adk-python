"""Response schemas returned by P2P agent tools."""

from __future__ import annotations

from datetime import date
from typing import Generic
from typing import TypeVar

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator

_T = TypeVar("_T")


class AgentToolResponse(BaseModel, Generic[_T]):
  """A standard response wrapper for all tool functions."""

  ok: bool = True
  message: str = ""
  data: _T | None = None
  error: str | None = None

  @model_validator(mode="after")
  def _validate_error_fields(self) -> AgentToolResponse[_T]:
    if self.ok and self.error is not None:
      raise ValueError("Successful tool responses cannot include an error.")
    if not self.ok and not self.error:
      raise ValueError("Failed tool responses must include an error message.")
    return self


class PaymentStatusPayload(BaseModel):
  """Payment status details for invoice and vendor status lookups."""

  invoice_number: str | None = None
  vendor: str = Field(min_length=1)
  status: str = Field(min_length=1)
  amount: float = Field(ge=0)
  due_date: date | None = None
  payment_date: date | None = None


class ApprovalReminderPayload(BaseModel):
  """Summary of reminders sent for pending approvals."""

  reminders_sent: int = Field(ge=0)
  approver_ids: list[str] = Field(default_factory=list)
  escalated_transactions: int = Field(ge=0, default=0)


class ReimbursementPayload(BaseModel):
  """Result of reimbursement validation and processing."""

  claim_id: str
  employee_id: str
  status: str
  approved_amount: float = Field(ge=0)
  needs_manager_approval: bool
  notes: str | None = None


class VendorOnboardingPayload(BaseModel):
  """Aggregated vendor onboarding checklist data."""

  vendor_id: str
  vendor_name: str
  overall_status: str
  kyc_verified: bool
  agreement_status: str
  missing_items: list[str] = Field(default_factory=list)


class P2PReportPayload(BaseModel):
  """Report metadata and summarized P2P metrics."""

  report_type: str = Field(min_length=1)
  period_start: date
  period_end: date
  metrics: dict[str, float | int | str] = Field(default_factory=dict)


class BankReconciliationPayload(BaseModel):
  """Summary of credit-card or bank reconciliation execution."""

  total_transactions: int = Field(ge=0)
  matched_transactions: int = Field(ge=0)
  unmatched_transactions: int = Field(ge=0)
  discrepancies: list[str] = Field(default_factory=list)
