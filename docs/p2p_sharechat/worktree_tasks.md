# P2P ShareChat — Worktree Tasks

## Dependency Graph

```
WT1 (NetSuite Mock) ──────┐
                           ├──→ WT4 (Tools) ──→ WT6 (Agents + Integration)
WT2 (Spotdraft Mock) ─────┘        ↑
                                   │
WT3 (Config + Schemas) ────────────┘

WT5 (Seed Data) ──────────→ WT6 (Agents + Integration)
```

WT1, WT2, WT3 can all start in parallel (zero dependencies).
WT4 can start once WT3 is done (needs schemas/config imports).
WT5 can start in parallel with everything (just JSON).
WT6 starts last (needs tools + mock servers running).

---

## WT1: NetSuite Mock Server

**Branch**: `Postergully/netsuite-mock`
**Directory**: `mock_servers/netsuite_mock/`
**Depends on**: Nothing
**Estimated files**: 10

### Deliverables
Create a FastAPI server mimicking NetSuite's REST API with Token-Based Auth.

### Files to create
```
mock_servers/__init__.py
mock_servers/netsuite_mock/__init__.py
mock_servers/netsuite_mock/app.py              # FastAPI app, CORS, mount routers
mock_servers/netsuite_mock/auth.py             # TBA auth: POST /auth/token, dependency for protected routes
mock_servers/netsuite_mock/db.py               # In-memory data store (dict-based, loaded from seed)
mock_servers/netsuite_mock/routes/__init__.py
mock_servers/netsuite_mock/routes/payments.py  # GET /payments/{id}, /payments/search, /payments/pending, /payments/overdue, /payments/stats
mock_servers/netsuite_mock/routes/invoices.py  # POST /invoices, GET /invoices/{id}, /invoices/stats
mock_servers/netsuite_mock/routes/vendors.py   # POST /vendors, GET /vendors/{id}, /vendors/{id}/status, PUT /vendors/{id}
mock_servers/netsuite_mock/routes/reimbursements.py  # GET /reimbursements/pending, POST /reimbursements, POST /reimbursements/{id}/approve
mock_servers/netsuite_mock/routes/bank_entries.py    # POST /bank-entries, POST /bank-entries/batch, GET /cc-invoices
mock_servers/netsuite_mock/routes/accruals.py        # GET /accruals, GET /accruals/check
mock_servers/netsuite_mock/routes/metrics.py         # GET /metrics/p2p, /metrics/invoices, /metrics/payments
```

### Auth spec
- `POST /auth/token` accepts `consumer_key`, `consumer_secret`, `token_id`, `token_secret`
- Returns `{"access_token": "mock-token-xxx", "expires_in": 3600}`
- All other routes require `Authorization: Bearer <token>` header
- Mock tokens: any token starting with `mock-token-` is valid

### Acceptance criteria
- `uvicorn mock_servers.netsuite_mock.app:app --port 8081` starts clean
- All endpoints return realistic JSON responses
- Auth middleware rejects requests without valid token
- Returns appropriate HTTP status codes (200, 201, 401, 404)

---

## WT2: Spotdraft Mock Server

**Branch**: `Postergully/spotdraft-mock`
**Directory**: `mock_servers/spotdraft_mock/`
**Depends on**: Nothing
**Estimated files**: 6

### Deliverables
Create a FastAPI server mimicking Spotdraft's API with API key auth.

### Files to create
```
mock_servers/spotdraft_mock/__init__.py
mock_servers/spotdraft_mock/app.py             # FastAPI app
mock_servers/spotdraft_mock/auth.py            # API key auth: X-API-Key header validation
mock_servers/spotdraft_mock/db.py              # In-memory data store
mock_servers/spotdraft_mock/routes/__init__.py
mock_servers/spotdraft_mock/routes/contracts.py   # GET /contracts/{vendor_id}
mock_servers/spotdraft_mock/routes/documents.py   # GET /documents/{vendor_id}, GET /onboarding/{vendor_id}
```

### Auth spec
- All routes require `X-API-Key: <key>` header
- Mock key: `mock-spotdraft-key-xxx` is valid
- `POST /auth/verify` to validate a key

### Data model
- Contracts: `{id, vendor_id, type, status, signed_date, expiry_date, document_url}`
- Documents: `{id, vendor_id, doc_type, filename, uploaded_date, status}`
- Onboarding: `{vendor_id, kyc_status, documents_received[], documents_pending[], overall_status}`

### Acceptance criteria
- `uvicorn mock_servers.spotdraft_mock.app:app --port 8082` starts clean
- Returns realistic vendor contract/document data
- API key auth works correctly

