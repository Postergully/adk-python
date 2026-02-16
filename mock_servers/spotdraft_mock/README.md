# Spotdraft Mock Server

FastAPI mock implementing the Spotdraft API subset for P2P ShareChat agent development.

## Quick Start

```bash
pip install fastapi uvicorn
uvicorn mock_servers.spotdraft_mock.app:app --port 8082
```

Server runs at `http://localhost:8082`.

## Authentication

All endpoints (except `/health`) require an `X-API-Key` header.

Accepted prefixes: `mock-spotdraft-key-`, `sd_live_`, `sd_test_`.

## Endpoints

### Health

```bash
curl http://localhost:8082/health
```

### Parties (Vendors)

```bash
# List all parties
curl -H "X-API-Key: mock-spotdraft-key-test" http://localhost:8082/parties/

# Get party by ID
curl -H "X-API-Key: mock-spotdraft-key-test" http://localhost:8082/parties/party_001/

# Create party
curl -X POST -H "X-API-Key: mock-spotdraft-key-test" \
  -H "Content-Type: application/json" \
  -d '{"name":"Acme Corp","email":"hello@acme.com","type":"vendor"}' \
  http://localhost:8082/parties/
```

### Contracts

```bash
# List all contracts
curl -H "X-API-Key: mock-spotdraft-key-test" http://localhost:8082/contracts/

# Filter by party
curl -H "X-API-Key: mock-spotdraft-key-test" "http://localhost:8082/contracts/?party_id=party_001"

# Get contract by ID
curl -H "X-API-Key: mock-spotdraft-key-test" http://localhost:8082/contracts/con_001/

# Create contract
curl -X POST -H "X-API-Key: mock-spotdraft-key-test" \
  -H "Content-Type: application/json" \
  -d '{"name":"NDA - Acme","party_ids":["party_001"],"status":"draft"}' \
  http://localhost:8082/contracts/
```

### Documents

```bash
# List all documents
curl -H "X-API-Key: mock-spotdraft-key-test" http://localhost:8082/documents/

# Get document by ID
curl -H "X-API-Key: mock-spotdraft-key-test" http://localhost:8082/documents/doc_001/

# Upload document
curl -X POST -H "X-API-Key: mock-spotdraft-key-test" \
  -H "Content-Type: application/json" \
  -d '{"name":"Acme - PAN Card.pdf","type":"kyc_document","party_id":"party_001"}' \
  http://localhost:8082/documents/
```

### Onboarding Status

```bash
curl -H "X-API-Key: mock-spotdraft-key-test" http://localhost:8082/api/custom/onboarding/party_001/
```

Returns aggregated onboarding status including KYC, documents received/pending, and contract summaries.

## Seed Data

21 parties, 17 contracts (MSA/NDA/SOW), 40 documents. Loaded from `data/seed_data.json` on startup.

Key test scenarios:
- `party_001` (Google): **complete** onboarding, all docs verified
- `party_008` (Freshworks): **in_progress**, pending GST verification, draft MSA
- `party_010` (Razorpay): **blocked**, rejected GST document
- `party_019` (Notion): **blocked**, rejected PAN card
- `party_021` (CloudFlare): **pending**, only PAN submitted
