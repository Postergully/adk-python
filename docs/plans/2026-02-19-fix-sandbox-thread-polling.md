# Fix Sandbox Thread Polling Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the Finny sandbox E2E smoke test so it detects threaded agent replies by polling `conversations.replies` instead of only `conversations.history`.

**Architecture:** The Slack mock's `conversations.history` correctly returns only top-level messages (matching real Slack API). The agent posts threaded replies (with `thread_ts`), so those are invisible to the current sandbox polling. We fix the sandbox to poll `conversations.replies` using the event's `ts` as the thread parent, and add a corresponding unit test for the mock endpoint.

**Tech Stack:** Python, httpx, FastAPI (mock server), pytest

---

## Root Cause Analysis

- `mock_servers/slack_mock/db.py:70` — `get_messages()` filters to `thread_ts is None` (top-level only). This is **correct** behavior matching the real Slack API.
- `scripts/finny_sandbox.py:132-140` — `_get_messages()` calls `conversations.history` which only returns top-level messages.
- The agent gateway (`p2p_agents/finny_v1/gateway/event_handler.py:120`) posts replies with `thread_ts = event.get("thread_ts") or event.get("ts")`, making them threaded.
- Result: sandbox polls `conversations.history`, never sees the threaded reply, times out after 30s.

---

### Task 1: Add `_get_thread_replies` helper to the sandbox

**Files:**
- Modify: `scripts/finny_sandbox.py:132-140`

**Step 1: Add the `_get_thread_replies` function after `_get_messages`**

Add this new function at line 142 (after `_get_messages`):

```python
def _get_thread_replies(
    client: httpx.Client, slack_url: str, channel: str, thread_ts: str,
) -> list[dict]:
    """Fetch replies for a specific thread from the Slack mock."""
    resp = client.get(
        f"{slack_url}/api/conversations.replies",
        params={"channel": channel, "ts": thread_ts},
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("messages", [])
```

**Step 2: Verify the file saves correctly**

Run: `python -c "import ast; ast.parse(open('scripts/finny_sandbox.py').read()); print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add scripts/finny_sandbox.py
git commit -m "feat(sandbox): add _get_thread_replies helper for thread polling"
```

---

### Task 2: Update `run_scenario` to poll thread replies

**Files:**
- Modify: `scripts/finny_sandbox.py:155-226`

**Step 1: Capture the event `ts` from the payload**

After line 168 (`payload = scenario.build_payload()`), add:

```python
        event_ts = payload["event"]["ts"]
```

**Step 2: Replace the polling loop (lines 199-204)**

Replace the current polling block:

```python
        while time.time() < deadline:
            time.sleep(poll_interval)
            current_msgs = _get_messages(client, slack_url, scenario.channel)
            if len(current_msgs) > baseline_count:
                new_messages = current_msgs[baseline_count:]
                break
```

With:

```python
        while time.time() < deadline:
            time.sleep(poll_interval)
            # Check both top-level messages AND thread replies.
            # The agent posts threaded replies (thread_ts set), so they
            # only appear in conversations.replies, not conversations.history.
            current_msgs = _get_messages(client, slack_url, scenario.channel)
            if len(current_msgs) > baseline_count:
                new_messages = current_msgs[baseline_count:]
                break

            thread_msgs = _get_thread_replies(
                client, slack_url, scenario.channel, event_ts,
            )
            # Thread replies include the parent (if it exists); we only
            # want messages that are *not* the original event itself.
            replies = [m for m in thread_msgs if m.get("ts") != event_ts]
            if replies:
                new_messages = replies
                break
```

**Step 3: Verify syntax**

Run: `python -c "import ast; ast.parse(open('scripts/finny_sandbox.py').read()); print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add scripts/finny_sandbox.py
git commit -m "fix(sandbox): poll conversations.replies for threaded agent responses"
```

---

### Task 3: Write a unit test for thread reply detection

**Files:**
- Create: `tests/finny_v1/test_sandbox_helpers.py`

**Step 1: Write the failing test**

```python
"""Tests for sandbox helper functions."""

from __future__ import annotations

import httpx
import pytest
from unittest.mock import patch

from scripts.finny_sandbox import _get_messages, _get_thread_replies


class TestGetMessages:
    """Verify _get_messages calls conversations.history."""

    def test_returns_messages_from_history(self, httpx_mock):
        mock_response = {"ok": True, "messages": [{"ts": "1.0", "text": "hello"}]}
        with httpx.Client() as client:
            with patch.object(client, "get") as mock_get:
                mock_get.return_value = httpx.Response(200, json=mock_response)
                result = _get_messages(client, "http://localhost:8083", "C001")
        assert result == [{"ts": "1.0", "text": "hello"}]


class TestGetThreadReplies:
    """Verify _get_thread_replies calls conversations.replies."""

    def test_returns_thread_messages(self):
        mock_response = {
            "ok": True,
            "messages": [
                {"ts": "1.0", "text": "parent", "thread_ts": None},
                {"ts": "1.1", "text": "reply", "thread_ts": "1.0"},
            ],
        }
        with httpx.Client() as client:
            with patch.object(client, "get") as mock_get:
                mock_get.return_value = httpx.Response(200, json=mock_response)
                result = _get_thread_replies(
                    client, "http://localhost:8083", "C001", "1.0",
                )
        assert len(result) == 2
        assert result[1]["text"] == "reply"
```

**Step 2: Run test to verify it passes**

