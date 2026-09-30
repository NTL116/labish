import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_async_engine, get_async_session, get_sessionmaker


def test_settings_use_test_environment() -> None:
    settings = get_settings()
    assert settings.environment == "test"


def test_test_environment_falls_back_to_sqlite() -> None:
    settings = Settings(environment="test")
    assert settings.effective_database_url == "sqlite+aiosqlite:///:memory:"


def test_non_test_environment_defaults_to_postgres() -> None:
    settings = Settings(environment="development")
    assert settings.effective_database_url.startswith("postgresql+asyncpg://")


def test_explicit_database_url_overrides_fallback() -> None:
    settings = Settings(
        environment="test",
        database_url="postgresql+asyncpg://db.example.com:5432/custom",
    )
    assert settings.effective_database_url.endswith("/custom")


def test_engine_and_sessionmaker_are_cached_singletons() -> None:
    assert get_async_engine() is get_async_engine()
    assert get_sessionmaker() is get_sessionmaker()


@pytest.mark.asyncio
async def test_get_async_session_yields_working_session() -> None:
    async for session in get_async_session():
        assert isinstance(session, AsyncSession)
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1
