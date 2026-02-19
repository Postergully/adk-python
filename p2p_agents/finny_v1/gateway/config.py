"""Gateway-specific configuration for Finny V1."""

from __future__ import annotations

from functools import lru_cache

from p2p_agents.config.settings import P2PSettings


class FinnyGatewaySettings(P2PSettings):
  """Extends P2PSettings with Slack gateway defaults."""

  @property
  def slack_events_url(self) -> str:
    return f"{self.slack_mock_base_url}/slack/events"

  @property
  def slack_chat_url(self) -> str:
    return f"{self.slack_mock_base_url}/api/chat.postMessage"


@lru_cache(maxsize=1)
def get_gateway_settings() -> FinnyGatewaySettings:
  return FinnyGatewaySettings()
