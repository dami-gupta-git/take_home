"""
Backend API entry point. Exposes liveness and readiness probes; routers added in later stages.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from sqlalchemy import text

import app.database as db
import app.http_client as http
from app.config import get_settings
from app.logging import configure_logging
from app.middleware import RequestIDMiddleware
from app.routers.search import router as search_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(get_settings().LOG_LEVEL)
    db.AsyncSessionLocal = db.make_session_factory()
    http.client = http.make_client()
    if http.client is None:
        raise RuntimeError("Failed to initialise HTTP client")
    yield
    await http.client.aclose()


app = FastAPI(lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)
app.include_router(search_router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz", response_model=None)
async def readyz() -> Response | dict[str, str]:
    try:
        assert db.AsyncSessionLocal is not None
        async with db.AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        return Response(
            content='{"status": "unavailable"}',
            status_code=503,
            media_type="application/json",
        )
