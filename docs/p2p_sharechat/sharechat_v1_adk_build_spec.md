# Sharechat Finny V1 Build Spec (Internal)

## 1) Objective

Build **V1** of Sharechat's finance agent (`@finny`) using Google ADK.
V1 supports one workflow only:

- Slack user asks payment status by invoice number and/or vendor name via `@finny`
  mention or direct message (both available from day one).
- Agent fetches status from NetSuite.
- Agent responds in a fixed business format.
- Agent can optionally trigger reminder intent (Slack + email) for pending
  approvals.

## 2) V1 Scope and Non-Goals

### In scope (V1)

- Slack `@mention` and DM entrypoint for payment status (both ready from day one).
- NetSuite read access for `vendor`, `vendorBill`, `vendorPayment`.
- Pending-stage classification and next-action suggestion.
- Optional reminder action initiation (request confirmation before sending).
- Not-found handling with handoff option.
- Audit logs for query, lookup result, and response metadata.
- Test strategy using existing repo mocks (`mock_servers/netsuite_mock`).

### Out of scope (V1)

- Reimbursements, vendor onboarding, and contract workflows (V2+).
- Analytics dashboards and trend reports (V3).
- Multi-ERP support.
- Autonomous outbound emailing without user confirmation.

## 3) User Experience Contract (V1)

### Trigger examples

- `@finny what is the status of INV-2024-001`
- `@finny payment status for Google`
- `@finny status of invoice 12345 for Tencent`

### Response format (must stay stable)

```text
Vendor name: <name>
Invoice #: <invoice_id>
Status: <Paid | Pending Approval | Scheduled | Processing | Not Found>
Pending stage: <L1 | L2 | Treasury | N/A>
Action: <suggested next step>
Reminder: <ask user confirmation before sending reminder>
Fallback: <ask to verify input or offer Human handoff>
```

## 4) Target Architecture (ADK)

### Runtime components

- `finny_slack_gateway` (FastAPI service):
  - Receives Slack Events API callbacks.
  - Verifies Slack signature.
  - Acknowledges within 3 seconds.
  - Pushes processing to async worker.
- `finny_agent` (ADK App pattern):
  - `root_agent` specialized for payment status.
  - Uses `get_payment_status`, `get_pending_approvals`,
    `send_approval_reminder`.
- `netsuite_connector`:
  - HTTP client over NetSuite REST record/query services.
  - Auth abstraction for OAuth 2.0 (required for production).
- `notification_adapter`:
  - Slack message replies (`chat.postMessage`).
  - Email integration (initially mock + pluggable provider).
- `state/logging`:
  - Request/response correlation ID.
  - Minimal metadata storage, no unnecessary Slack data retention.

### ADK file structure

```text
p2p_agents/finny_v1/
  __init__.py        # must contain: from . import agent
  agent.py           # must define root_agent or app
```

Use **App pattern** (not simple agent) to support plugins, event compaction,
and production config.

## 5) API Design and Endpoint Mapping

## Slack APIs (official)

- Events ingestion:
  - Event type: `app_mention`
  - Transport: Events API via HTTP endpoint or Socket Mode
  - Include `message.im` (DM) events for private queries.
- Auth and installation:
  - OAuth v2 (`/oauth/v2/authorize`, `oauth.v2.access`)
- Message response:
  - `chat.postMessage` (thread reply with `thread_ts`)
- Security:
  - Verify `X-Slack-Signature` and `X-Slack-Request-Timestamp`

Recommended V1 scopes:

- `app_mentions:read`
- `chat:write`
- `channels:read` (or channel-specific approach)
- `im:history` (if DM support required)

## NetSuite APIs (official)

Base URL pattern:

- `https://<account>.suitetalk.api.netsuite.com/services/rest/...`

Record endpoints:

- `GET /services/rest/record/v1/vendor`
- `GET /services/rest/record/v1/vendorBill`
- `GET /services/rest/record/v1/vendorPayment`

Query/filter endpoints:

- Record filtering via `q` query parameter.
- `POST /services/rest/query/v1/suiteql` with `Prefer: transient`.

Auth:

- OAuth 2.0 flows as mandated by the production account.

## Repo mock endpoints (for tests/dev)

From `mock_servers/netsuite_mock`:

- `GET /record/v1/vendor`
- `GET /record/v1/vendorBill`
- `GET /record/v1/vendorPayment`
- `POST /query/v1/suiteql`

## 6) Data Contract for Payment Lookup

### Inputs

- `invoice_number` (optional but preferred)
- `vendor_name` (optional)
- `requestor_slack_user_id`
- `channel_id`
- `thread_ts` (if replying in thread)

### Internal resolution

- If invoice present: resolve `vendorBill` by invoice identifier.
- If vendor only: resolve vendor first, then latest relevant bills/payments.
- If multiple matches: ask disambiguation question before final answer.

### Output normalization

