# P2P ShareChat — Worktree Tasks v2 (Revised)

## Key Changes from v1
- **Agents are separate from mock servers** — different repos/tasks
- **Real API schema compliance** — NetSuite REST API Browser + Spotdraft API docs
- **7 independent worktrees** (was 6) — cleaner separation of concerns

---

## Dependency Graph

```
WT1 (NetSuite Mock) ──────┐
                           ├──→ WT6 (Agent Tools) ──→ WT7 (Agent System)
WT2 (Spotdraft Mock) ─────┘        ↑
                                   │
WT3 (Config + Schemas) ────────────┘

WT4 (Seed Data - NetSuite) ──→ WT1
WT5 (Seed Data - Spotdraft) ─→ WT2
```

**Wave 1 (parallel)**: WT3
**Wave 2 (parallel, after WT3)**: WT1, WT2, WT4, WT5
**Wave 3 (after Wave 2)**: WT6
**Wave 4 (after WT6 + WT1 + WT2)**: WT7

---

## WT1: NetSuite Mock Server (Mock Service)

**Branch**: `Postergully/netsuite-mock`
**Directory**: `mock_servers/netsuite_mock/`
**Depends on**: WT3 (schemas for validation), WT4 (seed data)
**Type**: Standalone service (separate from agents)
**Estimated files**: 11

### Deliverables
FastAPI server implementing NetSuite REST API subset based on **real NetSuite REST API Browser** (2025.2).

### API Reference
**NetSuite REST API Browser**: https://system.netsuite.com/help/helpcenter/en_US/APIs/REST_API_Browser/record/v1/2025.2/index.html

Key endpoints we need:
- `vendor` record type → `/record/v1/vendor`
- `vendorBill` (invoice) → `/record/v1/vendorBill`
- `vendorPayment` → `/record/v1/vendorPayment`
- `expense` (reimbursement) → `/record/v1/expense`
- Custom saved search → `/query/v1/suiteql` for reports

### Files to create
```
mock_servers/__init__.py
mock_servers/netsuite_mock/__init__.py
mock_servers/netsuite_mock/app.py              # FastAPI app, CORS, routers
mock_servers/netsuite_mock/auth.py             # OAuth 1.0a (TBA) implementation
mock_servers/netsuite_mock/db.py               # In-memory DB with seed data loader
mock_servers/netsuite_mock/models.py           # NetSuite record models (vendor, vendorBill, etc.)
mock_servers/netsuite_mock/routes/__init__.py
mock_servers/netsuite_mock/routes/vendor.py    # POST/GET/PUT/DELETE /record/v1/vendor
mock_servers/netsuite_mock/routes/vendor_bill.py  # POST/GET /record/v1/vendorBill
mock_servers/netsuite_mock/routes/vendor_payment.py  # POST/GET /record/v1/vendorPayment
mock_servers/netsuite_mock/routes/expense.py   # POST/GET /record/v1/expense (reimbursements)
mock_servers/netsuite_mock/routes/suiteql.py   # POST /query/v1/suiteql (for reports/metrics)
mock_servers/netsuite_mock/routes/bank.py      # Custom endpoints for bank entries/CC invoices
README.md                                       # Startup instructions, API examples
```

### NetSuite Auth Spec (OAuth 1.0a / TBA)
NetSuite uses **OAuth 1.0a** (Token-Based Authentication):
- Consumer Key/Secret (integration credentials)
- Token ID/Secret (user credentials)
- HMAC-SHA256 signature generation
- OAuth header: `Authorization: OAuth realm="...", oauth_consumer_key="...", oauth_token="...", oauth_signature="...", ...`

**For mock**: Accept any `Authorization: Bearer mock-netsuite-token-*` for simplicity, but document the real TBA flow.

### Endpoint Specifications (matching NetSuite REST API)

#### Vendor Management
```
POST   /record/v1/vendor
GET    /record/v1/vendor/{id}
PUT    /record/v1/vendor/{id}
DELETE /record/v1/vendor/{id}
GET    /record/v1/vendor?q=companyName LIKE 'Google%'  # Search
```

Request/Response models match NetSuite `vendor` record:
```json
{
  "companyName": "Google LLC",
  "isPerson": false,
  "email": "ap@google.com",
  "phone": "+1-650-123-4567",
  "taxIdNum": "AABCG1234E",  // PAN in India
  "gstIdNum": "29AABCG1234E1ZF",  // GST
  "accountNumber": "12345678901234",
  "terms": {"id": "5"},  // Payment terms: Net 30
  "category": {"id": "2"},  // Vendor category
  "subsidiary": {"id": "1"}
}
```

