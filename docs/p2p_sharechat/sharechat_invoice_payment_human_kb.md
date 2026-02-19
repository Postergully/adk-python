# Invoice Payment Human Knowledge Base (V1 Reference)

This document captures the manual process that Sharechat's finance team
currently follows when answering invoice payment queries so the Finny agent can
align with the same guardrails.

Source discussion notes:
`docs/p2p_sharechat/Proposal For Sharechat.md`.

## 1) Trigger (consistent with Proposal For Sharechat)

- Billing@sharechat.com receives invoices and vendor queries through email/slack.
- Most queries mention an invoice number or vendor name. If missing, the human analyst asks for it before replying.
- Responses are expected in a structured format (vendor, invoice, status, pending stage, actions, reminder options).

## 2) Step-by-step human workflow (used by L1/L2 approvers)

1. Identify the invoice:
   - Search NetSuite `vendorBill` using the provided invoice number.
   - If only vendor name is given, list bills/payments by that vendor and infer the most likely invoice (ask for clarification if ambiguous).
2. Validate vendor status:
   - Confirm vendor exists and is registered (if not, note vendor onboarding is required before paying).
3. Read payment and approval status:
   - Check `vendorBill` for `approvalStatus` (L1, L2, finance).
   - Check related `vendorPayment` records for scheduled/paid status.
   - L1 is the user who consumed the service, L2 is finance approver; NetSuite stores these approvers.
4. Summarize pending stage:
   - Determine whether approval is pending at L1, L2, or finance/tax gating before payment.
5. Actionable next steps:
   - If approvals pending, ask whether the agent should notify the approver (via Slack/email reminders).
   - If payment is scheduled, mention expected clearing date.
6. Human handoff:
   - When data is missing or inconsistent, escalate to a human (people on slack or email).
   - Avoid speculating about payment dates; only share what NetSuite shows.

## 3) Guardrails

- Never invent payment or approval details; always cite NetSuite fields.
- If the invoice is not found, verify input and offer the option to escalate to a human.
- Do not act on invoices without both L1 and L2 approvals per the current process.
- Double-check HG (GST/date) fields before confirming invoice identity.
- Avoid emailing vendors without explicit user confirmation.

## 4) Systems consulted

- **NetSuite** (primary source): vendor, vendorBill, vendorPayment details, approval statuses, approver identities.
- **Slack**: existing accelerations (billing channel mentioned) for human follow-up when automation cannot answer.
- **Email**: receipts/logs used when documents are attached and invoice number needs cross-verification.

## 5) Takeaways for Finny V1

- Mirror the structured response format described above.
- Use Slack and email reminders only after confirming the approver stage in NetSuite.
- Build in fallback prompts to request clarification rather than guessing.
