"""Shared notification tools — Slack messages and email for all agents."""

from __future__ import annotations

from p2p_agents.tools.helpers import send_email, send_slack_message


def send_slack_notification(channel: str, message: str) -> dict:
    """Sends a notification message to a Slack channel.

    Args:
        channel: Slack channel name, e.g. "#finance-ops".
        message: The message body to send.

    Returns:
        dict with send status and channel info.
    """
    result = send_slack_message(f"[{channel}] {message}")
    return {"channel": channel, **result}


def send_email_notification(
    to: str, subject: str, body: str, cc: str = ""
) -> dict:
    """Sends an email notification.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Email body text.
        cc: Optional CC email address.

    Returns:
        dict with send status and email details.
    """
    result = send_email(to=to, subject=subject, body=body)
    if cc:
        result["cc"] = cc
    return result
