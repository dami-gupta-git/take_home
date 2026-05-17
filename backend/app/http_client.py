"""
Shared async httpx client. Initialised at startup via lifespan.
Forwards X-Request-ID from the current structlog context on every outbound request.
"""

import httpx
import structlog

client: httpx.AsyncClient | None = None


class _RequestIDTransport(httpx.AsyncHTTPTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        ctx = structlog.contextvars.get_contextvars()
        request_id = ctx.get("request_id")
        if request_id:
            request.headers["X-Request-ID"] = str(request_id)
        return await super().handle_async_request(request)


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=_RequestIDTransport(), timeout=10.0)
