import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("MICROSERVICE_URL", "http://localhost:8001")
os.environ.setdefault("BACKEND_URL", "http://localhost:8000")


@pytest.fixture
def app():
    from app.main import app

    return app


@pytest.fixture
def db_mock():
    """Provides a patched AsyncSessionLocal and the underlying session mock."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    with patch("app.routers.search.AsyncSessionLocal", factory):
        yield factory, session
