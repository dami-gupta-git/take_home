"""
Search router — POST /api/search.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

import app.http_client as http
from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.db import Search
from models import SearchCreateRequest, SearchCreateResponse
from retrosynthesis_search import create_search_request

router = APIRouter(prefix="/api")

logger = logging.getLogger(__name__)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/search", response_model=SearchCreateResponse, status_code=201)
async def create_search(
    body: SearchCreateRequest,
    session: AsyncSession = Depends(get_db),
) -> SearchCreateResponse:
    data = create_search_request(body.smiles)

    row = Search(
        id=data["id"],
        smiles=data["smiles"],
        status=data["status"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )
    session.add(row)
    await session.commit()

    settings = get_settings()
    callback_url = f"{settings.BACKEND_URL}/api/search/{data['id']}/update"

    asyncio.create_task(_notify_microservice(body.smiles, callback_url))

    return SearchCreateResponse(id=str(data["id"]))


async def _notify_microservice(smiles: str, callback_url: str) -> None:
    assert http.client is not None
    settings = get_settings()
    try:
        await http.client.post(
            f"{settings.MICROSERVICE_URL}/start_search",
            json={"smiles": smiles, "callback_url": callback_url},
        )
    except Exception:
        logger.exception("Failed to notify microservice")