#### Invoice (Vendor Bill) Management
```
POST   /record/v1/vendorBill
GET    /record/v1/vendorBill/{id}
GET    /record/v1/vendorBill?q=entity.id='123' AND status='pendingApproval'
```

Model:
```json
{
  "entity": {"id": "123"},  // vendor ref
  "tranId": "INV-2024-001",
  "tranDate": "2024-01-15",
  "dueDate": "2024-02-14",
  "amount": 12000.00,
  "currency": {"id": "1"},  // INR
  "approvalStatus": "pendingApproval",
  "item": [  // Line items
    {
      "item": {"id": "10"},
      "description": "Cloud Services - Jan 2024",
      "amount": 12000.00,
      "account": {"id": "500"}
    }
  ]
}
```

#### Payment Management
```
POST   /record/v1/vendorPayment
GET    /record/v1/vendorPayment/{id}
GET    /record/v1/vendorPayment?q=status='pendingApproval'
```

Model:
```json
{
  "entity": {"id": "123"},
  "tranDate": "2024-01-20",
  "account": {"id": "100"},  // Bank account
  "amount": 12000.00,
  "status": "pendingApproval",
  "approver": {"id": "5"},
  "apply": [  // Bills being paid
    {"doc": {"id": "456"}, "amount": 12000.00}
  ]
}
```

#### Reimbursements (Expense)
```
POST   /record/v1/expense
GET    /record/v1/expense/{id}
GET    /record/v1/expense?q=employee.id='789' AND approvalStatus='pendingApproval'
```

Model:
```json
{
  "employee": {"id": "789"},
  "tranDate": "2024-01-10",
  "amount": 450.00,
  "memo": "Travel expense - Mumbai trip",
  "category": {"id": "3"},  // Travel
  "approvalStatus": "pendingApproval",
  "expenseList": [
    {
      "category": {"id": "3"},
      "amount": 450.00,
      "receipt": "https://..."
    }
  ]
}
```

#### Reports/Metrics (SuiteQL)
```
POST   /query/v1/suiteql
Body: {"q": "SELECT COUNT(*) FROM vendorBill WHERE TRUNC(tranDate) >= '2024-01-01'"}
```

Response:
```json
{
  "items": [{"count": 342}],
  "hasMore": false
}
```

#### Custom Endpoints (for bank ops, not in NetSuite API)
```
POST   /api/custom/bank-entries           # Create bank entry
POST   /api/custom/bank-entries/batch     # Batch create
GET    /api/custom/cc-invoices             # Credit card invoices
GET    /api/custom/accruals                # Accrual tracking data
```

### Acceptance Criteria
- Server starts: `uvicorn mock_servers.netsuite_mock.app:app --port 8081`
- All endpoints return NetSuite-compliant JSON
- Auth middleware validates Bearer tokens
- SuiteQL endpoint supports basic SELECT queries
- Seed data loaded from `data/seed_data.json`
- README documents all endpoints with curl examples

---

## WT2: Spotdraft Mock Server (Mock Service)

**Branch**: `Postergully/spotdraft-mock`
**Directory**: `mock_servers/spotdraft_mock/`
**Depends on**: WT3 (schemas), WT5 (seed data)
**Type**: Standalone service (separate from agents)
**Estimated files**: 8

### Deliverables
FastAPI server implementing Spotdraft API subset based on **real Spotdraft API docs**.

### API Reference
**Spotdraft API Docs**: https://api.spotdraft.com/api/docs/#section/API-Reference

Key endpoints we need:
- Contracts API → `/contracts/`
- Documents API → `/documents/`
- Parties API → `/parties/` (vendors)
- Templates API → `/templates/` (contract templates)

### Files to create
```
mock_servers/spotdraft_mock/__init__.py
mock_servers/spotdraft_mock/app.py             # FastAPI app
mock_servers/spotdraft_mock/auth.py            # API key auth (X-API-Key header)
mock_servers/spotdraft_mock/db.py              # In-memory DB
mock_servers/spotdraft_mock/models.py          # Spotdraft models
mock_servers/spotdraft_mock/routes/__init__.py
mock_servers/spotdraft_mock/routes/contracts.py   # GET /contracts/, /contracts/{id}
mock_servers/spotdraft_mock/routes/documents.py   # GET /documents/, POST /documents/
mock_servers/spotdraft_mock/routes/parties.py     # GET /parties/ (vendor entities)
README.md
```

