import os

# Force the test environment before any app modules are imported so the
# settings layer falls back to in-memory SQLite instead of requiring a
# live PostgreSQL server.
os.environ.setdefault("LABISH_ENVIRONMENT", "test")
os.environ.pop("LABISH_DATABASE_URL", None)
