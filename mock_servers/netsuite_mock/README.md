# NetSuite REST API Mock Server

Mock implementation of the NetSuite REST API (2025.2) for P2P ShareChat agent development.

## Quick Start

```bash
pip install fastapi uvicorn pydantic
uvicorn mock_servers.netsuite_mock.app:app --port 8081
```

Server runs at `http://localhost:8081`. Swagger docs at `http://localhost:8081/docs`.

## Authentication

All endpoints (except `/`, `/health`, `/docs`) require a Bearer token:

```
Authorization: Bearer mock-netsuite-token-xxx
```

Any `Bearer` token is accepted in mock mode.

## Endpoints

### Vendor — `/record/v1/vendor`

```bash
# List all vendors
curl -H "Authorization: Bearer mock-netsuite-token-1" \
  http://localhost:8081/record/v1/vendor

# Search by name
curl -H "Authorization: Bearer mock-netsuite-token-1" \
  "http://localhost:8081/record/v1/vendor?q=companyName%20LIKE%20'Google%25'"

# Get by ID
curl -H "Authorization: Bearer mock-netsuite-token-1" \
  http://localhost:8081/record/v1/vendor/1

# Create
curl -X POST -H "Authorization: Bearer mock-netsuite-token-1" \
  -H "Content-Type: application/json" \
  -d '{"companyName":"New Vendor","email":"new@vendor.com","taxIdNum":"AABCN1234X"}' \
  http://localhost:8081/record/v1/vendor

# Update
curl -X PUT -H "Authorization: Bearer mock-netsuite-token-1" \
  -H "Content-Type: application/json" \
  -d '{"email":"updated@vendor.com"}' \
  http://localhost:8081/record/v1/vendor/1

# Delete
curl -X DELETE -H "Authorization: Bearer mock-netsuite-token-1" \
  http://localhost:8081/record/v1/vendor/999
```

### Vendor Bill (Invoice) — `/record/v1/vendorBill`

```bash
# List all
curl -H "Authorization: Bearer mock-netsuite-token-1" \
  http://localhost:8081/record/v1/vendorBill

# Search pending approval
curl -H "Authorization: Bearer mock-netsuite-token-1" \
  "http://localhost:8081/record/v1/vendorBill?q=approvalStatus%3D'pendingApproval'"

# Get by ID
curl -H "Authorization: Bearer mock-netsuite-token-1" \
  http://localhost:8081/record/v1/vendorBill/1001
```

### Vendor Payment — `/record/v1/vendorPayment`

```bash
# List all
curl -H "Authorization: Bearer mock-netsuite-token-1" \
  http://localhost:8081/record/v1/vendorPayment

# Search pending approval
curl -H "Authorization: Bearer mock-netsuite-token-1" \
  "http://localhost:8081/record/v1/vendorPayment?q=status%3D'pendingApproval'"
```

### Expense (Reimbursement) — `/record/v1/expense`

```bash
# List all
curl -H "Authorization: Bearer mock-netsuite-token-1" \
  http://localhost:8081/record/v1/expense

# Search by employee
curl -H "Authorization: Bearer mock-netsuite-token-1" \
  "http://localhost:8081/record/v1/expense?q=employee.id%3D'789'"
```

### SuiteQL — `/query/v1/suiteql`

```bash
# Count invoices
curl -X POST -H "Authorization: Bearer mock-netsuite-token-1" \
  -H "Content-Type: application/json" \
  -d '{"q": "SELECT COUNT(*) FROM vendorBill"}' \
  http://localhost:8081/query/v1/suiteql

# Sum amounts
curl -X POST -H "Authorization: Bearer mock-netsuite-token-1" \
  -H "Content-Type: application/json" \
  -d '{"q": "SELECT SUM(amount) FROM vendorBill WHERE approvalStatus='\''pendingApproval'\''"}' \
  http://localhost:8081/query/v1/suiteql

# Select all overdue
curl -X POST -H "Authorization: Bearer mock-netsuite-token-1" \
  -H "Content-Type: application/json" \
  -d '{"q": "SELECT * FROM vendorBill WHERE status='\''overdue'\''"}' \
  http://localhost:8081/query/v1/suiteql
```

### Custom Endpoints

```bash
# Bank entries
curl -H "Authorization: Bearer mock-netsuite-token-1" \
  http://localhost:8081/api/custom/bank-entries

# Credit card invoices
curl -H "Authorization: Bearer mock-netsuite-token-1" \
  http://localhost:8081/api/custom/cc-invoices

# Accruals
curl -H "Authorization: Bearer mock-netsuite-token-1" \
  http://localhost:8081/api/custom/accruals
```

## Seed Data

Loaded automatically from `data/seed_data.json`. Contains:

- 15 vendors (including priority: Google, Agora, Tencent)
- 14 vendor bills (mix of paid, pending, overdue)
- 7 vendor payments (completed, pending approval, scheduled)
- 6 expense claims (approved and pending)
- 8 bank entries (matched and unmatched)
- 8 credit card invoices (matched and unmatched)
- 7 accrual records (posted and pending)

## Real NetSuite API Reference

This mock is based on the [NetSuite REST API Browser 2025.2](https://system.netsuite.com/help/helpcenter/en_US/APIs/REST_API_Browser/record/v1/2025.2/index.html).

Real NetSuite uses OAuth 1.0a (TBA) authentication with HMAC-SHA256 signatures. This mock accepts any Bearer token for simplicity.