### Spotdraft Auth Spec
- API Key authentication via `X-API-Key` header
- Mock key: `mock-spotdraft-key-*` accepted
- Real format: `sd_live_...` or `sd_test_...`

### Endpoint Specifications (matching Spotdraft API)

#### Contracts
```
GET    /contracts/                        # List all contracts
GET    /contracts/{contract_id}/          # Get contract detail
POST   /contracts/                        # Create contract
GET    /contracts/?party_id={id}          # Filter by party (vendor)
```

Model (from Spotdraft docs):
```json
{
  "id": "con_abc123",
  "name": "Master Services Agreement - Google",
  "status": "executed",  // draft, sent, executed, expired
  "party_ids": ["party_xyz"],
  "template_id": "tmpl_001",
  "contract_value": 1000000.00,
  "currency": "INR",
  "start_date": "2024-01-01",
  "end_date": "2025-12-31",
  "created_at": "2024-01-01T10:00:00Z",
  "signed_at": "2024-01-05T15:30:00Z",
  "document_url": "https://spotdraft.s3.../contract.pdf"
}
```

#### Documents
```
GET    /documents/                        # List documents
GET    /documents/{doc_id}/               # Get document detail
POST   /documents/                        # Upload document
```

Model:
```json
{
  "id": "doc_def456",
  "name": "Google - PAN Card.pdf",
  "type": "kyc_document",
  "party_id": "party_xyz",
  "uploaded_at": "2024-01-02T09:00:00Z",
  "status": "verified",  // pending, verified, rejected
  "file_url": "https://spotdraft.s3.../doc.pdf"
}
```

#### Parties (Vendors)
```
GET    /parties/                          # List parties
GET    /parties/{party_id}/               # Get party detail
POST   /parties/                          # Create party
```

Model:
```json
{
  "id": "party_xyz",
  "name": "Google LLC",
  "type": "vendor",
  "email": "contracts@google.com",
  "phone": "+1-650-123-4567",
  "address": {
    "street": "1600 Amphitheatre Parkway",
    "city": "Mountain View",
    "state": "CA",
    "country": "USA",
    "zipcode": "94043"
  },
  "tax_id": "AABCG1234E",  // PAN
  "created_at": "2023-12-01T10:00:00Z"
}
```

### Custom Endpoint for Onboarding Status
```
GET    /api/custom/onboarding/{party_id}/
```

Response:
```json
{
  "party_id": "party_xyz",
  "party_name": "Google LLC",
  "overall_status": "complete",  // pending, in_progress, complete, blocked
  "kyc_status": "verified",
  "documents_received": ["PAN", "GST", "Bank Details", "MSA"],
  "documents_pending": [],
  "contracts": [
    {"id": "con_abc123", "status": "executed", "type": "MSA"}
  ]
}
```

### Acceptance Criteria
- Server starts: `uvicorn mock_servers.spotdraft_mock.app:app --port 8082`
- All endpoints return Spotdraft-compliant JSON
- API key auth works correctly
- Cross-reference with NetSuite vendor IDs via `party.tax_id` = NetSuite `vendor.taxIdNum`
- README documents API with curl examples

---

## WT3: Config, Schemas & Shared Utilities

**Branch**: `Postergully/config-schemas`
**Directory**: `p2p_agents/config/`, `p2p_agents/schemas/`
**Depends on**: Nothing
**Type**: Shared library for both mock servers and agents
**Estimated files**: 9

### Deliverables
All Pydantic models, config settings, constants. Used by BOTH mock servers (for validation) and agent tools (for API calls).

### Files to create
```
p2p_agents/__init__.py
p2p_agents/config/__init__.py
p2p_agents/config/settings.py         # BaseSettings with env vars
p2p_agents/config/constants.py        # Priority vendors, thresholds
p2p_agents/schemas/__init__.py
p2p_agents/schemas/common.py          # APIResponse, Error models
p2p_agents/schemas/netsuite.py        # NetSuite record models (vendor, vendorBill, etc.)
p2p_agents/schemas/spotdraft.py       # Spotdraft models (contract, document, party)
p2p_agents/schemas/agent_responses.py # Agent tool response models
```

