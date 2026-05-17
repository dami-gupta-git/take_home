"""
Backend API entry point. Exposes liveness and readiness probes; routers added in later stages.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from sqlalchemy import text

import app.database as db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    db.AsyncSessionLocal = db.make_session_factory()
    yield


app = FastAPI(lifespan=lifespan)


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
