"""
Microservice entry point. Exposes liveness and readiness probes; routes added in later stages.
"""

from fastapi import FastAPI

app = FastAPI()


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    # Microservice is stateless — no DB to check, always ready if process is up
    return {"status": "ok"}
