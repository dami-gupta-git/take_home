import pytest


@pytest.mark.anyio
async def test_healthz(client):
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_readyz(client):
    response = await client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
