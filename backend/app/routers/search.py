"""
Search router — POST /api/search, POST /api/search/{id}/update,
GET /api/search/{id}/status, GET /api/search/{id}/results.
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from typing import cast

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

import app.database as db
import app.http_client as http
from app.config import get_settings
from app.models.db import Route, Search
from models import (
    SearchCreateRequest,
    SearchCreateResponse,
    SearchResultsResponse,
    SearchStatusResponse,
    SearchUpdate,
    UpdateResponse,
)
from retrosynthesis_search import (
    RouteData,
    build_retrosynthesis_tree,
    create_search_request,
    update_search_progress,
)

router = APIRouter(prefix="/api")

logger = structlog.get_logger(__name__)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    assert db.AsyncSessionLocal is not None
    async with db.AsyncSessionLocal() as session:
        yield session


async def _get_search_or_404(session: AsyncSession, search_id: uuid.UUID) -> Search:
    result = await session.execute(select(Search).where(Search.id == search_id))
    search = result.scalar_one_or_none()
    if search is None:
        raise HTTPException(status_code=404, detail="Search not found")
    return search


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

    logger.info("search_created", search_id=str(data["id"]), smiles=body.smiles)

    asyncio.create_task(_notify_microservice(body.smiles, callback_url))

    return SearchCreateResponse(id=str(data["id"]))


@router.post("/search/{search_id}/update", response_model=UpdateResponse)
async def update_search(
    search_id: uuid.UUID,
    body: SearchUpdate,
    session: AsyncSession = Depends(get_db),
) -> UpdateResponse:
    """
    Receive a batch of routes from the microservice.
    Inserts routes idempotently and updates the search status.
    """
    search = await _get_search_or_404(session, search_id)

    if body.routes:
        batch_index = await _next_batch_index(session, search_id)
        for route_index, route in enumerate(body.routes):
            stmt = (
                insert(Route)
                .values(
                    search_id=search_id,
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
    await session.execute(update(Search).where(Search.id == search_id).values(**update_data))
    await session.commit()

    if body.is_complete:
        result = await session.execute(
            select(Route).where(Route.search_id == search_id).order_by(Route.score.desc())
        )
        routes = result.scalars().all()
        logger.info(
            "search_completed",
            search_id=str(search_id),
            total_routes=len(routes),
            routes=[
                {"score": r.score, "smiles": r.molecules[0]["smiles"] if r.molecules else None}
                for r in routes
            ],
        )

    return UpdateResponse(status="ok")


@router.get("/search/{search_id}/status", response_model=SearchStatusResponse)
async def get_search_status(
    search_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> SearchStatusResponse:
    search = await _get_search_or_404(session, search_id)
    return SearchStatusResponse(
        id=str(search.id),
        smiles=search.smiles,
        status=search.status,
        created_at=search.created_at.isoformat(),
        updated_at=search.updated_at.isoformat(),
        error_message=search.error_message,
    )


@router.get("/search/{search_id}/results", response_model=SearchResultsResponse)
async def get_search_results(
    search_id: uuid.UUID,
    min_score: float | None = None,
    session: AsyncSession = Depends(get_db),
) -> SearchResultsResponse:
    await _get_search_or_404(session, search_id)

    stmt = select(Route).where(Route.search_id == search_id)
    if min_score is not None:
        stmt = stmt.where(Route.score >= min_score)
    stmt = stmt.order_by(Route.score.desc())

    result = await session.execute(stmt)
    trees = [
        build_retrosynthesis_tree(
            cast(RouteData, {"score": r.score, "molecules": r.molecules, "reactions": r.reactions})
        )
        for r in result.scalars().all()
    ]

    return SearchResultsResponse(
        search_id=str(search_id),
        total_routes=len(trees),
        routes=trees,
    )


async def _next_batch_index(session: AsyncSession, search_id: uuid.UUID) -> int:
    """Returns the next batch index for a search (max existing + 1, or 0)."""
    from sqlalchemy import func as sqlfunc

    result = await session.execute(
        select(sqlfunc.max(Route.batch_index)).where(Route.search_id == search_id)
    )
    current_max = result.scalar_one_or_none()
    return 0 if current_max is None else current_max + 1


async def _notify_microservice(smiles: str, callback_url: str) -> None:
    settings = get_settings()
    try:
        response = await http.client.post(  # type: ignore[union-attr]
            f"{settings.MICROSERVICE_URL}/start_search",
            json={"smiles": smiles, "callback_url": callback_url},
        )
        response.raise_for_status()
    except Exception:
        logger.exception("microservice_notify_failed")
