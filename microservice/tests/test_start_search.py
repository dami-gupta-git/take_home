from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_run_search():
    with patch("app.routers.run_search", AsyncMock()) as m:
        yield m


@pytest.mark.anyio
async def test_start_search_returns_202(client):
    response = await client.post(
        "/start_search",
        json={"smiles": "CCO", "callback_url": "http://backend/api/search/123/update"},
    )
    assert response.status_code == 202


@pytest.mark.anyio
async def test_start_search_launches_background_task(client, mock_run_search):
    await client.post(
        "/start_search",
        json={"smiles": "CCO", "callback_url": "http://backend/api/search/123/update"},
    )
    mock_run_search.assert_called_once_with(
        "CCO", "http://backend/api/search/123/update"
    )


@pytest.mark.anyio
async def test_start_search_missing_fields_returns_422(client):
    response = await client.post("/start_search", json={"smiles": "CCO"})
    assert response.status_code == 422
