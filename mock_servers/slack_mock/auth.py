"""Authentication middleware for Slack mock server.

Real Slack uses Bot User OAuth tokens (xoxb-*) or User tokens (xoxp-*).

For mock: Accept any `Authorization: Bearer xoxb-*` header.
Also accepts "xoxb-mock-token" for testing convenience.
"""

from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response


# Paths that don't require auth
PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}


def _auth_error(error: str) -> JSONResponse:
    """Return a Slack-style error response."""
    return JSONResponse(
        status_code=401,
        content={"ok": False, "error": error},
    )


class SlackAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in PUBLIC_PATHS or request.url.path.startswith("/docs"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")

        if not auth_header:
            return _auth_error("not_authed")

        # Must be a Bearer token
        if not auth_header.startswith("Bearer "):
            return _auth_error("invalid_auth")

        token = auth_header[len("Bearer "):]

        # Accept the test token directly
        if token == "xoxb-mock-token":
            return await call_next(request)

        # Accept any token starting with xoxb-
        if token.startswith("xoxb-"):
            return await call_next(request)

        return _auth_error("invalid_auth")
