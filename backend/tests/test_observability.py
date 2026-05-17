"""
Tests for request-ID middleware and SMILES redaction.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.anyio
async def test_request_id_generated_when_absent(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/healthz")
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) == 36


@pytest.mark.anyio
async def test_request_id_propagated_when_present(app):
    sent_id = "test-request-id-1234"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/healthz", headers={"X-Request-ID": sent_id})
    assert response.headers["x-request-id"] == sent_id


def test_smiles_logged_at_info_level():
    import asyncio
    from app.routers.search import create_search

    smiles = "CCO"
    logged_values: list[dict] = []

    mock_logger = MagicMock()
    mock_logger.info = MagicMock(side_effect=lambda event, **kw: logged_values.append(kw))

    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    mock_settings = MagicMock()
    mock_settings.LOG_LEVEL = "INFO"
    mock_settings.BACKEND_URL = "http://backend:8000"

    with (
        patch("app.routers.search.logger", mock_logger),
        patch("app.routers.search.get_settings", return_value=mock_settings),
        patch("app.routers.search.asyncio.create_task"),
    ):
        from models import SearchCreateRequest
        body = SearchCreateRequest(smiles=smiles)
        asyncio.run(create_search(body, session))

    assert any(kw.get("smiles") == smiles for kw in logged_values)