### Config Spec
```python
from pydantic_settings import BaseSettings

class P2PSettings(BaseSettings):
    # Mode
    mode: str = "MOCK"  # MOCK or LIVE

    # NetSuite
    netsuite_base_url: str = "http://localhost:8081"
    netsuite_account_id: str = "TSTDRV123456"
    netsuite_consumer_key: str = "mock-consumer-key"
    netsuite_consumer_secret: str = "mock-consumer-secret"
    netsuite_token_id: str = "mock-token-id"
    netsuite_token_secret: str = "mock-token-secret"

    # Spotdraft
    spotdraft_base_url: str = "http://localhost:8082"
    spotdraft_api_key: str = "mock-spotdraft-key-xxx"

    # Notifications
    slack_webhook_url: str = ""
    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_from: str = "p2p@sharechat.com"

    class Config:
        env_prefix = "P2P_"
        env_file = ".env"

def get_settings() -> P2PSettings:
    return P2PSettings()
```

### Schema Examples

**netsuite.py**:
```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

class NetsuiteVendor(BaseModel):
    id: Optional[str] = None
    companyName: str
    isPerson: bool = False
    email: str
    phone: Optional[str] = None
    taxIdNum: str  # PAN
    gstIdNum: Optional[str] = None
    accountNumber: str
    terms: dict  # {"id": "5"} for payment terms
    category: Optional[dict] = None
    subsidiary: dict = {"id": "1"}

class NetsuiteVendorBill(BaseModel):
    id: Optional[str] = None
    entity: dict  # {"id": vendor_id}
    tranId: str  # Invoice number
    tranDate: date
    dueDate: date
    amount: float
    currency: dict = {"id": "1"}
    approvalStatus: str = "pendingApproval"
    item: List[dict]  # Line items
```

**spotdraft.py**:
```python
class SpotdraftContract(BaseModel):
    id: Optional[str] = None
    name: str
    status: str  # draft, sent, executed, expired
    party_ids: List[str]
    template_id: Optional[str] = None
    contract_value: Optional[float] = None
    currency: str = "INR"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    document_url: Optional[str] = None
```

### Constants
```python
# Priority vendors (key accounts)
PRIORITY_VENDORS = ["Google", "Agora", "Tencent"]

# Reimbursement auto-approve limit (INR)
REIMBURSEMENT_AUTO_APPROVE_LIMIT = 5000

# Payment aging buckets (days)
AGING_BUCKETS = [(0, 30), (30, 60), (60, 90), (90, None)]

# Approval reminder threshold
APPROVAL_REMINDER_THRESHOLD_DAYS = 3

# NetSuite payment terms IDs
PAYMENT_TERMS = {
    "net_30": "5",
    "net_60": "6",
    "net_90": "7",
}
```

### Acceptance Criteria
- All schemas importable and validate correctly
- Settings loads from env vars with defaults
- Can be used by both mock servers and agent tools
- No circular dependencies

---

## WT4: Seed Data - NetSuite

**Branch**: `Postergully/seed-netsuite`
**Directory**: `mock_servers/netsuite_mock/data/`
**Depends on**: WT3 (schemas for validation)
**Type**: Data only
**Estimated files**: 1 (large JSON)

### Deliverables
Realistic seed data following NetSuite record structures.

### Files to create
```
mock_servers/netsuite_mock/data/seed_data.json
```

### Data Structure
```json
{
  "vendors": [
    // 20+ vendors including Google, Agora, Tencent
    // Mix of active, onboarding, inactive
  ],
  "vendorBills": [
    // 40+ invoices across vendors
    // Mix of paid, pendingApproval, overdue
  ],
  "vendorPayments": [
    // 30+ payments
    // Mix of completed, pendingApproval, scheduled
  ],
  "expenses": [
    // 15+ reimbursement claims
    // Mix of pendingApproval, approved, rejected
  ],
  "bankEntries": [
    // 25+ bank entries (custom)
  ],
  "ccInvoices": [
    // 20+ credit card transactions (custom)
  ],
  "accruals": [
    // 10+ monthly accrual records (custom)
  ]
}
```

### Data Requirements
- Include 3+ priority vendors (Google, Agora, Tencent)
- Include 5+ overdue payments (for delay email testing)
- Include 3+ vendors in onboarding status
- Include 2+ months with missed accruals
- Include 5+ unmatched CC transactions
- Use realistic Indian company names, INR amounts
- PAN format: `AABCG1234E`
- GST format: `29AABCG1234E1ZF`
- NetSuite vendor IDs match Spotdraft party tax_id

