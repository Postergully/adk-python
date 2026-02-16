"""Settings model for P2P tools and mock service connectors."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

_VALID_MODES = frozenset({"MOCK", "LIVE"})


class P2PSettings(BaseSettings):
  """Runtime settings loaded from environment variables."""

  mode: Literal["MOCK", "LIVE"] = "MOCK"

  netsuite_base_url: str = "http://localhost:8081"
  netsuite_account_id: str = "TSTDRV123456"
  netsuite_consumer_key: str = "mock-consumer-key"
  netsuite_consumer_secret: str = "mock-consumer-secret"
  netsuite_token_id: str = "mock-token-id"
  netsuite_token_secret: str = "mock-token-secret"

  spotdraft_base_url: str = "http://localhost:8082"
  spotdraft_api_key: str = "mock-spotdraft-key-xxx"

  slack_webhook_url: str = ""
  email_smtp_host: str = ""
  email_smtp_port: int = 587
  email_from: str = "p2p@sharechat.com"

  model_config = SettingsConfigDict(
    env_prefix="P2P_",
    env_file=".env",
    extra="ignore",
  )

  @field_validator("mode", mode="before")
  @classmethod
  def _validate_mode(cls, mode: str) -> str:
    normalized_mode = mode.upper()
    if normalized_mode not in _VALID_MODES:
      raise ValueError(
        f"Invalid mode {mode!r}. Expected one of {sorted(_VALID_MODES)}."
      )
    return normalized_mode


@lru_cache(maxsize=1)
def get_settings() -> P2PSettings:
  """Returns a cached settings object for repeated tool calls."""

  return P2PSettings()
