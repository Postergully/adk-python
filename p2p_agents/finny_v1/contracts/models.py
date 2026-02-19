"""Shared data models for Finny V1 payment status agent."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .enums import Confidence, PaymentStatus, PendingStage


# --- Request / Response models ---


class PaymentStatusRequest(BaseModel):
    """Inbound request to look up payment status."""

    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    requestor_slack_user_id: str = ""
    channel_id: str = ""
    thread_ts: str = ""


class PaymentStatusResponse(BaseModel):
    """Normalized payment status returned to the agent."""

    vendor_name: str
    invoice_number: str
    amount: float = 0.0
    currency: str = "INR"
    due_date: str = ""
    payment_status: PaymentStatus
    approval_status: str = ""
    pending_stage: PendingStage = PendingStage.NA
    approver_name: str = ""
    next_action: str = ""
    confidence: Confidence = Confidence.HIGH
    payment_date: str = ""


class ReminderRequest(BaseModel):
    """Request to send an approval reminder."""

    approver_name: str
    transaction_ids: list[str] = Field(default_factory=list)
    channel_id: str = ""


# --- Slack event models ---


class SlackEventPayload(BaseModel):
    """Parsed Slack event from Events API."""

    event_id: str = ""
    event_type: str = ""  # app_mention, message
    user: str = ""
    text: str = ""
    channel: str = ""
    channel_type: str = ""  # channel, im
    thread_ts: str = ""
    ts: str = ""
    team: str = ""


# --- Audit ---


class AuditLogEntry(BaseModel):
    """Single audit log row."""

    correlation_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str = ""
    query_type: str = ""
    query_text: str = ""
    response_status: str = ""
    netsuite_records_accessed: list[str] = Field(default_factory=list)
    error_message: str = ""
