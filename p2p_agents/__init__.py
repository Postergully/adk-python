"""P2P ShareChat package with shared config and schemas."""

from __future__ import annotations

from .config.settings import P2PSettings
from .config.settings import get_settings

__all__ = [
  "P2PSettings",
  "get_settings",
]
