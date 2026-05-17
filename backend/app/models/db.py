"""
SQLAlchemy ORM models for the searches and routes tables.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from retrosynthesis_search import SearchStatus


class Base(DeclarativeBase):
    pass


class Search(Base):
    __tablename__ = "searches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    smiles: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[SearchStatus] = mapped_column(
        Enum(SearchStatus), nullable=False, default=SearchStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    routes: Mapped[list["Route"]] = relationship("Route", back_populates="search")


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("searches.id"), nullable=False
    )
    batch_index: Mapped[int] = mapped_column(Integer, nullable=False)
    route_index: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    molecules: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    reactions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)

    search: Mapped["Search"] = relationship("Search", back_populates="routes")

    __table_args__ = (
        # Idempotency: duplicate callbacks with same batch/route index are ignored
        UniqueConstraint("search_id", "batch_index", "route_index", name="uq_route_batch"),
    )
