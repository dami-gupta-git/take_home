"""
Background worker that processes a search and posts route batches to the callback URL.
"""

import asyncio

import structlog

import app.http_client as http
from app.config import get_settings
from get_routes import get_routes

logger = structlog.get_logger(__name__)


async def run_search(smiles: str, callback_url: str) -> None:
    """
    Load routes for the given SMILES and post each batch to the callback URL.
    On error, posts a final callback with is_complete=True and an error_message.
    """
    settings = get_settings()
    assert http.client is not None

    smiles_log = smiles if settings.LOG_LEVEL.upper() == "DEBUG" else "<redacted>"

    try:
        for batch, is_last in get_routes(smiles, batch_size=settings.BATCH_SIZE):
            payload = {
                "routes": [
                    {
                        "score": route["score"],
                        "molecules": route["molecules"],
                        "reactions": route["reactions"],
                    }
                    for route in batch
                ],
                "is_complete": is_last,
            }
            await http.client.post(callback_url, json=payload)
            logger.info(
                "batch_posted",
                smiles=smiles_log,
                batch_size=len(batch),
                is_last=is_last,
            )

            if not is_last:
                await asyncio.sleep(settings.BATCH_DELAY_SECONDS)

    except Exception:
        logger.exception("search_failed", smiles=smiles_log)
        await http.client.post(
            callback_url, json={"routes": [], "is_complete": True, "error_message": "Search failed"}
        )