---

## WT3: Config, Schemas & Shared Utilities

**Branch**: `Postergully/config-schemas`
**Directory**: `p2p_agents/config/`, `p2p_agents/schemas/`, `p2p_agents/__init__.py`
**Depends on**: Nothing
**Estimated files**: 9

### Deliverables
All Pydantic models, config settings, and constants used by tools and agents.

### Files to create
```
p2p_agents/__init__.py                # Empty for now (will expose root_agent later)
p2p_agents/config/__init__.py
p2p_agents/config/settings.py         # BaseSettings with env vars for URLs, auth, MOCK/LIVE toggle
p2p_agents/config/constants.py        # Priority vendor list, policy thresholds, aging buckets
p2p_agents/schemas/__init__.py
p2p_agents/schemas/common.py          # APIResponse, PaginatedResponse, ErrorResponse
p2p_agents/schemas/payment.py         # PaymentStatus, PendingApproval, ReimbursementClaim
p2p_agents/schemas/invoice.py         # InvoiceData, OCRResult, BankUploadRecord
p2p_agents/schemas/vendor.py          # Vendor, VendorOnboardingStatus, KYCResult
```

### Config spec (`settings.py`)
```python
class P2PSettings(BaseSettings):
    mode: str = "MOCK"                              # MOCK or LIVE
    netsuite_base_url: str = "http://localhost:8081"
    netsuite_consumer_key: str = "mock-consumer-key"
    netsuite_consumer_secret: str = "mock-consumer-secret"
    netsuite_token_id: str = "mock-token-id"
    netsuite_token_secret: str = "mock-token-secret"
    spotdraft_base_url: str = "http://localhost:8082"
    spotdraft_api_key: str = "mock-spotdraft-key-xxx"
    slack_webhook_url: str = ""
    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_from: str = "p2p@sharechat.com"

    class Config:
        env_prefix = "P2P_"
```

### Constants spec (`constants.py`)
```python
PRIORITY_VENDORS = ["Google", "Agora", "Tencent"]
REIMBURSEMENT_AUTO_APPROVE_LIMIT = 5000  # INR
AGING_BUCKETS = [(0, 30), (30, 60), (60, 90), (90, None)]
APPROVAL_REMINDER_THRESHOLD_DAYS = 3
```

### Acceptance criteria
- All schemas importable: `from p2p_agents.schemas.payment import PaymentStatus`
- Settings loads from env vars with sensible defaults
- No dependency on mock servers or tools

---

## WT4: All 32 Tool Functions

**Branch**: `Postergully/agent-tools`
**Directory**: `p2p_agents/tools/`
**Depends on**: WT3 (config + schemas)
**Estimated files**: 7

### Deliverables
All 32 tool functions organized by agent domain. Each tool is a Python function with docstring (for ADK FunctionTool auto-wrapping) that calls the mock server via `httpx`.

### Files to create
```
p2p_agents/tools/__init__.py
p2p_agents/tools/payment_tools.py      # 8 tools
p2p_agents/tools/invoice_tools.py      # 6 tools
p2p_agents/tools/vendor_tools.py       # 6 tools
p2p_agents/tools/reporting_tools.py    # 6 tools
p2p_agents/tools/bank_ops_tools.py     # 6 tools
p2p_agents/tools/notification_tools.py # shared: send_slack, send_email helpers
```

### Tool implementation pattern
Every tool follows this pattern:
```python
import httpx
from p2p_agents.config.settings import get_settings

def get_payment_status(invoice_number: str = "", vendor_name: str = "") -> dict:
    """Retrieves payment status from NetSuite by invoice number or vendor name.

    Args:
        invoice_number: The invoice number to look up (e.g., "INV-2024-001")
        vendor_name: The vendor name to search for (e.g., "Google")

    Returns:
        dict with keys: status, vendor, amount, due_date, payment_date, invoice_number
    """
    settings = get_settings()
    token = _get_netsuite_token(settings)
    if invoice_number:
        resp = httpx.get(f"{settings.netsuite_base_url}/api/payments/{invoice_number}",
                         headers={"Authorization": f"Bearer {token}"})
    elif vendor_name:
        resp = httpx.get(f"{settings.netsuite_base_url}/api/payments/search",
                         params={"vendor": vendor_name},
                         headers={"Authorization": f"Bearer {token}"})
    else:
        return {"error": "Provide either invoice_number or vendor_name"}
    return resp.json()
```

### Tool list per file

