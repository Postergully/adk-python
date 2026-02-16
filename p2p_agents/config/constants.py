"""Shared constants for the P2P agent and mock server stack."""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

PRIORITY_VENDORS: tuple[str, ...] = ("Google", "Agora", "Tencent")

REIMBURSEMENT_AUTO_APPROVE_LIMIT: int = 5_000

AGING_BUCKETS: tuple[tuple[int, int | None], ...] = (
  (0, 30),
  (30, 60),
  (60, 90),
  (90, None),
)

APPROVAL_REMINDER_THRESHOLD_DAYS: int = 3

PAYMENT_TERMS: Mapping[str, str] = MappingProxyType(
  {
    "net_30": "5",
    "net_60": "6",
    "net_90": "7",
  }
)
