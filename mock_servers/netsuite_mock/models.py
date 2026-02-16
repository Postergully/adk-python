"""NetSuite record models for the mock server.

Based on NetSuite REST API Browser 2025.2:
https://system.netsuite.com/help/helpcenter/en_US/APIs/REST_API_Browser/record/v1/2025.2/index.html
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# --- Reference models (NetSuite uses {"id": "..."} for foreign keys) ---

class RecordRef(BaseModel):
    id: str
    refName: Optional[str] = None


# --- Vendor ---

class VendorCreate(BaseModel):
    companyName: str
    isPerson: bool = False
    email: str
    phone: Optional[str] = None
    taxIdNum: str  # PAN in India
    gstIdNum: Optional[str] = None
    accountNumber: Optional[str] = None
    terms: Optional[RecordRef] = None
    category: Optional[RecordRef] = None
    subsidiary: RecordRef = RecordRef(id="1")


class Vendor(VendorCreate):
    id: str
    dateCreated: Optional[str] = None
    lastModifiedDate: Optional[str] = None


# --- Vendor Bill (Invoice) ---

class VendorBillLineItem(BaseModel):
    item: Optional[RecordRef] = None
    description: str = ""
    amount: float
    account: Optional[RecordRef] = None


class VendorBillCreate(BaseModel):
    entity: RecordRef  # vendor ref
    tranId: str  # Invoice number
    tranDate: date
    dueDate: date
    amount: float
    currency: RecordRef = RecordRef(id="1")  # INR
    approvalStatus: str = "pendingApproval"
    memo: Optional[str] = None
    item: List[VendorBillLineItem] = Field(default_factory=list)


class VendorBill(VendorBillCreate):
    id: str
    status: Optional[str] = None
    createdDate: Optional[str] = None


# --- Vendor Payment ---

class PaymentApply(BaseModel):
    doc: RecordRef  # bill being paid
    amount: float


class VendorPaymentCreate(BaseModel):
    entity: RecordRef  # vendor ref
    tranDate: date
    account: RecordRef  # bank account
    amount: float
    status: str = "pendingApproval"
    approver: Optional[RecordRef] = None
    memo: Optional[str] = None
    apply: List[PaymentApply] = Field(default_factory=list)


class VendorPayment(VendorPaymentCreate):
    id: str
    createdDate: Optional[str] = None


# --- Expense (Reimbursement) ---

class ExpenseLineItem(BaseModel):
    category: Optional[RecordRef] = None
    amount: float
    memo: Optional[str] = None
    receipt: Optional[str] = None


class ExpenseCreate(BaseModel):
    employee: RecordRef
    tranDate: date
    amount: float
    memo: Optional[str] = None
    category: Optional[RecordRef] = None
    approvalStatus: str = "pendingApproval"
    expenseList: List[ExpenseLineItem] = Field(default_factory=list)


class Expense(ExpenseCreate):
    id: str
    createdDate: Optional[str] = None


# --- Custom records (not in standard NetSuite API) ---

class BankEntry(BaseModel):
    id: str
    tranDate: date
    amount: float
    type: str  # "debit" or "credit"
    description: str = ""
    account: Optional[RecordRef] = None
    matched: bool = False
    matchedTo: Optional[str] = None  # vendorBill id


class CreditCardInvoice(BaseModel):
    id: str
    tranDate: date
    amount: float
    vendor: str
    cardLast4: str
    category: Optional[str] = None
    matched: bool = False
    matchedTo: Optional[str] = None


class Accrual(BaseModel):
    id: str
    period: str  # "2024-01"
    vendor: RecordRef
    amount: float
    account: Optional[RecordRef] = None
    status: str = "pending"  # pending, posted, reversed


# --- SuiteQL ---

class SuiteQLRequest(BaseModel):
    q: str


class SuiteQLResponse(BaseModel):
    items: List[dict]
    hasMore: bool = False
    totalResults: Optional[int] = None


# --- Generic list response ---

class NetSuiteListResponse(BaseModel):
    items: List[dict]
    hasMore: bool = False
    totalResults: int = 0
    offset: int = 0
    count: int = 0
