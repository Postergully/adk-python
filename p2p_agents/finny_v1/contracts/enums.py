"""Enumerations for Finny V1 payment status agent."""

from __future__ import annotations

from enum import Enum


class PaymentStatus(str, Enum):
    """Payment status values from NetSuite."""

    PAID = "paid"
    PENDING_APPROVAL = "pending_approval"
    SCHEDULED = "scheduled"
    PROCESSING = "processing"
    NOT_FOUND = "not_found"


class PendingStage(str, Enum):
    """Which approval stage a pending payment is at."""

    L1 = "L1"
    L2 = "L2"
    TREASURY = "Treasury"
    NA = "N/A"


class Confidence(str, Enum):
    """Confidence level for a payment status lookup."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
