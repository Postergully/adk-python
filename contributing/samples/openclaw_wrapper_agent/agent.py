# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import os
from typing import Any

from google.adk import Agent
from google.adk.tools.tool_context import ToolContext

from .openclaw_client import new_correlation_id
from .openclaw_client import new_idempotency_key
from .openclaw_client import OpenClawGatewayClient
from .openclaw_client import OpenClawGatewayConfig

_DEFAULT_TIMEOUT_SECONDS = 10.0
_DEFAULT_MAX_RETRIES = 2
_DEFAULT_BACKOFF_SECONDS = 0.25


def _get_float_env(name: str, default_value: float) -> float:
  raw_value = os.getenv(name)
  if raw_value is None:
    return default_value
  try:
    return float(raw_value)
  except ValueError:
    return default_value


def _get_int_env(name: str, default_value: int) -> int:
  raw_value = os.getenv(name)
  if raw_value is None:
    return default_value
  try:
    return int(raw_value)
  except ValueError:
    return default_value


def _build_gateway_config() -> OpenClawGatewayConfig:
  return OpenClawGatewayConfig(
      base_url=os.getenv("OPENCLAW_BASE_URL", "http://127.0.0.1:8787"),
      endpoint=os.getenv("OPENCLAW_ENDPOINT", "/v1/responses"),
      timeout_seconds=_get_float_env(
          "OPENCLAW_TIMEOUT_SECONDS", _DEFAULT_TIMEOUT_SECONDS
      ),
      max_retries=_get_int_env("OPENCLAW_MAX_RETRIES", _DEFAULT_MAX_RETRIES),
      retry_backoff_seconds=_get_float_env(
          "OPENCLAW_RETRY_BACKOFF_SECONDS", _DEFAULT_BACKOFF_SECONDS
      ),
      api_key=os.getenv("OPENCLAW_API_KEY"),
  )


def call_openclaw_agent(
    request: str,
    session_key: str,
    user_id: str = "anonymous",
    metadata: dict[str, Any] | None = None,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
  """Thin wrapper tool that forwards a request to OpenClaw."""
  resolved_metadata = dict(metadata or {})
  correlation_id = str(
      resolved_metadata.pop(
          "correlation_id",
          (
              f"adk-invocation-{tool_context.invocation_id}"
              if tool_context
              else new_correlation_id()
          ),
      )
  )
  idempotency_key = str(
      resolved_metadata.pop(
          "idempotency_key",
          (
              f"adk-invocation-{tool_context.invocation_id}"
              if tool_context
              else new_idempotency_key()
          ),
      )
  )
  client = OpenClawGatewayClient(_build_gateway_config())
  return client.call_agent(
      request=request,
      session_key=session_key,
      user_id=user_id,
      metadata=resolved_metadata,
      correlation_id=correlation_id,
      idempotency_key=idempotency_key,
  )


root_agent = Agent(
    model="gemini-2.5-flash",
    name="openclaw_wrapper_agent",
    description=(
        "Thin ADK wrapper that delegates execution to OpenClaw runtime via HTTP."
    ),
    instruction=(
        "You are a gateway wrapper around OpenClaw. Keep your own reasoning"
        " minimal and call call_openclaw_agent for user tasks. Preserve stable"
        " session continuity by reusing the same session_key across turns."
        " Return OpenClaw output directly and do not fabricate tool results."
    ),
    tools=[call_openclaw_agent],
)
