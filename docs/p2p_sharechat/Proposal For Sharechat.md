# Proposal For Sharechat (Client Conversation Notes)

This document is the cleaned and structured record of the first client
conversation. It is the source context for:

- `docs/p2p_sharechat/sharechat_invoice_payment_human_kb.md`
- `docs/p2p_sharechat/sharechat_client_proposal_v1.md`
- `docs/p2p_sharechat/sharechat_v1_adk_build_spec.md`

## 1) What We Discussed

- Build a finance assistant agent (`@finny`) accessible in Slack.
- Immediate priority (`P0`): payment status queries.
- Primary query keys discussed:
  - Invoice number
  - Company/vendor name
  - Vendor number
  - Entity code (may already be mapped in NetSuite)
- Scope direction for initial route:
  - Search vendor/invoice/payment data in NetSuite.
  - Answer payment status in a consistent operational format.

## 2) Scope Roadmap (As Discussed)

## V1: Vendor Payment Status (Primary delivery focus)

- Vendor name
- Invoice number and status
- Pending stage
- Action prompt:
  - Should the agent remind L1/L2 where pending?
  - Reminders can be via Slack and email.
- Follow-up prompt:
  - Should the agent set a reminder/notification when paid?
- Not-found flow:
  - Verify input
  - Offer human connect/escalation

## V2: Expanded Operations

- Vendor + reimbursement status
- Access controls

## V3: Reporting and Trends

- Vendor monthly payment trends
- Reports based on access rights

## 3) Current P2P Context (From Meeting)

- Billing inbox receives most invoices (called out as ~90%).
- Team verifies vendor registration before recording invoice.
- If vendor is not registered, onboarding happens first.
- Invoice is recorded in NetSuite with attachment.
- Invoice checks include validity details such as date and GST details.
- Approval model discussed:
  - L1: business/service consumer approval
  - L2: finance approval in NetSuite
- Invoices are not processed without both L1 and L2 approvals.
- Payments are processed in cycles (noted as twice a week) via NetSuite payment
  file flow.
- Volume pain-point:
  - Billing team receives ~200-300 payment status queries from vendors.
  - Need classification/prioritization to avoid service disruption.

## 4) V1 Slack Interaction Pattern

- Mention/DM pattern discussed:
  - `@finny what is the status of <invoice #> or <vendor name>`
- Expected Finny behavior:
  - Pull exact invoice/payment status from NetSuite.
  - Return in agreed operational format.

### Expected response shape

```text
Vendor name
Invoice # - status
Pending stage
Action: shall I remind L1/L2 where it is pending (Slack + email)?
Shall I set reminder/notification when it is paid?
Not found: verify input or connect to human
```

## 5) Workflow and Configuration Needs

- Slack app integration for `@finny`
- Finny agent implementation on Google ADK
- NetSuite API integration (API/MCP route discussed)
- Skill/prompt design:
  - How Finny answers payment status
  - How Finny refuses out-of-scope requests
- Reminder actions:
  - If asked, Finny should be able to ping/send reminder to pending approvers
    via Slack/email

## 6) Integration Matrix

| System | Version Focus | Integration Mode |
| :---- | :---- | :---- |
| NetSuite | V1 | API |
| Slack | V1 | API / MCP (discussion point) |

## 7) References Mentioned In Discussion

1. Slack AI docs:
   https://docs.slack.dev/ai/developing-ai-apps
2. NetSuite REST API browser (original meeting reference):
   https://system.netsuite.com/help/helpcenter/en_US/APIs/REST_API_Browser/record/v1/2023.1/index.html

## 8) Connection To Human KB

- This file is the source conversation capture.
- `docs/p2p_sharechat/sharechat_invoice_payment_human_kb.md` converts these
  notes into a concrete human-operating workflow (what to do, what not to do,
  which systems to check).
