"""
Tests for GET /api/search/{id}/status and GET /api/search/{id}/results.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from retrosynthesis_search import SearchStatus

SEARCH_ID = str(uuid.uuid4())


def _make_search(status: SearchStatus = SearchStatus.COMPLETED) -> MagicMock:
    search = MagicMock()
    search.id = uuid.UUID(SEARCH_ID)
    search.smiles = "CCO"
    search.status = status
    search.created_at.isoformat.return_value = "2024-01-01T00:00:00+00:00"
    search.updated_at.isoformat.return_value = "2024-01-01T00:01:00+00:00"
    search.error_message = None
    return search


def _make_route(score: float = 0.9) -> MagicMock:
    route = MagicMock()
    route.score = score
    route.molecules = [{"smiles": "CCO", "catalog_entries": []}]
    route.reactions = [{"name": "r", "target": "CCO", "sources": ["CC", "O"]}]
    return route


def _make_client(app, session: AsyncMock):
    from app.routers.search import get_db

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# --- status ---

@pytest.mark.anyio
async def test_get_status_returns_search(app):
    session = AsyncMock()
    session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=_make_search()))
    )
    async with _make_client(app, session) as client:
        response = await client.get(f"/api/search/{SEARCH_ID}/status")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == SEARCH_ID
    assert data["smiles"] == "CCO"
    assert data["status"] == SearchStatus.COMPLETED.value


@pytest.mark.anyio
async def test_get_status_unknown_id_returns_404(app):
    session = AsyncMock()
    session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    async with _make_client(app, session) as client:
        response = await client.get(f"/api/search/{SEARCH_ID}/status")

    assert response.status_code == 404


# --- results ---

@pytest.mark.anyio
async def test_get_results_returns_trees(app):
    session = AsyncMock()
    route = _make_route(score=0.9)
    session.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=_make_search())),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[route])))),
        ]
    )
    async with _make_client(app, session) as client:
        response = await client.get(f"/api/search/{SEARCH_ID}/results")

    assert response.status_code == 200
    data = response.json()
    assert data["search_id"] == SEARCH_ID
    assert data["total_routes"] == 1
    assert data["routes"][0]["score"] == 0.9


@pytest.mark.anyio
async def test_get_results_unknown_id_returns_404(app):
    session = AsyncMock()
    session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    async with _make_client(app, session) as client:
        response = await client.get(f"/api/search/{SEARCH_ID}/results")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_results_ordered_by_score_desc(app):
    session = AsyncMock()
    routes = [_make_route(score=s) for s in [0.5, 0.9, 0.7]]
    session.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=_make_search())),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=routes)))),
        ]
    )
    async with _make_client(app, session) as client:
        response = await client.get(f"/api/search/{SEARCH_ID}/results")

    scores = [r["score"] for r in response.json()["routes"]]
    assert scores == [0.5, 0.9, 0.7]


@pytest.mark.anyio
async def test_get_results_min_score_filter(app):
    session = AsyncMock()
    routes = [_make_route(score=0.9)]
    session.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=_make_search())),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=routes)))),
        ]
    )
    async with _make_client(app, session) as client:
        response = await client.get(f"/api/search/{SEARCH_ID}/results?min_score=0.8")

    assert response.status_code == 200
    assert len(response.json()["routes"]) == 1
