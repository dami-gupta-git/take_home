from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.anyio
async def test_healthz(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_readyz_ok(app):
    mock_session = AsyncMock()
    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.main.db.AsyncSessionLocal", mock_factory):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_readyz_unavailable(app):
    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(side_effect=Exception("DB down"))
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.main.db.AsyncSessionLocal", mock_factory):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/readyz")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
