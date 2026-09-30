from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Default async PostgreSQL DSN used in normal (non-test) environments.
# Credentials are intentionally omitted; supply them via LABISH_DATABASE_URL.
_DEFAULT_POSTGRES_URL = "postgresql+asyncpg://127.0.0.1:5432/labish"

# Safe local fallback used when the app runs in test mode, so the test
# suite never requires a live PostgreSQL server.
_SQLITE_TEST_URL = "sqlite+aiosqlite:///:memory:"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LABISH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Labish Services"
    environment: str = "development"
    database_url: str = _DEFAULT_POSTGRES_URL
    database_echo: bool = False

    @property
    def effective_database_url(self) -> str:
        """Database URL with graceful test isolation.

        When running in the ``test`` environment and no explicit override
        was provided, fall back to an in-memory SQLite database so the
        suite never depends on a live PostgreSQL server.
        """
        if (
            self.environment == "test"
            and self.database_url == _DEFAULT_POSTGRES_URL
        ):
            return _SQLITE_TEST_URL
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
