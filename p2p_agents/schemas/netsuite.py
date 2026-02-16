"""Pydantic models for NetSuite record APIs and custom P2P records."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel
from pydantic import Field
from pydantic import HttpUrl
from pydantic import model_validator

_PAN_PATTERN = r"^[A-Z]{5}[0-9]{4}[A-Z]$"
_GST_PATTERN = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{3}$"

_APPROVAL_STATUS = Literal["pendingApproval", "approved", "rejected"]
_PAYMENT_STATUS = Literal[
  "pendingApproval",
  "approved",
  "rejected",
  "completed",
  "scheduled",
]


class NetsuiteRecordRef(BaseModel):
  """Reference object used by NetSuite record fields."""

  id: str = Field(min_length=1)


class NetsuiteVendor(BaseModel):
  """NetSuite vendor record."""

  id: str | None = None
  companyName: str = Field(min_length=1, max_length=255)
  isPerson: bool = False
  email: str = Field(min_length=3)
  phone: str | None = None
  taxIdNum: str = Field(pattern=_PAN_PATTERN)
  gstIdNum: str | None = Field(default=None, pattern=_GST_PATTERN)
  accountNumber: str = Field(min_length=4, max_length=34)
  terms: NetsuiteRecordRef = Field(
    default_factory=lambda: NetsuiteRecordRef(id="5")
  )
  category: NetsuiteRecordRef | None = None
  subsidiary: NetsuiteRecordRef = Field(
    default_factory=lambda: NetsuiteRecordRef(id="1")
  )
  status: Literal["active", "inactive", "onboarding"] = "active"


class NetsuiteVendorBillLine(BaseModel):
  """Single line item in a NetSuite vendor bill."""

  item: NetsuiteRecordRef
  description: str | None = None
  amount: float = Field(ge=0)
  account: NetsuiteRecordRef


class NetsuiteVendorBill(BaseModel):
  """NetSuite vendor bill (invoice) record."""

  id: str | None = None
  entity: NetsuiteRecordRef
  tranId: str = Field(min_length=1)
  tranDate: date
  dueDate: date
  amount: float = Field(ge=0)
  currency: NetsuiteRecordRef = Field(
    default_factory=lambda: NetsuiteRecordRef(id="1")
  )
  approvalStatus: _APPROVAL_STATUS = "pendingApproval"
  item: list[NetsuiteVendorBillLine] = Field(default_factory=list)
  memo: str | None = None

  @model_validator(mode="after")
  def _validate_bill(self) -> NetsuiteVendorBill:
    if self.dueDate < self.tranDate:
      raise ValueError("dueDate must be on or after tranDate.")
    if self.item:
      line_total = sum(line.amount for line in self.item)
      if abs(line_total - self.amount) > 0.01:
        raise ValueError("Vendor bill amount must match the sum of item lines.")
    return self


class NetsuiteVendorPaymentApplyLine(BaseModel):
  """Bill reference and amount for a vendor payment application."""

  doc: NetsuiteRecordRef
  amount: float = Field(ge=0)


class NetsuiteVendorPayment(BaseModel):
  """NetSuite vendor payment record."""

  id: str | None = None
  entity: NetsuiteRecordRef
  tranDate: date
  account: NetsuiteRecordRef = Field(
    default_factory=lambda: NetsuiteRecordRef(id="100")
  )
  amount: float = Field(ge=0)
  status: _PAYMENT_STATUS = "pendingApproval"
  approver: NetsuiteRecordRef | None = None
  apply: list[NetsuiteVendorPaymentApplyLine] = Field(default_factory=list)

  @model_validator(mode="after")
  def _validate_payment(self) -> NetsuiteVendorPayment:
    if self.apply:
      applied_total = sum(line.amount for line in self.apply)
      if abs(applied_total - self.amount) > 0.01:
        raise ValueError("Payment amount must match the applied total.")
    return self


class NetsuiteExpenseLine(BaseModel):
  """Single reimbursement line item."""

  category: NetsuiteRecordRef
  amount: float = Field(ge=0)
  receipt: HttpUrl | None = None


class NetsuiteExpense(BaseModel):
  """NetSuite expense record used for reimbursements."""

  id: str | None = None
  employee: NetsuiteRecordRef
  tranDate: date
  amount: float = Field(ge=0)
  memo: str = Field(min_length=1)
  category: NetsuiteRecordRef
  approvalStatus: _APPROVAL_STATUS = "pendingApproval"
  expenseList: list[NetsuiteExpenseLine] = Field(default_factory=list)

  @model_validator(mode="after")
  def _validate_expense(self) -> NetsuiteExpense:
    if self.expenseList:
      expense_total = sum(line.amount for line in self.expenseList)
      if abs(expense_total - self.amount) > 0.01:
        raise ValueError("Expense amount must match the expenseList total.")
    return self


class NetsuiteBankEntry(BaseModel):
  """Custom bank entry record for automation workflows."""

  id: str | None = None
  tranDate: date
  description: str = Field(min_length=1)
  amount: float
  account: NetsuiteRecordRef
  reference: str | None = None
  source: Literal["statement", "manual", "creditCard"] = "manual"


class NetsuiteCreditCardInvoice(BaseModel):
  """Custom credit-card invoice record used in reconciliation."""

  id: str | None = None
  cardId: str = Field(min_length=1)
  vendorName: str = Field(min_length=1)
  tranDate: date
  amount: float = Field(ge=0)
  currency: NetsuiteRecordRef = Field(
    default_factory=lambda: NetsuiteRecordRef(id="1")
  )
  status: Literal["pending", "matched", "disputed"] = "pending"
  matchedEntryId: str | None = None


class NetsuiteAccrual(BaseModel):
  """Custom accrual tracking record."""

  id: str | None = None
  vendorId: str = Field(min_length=1)
  period: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}$")
  expectedAmount: float = Field(ge=0)
  actualAmount: float = Field(ge=0)
  isPosted: bool = False


class NetsuiteSeedData(BaseModel):
  """Seed data container for NetSuite mock server bootstrapping."""

  vendors: list[NetsuiteVendor] = Field(default_factory=list)
  vendorBills: list[NetsuiteVendorBill] = Field(default_factory=list)
  vendorPayments: list[NetsuiteVendorPayment] = Field(default_factory=list)
  expenses: list[NetsuiteExpense] = Field(default_factory=list)
  bankEntries: list[NetsuiteBankEntry] = Field(default_factory=list)
  ccInvoices: list[NetsuiteCreditCardInvoice] = Field(default_factory=list)
  accruals: list[NetsuiteAccrual] = Field(default_factory=list)
