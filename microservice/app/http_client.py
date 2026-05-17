"""
Shared async httpx client. Initialised at startup via lifespan.
"""

import httpx

client: httpx.AsyncClient | None = None


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=10.0)
