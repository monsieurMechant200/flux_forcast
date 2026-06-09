"""
Pytest fixtures for async database testing with in-memory SQLite.
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.base import Base
from app.models.domain import (
    HistoricalFlux,
    PredictionsTactical,
    ModelMetrics,
    AgentStaffing,
)  # noqa: F401 ensure models loaded

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def async_session():
    """Provide a fresh in-memory database for each test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_factory() as session:
        yield session

    await engine.dispose()