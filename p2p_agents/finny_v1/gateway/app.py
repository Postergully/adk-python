"""Finny V1 Slack Gateway — FastAPI + Slack Bolt event receiver.

Reference: danishi/slack-bot-adk-python-cloudrun pattern.

Start with:
    uvicorn p2p_agents.finny_v1.gateway.app:fastapi_app --port 8080
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import time

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

from p2p_agents.finny_v1.gateway.config import get_gateway_settings
from p2p_agents.finny_v1.gateway.event_handler import (
  handle_event,
  is_duplicate,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _bg_task_done(task: asyncio.Task) -> None:
  """Log exceptions from background event-processing tasks."""
  if task.cancelled():
    return
  exc = task.exception()
  if exc:
    logger.error("Background event task failed: %s", exc, exc_info=exc)

fastapi_app = FastAPI(
  title="Finny V1 — Slack Gateway",
  description="Slack Events API receiver for the Finny payment status agent",
  version="1.0.0",
)


# --- Slack signature verification ---


def _verify_slack_signature(
  signing_secret: str,
  timestamp: str,
  body: bytes,
  signature: str,
) -> bool:
  """Verify Slack request signature (v0 scheme).

  See: https://api.slack.com/authentication/verifying-requests-from-slack
  """
  if not signing_secret or not signature:
    return False

  # Reject requests older than 5 minutes (replay protection)
  try:
    if abs(time.time() - float(timestamp)) > 300:
      return False
  except (ValueError, TypeError):
    return False

  sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
  computed = (
    "v0="
    + hmac.new(
      signing_secret.encode("utf-8"),
      sig_basestring.encode("utf-8"),
      hashlib.sha256,
    ).hexdigest()
  )
  return hmac.compare_digest(computed, signature)


# --- Events endpoint ---


@fastapi_app.post("/slack/events")
async def slack_events(request: Request):
  """Main Slack Events API endpoint.

  Handles:
  - url_verification challenge
  - app_mention events
  - message events (DMs with channel_type == "im")

  Uses the 3-second ack pattern: returns HTTP 200 immediately,
  processes the event in a background task.
  """
  body = await request.body()
  payload = await request.json()

  # URL verification challenge (Slack setup)
  if payload.get("type") == "url_verification":
    return {"challenge": payload.get("challenge", "")}

  # Signature verification
  settings = get_gateway_settings()
  if settings.slack_signing_secret:
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    if not _verify_slack_signature(
      settings.slack_signing_secret, timestamp, body, signature
    ):
      return JSONResponse(
        status_code=403,
        content={"error": "Invalid signature"},
      )

  # Extract event
  event = payload.get("event", {})
  event_id = payload.get("event_id", "")

  if not event:
    return {"ok": True}

  # Idempotency check
  if is_duplicate(event_id):
    logger.debug("Duplicate event %s, skipping", event_id)
    return {"ok": True}

  event_type = event.get("type", "")
  channel_type = event.get("channel_type", "")

  # Only handle app_mention and DM messages
  if event_type == "app_mention":
    # 3-second ack: return immediately, process in background
    task = asyncio.ensure_future(handle_event(event))
    task.add_done_callback(_bg_task_done)
    return {"ok": True}

  if event_type == "message" and channel_type == "im":
    # Skip bot messages to avoid loops
    if event.get("bot_id") or event.get("subtype"):
      return {"ok": True}

    task = asyncio.ensure_future(handle_event(event))
    task.add_done_callback(_bg_task_done)
    return {"ok": True}

  return {"ok": True}


@fastapi_app.get("/")
async def root():
  return {
    "name": "Finny V1 — Slack Gateway",
    "version": "1.0.0",
    "endpoints": ["/slack/events"],
  }


@fastapi_app.get("/health")
async def health():
  return {"status": "ok"}
