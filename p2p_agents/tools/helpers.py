"""Shared helpers for P2P agent tools: HTTP client, auth, notifications."""

from __future__ import annotations

import httpx

from p2p_agents.config.settings import P2PSettings, get_settings

_TOKEN_CACHE: dict[str, str] = {}


def _client() -> httpx.Client:
    return httpx.Client(timeout=15.0)


def get_netsuite_headers() -> dict[str, str]:
    """Return auth headers for NetSuite mock API."""
    settings = get_settings()
    token = _TOKEN_CACHE.get("netsuite")
    if not token:
        token = f"mock-netsuite-token-{settings.netsuite_token_id}"
        _TOKEN_CACHE["netsuite"] = token
    return {"Authorization": f"Bearer {token}"}


def get_spotdraft_headers() -> dict[str, str]:
    """Return auth headers for Spotdraft mock API."""
    settings = get_settings()
    return {"X-API-Key": settings.spotdraft_api_key}


def ns_url(path: str) -> str:
    """Build full NetSuite mock URL."""
    return f"{get_settings().netsuite_base_url}{path}"


def sd_url(path: str) -> str:
    """Build full Spotdraft mock URL."""
    return f"{get_settings().spotdraft_base_url}{path}"


def ns_get(path: str, params: dict | None = None) -> dict:
    """GET request to NetSuite mock."""
    with _client() as c:
        r = c.get(ns_url(path), headers=get_netsuite_headers(), params=params)
        r.raise_for_status()
        return r.json()


def ns_post(path: str, json: dict | None = None) -> dict:
    """POST request to NetSuite mock."""
    with _client() as c:
        r = c.post(ns_url(path), headers=get_netsuite_headers(), json=json)
        r.raise_for_status()
        return r.json()


def ns_put(path: str, json: dict | None = None) -> dict:
    """PUT request to NetSuite mock."""
    with _client() as c:
        r = c.put(ns_url(path), headers=get_netsuite_headers(), json=json)
        r.raise_for_status()
        return r.json()


def sd_get(path: str, params: dict | None = None) -> dict | list:
    """GET request to Spotdraft mock."""
    with _client() as c:
        r = c.get(sd_url(path), headers=get_spotdraft_headers(), params=params)
        r.raise_for_status()
        return r.json()


def sd_post(path: str, json: dict | None = None) -> dict:
    """POST request to Spotdraft mock."""
    with _client() as c:
        r = c.post(sd_url(path), headers=get_spotdraft_headers(), json=json)
        r.raise_for_status()
        return r.json()


def send_slack_message(message: str) -> dict:
    """Send a message to Slack webhook (mock: just logs)."""
    settings = get_settings()
    if not settings.slack_webhook_url:
        return {"status": "skipped", "reason": "No Slack webhook configured"}
    try:
        with _client() as c:
            r = c.post(settings.slack_webhook_url, json={"text": message})
            return {"status": "sent", "code": r.status_code}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email (mock: returns success without actually sending)."""
    settings = get_settings()
    return {
        "status": "sent",
        "from": settings.email_from,
        "to": to,
        "subject": subject,
        "body_preview": body[:100],
    }
