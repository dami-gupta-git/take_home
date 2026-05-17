"""
Shared async httpx client. Initialised at startup via lifespan.
Forwards X-Request-ID from the current structlog context on every outbound request.
"""

import httpx
import structlog

client: httpx.AsyncClient | None = None


def _inject_request_id(request: httpx.Request) -> None:
    request_id = structlog.contextvars.get_contextvars().get("request_id")
    if request_id:
        request.headers["X-Request-ID"] = str(request_id)


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(event_hooks={"request": [_inject_request_id]}, timeout=10.0)
