"""
Cross-service integration test against a real Postgres database.
Requires the DB to be running (make up or docker compose up postgres).

Flow:
  1. Backend app boots with a real DB session factory
  2. POST /api/search → saves search to DB
  3. Microservice worker runs in-process, posts batches to backend callback
  4. Backend inserts routes into DB and updates search status
  5. Assert DB contains the expected routes and search status is completed
"""

import asyncio
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

MICROSERVICE_ROOT = str(Path(__file__).parents[2] / "microservice")
DATABASE_URL = "postgresql+asyncpg://retro:retro@localhost:5440/retro"


@contextmanager
def _microservice_path():
    """Temporarily put the microservice root first on sys.path."""
    sys.path.insert(0, MICROSERVICE_ROOT)
    try:
        yield
    finally:
        sys.path.remove(MICROSERVICE_ROOT)
        # Remove any cached microservice modules to avoid leaking into other tests
        for key in [k for k in sys.modules if k.startswith("app.") or k == "app"]:
            sys.modules.pop(key, None)


@pytest.fixture
async def real_db():
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.mark.integration
@pytest.mark.anyio
async def test_full_flow_routes_persisted_to_db(app, real_db):
    import app.database as db
    import app.http_client as http

    db.AsyncSessionLocal = real_db

    backend_transport = ASGITransport(app=app)
    http.client = httpx.AsyncClient(
        transport=backend_transport,
        base_url="http://backend",
        timeout=10.0,
    )

    # Import and run the microservice worker with its http client
    # pointed at the backend app transport
    with _microservice_path():
        # Clear any stale cached modules before importing
        for key in [k for k in sys.modules if k.startswith("app.") or k == "app"]:
            sys.modules.pop(key, None)

        import app.http_client as ms_http  # microservice's http_client
        from app.worker import run_search

        ms_http.client = httpx.AsyncClient(
            transport=backend_transport,
            base_url="http://backend",
            timeout=10.0,
        )

        async with AsyncClient(transport=backend_transport, base_url="http://backend") as client:
            response = await client.post("/api/search", json={"smiles": "CCO"})
            assert response.status_code == 201
            search_id = response.json()["id"]

        callback_url = f"http://backend/api/search/{search_id}/update"
        await run_search("CCO", callback_url)
        await ms_http.client.aclose()

    await http.client.aclose()

    # Verify DB state
    async with real_db() as session:
        result = await session.execute(
            text("SELECT status FROM searches WHERE id = :id"),
            {"id": search_id},
        )
        assert result.one().status.lower() == "completed"

        result = await session.execute(
            text("SELECT COUNT(*) FROM routes WHERE search_id = :id"),
            {"id": search_id},
        )
        assert result.scalar_one() == 3


TEST_ROUTES_FILE = Path(__file__).parent / "fixtures" / "test_routes.json"
EMPTY_ROUTES_FILE = Path(__file__).parent / "fixtures" / "empty_routes.json"


@pytest.mark.integration
@pytest.mark.anyio
async def test_full_flow_with_injected_routes(app, real_db):
    """5 routes posted in batches of 2 (batches: 2, 2, 1).
    Verifies all 5 routes are persisted and status is completed."""
    import json

    import app.database as db
    import app.http_client as http

    db.AsyncSessionLocal = real_db

    backend_transport = ASGITransport(app=app)
    http.client = httpx.AsyncClient(
        transport=backend_transport,
        base_url="http://backend",
        timeout=10.0,
    )

    def load_test_routes() -> list:
        with open(TEST_ROUTES_FILE) as f:
            return json.load(f)

    with _microservice_path():
        for key in [k for k in sys.modules if k.startswith("app.") or k == "app"]:
            sys.modules.pop(key, None)

        import app.http_client as ms_http
        from app.worker import run_search

        ms_http.client = httpx.AsyncClient(
            transport=backend_transport,
            base_url="http://backend",
            timeout=10.0,
        )

        async with AsyncClient(transport=backend_transport, base_url="http://backend") as client:
            response = await client.post("/api/search", json={"smiles": "CCO"})
            assert response.status_code == 201
            search_id = response.json()["id"]

        callback_url = f"http://backend/api/search/{search_id}/update"

        mock_settings = MagicMock()
        mock_settings.BATCH_SIZE = 2
        mock_settings.BATCH_DELAY_SECONDS = 0

        with (
            patch("get_routes.load_example_routes", side_effect=load_test_routes),
            patch("app.worker.get_settings", return_value=mock_settings),
        ):
            await run_search("CCO", callback_url)

        await ms_http.client.aclose()

    await http.client.aclose()

    async with real_db() as session:
        result = await session.execute(
            text("SELECT status FROM searches WHERE id = :id"),
            {"id": search_id},
        )
        assert result.one().status.lower() == "completed"

        result = await session.execute(
            text("SELECT score FROM routes WHERE search_id = :id ORDER BY score DESC"),
            {"id": search_id},
        )
        scores = [row.score for row in result.all()]
        assert len(scores) == 5
        assert scores == pytest.approx([0.95, 0.85, 0.75, 0.65, 0.55])


@pytest.mark.integration
@pytest.mark.anyio
async def test_empty_routes_search_completes_with_no_results(app, real_db):
    """When the microservice returns no routes, the search should complete
    with status=completed and zero routes in the DB."""
    import json

    import app.database as db
    import app.http_client as http

    db.AsyncSessionLocal = real_db

    backend_transport = ASGITransport(app=app)
    http.client = httpx.AsyncClient(
        transport=backend_transport,
        base_url="http://backend",
        timeout=10.0,
    )

    def load_empty_routes() -> list:
        with open(EMPTY_ROUTES_FILE) as f:
            return json.load(f)

    with _microservice_path():
        for key in [k for k in sys.modules if k.startswith("app.") or k == "app"]:
            sys.modules.pop(key, None)

        import app.http_client as ms_http
        from app.worker import run_search

        ms_http.client = httpx.AsyncClient(
            transport=backend_transport,
            base_url="http://backend",
            timeout=10.0,
        )

        async with AsyncClient(transport=backend_transport, base_url="http://backend") as client:
            response = await client.post("/api/search", json={"smiles": "CCO"})
            assert response.status_code == 201
            search_id = response.json()["id"]

        callback_url = f"http://backend/api/search/{search_id}/update"

        with patch("get_routes.load_example_routes", side_effect=load_empty_routes):
            await run_search("CCO", callback_url)

        await ms_http.client.aclose()

    await http.client.aclose()

    async with real_db() as session:
        result = await session.execute(
            text("SELECT status FROM searches WHERE id = :id"),
            {"id": search_id},
        )
        assert result.one().status.lower() == "completed"

        result = await session.execute(
            text("SELECT COUNT(*) FROM routes WHERE search_id = :id"),
            {"id": search_id},
        )
        assert result.scalar_one() == 0
