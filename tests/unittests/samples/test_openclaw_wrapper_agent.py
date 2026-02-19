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

import http.server
import json
import socket
import threading
import time
from typing import Any

import pytest

from contributing.samples.openclaw_wrapper_agent.agent import call_openclaw_agent


class _FakeOpenClawServer(http.server.ThreadingHTTPServer):
  """In-memory fake OpenClaw gateway for wrapper tests."""

  def __init__(
      self,
      server_address: tuple[str, int],
      handler: type[http.server.BaseHTTPRequestHandler],
  ) -> None:
    super().__init__(server_address, handler)
    self.request_log: list[dict[str, Any]] = []
    self.turn_by_session: dict[str, int] = {}
    self.reminders_by_session: dict[str, list[tuple[float, str]]] = {}
    self.transient_failures_remaining = 1


class _OpenClawHandler(http.server.BaseHTTPRequestHandler):
  """Simple request handler for fake OpenClaw responses."""

  server: _FakeOpenClawServer

  def do_POST(self) -> None:
    content_length = int(self.headers.get("Content-Length", "0"))
    raw_body = self.rfile.read(content_length) if content_length else b"{}"
    body = json.loads(raw_body.decode("utf-8"))

    self.server.request_log.append({
        "path": self.path,
        "headers": dict(self.headers),
        "body": body,
    })

    if self.path != "/v1/responses":
      self._write_json(404, {"error": "not_found"})
      return

    user_input = str(body.get("input", ""))
    session_key = str(body.get("session_key", "missing-session"))
    metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}

    if user_input == "trigger-transient-retry":
      if self.server.transient_failures_remaining:
        self.server.transient_failures_remaining -= 1
        self._write_json(503, {"error": "busy"})
        return
      self._write_json(200, {"output_text": "Recovered after retry."})
      return

    if user_input == "delegate tool execution":
      self._write_json(
          200,
          {
              "output_text": "Delegated tool completed.",
              "tool_results": [
                  {
                      "name": "calendar.create_reminder",
                      "status": "ok",
                  }
              ],
          },
      )
      return

    if user_input == "schedule reminder":
      schedule_at_epoch = float(metadata["schedule_at_epoch"])
      schedule_message = str(metadata["schedule_message"])
      reminders = self.server.reminders_by_session.setdefault(session_key, [])
      reminders.append((schedule_at_epoch, schedule_message))
      self._write_json(200, {"output_text": "Reminder scheduled."})
      return

    if user_input == "check reminders":
      now_epoch = time.time()
      due_messages: list[str] = []
      remaining_messages: list[tuple[float, str]] = []
      for scheduled_epoch, message in self.server.reminders_by_session.get(
          session_key, []
      ):
        if scheduled_epoch <= now_epoch:
          due_messages.append(message)
        else:
          remaining_messages.append((scheduled_epoch, message))
      self.server.reminders_by_session[session_key] = remaining_messages
      if due_messages:
        self._write_json(
            200,
            {"output_text": f"Due reminders: {', '.join(due_messages)}"},
        )
      else:
        self._write_json(200, {"output_text": "No reminders due."})
      return

    turn = self.server.turn_by_session.get(session_key, 0) + 1
    self.server.turn_by_session[session_key] = turn
    self._write_json(
        200,
        {"output_text": f"session={session_key} turn={turn} echo={user_input}"},
    )

  def log_message(self, format: str, *args: object) -> None:
    del format, args

  def _write_json(self, status_code: int, payload: dict[str, Any]) -> None:
    payload_bytes = json.dumps(payload).encode("utf-8")
    self.send_response(status_code)
    self.send_header("Content-Type", "application/json")
    self.send_header("Content-Length", str(len(payload_bytes)))
    self.end_headers()
    self.wfile.write(payload_bytes)


@pytest.fixture
def fake_openclaw_server() -> _FakeOpenClawServer:
  server = _FakeOpenClawServer(("127.0.0.1", 0), _OpenClawHandler)
  thread = threading.Thread(target=server.serve_forever, daemon=True)
  thread.start()
  try:
    yield server
  finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=1.0)


