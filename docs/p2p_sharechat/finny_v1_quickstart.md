# Finny V1 Quickstart

## Overview

Finny V1 is a payment status agent built on Google ADK with Gemini (`gemini-2.0-flash`). It answers billing-team queries over Slack -- looking up invoice payment status, listing pending approvals, and sending approval reminders. A lightweight FastAPI gateway translates Slack events into ADK runner calls, and all external dependencies (NetSuite, Slack) are fully mocked so you can develop and test offline.

```
┌─────────────┐     ┌───────────────┐     ┌──────────────┐
│  Slack User  │────>│  Gateway:8080 │────>│  Finny Agent │
└─────────────┘     └───────┬───────┘     └──────┬───────┘
                            │                     │
                    ┌───────▼───────┐     ┌──────▼───────┐
                    │  Slack Mock   │     │ NetSuite Mock│
                    │    :8083      │     │    :8081     │
                    └───────────────┘     └──────────────┘
```

## Prerequisites

- Python 3.11+
- `GOOGLE_API_KEY` environment variable set (Gemini API key)
- Project dependencies installed (see below)

## Quick Start

```bash
pip install -e ".[dev]"        # or: uv pip install -e ".[dev]"
make finny-up                  # start all mock services + gateway
make finny-sandbox             # run E2E smoke test
```

That's it. The sandbox script sends a mock Slack event to the gateway, the agent queries the NetSuite mock, and you see the response printed to stdout.

## Detailed Setup

### Environment Variables

All settings use the `P2P_` prefix and are loaded via Pydantic Settings (see `p2p_agents/config/settings.py`).

| Variable | Default | Description |
|----------|---------|-------------|
| `P2P_MODE` | `MOCK` | Operation mode (`MOCK` or `LIVE`) |
| `P2P_SLACK_BOT_TOKEN` | `xoxb-mock-token` | Slack bot token |
| `P2P_SLACK_SIGNING_SECRET` | `mock-signing-secret` | Slack signing secret |
| `P2P_NETSUITE_BASE_URL` | `http://localhost:8081` | NetSuite mock URL |
| `P2P_SLACK_MOCK_BASE_URL` | `http://localhost:8083` | Slack mock URL |
| `GOOGLE_API_KEY` | *(required)* | Google Gemini API key |

The Makefile exports `P2P_MODE`, `P2P_SLACK_BOT_TOKEN`, and `P2P_SLACK_SIGNING_SECRET` automatically, so you only need to set `GOOGLE_API_KEY` yourself:

```bash
export GOOGLE_API_KEY=your-key-here
```

### Starting Services Individually

If you prefer to run services in separate terminals instead of using `make finny-up`:

```bash
# Terminal 1 — NetSuite mock
uvicorn mock_servers.netsuite_mock.app:app --port 8081

# Terminal 2 — Slack mock
uvicorn mock_servers.slack_mock.app:app --port 8083

# Terminal 3 — Gateway
uvicorn p2p_agents.finny_v1.gateway.app:fastapi_app --port 8080
```

## Running the ADK Web UI

The ADK web UI lets you interact with Finny directly in the browser (no Slack gateway needed):

```bash
make finny-adk
# or directly:
adk web p2p_agents/finny_v1
```

## Running Tests

```bash
make finny-test
# or directly:
python3.11 -m pytest tests/finny_v1/ -v
```

## Makefile Reference

| Target | Description |
|--------|-------------|
| `make help` | Show all available targets |
| `make finny-up` | Start all 3 services (NetSuite mock, Slack mock, gateway) |
| `make finny-down` | Stop all services and clean up PID files |
| `make finny-status` | Check health of each service |
| `make finny-logs` | Tail logs from all services |
| `make finny-test` | Run unit tests |
| `make finny-sandbox` | Run E2E smoke test |
| `make finny-adk` | Start ADK web UI |

## Project Structure

```
p2p_agents/finny_v1/
├── __init__.py
├── agent.py                # ADK agent definition (root_agent)
├── tools.py                # Agent tools (payment status, approvals, reminders)
├── netsuite_client.py      # NetSuite HTTP client
├── audit.py                # Audit logging
├── rate_limiter.py         # Rate limiting
├── contracts/
│   ├── enums.py            # Shared enumerations
│   └── models.py           # Pydantic models
├── gateway/
│   ├── app.py              # FastAPI Slack gateway
│   ├── config.py           # Gateway settings
│   └── event_handler.py    # Slack event processing logic
mock_servers/
├── netsuite_mock/          # Mock NetSuite API (port 8081)
│   ├── app.py
│   ├── db.py               # In-memory data store
│   └── routes/             # vendor, vendor_bill, vendor_payment, etc.
├── slack_mock/             # Mock Slack API (port 8083)
│   ├── app.py
│   ├── db.py
│   └── routes/             # chat, conversations, events
scripts/
├── finny_sandbox.py        # E2E smoke test
tests/finny_v1/             # Unit and integration tests
Makefile                    # Service orchestration
```

## Troubleshooting

**Port already in use**
Find and kill the process occupying the port, or tear down all services:
```bash
lsof -i :8080               # find PID
kill <PID>
# or simply:
make finny-down
```

**Missing GOOGLE_API_KEY**
The agent requires a valid Gemini API key. Export it before starting services:
```bash
export GOOGLE_API_KEY=your-key-here
```

**Signature verification errors**
The gateway validates Slack request signatures. Ensure `P2P_SLACK_SIGNING_SECRET` matches between the gateway and your sandbox/test client. The Makefile sets this to `mock-signing-secret` by default.

**Agent not responding (timeout in sandbox)**
Check the gateway logs for errors:
```bash
cat .pids/gateway.log
```
Common causes: missing or invalid `GOOGLE_API_KEY`, or the NetSuite mock is not running (`make finny-status`).

**Rate limit errors from Gemini**
Wait 60 seconds and retry, or switch to a different API key.
