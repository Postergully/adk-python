"""API key authentication for the Spotdraft mock server."""

from fastapi import Header, HTTPException


VALID_PREFIXES = ("mock-spotdraft-key-", "sd_live_", "sd_test_")


async def verify_api_key(x_api_key: str = Header(...)) -> str:
    """Validate the X-API-Key header.

    Accepts keys starting with ``mock-spotdraft-key-``, ``sd_live_``, or
    ``sd_test_``.
    """
    if not any(x_api_key.startswith(p) for p in VALID_PREFIXES):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
