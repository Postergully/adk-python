# OpenClaw Wrapper Agent (MVP)

This sample demonstrates a thin ADK wrapper around an OpenClaw gateway API.

## Environment variables

- `OPENCLAW_BASE_URL`: OpenClaw gateway base URL.
- `OPENCLAW_ENDPOINT`: Endpoint path (`/v1/responses` by default).
- `OPENCLAW_API_KEY`: Optional bearer token.
- `OPENCLAW_TIMEOUT_SECONDS`: Per-request timeout (default `10`).
- `OPENCLAW_MAX_RETRIES`: Transient retry count (default `2`).
- `OPENCLAW_RETRY_BACKOFF_SECONDS`: Initial retry backoff (default `0.25`).

## Tool contract

`call_openclaw_agent(request, session_key, user_id, metadata)`

Returns:
- `status="ok"` with `response_text` and `openclaw_response`
- or `status="error"` with normalized `error.code/message/http_status`