### Acceptance Criteria
- Valid JSON, loads correctly
- Passes Pydantic schema validation
- Cross-references consistent (vendor IDs in bills/payments match vendors)

---

## WT5: Seed Data - Spotdraft

**Branch**: `Postergully/seed-spotdraft`
**Directory**: `mock_servers/spotdraft_mock/data/`
**Depends on**: WT3 (schemas), WT4 (for vendor ID mapping)
**Type**: Data only
**Estimated files**: 1

### Deliverables
Realistic seed data following Spotdraft API structures.

### Files to create
```
mock_servers/spotdraft_mock/data/seed_data.json
```

### Data Structure
```json
{
  "parties": [
    // 20+ parties matching NetSuite vendors
    // party.tax_id = netsuite vendor.taxIdNum
  ],
  "contracts": [
    // 15+ contracts (MSA, NDA, SOW)
    // Link to parties via party_ids
  ],
  "documents": [
    // 30+ documents (KYC, agreements)
    // Link to parties via party_id
  ],
  "onboarding": [
    // Onboarding status for vendors
    // Include 3+ in progress, 2+ blocked
  ]
}
```

### Acceptance Criteria
- Valid JSON, loads correctly
- Party tax_id matches NetSuite vendor taxIdNum
- Contracts link to valid party_ids
- Documents have realistic types (PAN, GST, Bank Statement, MSA, NDA)

---

## WT6: Agent Tools

**Branch**: `Postergully/agent-tools`
**Directory**: `p2p_agents/tools/`
**Depends on**: WT3 (schemas, config), WT1 + WT2 (mock servers to test against)
**Type**: Agent tool library
**Estimated files**: 7

### Deliverables
All 32 tool functions as ADK FunctionTools.

### Files to create
```
p2p_agents/tools/__init__.py
p2p_agents/tools/payment_tools.py      # 8 tools
p2p_agents/tools/invoice_tools.py      # 6 tools
p2p_agents/tools/vendor_tools.py       # 6 tools
p2p_agents/tools/reporting_tools.py    # 6 tools
p2p_agents/tools/bank_ops_tools.py     # 6 tools
p2p_agents/tools/helpers.py            # Auth helpers, HTTP client
```

### Implementation Pattern
Each tool:
- Uses `httpx` for HTTP calls
- Calls NetSuite or Spotdraft mock API
- Returns `dict` (ADK-compatible)
- Has comprehensive docstring for LLM

Example:
```python
import httpx
from p2p_agents.config.settings import get_settings
from p2p_agents.tools.helpers import get_netsuite_token

def get_payment_status(invoice_number: str = "", vendor_name: str = "") -> dict:
    """Retrieves payment status from NetSuite by invoice number or vendor name.

    Args:
        invoice_number: Invoice number to look up (e.g., "INV-2024-001")
        vendor_name: Vendor name to search for (e.g., "Google")

    Returns:
        dict with keys: status, vendor, amount, due_date, payment_date, invoice_number
    """
    settings = get_settings()
    token = get_netsuite_token(settings)

    if invoice_number:
        url = f"{settings.netsuite_base_url}/record/v1/vendorPayment"
        params = {"q": f"tranId='{invoice_number}'"}
    elif vendor_name:
        url = f"{settings.netsuite_base_url}/record/v1/vendor"
        params = {"q": f"companyName LIKE '{vendor_name}%'"}
        # Then fetch payments for that vendor
    else:
        return {"error": "Provide either invoice_number or vendor_name"}

    resp = httpx.get(url, params=params, headers={"Authorization": f"Bearer {token}"})
    return resp.json()
```

### Tool List (32 total)
See worktree_tasks.md WT4 for full list.

### Acceptance Criteria
- All 32 tools importable
- Each tool has correct signature and docstring
- Tools successfully call mock APIs
- Returns structured dict with expected keys
- Error handling for API failures

---

## WT7: Agent System

**Branch**: `Postergully/agent-system`
**Directory**: `p2p_agents/agent.py`, `p2p_agents/__init__.py`, `tests/`
**Depends on**: WT6 (tools), mock servers running
**Type**: ADK multi-agent application
**Estimated files**: 8

### Deliverables
6 ADK agents (1 coordinator + 5 specialists) with full instructions encoding 17 skills.

