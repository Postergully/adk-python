"""P2P agent tools — thin wrappers over NetSuite and Spotdraft mock APIs."""

from p2p_agents.tools.payment_tools import (
    get_payment_status,
    get_pending_approvals,
    get_priority_vendor_list,
    get_reimbursement_claims,
    process_reimbursement,
    send_approval_reminder,
    send_holding_reply,
    send_payment_delay_email,
)
from p2p_agents.tools.invoice_tools import (
    convert_document_format,
    create_netsuite_invoice,
    extract_invoice_data_ocr,
    generate_bank_upload_file,
    get_invoice_from_email,
    validate_invoice_data,
)
from p2p_agents.tools.vendor_tools import (
    create_vendor,
    generate_onboarding_report,
    get_vendor_documents,
    get_vendor_onboarding_status,
    run_kyc_check,
    update_vendor_status,
)
from p2p_agents.tools.reporting_tools import (
    check_missed_accruals,
    generate_p2p_report,
    get_accrual_data,
    get_invoices_processed_count,
    get_p2p_efficiency_metrics,
    get_payments_made_count,
)
from p2p_agents.tools.bank_ops_tools import (
    create_bank_entry,
    flag_discrepancies,
    generate_reconciliation_report,
    get_credit_card_invoices,
    match_cc_transactions,
    parse_bank_statement,
)
from p2p_agents.tools.notification_tools import (
    send_email_notification,
    send_slack_notification,
)
from p2p_agents.tools.document_tools import (
    create_doc_report,
    create_ppt_report,
    create_spreadsheet,
)

__all__ = [
    # Payment tools (8)
    "get_payment_status",
    "get_pending_approvals",
    "send_approval_reminder",
    "send_payment_delay_email",
    "get_priority_vendor_list",
    "send_holding_reply",
    "get_reimbursement_claims",
    "process_reimbursement",
    # Invoice tools (6)
    "extract_invoice_data_ocr",
    "create_netsuite_invoice",
    "validate_invoice_data",
    "convert_document_format",
    "generate_bank_upload_file",
    "get_invoice_from_email",
    # Vendor tools (6)
    "create_vendor",
    "get_vendor_onboarding_status",
    "run_kyc_check",
    "get_vendor_documents",
    "update_vendor_status",
    "generate_onboarding_report",
    # Reporting tools (6)
    "get_invoices_processed_count",
    "get_payments_made_count",
    "get_p2p_efficiency_metrics",
    "check_missed_accruals",
    "get_accrual_data",
    "generate_p2p_report",
    # Bank ops tools (6)
    "parse_bank_statement",
    "create_bank_entry",
    "get_credit_card_invoices",
    "match_cc_transactions",
    "flag_discrepancies",
    "generate_reconciliation_report",
    # Notification tools (2)
    "send_slack_notification",
    "send_email_notification",
    # Document generation tools (3)
    "create_ppt_report",
    "create_spreadsheet",
    "create_doc_report",
]
