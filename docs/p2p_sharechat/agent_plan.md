# P2P ShareChat Agent System — Implementation Plan (v2)
## Using Google Agent Development Kit (ADK)

---

## 1. System Overview

The P2P (Procure-to-Pay) operations team at ShareChat (Sweta's Finance team) handles invoice processing, payment tracking, vendor management, reimbursements, and reporting — primarily through **NetSuite** and **Spotdraft**. We build a **multi-agent system** using Google ADK with a **root coordinator agent** that routes to **5 specialist agents**. Each specialist has **tools** (API connectors) and **skills** (teachable workflows/behaviors that can be improved over time).

### Design Philosophy: Tools + Skills

| Concept | What It Is | Example |
|---------|-----------|---------|
| **Tool** | A Python function that calls an API or performs a computation. Atomic, stateless. | `get_payment_status(invoice_id)` → calls NetSuite API |
| **Skill** | A higher-level workflow encoded in the agent's instruction. Describes *when* and *how* to chain tools together, handle edge cases, and communicate with users. Teachable — you improve skills by updating instructions. | "When a priority vendor asks about payment, first check status, then auto-send a holding reply, then escalate if overdue >30 days" |

Once agents + tools are built, **you improve the system by adding/refining skills** (instruction tuning) — no code changes needed.

---

## 2. Agent Architecture

```
                     ┌─────────────────────────────┐
                     │    P2P Coordinator Agent     │  (Root LlmAgent)
                     │    Routes to 5 specialists   │
                     └──────────────┬──────────────┘
                                    │
        ┌───────────┬───────────────┼───────────────┬───────────┐
        │           │               │               │           │
   ┌────▼────┐ ┌────▼─────┐  ┌─────▼──────┐  ┌────▼────┐ ┌────▼────┐
   │Payment  │ │ Invoice  │  │  Vendor    │  │Reporting│ │Bank Ops │
   │ Agent   │ │  Agent   │  │   Agent    │  │  Agent  │ │  Agent  │
   │         │ │          │  │            │  │         │ │         │
   │8 tools  │ │6 tools   │  │6 tools     │  │6 tools  │ │6 tools  │
   │4 skills │ │3 skills  │  │3 skills    │  │4 skills │ │3 skills │
   └─────────┘ └──────────┘  └────────────┘  └─────────┘ └─────────┘
```

### Total: 6 Agents (1 Coordinator + 5 Specialists), 32 Tools, 17 Skills

---

## 3. Agent Details

---

### Agent 0: `p2p_coordinator` (Root Agent)

| Attribute | Value |
|-----------|-------|
| **Type** | `LlmAgent` with `sub_agents` |
| **Model** | `gemini-2.5-flash` |
| **Role** | Entry point. Routes user intent to correct specialist via ADK auto-transfer. |
| **Tools** | None (pure router) |
| **Sub-agents** | `payment_agent`, `invoice_agent`, `vendor_agent`, `reporting_agent`, `bank_ops_agent` |

**Instruction**:
```
You are the P2P operations assistant for ShareChat's finance team.
Your job is to understand the user's query and route it to the right specialist:

- Payment status, reimbursements, payment delays, approval reminders → payment_agent
- Invoice processing, OCR, document conversion, bank upload files → invoice_agent
- Vendor creation, onboarding, KYC, vendor documents → vendor_agent
- Reports, metrics, accruals, statistics → reporting_agent
- Bank entries, credit card reconciliation → bank_ops_agent

Ask clarifying questions if the intent is ambiguous. Never try to answer domain questions yourself.
```

---

### Agent 1: `payment_agent`
**Handles**: Payment Status, Reimbursements, Payment Delays, Approval Reminders, Priority Vendor Replies

| Attribute | Value |
|-----------|-------|
| **Type** | `LlmAgent` |
| **Description** | "Handles all payment workflows — status lookups, reimbursement processing, delay notifications, approval reminders, and priority vendor communications" |
| **System of Truth** | NetSuite |

#### Tools (8)

| # | Tool | Function | Source |
|---|------|----------|--------|
| 1 | `get_payment_status` | Look up payment by invoice number or vendor name | NetSuite |
| 2 | `get_pending_approvals` | List transactions awaiting approval | NetSuite |
| 3 | `send_approval_reminder` | Send Slack/email reminder to approver | Slack/Email |
| 4 | `send_payment_delay_email` | Notify MSME/foreign vendors of payment delay | Email |
| 5 | `get_priority_vendor_list` | Return key vendors list (Google, Agora, Tencent) | Config |
| 6 | `send_holding_reply` | Auto-reply to priority vendors about payment status | Email |
| 7 | `get_reimbursement_claims` | Fetch pending employee reimbursement claims | NetSuite |
| 8 | `process_reimbursement` | Verify claim against policy, approve/route for approval | NetSuite |

#### Skills (4)

**Skill 1: Payment Status Lookup**
```
When a user asks about payment status:
1. If they provide an invoice number → call get_payment_status(invoice_number=...)
2. If they provide only a vendor name → call get_payment_status(vendor_name=...)
3. If the vendor is in the priority list → also call send_holding_reply
4. Present the status clearly: amount, due date, current state, expected payment date
```

**Skill 2: Approval Chasing**
```
When a user asks to chase approvals or mentions stuck payments:
1. Call get_pending_approvals to get all pending items
2. Group by approver
3. For each approver with items >3 days old → call send_approval_reminder
4. Prioritize based on priority_vendor_list
5. Report back: "Sent reminders to X approvers for Y transactions"
```

**Skill 3: Payment Delay Communication**
```
When user asks to send delay notifications (usually monthly):
1. Query overdue payments from NetSuite
2. Separate into MSME and foreign payment categories
3. For each category → call send_payment_delay_email with appropriate template
4. Report: "Sent delay notifications to X MSME vendors and Y foreign vendors"
```

**Skill 4: Reimbursement Processing**
```
When a user submits or asks about reimbursements:
1. If asking status → call get_reimbursement_claims(employee_id=...)
2. If submitting a new claim → call process_reimbursement with claim details
   - Auto-approve if amount < policy threshold
   - Route to manager if above threshold
   - Flag if missing receipts or policy violations
3. Generate AP team summary when asked
```

#### Workflows

**Workflow A — Payment Status Query**:
```
User: "What's the status of INV-2024-001?"
  → get_payment_status(invoice_number="INV-2024-001")
  → Check if vendor is priority → if yes, send_holding_reply
  → Return: "Invoice INV-2024-001 for vendor X: Paid on Jan 15, amount $5,000"
```

**Workflow B — Reimbursement Claim**:
```
User: "Process reimbursement for employee EMP-123, travel expense $450"
  → process_reimbursement(employee_id="EMP-123", amount=450, category="travel")
  → If within policy → "Approved. Payment will be processed in next cycle."
  → If needs approval → "Routed to manager [name] for approval."
```

**Workflow C — Monthly Delay Notifications**:
```
User: "Send monthly payment delay emails"
  → get_pending_approvals() filtered by overdue
  → Categorize MSME vs foreign
  → send_payment_delay_email for each
  → Report summary
```

---

### Agent 2: `invoice_agent`
**Handles**: Invoice Data Entry (OCR → NetSuite), Document Format Conversion, Payment File Formatting

| Attribute | Value |
|-----------|-------|
| **Type** | `LlmAgent` |
| **Description** | "Processes invoices — OCR extraction, data entry into NetSuite, document format conversion, and bank upload file generation" |
| **System of Truth** | NetSuite, Email |

#### Tools (6)

| # | Tool | Function | Source |
|---|------|----------|--------|
| 1 | `extract_invoice_data_ocr` | OCR extraction from invoice PDF/image → structured JSON | OCR service |
| 2 | `create_netsuite_invoice` | Create invoice record in NetSuite | NetSuite |
| 3 | `validate_invoice_data` | Validate extracted fields (amounts, dates, vendor ID) | Local logic |
| 4 | `convert_document_format` | Convert invoice/payment doc to required format | Local |
| 5 | `generate_bank_upload_file` | Format payment file for specific bank upload format | Local |
| 6 | `get_invoice_from_email` | Fetch invoice attachment from email | Email/Gmail |

#### Skills (3)

**Skill 1: Invoice Data Entry Pipeline**
```
When processing an invoice for NetSuite entry:
1. Get the invoice (from email via get_invoice_from_email, or user upload)
2. Call extract_invoice_data_ocr → get structured data
3. Call validate_invoice_data → check required fields
4. ALWAYS present extracted data to user for confirmation before entry
   Show: vendor name, invoice number, amount, date, line items
   Ask: "Does this look correct? Should I enter it into NetSuite?"
5. On confirmation → call create_netsuite_invoice
6. Confirm: "Invoice [number] created in NetSuite for vendor [name], amount [X]"
If OCR confidence is low on any field, highlight it and ask user to verify.
```

**Skill 2: Bank Upload File Generation**
```
When user needs a bank upload file:
1. Ask which bank format (if not specified)
2. Fetch pending payment data from NetSuite
3. Call generate_bank_upload_file with bank-specific format rules
4. Return the formatted file
5. Confirm: "Generated bank upload file with X payments totaling $Y"
```

**Skill 3: Document Format Conversion**
```
When user needs to convert a document:
1. Identify source format and target format
2. Call convert_document_format
3. Return converted file
4. Handle errors gracefully — if conversion fails, explain why and suggest alternatives
```

#### Workflows

**Workflow A — Invoice Entry (Primary)**:
```
User: "Process this invoice" [attaches PDF]
  → extract_invoice_data_ocr(file)
  → validate_invoice_data(extracted_data)
  → Present to user: "Extracted: Vendor=Acme, Amount=$12,000, Date=Jan 5..."
  → User confirms
  → create_netsuite_invoice(data)
  → "Invoice INV-2024-055 created in NetSuite"
```

**Workflow B — Bank Upload File**:
```
User: "Generate HDFC bank upload file for this week's payments"
  → Fetch pending payments from NetSuite
  → generate_bank_upload_file(bank="HDFC", payments=...)
  → Return file: "Generated HDFC upload file: 23 payments, total ₹45,00,000"
```

---

### Agent 3: `vendor_agent`
**Handles**: Vendor Creation, Onboarding Status, KYC Checks, Document Management

| Attribute | Value |
|-----------|-------|
| **Type** | `LlmAgent` |
| **Description** | "Manages entire vendor lifecycle — creation, onboarding, KYC verification, document tracking, and status reporting" |
| **System of Truth** | NetSuite, Spotdraft |

#### Tools (6)

| # | Tool | Function | Source |
|---|------|----------|--------|
| 1 | `create_vendor` | Create vendor record in NetSuite with all required fields | NetSuite |
| 2 | `get_vendor_onboarding_status` | Check document checklist and onboarding progress | NetSuite + Spotdraft |
| 3 | `run_kyc_check` | Validate vendor KYC documents (PAN, GST, bank details) | KYC service |
| 4 | `get_vendor_documents` | Fetch vendor agreements/contracts from Spotdraft | Spotdraft |
| 5 | `update_vendor_status` | Update vendor onboarding/active status in NetSuite | NetSuite |
| 6 | `generate_onboarding_report` | Auto-generate status report of all vendors in onboarding | NetSuite + Spotdraft |

#### Skills (3)

**Skill 1: Guided Vendor Creation**
```
When creating a new vendor:
1. Ask for required fields step-by-step:
   - Legal entity name, trade name
   - PAN, GST number, bank account details
   - Contact person, email, phone
   - Payment terms (Net 30/60/90)
2. Call run_kyc_check on provided documents
3. If KYC passes → call create_vendor in NetSuite
4. Check Spotdraft for agreement → call get_vendor_documents
5. If no agreement exists → flag for legal team
6. Call update_vendor_status with final state
7. Report: "Vendor [name] created. KYC: ✓, Agreement: [status]"
```

**Skill 2: Onboarding Status Check**
```
When user asks about vendor onboarding:
1. Call get_vendor_onboarding_status(vendor_id or vendor_name)
2. Present checklist:
   - KYC documents: [received/pending]
   - Bank details verified: [yes/no]
   - Agreement signed: [yes/no] (from Spotdraft)
   - NetSuite record: [created/pending]
3. Highlight what's missing and who needs to act
```

**Skill 3: Bulk Onboarding Report**
```
When user asks for onboarding status across all vendors:
1. Call generate_onboarding_report
2. Present summary: X vendors complete, Y pending, Z blocked
3. List blocked vendors with specific missing items
4. Suggest actions for each blocked vendor
```

#### Workflows

**Workflow A — New Vendor**:
```
User: "Create vendor Tencent Cloud"
  → Guided conversation for required fields
  → run_kyc_check(documents)
  → create_vendor(data)
  → get_vendor_documents(vendor_id) from Spotdraft
  → update_vendor_status(vendor_id, "onboarding_complete")
  → "Vendor Tencent Cloud created. ID: V-2024-089. KYC passed. Agreement on file."
```

**Workflow B — Status Check**:
```
User: "What's the onboarding status of all new vendors?"
  → generate_onboarding_report()
  → "12 vendors in onboarding: 8 complete, 3 pending KYC, 1 missing agreement"
```

---

### Agent 4: `reporting_agent`
**Handles**: P2P Metrics, Invoice/Payment Stats, Accrual Tracking, Custom Reports

| Attribute | Value |
|-----------|-------|
| **Type** | `LlmAgent` |
| **Description** | "Generates P2P efficiency metrics, tracks accruals, and produces reports across all P2P operations" |
| **System of Truth** | NetSuite |

#### Tools (6)

| # | Tool | Function | Source |
|---|------|----------|--------|
| 1 | `get_invoices_processed_count` | Count invoices processed in a date range | NetSuite |
| 2 | `get_payments_made_count` | Count payments made in a date range | NetSuite |
| 3 | `get_p2p_efficiency_metrics` | Calculate turnaround times, error rates, aging | NetSuite |
| 4 | `check_missed_accruals` | Compare expected vs actual accruals for a period | NetSuite |
| 5 | `get_accrual_data` | Fetch monthly accrual records | NetSuite |
| 6 | `generate_p2p_report` | Generate formatted report (accepts report type + params) | Local |

#### Skills (4)

**Skill 1: Monthly P2P Dashboard**
```
When user asks for monthly metrics or P2P dashboard:
1. Call get_invoices_processed_count(month=current)
2. Call get_payments_made_count(month=current)
3. Call get_p2p_efficiency_metrics(month=current)
4. Present as dashboard:
   - Invoices processed: X (vs last month: +/-Y%)
   - Payments made: X (total value: $Y)
   - Avg processing time: X days
   - Error rate: X%
   - Aging buckets: 0-30, 30-60, 60-90, 90+
```

**Skill 2: Accrual Tracking**
```
When user asks about accruals or missed accruals:
1. Call get_accrual_data(month=current)
2. Call check_missed_accruals(month=current)
3. If missed accruals found:
   - List each with vendor, expected amount, and reason
   - Suggest corrective entries
4. If all good: "All accruals for [month] are accounted for"
```

**Skill 3: Custom Report Generation**
```
When user asks for a specific report:
1. Identify report type (payment summary, vendor aging, invoice backlog, etc.)
2. Identify parameters (date range, vendor filter, category)
3. Fetch data using appropriate tools
4. Call generate_p2p_report(type, params, data)
5. Return formatted report
```

**Skill 4: Comparative Analysis**
```
When user asks to compare periods (e.g., "How did we do vs last quarter?"):
1. Fetch metrics for both periods
2. Calculate deltas and percentages
3. Highlight improvements and regressions
4. Suggest areas needing attention
```

#### Workflows

**Workflow A — Monthly Report**:
```
User: "Give me this month's P2P metrics"
  → get_invoices_processed_count + get_payments_made_count + get_p2p_efficiency_metrics
  → "January 2025: 342 invoices processed (+12% MoM), 287 payments ($4.2M), avg 3.2 days"
```

**Workflow B — Missed Accruals**:
```
User: "Check if we missed any accruals this month"
  → get_accrual_data(month="2025-01")
  → check_missed_accruals(month="2025-01")
  → "Found 3 potential missed accruals: [details]. Recommend corrective entries."
```

---

### Agent 5: `bank_ops_agent`
**Handles**: Bank Entry Automation, Credit Card Reconciliation

| Attribute | Value |
|-----------|-------|
| **Type** | `LlmAgent` |
| **Description** | "Automates bank entry creation from statements and performs credit card invoice reconciliation" |
| **System of Truth** | NetSuite |

#### Tools (6)

| # | Tool | Function | Source |
|---|------|----------|--------|
| 1 | `parse_bank_statement` | Extract transactions from bank statement (CSV/PDF) | Local parser |
| 2 | `create_bank_entry` | Create bank entry record in NetSuite | NetSuite |
| 3 | `get_credit_card_invoices` | Fetch CC invoices for reconciliation | NetSuite |
| 4 | `match_cc_transactions` | Match CC transactions to invoices | Local matching |
| 5 | `flag_discrepancies` | Identify unmatched/suspicious transactions | Local logic |
| 6 | `generate_reconciliation_report` | Generate reconciliation summary report | Local |

#### Skills (3)

**Skill 1: Bank Statement Processing**
```
When user uploads a bank statement:
1. Call parse_bank_statement → extract all transactions
2. Present summary: "Found X transactions totaling $Y"
3. For each transaction, attempt auto-matching to existing records
4. Show user: matched (auto-create), unmatched (need review)
5. On confirmation → call create_bank_entry for each
6. Report: "Created X bank entries. Y need manual review."
```

**Skill 2: Credit Card Reconciliation**
```
When user asks to reconcile credit card:
1. Call get_credit_card_invoices(card_id, period)
2. Call match_cc_transactions against bank records
3. Call flag_discrepancies for unmatched items
4. Present:
   - Matched: X transactions ($Y)
   - Unmatched CC charges: list with details
   - Missing invoices: list
5. Call generate_reconciliation_report
6. "Reconciliation complete. 95% matched. 3 items need attention."
```

**Skill 3: Bulk Bank Entry**
```
When user needs to create multiple bank entries at once:
1. Accept list of entries (or parse from statement)
2. Validate each entry (date, amount, account)
3. Create entries in batch via create_bank_entry
4. Report success/failure for each
5. Flag any duplicates detected
```

#### Workflows

**Workflow A — Bank Statement**:
```
User: "Process this month's HDFC statement" [attaches CSV]
  → parse_bank_statement(file)
  → "Found 156 transactions. 142 auto-matched, 14 need review."
  → User reviews 14 items
  → create_bank_entry for all confirmed
  → "156 bank entries created in NetSuite"
```

**Workflow B — CC Reconciliation**:
```
User: "Reconcile Amex corporate card for January"
  → get_credit_card_invoices(card="amex_corp", month="2025-01")
  → match_cc_transactions
  → flag_discrepancies
  → "47 charges, 44 matched. 3 unmatched: [details]"
```

---

## 4. Skills Evolution Strategy

The key insight: **agents are built once, skills are improved continuously**.

### How to Add a Skill
Update the agent's `instruction` string to include the new skill pattern. No code changes needed — just instruction tuning.

### How to Improve a Skill
1. Run the agent on test cases via `adk web`
2. Identify where it makes wrong decisions
3. Add edge cases, clarifications, or examples to the skill in the instruction
4. Re-test

### Skill Roadmap (Future)

| Agent | Future Skills |
|-------|--------------|
| `payment_agent` | "Recurring payment detection", "Vendor credit matching", "Payment forecasting" |
| `invoice_agent` | "Duplicate invoice detection", "Three-way matching (PO-GRN-Invoice)", "Multi-currency handling" |
| `vendor_agent` | "Vendor risk scoring", "Contract renewal alerts", "Vendor performance rating" |
| `reporting_agent` | "Anomaly detection", "Cash flow forecasting", "Budget vs actuals" |
| `bank_ops_agent` | "Auto-categorization", "Fraud detection patterns", "Multi-bank consolidation" |

---

## 5. Mock Server Architecture

### 5.1 NetSuite Mock Server
- **Framework**: FastAPI
- **Auth**: Token-Based Authentication (TBA) mimicking real NetSuite
- **Endpoints**:

```
POST   /auth/token                          → Get auth token

# Payments
GET    /api/payments/{invoice_id}           → Payment status by invoice
GET    /api/payments/search?vendor=X        → Payment status by vendor
GET    /api/payments/pending                → Pending approvals
GET    /api/payments/overdue                → Overdue payments
GET    /api/payments/stats                  → Payment statistics

# Invoices
POST   /api/invoices                        → Create invoice
GET    /api/invoices/stats                  → Invoice statistics
GET    /api/invoices/{id}                   → Get invoice detail

# Vendors
POST   /api/vendors                         → Create vendor
GET    /api/vendors/{id}                    → Get vendor
GET    /api/vendors/{id}/status             → Vendor onboarding status
PUT    /api/vendors/{id}                    → Update vendor

# Reimbursements
GET    /api/reimbursements/pending          → Pending claims
POST   /api/reimbursements                  → Submit claim
POST   /api/reimbursements/{id}/approve     → Approve claim

# Bank & Accruals
POST   /api/bank-entries                    → Create bank entry
POST   /api/bank-entries/batch              → Batch create
GET    /api/cc-invoices                     → Credit card invoices
GET    /api/accruals                        → Accrual data
GET    /api/accruals/check                  → Check missed accruals

# Metrics
GET    /api/metrics/p2p                     → P2P efficiency metrics
GET    /api/metrics/invoices                → Invoice metrics
GET    /api/metrics/payments                → Payment metrics
```

### 5.2 Spotdraft Mock Server
- **Framework**: FastAPI
- **Auth**: API Key based
- **Endpoints**:

```
POST   /auth/verify                         → Verify API key
GET    /api/contracts/{vendor_id}           → Get vendor contracts
GET    /api/documents/{vendor_id}           → Get vendor documents
GET    /api/onboarding/{vendor_id}          → Onboarding status
```

### 5.3 Connector Config
A config module for credential management:
- NetSuite: consumer key/secret, token ID/secret
- Spotdraft: API key
- Slack: webhook URL
- Email: SMTP config
- Mode toggle: `MOCK` vs `LIVE`

Pre-filled with mock values. Swap to real credentials when ready.

---

## 6. Project Structure

```
daegu/
├── p2p_agents/
│   ├── __init__.py                    # Exposes root_agent for `adk web`
│   ├── agent.py                       # All 6 agents defined here
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── payment_tools.py           # 8 payment + reimbursement tools
│   │   ├── invoice_tools.py           # 6 invoice/OCR/format tools
│   │   ├── vendor_tools.py            # 6 vendor management tools
│   │   ├── reporting_tools.py         # 6 metrics/accrual tools
│   │   ├── bank_ops_tools.py          # 6 bank entry/recon tools
│   │   └── notification_tools.py      # Shared: Slack/email helpers
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py                # Connection URLs, mock vs live toggle
│   │   └── constants.py               # Priority vendors, policy thresholds
│   └── schemas/
│       ├── __init__.py
│       ├── invoice.py                 # Pydantic models for invoice data
│       ├── payment.py                 # Payment/reimbursement models
│       ├── vendor.py                  # Vendor models
│       └── common.py                  # Shared response models
├── mock_servers/
│   ├── netsuite_mock/
│   │   ├── __init__.py
│   │   ├── app.py                     # FastAPI app
│   │   ├── auth.py                    # TBA auth middleware
│   │   ├── routes/
│   │   │   ├── payments.py
│   │   │   ├── invoices.py
│   │   │   ├── vendors.py
│   │   │   ├── reimbursements.py
│   │   │   ├── bank_entries.py
│   │   │   ├── accruals.py
│   │   │   └── metrics.py
│   │   └── data/
│   │       └── seed_data.json         # Realistic sample data
│   └── spotdraft_mock/
│       ├── __init__.py
│       ├── app.py                     # FastAPI app
│       ├── auth.py                    # API key auth
│       └── routes/
│           ├── contracts.py
│           └── documents.py
├── tests/
│   ├── test_payment_agent.py
│   ├── test_invoice_agent.py
│   ├── test_vendor_agent.py
│   ├── test_reporting_agent.py
│   └── test_bank_ops_agent.py
├── requirements.txt
└── README.md
```

---

## 7. Execution Phases

| Phase | What | Deliverables |
|-------|------|-------------|
| **Phase 1** | Mock Servers | NetSuite mock (FastAPI + TBA auth + seed data), Spotdraft mock (FastAPI + API key auth) |
| **Phase 2** | Config & Schemas | settings.py, constants.py, all Pydantic models |
| **Phase 3** | Tools | All 32 tool functions wired to mock server APIs |
| **Phase 4** | Agents + Skills | 6 agents with instructions encoding all 17 skills |
| **Phase 5** | Integration | Coordinator routing, end-to-end workflow tests |
| **Phase 6** | Test via `adk web` | Interactive testing of each workflow, skill refinement |

---

## 8. Summary Table

| Agent | Tools | Skills | Domain |
|-------|-------|--------|--------|
| `p2p_coordinator` | 0 | — | Routing |
| `payment_agent` | 8 | 4 | Payments, reimbursements, approvals, delay comms |
| `invoice_agent` | 6 | 3 | OCR entry, format conversion, bank upload files |
| `vendor_agent` | 6 | 3 | Vendor creation, onboarding, KYC, documents |
| `reporting_agent` | 6 | 4 | Metrics, accruals, reports, comparisons |
| `bank_ops_agent` | 6 | 3 | Bank entries, CC reconciliation |
| **Total** | **32** | **17** | |

---

## 9. ADK Patterns Used

| Pattern | Where |
|---------|-------|
| **LLM-Driven Delegation** (`transfer_to_agent`) | Coordinator → specialist routing |
| **FunctionTool** | All 32 tools wrapping mock API calls |
| **output_key + session state** | Passing data between tool calls |
| **Callbacks** (`before_model_callback`) | Human-in-the-loop for invoice verification |
| **SequentialAgent** | Can wrap invoice pipeline (OCR → validate → create) if needed |
| **ParallelAgent** | Reporting agent fetching multiple metrics concurrently |
| **InMemorySessionService** | Dev/test; swap to persistent for production |

---

## 10. Key Design Decisions

1. **5 specialist agents, not 6** — reimbursements folded into payment_agent since they're payment workflows. Payment agent handles "anything money goes out".
2. **Skills over code** — the system improves by refining agent instructions, not rewriting tools. Tools are stable API wrappers; skills encode business logic.
3. **Future-proof** — new payment types (vendor credits, advances) → add a skill to payment_agent. New report types → add a skill to reporting_agent. No new agents needed.
4. **Mock-first** — build and test everything against mocks. Switching to real NetSuite/Spotdraft = change URLs + credentials in config.
5. **Human-in-the-loop** — invoice OCR always requires confirmation. Reimbursements above threshold require approval routing.

---

## 11. Running the System

```bash
# 1. Start mock servers
uvicorn mock_servers.netsuite_mock.app:app --port 8081 &
uvicorn mock_servers.spotdraft_mock.app:app --port 8082 &

# 2. Set env vars
export GOOGLE_GENAI_USE_VERTEXAI=FALSE
export GOOGLE_API_KEY=your-gemini-api-key
export NETSUITE_BASE_URL=http://localhost:8081
export SPOTDRAFT_BASE_URL=http://localhost:8082
export P2P_MODE=MOCK

# 3. Run via ADK Web UI
adk web p2p_agents
```