@pytest.fixture
def configure_openclaw_env(
    fake_openclaw_server: _FakeOpenClawServer, monkeypatch: pytest.MonkeyPatch
) -> None:
  base_url = f"http://127.0.0.1:{fake_openclaw_server.server_port}"
  monkeypatch.setenv("OPENCLAW_BASE_URL", base_url)
  monkeypatch.setenv("OPENCLAW_ENDPOINT", "/v1/responses")
  monkeypatch.setenv("OPENCLAW_TIMEOUT_SECONDS", "1")
  monkeypatch.setenv("OPENCLAW_MAX_RETRIES", "2")
  monkeypatch.setenv("OPENCLAW_RETRY_BACKOFF_SECONDS", "0.01")


def test_scenario_1_basic_pass_through(
    configure_openclaw_env: None, fake_openclaw_server: _FakeOpenClawServer
) -> None:
  del configure_openclaw_env
  response = call_openclaw_agent(
      request="hello from ADK",
      session_key="mvp-session-1",
      user_id="user-1",
      metadata={"tenant": "acme"},
  )

  assert response["status"] == "ok"
  assert "echo=hello from ADK" in response["response_text"]
  assert fake_openclaw_server.request_log
  request_headers = fake_openclaw_server.request_log[-1]["headers"]
  assert request_headers.get("X-Correlation-Id")
  assert request_headers.get("Idempotency-Key")


def test_scenario_2_multi_turn_memory_continuity(
    configure_openclaw_env: None,
) -> None:
  del configure_openclaw_env
  first = call_openclaw_agent(
      request="first turn",
      session_key="continuity-session",
      user_id="user-2",
      metadata=None,
  )
  second = call_openclaw_agent(
      request="second turn",
      session_key="continuity-session",
      user_id="user-2",
      metadata=None,
  )

  assert first["status"] == "ok"
  assert second["status"] == "ok"
  assert "turn=1" in first["response_text"]
  assert "turn=2" in second["response_text"]


def test_scenario_3_tool_execution_and_transient_retry(
    configure_openclaw_env: None,
) -> None:
  del configure_openclaw_env
  retry_response = call_openclaw_agent(
      request="trigger-transient-retry",
      session_key="retry-session",
      user_id="user-3",
      metadata=None,
  )
  delegated_tool_response = call_openclaw_agent(
      request="delegate tool execution",
      session_key="retry-session",
      user_id="user-3",
      metadata=None,
  )

  assert retry_response["status"] == "ok"
  assert retry_response["attempts"] == 2
  assert delegated_tool_response["status"] == "ok"
  assert delegated_tool_response["openclaw_response"]["tool_results"][0][
      "name"
  ] == "calendar.create_reminder"


def test_scenario_4_scheduled_task_end_to_end(
    configure_openclaw_env: None,
) -> None:
  del configure_openclaw_env
  session_key = "schedule-session"
  schedule_at_epoch = time.time() + 0.2
  schedule = call_openclaw_agent(
      request="schedule reminder",
      session_key=session_key,
      user_id="user-4",
      metadata={
          "schedule_at_epoch": schedule_at_epoch,
          "schedule_message": "drink water",
      },
  )
  assert schedule["status"] == "ok"
  assert "Reminder scheduled" in schedule["response_text"]

  time.sleep(0.25)
  reminder = call_openclaw_agent(
      request="check reminders",
      session_key=session_key,
      user_id="user-4",
      metadata=None,
  )
  assert reminder["status"] == "ok"
  assert "drink water" in reminder["response_text"]


def test_scenario_5_openclaw_unavailable_graceful_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    unused_port = sock.getsockname()[1]

  monkeypatch.setenv("OPENCLAW_BASE_URL", f"http://127.0.0.1:{unused_port}")
  monkeypatch.setenv("OPENCLAW_ENDPOINT", "/v1/responses")
  monkeypatch.setenv("OPENCLAW_TIMEOUT_SECONDS", "0.2")
  monkeypatch.setenv("OPENCLAW_MAX_RETRIES", "1")
  monkeypatch.setenv("OPENCLAW_RETRY_BACKOFF_SECONDS", "0")

  response = call_openclaw_agent(
      request="this should fail",
      session_key="failure-session",
      user_id="user-5",
      metadata=None,
  )

  assert response["status"] == "error"
  assert response["error"]["code"] == "openclaw_unavailable"
  assert "unavailable" in response["error"]["message"].lower()
