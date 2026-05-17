"""
Async SQLAlchemy engine and session factory. Initialised at startup via lifespan.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings


def make_session_factory() -> async_sessionmaker[AsyncSession]:
    s = get_settings()
    engine = create_async_engine(
        s.DATABASE_URL,
        pool_size=s.DB_POOL_SIZE,
        max_overflow=s.DB_MAX_OVERFLOW,
        pool_pre_ping=True,  # drops stale connections after Postgres idle timeout
    )
    return async_sessionmaker(engine, expire_on_commit=False)


# Set in lifespan so settings are not read at import time
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None
