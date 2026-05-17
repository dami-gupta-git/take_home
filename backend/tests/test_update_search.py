"""
Tests for POST /api/search/{id}/update.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

SEARCH_ID = str(uuid.uuid4())

ROUTE_PAYLOAD = {
    "score": 0.9,
    "molecules": [{"smiles": "CCO", "catalog_entries": []}],
    "reactions": [{"name": "esterification", "target": "CCO", "sources": ["CC", "O"]}],
}


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def _make_search_mock(status: str = "in_progress") -> MagicMock:
    search = MagicMock()
    search.status.value = status
    return search


@pytest.mark.anyio
async def test_update_search_returns_ok(client, db_mock):
    _, session = db_mock
    session.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=_make_search_mock())),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # max batch_index
            MagicMock(),  # insert route
            MagicMock(),  # update Search
        ]
    )

    response = await client.post(
        f"/api/search/{SEARCH_ID}/update",
        json={"routes": [ROUTE_PAYLOAD], "is_complete": False},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_update_search_unknown_id_returns_404(client, db_mock):
    _, session = db_mock
    session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )

    response = await client.post(
        f"/api/search/{SEARCH_ID}/update",
        json={"routes": [], "is_complete": False},
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_search_commits_to_db(client, db_mock):
    _, session = db_mock
    session.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=_make_search_mock())),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
            MagicMock(),
            MagicMock(),
        ]
    )

    await client.post(
        f"/api/search/{SEARCH_ID}/update",
        json={"routes": [ROUTE_PAYLOAD], "is_complete": False},
    )

    session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_update_search_is_complete_sets_status(client, db_mock):
    """is_complete=True with no routes should still commit and return ok."""
    _, session = db_mock
    session.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=_make_search_mock())),
            MagicMock(),  # update Search
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),  # count routes
        ]
    )

    response = await client.post(
        f"/api/search/{SEARCH_ID}/update",
        json={"routes": [], "is_complete": True},
    )

    assert response.status_code == 200
    session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_update_search_error_message(client, db_mock):
    """error_message triggers a failed status update."""
    _, session = db_mock
    session.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=_make_search_mock())),
            MagicMock(),  # update Search
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),  # count routes
        ]
    )

    response = await client.post(
        f"/api/search/{SEARCH_ID}/update",
        json={"routes": [], "is_complete": True, "error_message": "Search failed"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
