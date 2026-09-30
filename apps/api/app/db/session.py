from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


@lru_cache
def get_async_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.effective_database_url,
        echo=settings.database_echo,
        pool_pre_ping=True,
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_async_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_async_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a database session per request."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        yield session
