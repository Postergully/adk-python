#!/usr/bin/env python3
"""Finny V1 — Slack Sandbox E2E Smoke Test.

Sends Slack event payloads to the Finny gateway, then polls the Slack mock
to verify that the agent produced a meaningful reply.

Usage:
    python scripts/finny_sandbox.py
    python scripts/finny_sandbox.py --gateway-url http://localhost:8080 -v
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sys
import time
from dataclasses import dataclass, field

import httpx

# ---------------------------------------------------------------------------
# ANSI colour helpers
# ---------------------------------------------------------------------------
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _pass(msg: str) -> str:
    return f"{GREEN}{BOLD}PASS{RESET} {msg}"


def _fail(msg: str) -> str:
    return f"{RED}{BOLD}FAIL{RESET} {msg}"


def _info(msg: str) -> str:
    return f"{YELLOW}{msg}{RESET}"


# ---------------------------------------------------------------------------
# Slack HMAC signature
# ---------------------------------------------------------------------------

def compute_slack_signature(secret: str, timestamp: str, body: str) -> str:
    """Compute Slack v0 request signature matching the gateway verifier."""
    sig_basestring = f"v0:{timestamp}:{body}"
    return "v0=" + hmac.new(
        secret.encode("utf-8"),
        sig_basestring.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


# ---------------------------------------------------------------------------
# Scenario definition
# ---------------------------------------------------------------------------

@dataclass
class Scenario:
    num: int
    name: str
    event_type: str          # "app_mention" or "message"
    text: str
    channel: str
    keywords: list[str]
    channel_type: str = ""   # "im" for DMs

    def build_payload(self) -> dict:
        event: dict = {
            "type": self.event_type,
            "user": "U001",
            "text": self.text,
            "channel": self.channel,
            "ts": f"{int(time.time())}.{self.num:06d}",
        }
        if self.channel_type:
            event["channel_type"] = self.channel_type
        return {
            "type": "event_callback",
            "event_id": f"Ev_sandbox_{self.num:03d}",
            "event": event,
        }


SCENARIOS: list[Scenario] = [
    Scenario(
        num=1,
        name="Invoice status lookup by ID",
        event_type="app_mention",
        text="<@UFINNY> status of INV-2024-001?",
        channel="C001",
        keywords=["paid", "status", "INV-2024-001", "1250000", "Google"],
    ),
    Scenario(
        num=2,
        name="Payment status by vendor name",
        event_type="app_mention",
        text="<@UFINNY> payment status for Google",
        channel="C001",
        keywords=["Google", "vendor", "invoice", "payment"],
    ),
    Scenario(
        num=3,
        name="Pending approvals via DM",
        event_type="message",
        text="show pending approvals",
        channel="D001",
        keywords=["pending", "approval", "Tencent", "Freshworks", "Keka"],
        channel_type="im",
    ),
    Scenario(
        num=4,
        name="Out-of-scope request rejection",
        event_type="app_mention",
        text="<@UFINNY> create a new invoice",
        channel="C001",
        keywords=["scope", "beyond", "cannot", "don't", "outside"],
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_messages(client: httpx.Client, slack_url: str, channel: str) -> list[dict]:
    """Fetch current messages for a channel from the Slack mock."""
    resp = client.get(
        f"{slack_url}/api/conversations.history",
        params={"channel": channel},
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("messages", [])


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


# ---------------------------------------------------------------------------
# Run a single scenario
# ---------------------------------------------------------------------------

def run_scenario(
    scenario: Scenario,
    *,
    gateway_url: str,
    slack_url: str,
    signing_secret: str,
    verbose: bool,
) -> bool:
    """Execute one scenario and return True on success."""
    label = f"[{scenario.num}/{len(SCENARIOS)}] {scenario.name}"
    print(f"\n{BOLD}--- {label} ---{RESET}")

    slack_headers = {"Authorization": "Bearer xoxb-mock-token"}
    with httpx.Client(timeout=10, headers=slack_headers) as client:
        # 1. Baseline message count
        baseline_msgs = _get_messages(client, slack_url, scenario.channel)
        baseline_count = len(baseline_msgs)
        if verbose:
            print(_info(f"  Baseline messages in {scenario.channel}: {baseline_count}"))

        # 2. Build payload
        payload = scenario.build_payload()
        event_ts = payload["event"]["ts"]
        body_str = json.dumps(payload)

        # 3. Compute signature
        timestamp = str(int(time.time()))
        signature = compute_slack_signature(signing_secret, timestamp, body_str)

        # 4. POST to gateway
        headers = {
            "Content-Type": "application/json",
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": signature,
        }
        if verbose:
            print(_info(f"  POST {gateway_url}/slack/events"))
            print(_info(f"  Payload: {body_str[:120]}..."))

        resp = client.post(f"{gateway_url}/slack/events", content=body_str, headers=headers)
        if resp.status_code != 200:
            print(_fail(f"{label} — gateway returned HTTP {resp.status_code}: {resp.text}"))
            return False

        if verbose:
            print(_info(f"  Gateway ack: {resp.json()}"))

        # 5. Poll Slack mock for new message(s)
        max_wait = 30  # seconds
        poll_interval = 2  # seconds
        deadline = time.time() + max_wait
        new_messages: list[dict] = []

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

        if not new_messages:
            print(_fail(f"{label} — no new messages after {max_wait}s"))
            return False

        # 6. Keyword check (case-insensitive)
        all_text = " ".join(m.get("text", "") for m in new_messages).lower()
        matched = [kw for kw in scenario.keywords if kw.lower() in all_text]

        if verbose:
            for m in new_messages:
                print(_info(f"  Reply: {m.get('text', '')[:200]}"))

        if matched:
            print(_pass(f"{label} — matched keywords: {matched}"))
            return True
        else:
            print(_fail(f"{label} — none of {scenario.keywords} found in reply"))
            if not verbose:
                for m in new_messages:
                    print(f"  Reply text: {m.get('text', '')[:200]}")
            return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Finny V1 — Slack Sandbox E2E Smoke Test",
    )
    parser.add_argument(
        "--gateway-url",
        default="http://localhost:8080",
        help="Finny gateway base URL (default: http://localhost:8080)",
    )
    parser.add_argument(
        "--slack-url",
        default="http://localhost:8083",
        help="Slack mock base URL (default: http://localhost:8083)",
    )
    parser.add_argument(
        "--signing-secret",
        default="mock-signing-secret",
        help="Slack signing secret (default: mock-signing-secret)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="Print full response details",
    )
    args = parser.parse_args()

    print(f"{BOLD}Finny V1 — Sandbox Smoke Test{RESET}")
    print(f"  Gateway : {args.gateway_url}")
    print(f"  Slack   : {args.slack_url}")
    print(f"  Scenarios: {len(SCENARIOS)}")

    # Pre-flight: check that both services are reachable
    try:
        httpx.get(f"{args.gateway_url}/health", timeout=5).raise_for_status()
    except (httpx.ConnectError, httpx.HTTPStatusError) as exc:
        print(f"\n{RED}Cannot reach gateway at {args.gateway_url} — is it running?{RESET}")
        print(f"  Error: {exc}")
        sys.exit(1)

    try:
        httpx.get(f"{args.slack_url}/health", timeout=5)
    except httpx.ConnectError as exc:
        print(f"\n{RED}Cannot reach Slack mock at {args.slack_url} — is it running?{RESET}")
        print(f"  Error: {exc}")
        sys.exit(1)

    # Run scenarios
    results: list[bool] = []
    for scenario in SCENARIOS:
        try:
            passed = run_scenario(
                scenario,
                gateway_url=args.gateway_url,
                slack_url=args.slack_url,
                signing_secret=args.signing_secret,
                verbose=args.verbose,
            )
        except httpx.ConnectError as exc:
            print(_fail(f"[{scenario.num}] {scenario.name} — connection error: {exc}"))
            passed = False
        except Exception as exc:
            print(_fail(f"[{scenario.num}] {scenario.name} — unexpected error: {exc}"))
            passed = False
        results.append(passed)

    # Summary
    passed_count = sum(results)
    total = len(results)
    color = GREEN if passed_count == total else RED
    print(f"\n{BOLD}{'=' * 40}{RESET}")
    print(f"{color}{BOLD}{passed_count}/{total} scenarios passed{RESET}")
    print(f"{BOLD}{'=' * 40}{RESET}")

    sys.exit(0 if passed_count == total else 1)


if __name__ == "__main__":
    main()