**payment_tools.py** (8):
1. `get_payment_status(invoice_number, vendor_name)` → NetSuite
2. `get_pending_approvals()` → NetSuite
3. `send_approval_reminder(approver_name, transaction_ids)` → Slack/Email
4. `send_payment_delay_email(vendor_name, vendor_type, amount, days_overdue)` → Email
5. `get_priority_vendor_list()` → Config
6. `send_holding_reply(vendor_name, invoice_number)` → Email
7. `get_reimbursement_claims(employee_id)` → NetSuite
8. `process_reimbursement(employee_id, amount, category, description)` → NetSuite

**invoice_tools.py** (6):
1. `extract_invoice_data_ocr(file_path)` → OCR mock (returns structured JSON)
2. `create_netsuite_invoice(vendor_name, invoice_number, amount, date, line_items)` → NetSuite
3. `validate_invoice_data(invoice_data)` → Local validation
4. `convert_document_format(file_path, target_format)` → Local
5. `generate_bank_upload_file(bank_name, payment_ids)` → Local + NetSuite
6. `get_invoice_from_email(email_subject, sender)` → Email mock

**vendor_tools.py** (6):
1. `create_vendor(name, pan, gst, bank_account, contact_email, payment_terms)` → NetSuite
2. `get_vendor_onboarding_status(vendor_id)` → NetSuite + Spotdraft
3. `run_kyc_check(vendor_name, pan, gst)` → KYC mock
4. `get_vendor_documents(vendor_id)` → Spotdraft
5. `update_vendor_status(vendor_id, status)` → NetSuite
6. `generate_onboarding_report()` → NetSuite + Spotdraft

**reporting_tools.py** (6):
1. `get_invoices_processed_count(month)` → NetSuite
2. `get_payments_made_count(month)` → NetSuite
3. `get_p2p_efficiency_metrics(month)` → NetSuite
4. `check_missed_accruals(month)` → NetSuite
5. `get_accrual_data(month)` → NetSuite
6. `generate_p2p_report(report_type, date_range, filters)` → Local

**bank_ops_tools.py** (6):
1. `parse_bank_statement(file_content)` → Local parser
2. `create_bank_entry(date, amount, description, account)` → NetSuite
3. `get_credit_card_invoices(card_id, month)` → NetSuite
4. `match_cc_transactions(cc_transactions, invoices)` → Local
5. `flag_discrepancies(unmatched_items)` → Local
6. `generate_reconciliation_report(matched, unmatched, period)` → Local

**notification_tools.py** (shared helpers, not directly agent tools):
- `_send_slack_message(webhook_url, message)` → HTTP POST
- `_send_email(to, subject, body)` → SMTP mock
- `_get_netsuite_token(settings)` → Auth helper, cached

### Acceptance criteria
- All 32 functions importable with correct signatures and docstrings
- Each function makes HTTP calls to mock server URLs from config
- Functions return `dict` (ADK-compatible)
- `_get_netsuite_token` caches token for session duration

---

## WT5: Seed Data

**Branch**: `Postergully/seed-data`
**Directory**: `mock_servers/netsuite_mock/data/`, `mock_servers/spotdraft_mock/data/`
**Depends on**: Nothing (just JSON)
**Estimated files**: 2

### Deliverables
Realistic sample data for both mock servers. Should cover enough variety to test all workflows.

### Files to create
```
mock_servers/netsuite_mock/data/seed_data.json
mock_servers/spotdraft_mock/data/seed_data.json
```

### NetSuite seed data should include
```json
{
  "vendors": [
    // 15+ vendors including priority ones (Google, Agora, Tencent)
    // Mix of: active, onboarding, inactive
    // Fields: id, name, pan, gst, bank_account, contact_email, payment_terms, status, created_date
  ],
  "invoices": [
    // 30+ invoices across different vendors
    // Mix of: paid, pending, overdue, processing
    // Fields: id, vendor_id, amount, currency, date, due_date, status, line_items[]
  ],
  "payments": [
    // 25+ payments
    // Mix of: completed, pending_approval, scheduled, failed
    // Fields: id, invoice_id, vendor_id, amount, status, payment_date, approver, approval_status
  ],
  "reimbursements": [
    // 10+ reimbursement claims
    // Mix of: pending, approved, rejected, processing
    // Fields: id, employee_id, employee_name, amount, category, description, receipts[], status, submitted_date
  ],
  "bank_entries": [
    // 20+ bank entries
    // Fields: id, date, amount, description, account, reference, status
  ],
  "cc_invoices": [
    // 15+ credit card transactions
    // Fields: id, card_id, date, amount, merchant, category, invoice_matched, status
  ],
  "accruals": [
    // 8+ monthly accrual records
    // Fields: id, month, vendor_id, expected_amount, actual_amount, status, notes
  ]
}
```

