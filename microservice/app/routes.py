"""
Microservice routes — POST /start_search.
"""

import asyncio
import logging

from fastapi import APIRouter
from starlette.responses import Response

from app.worker import run_search
from models import SearchRequest

router = APIRouter()

logger = logging.getLogger(__name__)

# Tracks running background tasks to allow graceful shutdown
_tasks: set[asyncio.Task[None]] = set()


@router.post("/start_search", status_code=202)
async def start_search(body: SearchRequest) -> Response:
    """
    Accept a search request, launch a background task to process it, and return 202 immediately.
    Results are posted back to the callback URL in batches by the worker.
    """
    # Fire-and-forget: return 202 immediately, process in background
    task = asyncio.create_task(run_search(body.smiles, body.callback_url))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return Response(status_code=202)