- `vendor_name`
- `invoice_number`
- `payment_status`
- `approval_status`
- `pending_stage`
- `next_action`
- `confidence` (`high|medium|low`)

## 7) Development Phases (15 working days)

## Phase 0: Discovery and Access (Day 1-2)

- Confirm production vs sandbox targets.
- Validate Slack app creation path and scopes.
- Validate OAuth 2.0 connectivity and roles.
- Freeze V1 acceptance criteria and response template.

## Phase 1: Slack and ADK Skeleton (Day 3-5)

- Build Slack event receiver and signature verifier.
- Implement ack-within-3-seconds pattern + async execution queue.
- Support both `app_mention` and direct-message event wiring from day one.
- Create ADK `finny_v1` agent package using App pattern.
- Add baseline prompt guardrails (V1 scope refusal behavior).

## Phase 2: NetSuite Connector and Tools (Day 6-8)

- Implement `netsuite_client` with auth abstraction.
- Implement tools:
  - `get_payment_status`
  - `get_pending_approvals`
  - `send_approval_reminder` (mock-safe)
- Map NetSuite records into V1 normalized response schema.

## Phase 3: Conversation and Action Logic (Day 9-11)

- Handle happy paths: invoice lookup, vendor lookup.
- Handle edge paths: multiple matches, not found, incomplete input.
- Add optional reminder confirmation flow.
- Enforce standard response format in all outcomes.

## Phase 4: Testing and Hardening (Day 12-14)

- Unit tests for tool parsing and output shaping.
- Integration tests using `mock_servers/netsuite_mock`.
- Slack event contract tests:
  - signature validation
  - retry/idempotency behavior
  - threaded reply behavior
- Failure injection tests (NetSuite timeout, 404, 401, malformed payload).

## Phase 5: UAT and Cutover Prep (Day 15)

- UAT checklist with finance team scenarios.
- Runbook: env vars, rollback, token rotation.
- Handover docs and go-live sign-off.

## 8) Testing Strategy (repo-aligned)

### Unit tests

- ADK flow and tool behavior:
  - follow existing patterns using `MockModel`
  - reference style in `tests/unittests/flows/llm_flows/...`

### Integration tests

- Start local mock server:
  - `uvicorn mock_servers.netsuite_mock.app:app --port 8081`
- Validate end-to-end query transforms with seeded test records.

### Contract tests

- Slack payload schema and signature verification tests.
- NetSuite response schema assertions for vendor/bill/payment.

### Non-functional checks

- Response latency target:
  - Slack ack < 3s
  - business response p95 < 8s with warm connector
- Idempotency:
  - deduplicate retries using event ID + timestamp window.

## 9) Required Credentials and Access (for implementation)

## Slack

- App Client ID
- App Client Secret
- Signing Secret
- Bot User OAuth Token (`xoxb-...`)
- App-level token (only if Socket Mode selected)
- Workspace admin app-install approval
- Allowed redirect URLs and request URL

## NetSuite

- Account ID / account-specific domain
- Integration record enabled for REST
- OAuth 2.0 credentials: client ID, client secret, redirect URI (or token)
- Role with permissions on vendor/vendor bill/vendor payment records
- Sandbox access + representative dataset

## 10) Risks and Mitigations

- Slack retries / duplicate events:
  - mitigate with idempotency key on event ID.
- NetSuite field variability across accounts:
  - mitigate with mapping config + schema adapters.
- Permission gaps in client role setup:
  - mitigate with day-1 permission validation checklist.
- Ambiguous vendor queries:
  - mitigate with deterministic disambiguation prompt.

## 11) Deliverables (end of V1)

- Running Slack-connected ADK `finny` agent for payment status.
- NetSuite connector with production auth strategy.
- Test suite: unit + integration + basic contract tests.
- Runbook and handover checklist.
- Backlog items for V2/V3 with effort estimates.

## 12) External References

- Slack Events API:
  https://docs.slack.dev/apis/events-api/
- Slack app setup and `app_mention` subscription:
  https://docs.slack.dev/app-management/quickstart-app-settings/
- Slack OAuth v2:
  https://docs.slack.dev/authentication/installing-with-oauth/
- Slack request signing:
  https://docs.slack.dev/authentication/verifying-requests-from-slack/
- Slack `chat.postMessage`:
  https://docs.slack.dev/reference/methods/chat.postMessage/
- Slack AI app capabilities (optional/future):
  https://docs.slack.dev/ai/developing-ai-apps
- NetSuite auth setup:
  https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/article_0627022005.html
- NetSuite vendor record:
  https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/article_164337045826.html
- NetSuite vendor bill record:
  https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/article_164484956387.html
- NetSuite vendor payment record:
  https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/article_7095737506.html
- NetSuite record filtering (`q`):
  https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_1545222128.html
- NetSuite SuiteQL endpoint:
  https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_157909186990.html
