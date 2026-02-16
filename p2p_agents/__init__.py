"""P2P ShareChat agent system — exposes root_agent for `adk web p2p_agents`."""

from __future__ import annotations

from .agent import root_agent
from .config.settings import P2PSettings, get_settings

__all__ = [
    "root_agent",
    "P2PSettings",
    "get_settings",
]
