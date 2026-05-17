"""
Microservice entry point. Exposes liveness and readiness probes; routes added in later stages.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.http_client as http
from app.routers import _tasks, router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    http.client = http.make_client()
    yield
    # Cancel and await all running background tasks on shutdown
    for task in list(_tasks):
        task.cancel()
    if _tasks:
        await asyncio.gather(*_tasks, return_exceptions=True)
    await http.client.aclose()


app = FastAPI(lifespan=lifespan)
app.include_router(router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    # Microservice is stateless — no DB to check, always ready if process is up
    return {"status": "ok"}
