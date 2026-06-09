"""
Async engine and session factory, with utility to initialise tables.
"""
from app.core.config import settings
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.models.base import Base
import logging

logger = logging.getLogger(__name__)

# Détection SQLite pour éviter les paramètres incompatibles
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine_kwargs = {
    "echo": False,
    "future": True,
}
if not is_sqlite:
    engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 2,
        "pool_pre_ping": True,
    })

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Create all tables if they don't exist (safe for idempotent runs)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured.")


async def get_session() -> AsyncSession:
    """Dependency-style session generator."""
    async with async_session_factory() as session:
        yield session