Run: `python3.11 -m pytest tests/finny_v1/test_sandbox_helpers.py -v`
Expected: PASS (2 tests)

**Step 3: Commit**

```bash
git add tests/finny_v1/test_sandbox_helpers.py
git commit -m "test(sandbox): add unit tests for thread reply polling helpers"
```

---

### Task 4: Write a Slack mock integration test for thread replies

**Files:**
- Modify: `tests/finny_v1/test_slack_mock.py` (add test case)

**Step 1: Read `tests/finny_v1/test_slack_mock.py` to understand existing patterns**

Understand how the existing tests set up the mock DB and query endpoints.

**Step 2: Add test for thread reply visibility**

Add a test that:
1. Posts a parent message (no `thread_ts`)
2. Posts a threaded reply (with `thread_ts` = parent's `ts`)
3. Asserts `conversations.history` does NOT include the reply
4. Asserts `conversations.replies?ts=<parent_ts>` DOES include the reply

```python
@pytest.mark.asyncio
async def test_threaded_reply_only_in_conversations_replies(
    async_client: httpx.AsyncClient,
):
    """Agent threaded replies must appear in conversations.replies, not history."""
    # Post parent message
    parent_resp = await async_client.post(
        "/api/chat.postMessage",
        json={"channel": "C001", "text": "user question"},
    )
    parent_ts = parent_resp.json()["ts"]

    # Post threaded reply (simulates agent response)
    await async_client.post(
        "/api/chat.postMessage",
        json={"channel": "C001", "text": "agent answer", "thread_ts": parent_ts},
    )

    # conversations.history should NOT contain the threaded reply
    history = await async_client.get(
        "/api/conversations.history", params={"channel": "C001"}
    )
    history_texts = [m["text"] for m in history.json()["messages"]]
    assert "agent answer" not in history_texts

    # conversations.replies SHOULD contain the threaded reply
    replies = await async_client.get(
        "/api/conversations.replies",
        params={"channel": "C001", "ts": parent_ts},
    )
    reply_texts = [m["text"] for m in replies.json()["messages"]]
    assert "agent answer" in reply_texts
```

**Step 3: Run the test**

Run: `python3.11 -m pytest tests/finny_v1/test_slack_mock.py -v -k "threaded_reply"`
Expected: PASS

**Step 4: Commit**

```bash
git add tests/finny_v1/test_slack_mock.py
git commit -m "test(slack-mock): verify threaded replies only appear in conversations.replies"
```

---

### Task 5: Run full test suite and verify

**Files:**
- None (verification only)

**Step 1: Run all finny tests**

Run: `python3.11 -m pytest tests/finny_v1/ -v`
Expected: All tests PASS (no regressions)

**Step 2: Run syntax check on all modified files**

Run: `python -c "import ast; ast.parse(open('scripts/finny_sandbox.py').read()); print('sandbox OK')"`
Expected: `sandbox OK`

**Step 3: Commit (if any formatting fixes needed)**

Only commit if changes were required.

---

### Task 6: Update build spec docs with progress

**Files:**
- Modify: `docs/p2p_sharechat/sharechat_v1_adk_build_spec.md`

**Step 1: Add a "V1 Progress Tracker" section at the end of the doc**

Append after section 13:

```markdown
## 14) V1 Progress Tracker

### Completed
- Phase 1: Slack gateway with signature verification, 3s ack, async processing
- Phase 1: ADK agent package with App pattern (`p2p_agents/finny_v1/`)
- Phase 1: Both `app_mention` and DM event wiring
- Phase 2: NetSuite connector with auth abstraction
- Phase 2: Tools — `get_payment_status`, `get_pending_approvals`, `send_approval_reminder`
- Phase 3: Happy paths — invoice lookup, vendor lookup, pending approvals
- Phase 3: Edge paths — out-of-scope rejection, disambiguation
- Phase 4: Unit tests — gateway, tools, audit, NetSuite client, Slack mock
- Phase 4: E2E sandbox smoke test with 4 scenarios
- Infra: Full mock server stack (NetSuite :8081, Slack :8083)
- Infra: Makefile orchestration (finny-up/down/test/sandbox/adk)
- Docs: Quickstart guide, build spec

### Bug Fixes
- Fixed sandbox thread polling: `conversations.history` only returns top-level
  messages (correct Slack API behavior). Sandbox now also polls
  `conversations.replies` for threaded agent responses.

### Remaining
- Phase 4: Failure injection tests (NetSuite timeout, 404, 401)
- Phase 5: UAT with finance team
- Phase 5: Runbook and go-live checklist
```

**Step 2: Commit**

```bash
git add docs/p2p_sharechat/sharechat_v1_adk_build_spec.md
git commit -m "docs: add V1 progress tracker to build spec"
```

---

## Summary

| Task | Description | Files Changed |
|------|-------------|---------------|
| 1 | Add `_get_thread_replies` helper | `scripts/finny_sandbox.py` |
| 2 | Update polling loop to check thread replies | `scripts/finny_sandbox.py` |
| 3 | Unit test for sandbox helpers | `tests/finny_v1/test_sandbox_helpers.py` (new) |
| 4 | Integration test for mock thread behavior | `tests/finny_v1/test_slack_mock.py` |
| 5 | Run full test suite verification | (none) |
| 6 | Update build spec docs with progress | `docs/p2p_sharechat/sharechat_v1_adk_build_spec.md` |
