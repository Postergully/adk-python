"""Authentication middleware for NetSuite mock server.

Real NetSuite uses OAuth 1.0a (Token-Based Authentication / TBA) with:
- Consumer Key/Secret (integration credentials)
- Token ID/Secret (user credentials)
- HMAC-SHA256 signature

For mock: Accept any `Authorization: Bearer mock-netsuite-token-*` header.
"""

from __future__ import annotations

import json

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response


# Paths that don't require auth
PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}


def _auth_error(detail: dict) -> JSONResponse:
    return JSONResponse(status_code=401, content=detail)


class NetSuiteAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in PUBLIC_PATHS or request.url.path.startswith("/docs"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")

        if not auth_header:
            return _auth_error({
                "type": "error.AuthenticationError",
                "title": "Missing Authorization header",
                "detail": "Provide 'Authorization: Bearer mock-netsuite-token-<id>'",
            })

        # Accept Bearer tokens
        if auth_header.startswith("Bearer "):
            return await call_next(request)

        # Accept OAuth header (for future compatibility)
        if auth_header.startswith("OAuth "):
            return await call_next(request)

        return _auth_error({
            "type": "error.AuthenticationError",
            "title": "Invalid Authorization",
            "detail": "Use Bearer token or OAuth 1.0a TBA authentication",
        })
