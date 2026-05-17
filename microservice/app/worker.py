"""
Background worker that processes a search and posts route batches to the callback URL.
"""

import asyncio
import logging

import app.http_client as http
from app.config import get_settings
from get_routes import get_routes

logger = logging.getLogger(__name__)


async def run_search(smiles: str, callback_url: str) -> None:
    """
    Load routes for the given SMILES and post each batch to the callback URL.
    On error, posts a final callback with is_complete=True and an error_message.
    """
    settings = get_settings()
    assert http.client is not None

    try:
        # Yield one batch at a time; is_last=True on the final batch
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

            if not is_last:
                await asyncio.sleep(settings.BATCH_DELAY_SECONDS)

    except Exception:
        logger.exception("Error during search, posting failure to callback")
        await http.client.post(
            callback_url, json={"routes": [], "is_complete": True, "error_message": "Search failed"}
        )
