"""
Search router — POST /api/search, POST /api/search/{id}/update.
"""

import asyncio
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

import app.http_client as http
from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.db import Route, Search
from models import SearchCreateRequest, SearchCreateResponse, SearchUpdate, UpdateResponse
from retrosynthesis_search import RouteData, create_search_request, update_search_progress

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


@router.post("/search/{search_id}/update", response_model=UpdateResponse)
async def update_search(
    search_id: str,
    body: SearchUpdate,
    session: AsyncSession = Depends(get_db),
) -> UpdateResponse:
    """
    Receive a batch of routes from the microservice.
    Inserts routes idempotently and updates the search status.
    """
    result = await session.execute(select(Search).where(Search.id == uuid.UUID(search_id)))
    search = result.scalar_one_or_none()
    if search is None:
        raise HTTPException(status_code=404, detail="Search not found")

    if body.routes:
        batch_index = await _next_batch_index(session, uuid.UUID(search_id))
        for route_index, route in enumerate(body.routes):
            stmt = (
                insert(Route)
                .values(
                    search_id=uuid.UUID(search_id),
                    batch_index=batch_index,
                    route_index=route_index,
                    score=route.score,
                    molecules=[m.model_dump() for m in route.molecules],
                    reactions=[r.model_dump() for r in route.reactions],
                )
                .on_conflict_do_nothing(constraint="uq_route_batch")
            )
            await session.execute(stmt)

    update_data = update_search_progress(
        {"status": search.status.value},
        cast(list[RouteData], [r.model_dump() for r in body.routes]),
        is_complete=body.is_complete,
        error_message=body.error_message,
    )
    await session.execute(
        update(Search).where(Search.id == uuid.UUID(search_id)).values(**update_data)
    )
    await session.commit()

    return UpdateResponse(status="ok")


async def _next_batch_index(session: AsyncSession, search_id: uuid.UUID) -> int:
    """Returns the next batch index for a search (max existing + 1, or 0)."""
    from sqlalchemy import func as sqlfunc

    result = await session.execute(
        select(sqlfunc.max(Route.batch_index)).where(Route.search_id == search_id)
    )
    current_max = result.scalar_one_or_none()
    return 0 if current_max is None else current_max + 1


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
