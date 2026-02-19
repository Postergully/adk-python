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

import dataclasses
import json
import logging
import time
import uuid
from typing import Any

import httpx

_LOGGER = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://127.0.0.1:8787"
_DEFAULT_ENDPOINT = "/v1/responses"
_TRANSIENT_STATUS_CODES = frozenset((408, 409, 425, 429, 500, 502, 503, 504))


@dataclasses.dataclass(frozen=True)
class OpenClawGatewayConfig:
  """Config for OpenClaw gateway calls."""

  base_url: str = _DEFAULT_BASE_URL
  endpoint: str = _DEFAULT_ENDPOINT
  timeout_seconds: float = 10.0
  max_retries: int = 2
  retry_backoff_seconds: float = 0.25
  api_key: str | None = None


def _normalize_error(
    *,
    message: str,
    correlation_id: str,
    idempotency_key: str,
    code: str,
    retriable: bool,
    attempts: int,
    http_status: int | None = None,
) -> dict[str, Any]:
  return {
      "status": "error",
      "error": {
          "code": code,
          "message": message,
          "http_status": http_status,
          "retriable": retriable,
          "attempts": attempts,
      },
      "correlation_id": correlation_id,
      "idempotency_key": idempotency_key,
  }


def _extract_output_text(response_json: dict[str, Any]) -> str:
  """Best-effort output text extraction across common response shapes."""
  output_text = response_json.get("output_text")
  if isinstance(output_text, str) and output_text:
    return output_text

  choices = response_json.get("choices")
  if isinstance(choices, list) and choices:
    first_choice = choices[0]
    if isinstance(first_choice, dict):
      message = first_choice.get("message")
      if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
          return content
        if isinstance(content, list):
          text_parts = []
          for part in content:
            if isinstance(part, dict):
              text_value = part.get("text")
              if isinstance(text_value, str):
                text_parts.append(text_value)
          if text_parts:
            return "\n".join(text_parts)

  output = response_json.get("output")
  if isinstance(output, list):
    text_parts = []
    for item in output:
      if not isinstance(item, dict):
        continue
      content = item.get("content")
      if not isinstance(content, list):
        continue
      for part in content:
        if isinstance(part, dict):
          text_value = part.get("text")
          if isinstance(text_value, str):
            text_parts.append(text_value)
    if text_parts:
      return "\n".join(text_parts)

  return json.dumps(response_json, sort_keys=True)


class OpenClawGatewayClient:
  """HTTP client for OpenClaw gateway passthrough."""

  def __init__(self, config: OpenClawGatewayConfig) -> None:
    self._config = config

  def call_agent(
      self,
      *,
      request: str,
      session_key: str,
      user_id: str,
      metadata: dict[str, Any] | None,
      correlation_id: str,
      idempotency_key: str,
  ) -> dict[str, Any]:
    """Calls OpenClaw and returns normalized success/error payload."""
    request_metadata = dict(metadata or {})
    payload = {
        "input": request,
        "session_key": session_key,
        "user_id": user_id,
        "metadata": request_metadata,
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Correlation-Id": correlation_id,
        "Idempotency-Key": idempotency_key,
    }
    if self._config.api_key:
      headers["Authorization"] = f"Bearer {self._config.api_key}"

    url = f"{self._config.base_url.rstrip('/')}{self._config.endpoint}"
    last_response: httpx.Response | None = None
    attempts = 0

    for attempt in range(1, self._config.max_retries + 2):
      attempts = attempt
      try:
        with httpx.Client(timeout=self._config.timeout_seconds) as client:
          response = client.post(url, json=payload, headers=headers)
      except httpx.TimeoutException:
        _LOGGER.warning(
            "OpenClaw timeout. correlation_id=%s attempt=%d/%d",
            correlation_id,
            attempt,
            self._config.max_retries + 1,
        )
        if attempt <= self._config.max_retries:
          time.sleep(self._config.retry_backoff_seconds * (2 ** (attempt - 1)))
          continue
        return _normalize_error(
            message="OpenClaw timeout while processing request.",
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            code="openclaw_timeout",
            retriable=True,
            attempts=attempts,
        )
      except httpx.RequestError as error:
        _LOGGER.warning(
            "OpenClaw unavailable. correlation_id=%s attempt=%d/%d error=%s",
            correlation_id,
            attempt,
            self._config.max_retries + 1,
            repr(error),
        )
        if attempt <= self._config.max_retries:
          time.sleep(self._config.retry_backoff_seconds * (2 ** (attempt - 1)))
          continue
        return _normalize_error(
            message="OpenClaw is unavailable.",
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            code="openclaw_unavailable",
            retriable=True,
            attempts=attempts,
        )

      last_response = response
      if response.status_code in _TRANSIENT_STATUS_CODES:
        if attempt <= self._config.max_retries:
          _LOGGER.warning(
              (
                  "OpenClaw transient HTTP status. correlation_id=%s "
                  "attempt=%d/%d status=%d"
              ),
              correlation_id,
              attempt,
              self._config.max_retries + 1,
              response.status_code,
          )
          time.sleep(self._config.retry_backoff_seconds * (2 ** (attempt - 1)))
          continue
        return _normalize_error(
            message=f"OpenClaw transient failure (HTTP {response.status_code}).",
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            code="openclaw_transient_error",
            retriable=True,
            attempts=attempts,
            http_status=response.status_code,
        )

      if 400 <= response.status_code < 500:
        return _normalize_error(
            message=f"OpenClaw rejected request (HTTP {response.status_code}).",
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            code="openclaw_client_error",
            retriable=False,
            attempts=attempts,
            http_status=response.status_code,
        )

      if response.status_code >= 500:
        return _normalize_error(
            message=f"OpenClaw server error (HTTP {response.status_code}).",
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            code="openclaw_server_error",
            retriable=True,
            attempts=attempts,
            http_status=response.status_code,
        )

      try:
        response_json = response.json()
      except ValueError:
        response_json = {"raw_text": response.text}

      return {
          "status": "ok",
          "response_text": _extract_output_text(response_json),
          "openclaw_response": response_json,
          "correlation_id": correlation_id,
          "idempotency_key": idempotency_key,
          "attempts": attempts,
      }

    if last_response is None:
      return _normalize_error(
          message="OpenClaw request failed before any HTTP response.",
          correlation_id=correlation_id,
          idempotency_key=idempotency_key,
          code="openclaw_unknown_error",
          retriable=True,
          attempts=attempts,
      )

    return _normalize_error(
        message="OpenClaw request failed with unknown error.",
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        code="openclaw_unknown_error",
        retriable=True,
        attempts=attempts,
        http_status=last_response.status_code,
    )


def new_correlation_id() -> str:
  """Returns a generated correlation ID."""
  return f"ocw-{uuid.uuid4()}"


def new_idempotency_key() -> str:
  """Returns a generated idempotency key."""
  return f"ocw-idem-{uuid.uuid4()}"