### Spotdraft seed data should include
```json
{
  "contracts": [
    // 10+ contracts mapped to netsuite vendor IDs
    // Fields: id, vendor_id, type, status, signed_date, expiry_date, document_url
  ],
  "documents": [
    // 20+ documents across vendors
    // Fields: id, vendor_id, doc_type (KYC/agreement/NDA/...), filename, uploaded_date, status
  ],
  "onboarding": [
    // Status records for vendors in onboarding
    // Fields: vendor_id, kyc_status, documents_received[], documents_pending[], overall_status
  ]
}
```

### Key data constraints
- Vendor IDs must match between NetSuite and Spotdraft data
- Include at least 3 vendors with overdue payments (for delay email testing)
- Include at least 2 vendors missing KYC docs (for onboarding testing)
- Include at least 1 month with missed accruals
- Include CC transactions with 3+ unmatched items
- Use realistic Indian company names, INR amounts, PAN/GST formats

### Acceptance criteria
- Valid JSON, loadable by both mock servers
- Cross-references are consistent (vendor IDs match across datasets)
- Enough data variety to exercise all 17 skills

---

## WT6: Agents + Integration

**Branch**: `Postergully/agents-integration`
**Directory**: `p2p_agents/agent.py`, `p2p_agents/__init__.py`, `tests/`
**Depends on**: WT3 + WT4 (schemas, config, tools)
**Estimated files**: 8

### Deliverables
Define all 6 agents with full instructions (encoding 17 skills), wire coordinator to sub-agents, expose `root_agent` for `adk web`.

### Files to create/modify
```
p2p_agents/agent.py         # All 6 agent definitions
p2p_agents/__init__.py      # Expose: from .agent import root_agent
tests/__init__.py
tests/test_payment_agent.py
tests/test_invoice_agent.py
tests/test_vendor_agent.py
tests/test_reporting_agent.py
tests/test_bank_ops_agent.py
requirements.txt
```

### Agent definition pattern
```python
from google.adk.agents import LlmAgent

MODEL = "gemini-2.5-flash"

payment_agent = LlmAgent(
    name="payment_agent",
    model=MODEL,
    description="Handles all payment workflows — status lookups, reimbursement processing, delay notifications, approval reminders, and priority vendor communications",
    instruction="""You are the Payment Agent for ShareChat's P2P finance team.

    ## Your Skills

    ### Skill 1: Payment Status Lookup
    When a user asks about payment status:
    1. If they provide an invoice number → call get_payment_status(invoice_number=...)
    ...

    ### Skill 2: Approval Chasing
    ...
    """,
    tools=[
        get_payment_status,
        get_pending_approvals,
        send_approval_reminder,
        send_payment_delay_email,
        get_priority_vendor_list,
        send_holding_reply,
        get_reimbursement_claims,
        process_reimbursement,
    ],
)

# ... same for all 5 specialists ...

root_agent = LlmAgent(
    name="p2p_coordinator",
    model=MODEL,
    description="P2P operations coordinator for ShareChat finance",
    instruction="...",  # Routing instruction
    sub_agents=[payment_agent, invoice_agent, vendor_agent, reporting_agent, bank_ops_agent],
)
```

### Test pattern
Each test file should have at least:
- Test that agent is importable and has correct tools count
- Test that each tool function is callable with mock data
- Integration test: start mock server → call agent workflow → verify response

### Acceptance criteria
- `from p2p_agents import root_agent` works
- `adk web p2p_agents` launches the UI
- Coordinator correctly routes to each specialist (test 5 sample queries)
- Each specialist can execute its primary workflow end-to-end against mock servers

---

## Summary: Parallel Execution Plan

```
Time →  ──────────────────────────────────────────────────────►

WT1 [NetSuite Mock]     ████████████░░░░░░░░░░░░░░░░░░░░░░░░░
WT2 [Spotdraft Mock]    ██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
WT3 [Config+Schemas]    ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
WT5 [Seed Data]         ██████████░░░░░░░░░░░░░░░░░░░░░░░░░░░
WT4 [Tools]             ░░░░░░░░████████████░░░░░░░░░░░░░░░░░
                                 (after WT3)
WT6 [Agents+Integration]░░░░░░░░░░░░░░░░░░░████████████████░░
                                            (after WT1-5)
```

**Wave 1 (parallel)**: WT1 + WT2 + WT3 + WT5
**Wave 2**: WT4 (needs WT3)
**Wave 3**: WT6 (needs all)
