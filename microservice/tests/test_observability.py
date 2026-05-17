"""
Tests for request-ID middleware.
"""

import pytest


@pytest.mark.anyio
async def test_request_id_generated_when_absent(client):
    response = await client.get("/healthz")
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) == 36  # UUID format


@pytest.mark.anyio
async def test_request_id_propagated_when_present(client):
    sent_id = "test-request-id-5678"
    response = await client.get("/healthz", headers={"X-Request-ID": sent_id})
    assert response.headers["x-request-id"] == sent_id
