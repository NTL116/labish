import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlmodel import SQLModel

from app.core.security import decode_access_token, hash_password
from app.db.session import get_async_engine, get_sessionmaker
from app.main import app
from app.models import User


@pytest_asyncio.fixture
async def seeded_user() -> User:
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    user = User(
        email="alice@example.com",
        hashed_password=hash_password("correct-horse"),
    )
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        session.add(user)
        await session.commit()
        await session.refresh(user)

    yield user

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_login_with_valid_credentials_returns_token(
    client: AsyncClient, seeded_user: User
) -> None:
    response = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "correct-horse"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    payload = decode_access_token(body["access_token"])
    assert payload["sub"] == str(seeded_user.id)


@pytest.mark.asyncio
async def test_login_with_wrong_password_returns_401(
    client: AsyncClient, seeded_user: User
) -> None:
    response = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "wrong"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_with_unknown_email_returns_401(
    client: AsyncClient, seeded_user: User
) -> None:
    response = await client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "correct-horse"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_with_invalid_email_format_returns_422(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/auth/login",
        json={"email": "not-an-email", "password": "x"},
    )

    assert response.status_code == 422
