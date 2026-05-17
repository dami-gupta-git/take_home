"""
Tests for request-ID middleware and SMILES redaction.
"""

import structlog
import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.anyio
async def test_request_id_generated_when_absent(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/healthz")
    assert "x-request-id" in response.headers
    request_id = response.headers["x-request-id"]
    assert len(request_id) == 36  # UUID format


@pytest.mark.anyio
async def test_request_id_propagated_when_present(app):
    sent_id = "test-request-id-1234"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/healthz", headers={"X-Request-ID": sent_id})
    assert response.headers["x-request-id"] == sent_id


@pytest.mark.anyio
async def test_smiles_redacted_at_info_level(app, capfd):
    """SMILES must not appear in log output when LOG_LEVEL is INFO."""
    from unittest.mock import AsyncMock, MagicMock, patch
    import os

    os.environ["LOG_LEVEL"] = "INFO"

    from app.logging import configure_logging
    configure_logging("INFO")

    smiles = "CCO"
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.routers.search.AsyncSessionLocal", mock_factory),
        patch("app.routers.search.asyncio.create_task"),
        patch("app.config.get_settings") as mock_settings,
    ):
        mock_settings.return_value.LOG_LEVEL = "INFO"
        mock_settings.return_value.BACKEND_URL = "http://backend:8000"
        mock_settings.return_value.MICROSERVICE_URL = "http://microservice:8001"

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/search", json={"smiles": smiles})

    captured = capfd.readouterr()
    assert smiles not in captured.out
    assert "<redacted>" in captured.out