### Files to create
```
p2p_agents/agent.py                # All 6 agent definitions
p2p_agents/__init__.py             # Expose root_agent
tests/__init__.py
tests/test_coordinator.py
tests/test_payment_agent.py
tests/test_invoice_agent.py
tests/test_vendor_agent.py
tests/test_reporting_agent.py
tests/test_bank_ops_agent.py
requirements.txt
README.md                          # How to run adk web
```

### Agent Structure
```python
from google.adk.agents import LlmAgent
from p2p_agents.tools.payment_tools import *
from p2p_agents.tools.invoice_tools import *
# ... etc

MODEL = "gemini-2.5-flash"

# Define 5 specialists
payment_agent = LlmAgent(
    name="payment_agent",
    model=MODEL,
    description="Handles all payment workflows...",
    instruction="""
    You are the Payment Agent for ShareChat's P2P finance team.

    ## Your Skills

    ### Skill 1: Payment Status Lookup
    When a user asks about payment status:
    1. If they provide an invoice number → call get_payment_status(invoice_number=...)
    2. If they provide only a vendor name → call get_payment_status(vendor_name=...)
    3. If the vendor is in the priority list → also call send_holding_reply
    4. Present the status clearly: amount, due date, current state, expected payment date

    ... (all 4 skills) ...
    """,
    tools=[
        get_payment_status,
        get_pending_approvals,
        # ... all 8 tools
    ],
)

# ... invoice_agent, vendor_agent, reporting_agent, bank_ops_agent ...

# Root coordinator
root_agent = LlmAgent(
    name="p2p_coordinator",
    model=MODEL,
    description="P2P operations coordinator for ShareChat finance",
    instruction="""
    You are the P2P operations assistant for ShareChat's finance team.
    Route queries to specialists:

    - Payment/reimbursement queries → payment_agent
    - Invoice processing queries → invoice_agent
    - Vendor onboarding queries → vendor_agent
    - Reports/metrics queries → reporting_agent
    - Bank operations queries → bank_ops_agent

    Ask clarifying questions if intent is ambiguous.
    """,
    sub_agents=[
        payment_agent,
        invoice_agent,
        vendor_agent,
        reporting_agent,
        bank_ops_agent,
    ],
)
```

### Test Structure
Each test file:
- Test agent is importable
- Test tool count matches expected
- Test tool functions are callable
- Integration test: query → agent → response

### Acceptance Criteria
- `from p2p_agents import root_agent` works
- `adk web p2p_agents` launches UI
- Coordinator routes correctly to all 5 specialists
- Each specialist executes its primary workflow end-to-end
- All tests pass

---

## Execution Plan: Creating Worktrees

```bash
# Base directory
cd /Users/kalicharanshukla/conductor/workspaces/adk-python

# Wave 1: Config + Schemas (foundation)
git worktree add oslo Postergully/config-schemas
# Work in oslo: implement WT3

# Wave 2: Mock servers + seed data (parallel after WT3)
git worktree add tokyo Postergully/netsuite-mock
git worktree add seoul Postergully/spotdraft-mock
git worktree add berlin Postergully/seed-netsuite
git worktree add paris Postergully/seed-spotdraft
# Work in tokyo, seoul, berlin, paris in parallel

# Wave 3: Agent tools (after Wave 2)
git worktree add london Postergully/agent-tools
# Work in london: implement WT6

# Wave 4: Agent system (after WT6)
git worktree add sydney Postergully/agent-system
# Work in sydney: implement WT7
```

---

## Summary Table

| WT | Branch | City | Type | Depends On | Files | Est Hours |
|----|--------|------|------|------------|-------|-----------|
| WT3 | `config-schemas` | oslo | Library | - | 9 | 3h |
| WT1 | `netsuite-mock` | tokyo | Service | WT3, WT4 | 11 | 6h |
| WT2 | `spotdraft-mock` | seoul | Service | WT3, WT5 | 8 | 4h |
| WT4 | `seed-netsuite` | berlin | Data | WT3 | 1 | 2h |
| WT5 | `seed-spotdraft` | paris | Data | WT3, WT4 | 1 | 1h |
| WT6 | `agent-tools` | london | Library | WT3, WT1, WT2 | 7 | 5h |
| WT7 | `agent-system` | sydney | App | WT6 | 8 | 4h |
| **Total** | | | | | **45** | **25h** |
