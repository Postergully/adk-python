"""Event handler — parses Slack events, runs ADK agent, posts replies."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

import httpx
from google.adk.runners import InMemoryRunner
from google.adk.sessions import InMemorySessionService

from p2p_agents.finny_v1.agent import root_agent
from p2p_agents.finny_v1.audit import AuditLogger
from p2p_agents.finny_v1.gateway.config import get_gateway_settings
from p2p_agents.finny_v1.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# --- Singletons ---

_runner: InMemoryRunner | None = None
_session_service: InMemorySessionService | None = None
_audit = AuditLogger()
_rate_limiter = RateLimiter()

# Idempotency dedup: event_id -> timestamp
_seen_events: dict[str, float] = {}
_DEDUP_WINDOW = 60.0  # seconds


def _get_runner() -> InMemoryRunner:
  global _runner, _session_service
  if _runner is None:
    _session_service = InMemorySessionService()
    _runner = InMemoryRunner(
      agent=root_agent,
      app_name="finny_v1",
      session_service=_session_service,
    )
  return _runner


def _get_session_service() -> InMemorySessionService:
  if _session_service is None:
    _get_runner()
  assert _session_service is not None
  return _session_service


def is_duplicate(event_id: str) -> bool:
  """Check idempotency — reject events seen within the dedup window."""
  now = time.time()

  # Prune old entries
  expired = [k for k, v in _seen_events.items() if now - v > _DEDUP_WINDOW]
  for k in expired:
    del _seen_events[k]

  if event_id in _seen_events:
    return True

  _seen_events[event_id] = now
  return False


def strip_bot_mention(text: str) -> str:
  """Remove <@BOT_ID> mention prefix from event text."""
  return re.sub(r"<@[A-Z0-9]+>\s*", "", text).strip()


async def post_slack_message(
  channel: str,
  text: str,
  thread_ts: str = "",
) -> dict[str, Any]:
  """Post a threaded reply to Slack (or Slack mock)."""
  settings = get_gateway_settings()
  payload: dict[str, Any] = {"channel": channel, "text": text}
  if thread_ts:
    payload["thread_ts"] = thread_ts

  async with httpx.AsyncClient(timeout=10.0) as client:
    headers = {"Authorization": f"Bearer {settings.slack_bot_token}"}
    r = await client.post(settings.slack_chat_url, json=payload, headers=headers)
    r.raise_for_status()
    return r.json()


async def escalate_to_ops(
  error_msg: str,
  original_channel: str,
  original_ts: str,
) -> None:
  """Post error details to #billing-ops for manual follow-up."""
  settings = get_gateway_settings()
  text = (
    f":warning: *Finny auto-escalation*\n"
    f"Error processing query in <#{original_channel}> (ts: {original_ts}):\n"
    f"```{error_msg}```"
  )
  try:
    await post_slack_message(
      channel=settings.slack_billing_ops_channel,
      text=text,
    )
  except Exception:
    logger.exception("Failed to escalate to ops channel")


async def handle_event(event: dict[str, Any]) -> None:
  """Process a single Slack event through the ADK agent.

  Steps:
  1. Parse user query (strip bot mention)
  2. Rate-limit check
  3. Run agent via InMemoryRunner
  4. Post threaded reply
  5. On error: friendly message + escalate + schedule retry
  """
  user_id = event.get("user", "")
  text = event.get("text", "")
  channel = event.get("channel", "")
  thread_ts = event.get("thread_ts") or event.get("ts", "")
  event_ts = event.get("ts", "")

  query = strip_bot_mention(text)
  if not query:
    return

  # Rate limit
  if not _rate_limiter.is_allowed(user_id):
    await post_slack_message(
      channel=channel,
      text=_rate_limiter.cooldown_message(user_id),
      thread_ts=thread_ts,
    )
    return

  # Audit — log query
  correlation_id = _audit.new_correlation_id()
  _audit.log_query(
    correlation_id=correlation_id,
    user_id=user_id,
    query_text=query,
  )

  try:
    runner = _get_runner()
    session_service = _get_session_service()

    # Create or reuse session keyed by thread
    session_id = f"slack-{channel}-{thread_ts}"
    session = await session_service.get_session(
      app_name="finny_v1",
      user_id=user_id,
      session_id=session_id,
    )
    if session is None:
      session = await session_service.create_session(
        app_name="finny_v1",
        user_id=user_id,
        session_id=session_id,
      )

    # Run agent
    from google.genai import types

    content = types.Content(
      role="user",
      parts=[types.Part.from_text(text=query)],
    )

    response_text = ""
    async for event_resp in runner.run_async(
      user_id=user_id,
      session_id=session.id,
      new_message=content,
    ):
      if event_resp.content and event_resp.content.parts:
        for part in event_resp.content.parts:
          if part.text:
            response_text += part.text

    if not response_text:
      response_text = (
        "I couldn't process that request. Please try rephrasing, "
        "or contact #billing-support for help."
      )

    # Post reply
    await post_slack_message(
      channel=channel,
      text=response_text,
      thread_ts=thread_ts,
    )

    # Audit — log response
    _audit.log_response(
      correlation_id=correlation_id,
      response_status="ok",
    )

  except Exception as exc:
    logger.exception("Error handling Slack event")

    # Friendly error message
    await post_slack_message(
      channel=channel,
      text=(
        "Sorry, I ran into an issue processing your request. "
        "I've notified the billing ops team. Please try again shortly."
      ),
      thread_ts=thread_ts,
    )

    # Audit
    _audit.log_response(
      correlation_id=correlation_id,
      response_status="error",
      error_message=str(exc),
    )

    # Escalate
    await escalate_to_ops(str(exc), channel, event_ts)

    # Schedule async retry (15 min)
    asyncio.get_event_loop().call_later(
      900,
      lambda: asyncio.ensure_future(
        _retry_event(event, correlation_id)
      ),
    )


async def _retry_event(event: dict[str, Any], correlation_id: str) -> None:
  """Retry a failed event processing once after 15 minutes."""
  logger.info("Retrying event %s (correlation: %s)", event.get("ts"), correlation_id)
  try:
    await handle_event(event)
  except Exception:
    logger.exception("Retry also failed for correlation %s", correlation_id)
