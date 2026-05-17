from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
def mock_notify():
    with patch("app.routers.search._notify_microservice", AsyncMock()) as m:
        yield m


@pytest.mark.anyio
async def test_create_search_returns_search_id(client, db_mock):
    response = await client.post("/api/search", json={"smiles": "CCO"})

    assert response.status_code == 201
    assert "id" in response.json()


@pytest.mark.anyio
async def test_create_search_persists_to_db(client, db_mock):
    _, session = db_mock

    await client.post("/api/search", json={"smiles": "CCO"})

    session.add.assert_called_once()
    session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_create_search_notifies_microservice(client, db_mock, mock_notify):
    response = await client.post("/api/search", json={"smiles": "CCO"})

    search_id = response.json()["id"]
    mock_notify.assert_called_once()
    args = mock_notify.call_args
    assert args[0][0] == "CCO"
    assert search_id in args[0][1]


@pytest.mark.anyio
async def test_create_search_missing_smiles_returns_422(client, db_mock):
    response = await client.post("/api/search", json={})

    assert response.status_code == 422
