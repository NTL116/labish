"""SAP gateway settings + federated login tests.

External SAP network traffic is simulated by patching the Service Layer
client's HTTP surface with ``unittest.mock.patch`` decorators, so the
suite never performs live network calls.
"""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlmodel import SQLModel, select

from app.core.security import decode_access_token, encrypt_secret
from app.db.session import get_async_engine, get_sessionmaker
from app.main import app
from app.models import SAPConfig

SAP_CLIENT = "app.integrations.sap.service_layer.SAPServiceLayerClient"

VALID_PAYLOAD = {
    "service_layer_url": "https://sap.example.com:50000/b1s/v1",
    "company_db": "SBO_LABISH",
    "username": "manager",
    "password": "sap-secret",
}


@pytest_asyncio.fixture
async def db() -> None:
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def validated_sap_config(db) -> SAPConfig:
    config = SAPConfig(
        service_layer_url=VALID_PAYLOAD["service_layer_url"],
        company_db=VALID_PAYLOAD["company_db"],
        username=VALID_PAYLOAD["username"],
        password=encrypt_secret("sap-secret"),
        is_validated=True,
    )
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        session.add(config)
        await session.commit()
        await session.refresh(config)
    return config


def _login_response(status_code: int = 200, session_id: str = "abc123"):
    request = pytest.importorskip("httpx").Request("POST", "http://sap/Login")
    return pytest.importorskip("httpx").Response(
        status_code, json={"SessionId": session_id}, request=request
    )


# -- /settings/sap/test ----------------------------------------------------


@pytest.mark.asyncio
@patch(f"{SAP_CLIENT}.login", new_callable=AsyncMock)
async def test_sap_test_endpoint_success(
    mock_login: AsyncMock, client: AsyncClient
) -> None:
    from app.integrations.sap.service_layer import SAPLoginResult

    mock_login.return_value = SAPLoginResult(success=True, session_id="s1")

    response = await client.post("/settings/sap/test", json=VALID_PAYLOAD)

    assert response.status_code == 200
    assert response.json()["success"] is True
    mock_login.assert_awaited_once()


@pytest.mark.asyncio
@patch(f"{SAP_CLIENT}.login", new_callable=AsyncMock)
async def test_sap_test_endpoint_failure_returns_502(
    mock_login: AsyncMock, client: AsyncClient
) -> None:
    from app.integrations.sap.service_layer import SAPLoginResult

    mock_login.return_value = SAPLoginResult(success=False, error="bad creds")

    response = await client.post("/settings/sap/test", json=VALID_PAYLOAD)

    assert response.status_code == 502


# -- /settings/sap/save ----------------------------------------------------


@pytest.mark.asyncio
@patch(f"{SAP_CLIENT}.login", new_callable=AsyncMock)
async def test_sap_save_verifies_and_locks_validated_flag(
    mock_login: AsyncMock, client: AsyncClient
) -> None:
    from app.integrations.sap.service_layer import SAPLoginResult

    mock_login.return_value = SAPLoginResult(success=True, session_id="s1")

    response = await client.post("/settings/sap/save", json=VALID_PAYLOAD)

    assert response.status_code == 200
    assert response.json()["is_validated"] is True

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        result = await session.execute(select(SAPConfig))
        config = result.scalars().one()
    assert config.is_validated is True
    assert config.company_db == "SBO_LABISH"
    # Credential must be encrypted at rest, never plaintext.
    assert config.password != "sap-secret"


@pytest.mark.asyncio
@patch(f"{SAP_CLIENT}.login", new_callable=AsyncMock)
async def test_sap_save_rejects_unverified_credentials(
    mock_login: AsyncMock, client: AsyncClient
) -> None:
    from app.integrations.sap.service_layer import SAPLoginResult

    mock_login.return_value = SAPLoginResult(success=False, error="nope")

    response = await client.post("/settings/sap/save", json=VALID_PAYLOAD)

    assert response.status_code == 502
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        result = await session.execute(select(SAPConfig))
        assert result.scalars().first() is None


# -- federated /auth/login -------------------------------------------------


@pytest.mark.asyncio
@patch(f"{SAP_CLIENT}.authenticate_identity", new_callable=AsyncMock)
async def test_login_federates_staff_via_sap(
    mock_identity: AsyncMock,
    client: AsyncClient,
    validated_sap_config: SAPConfig,
) -> None:
    from app.integrations.sap.service_layer import SAPIdentity

    mock_identity.return_value = SAPIdentity(
        authenticated=True, role="staff", subject="emp@example.com"
    )

    response = await client.post(
        "/auth/login",
        json={"email": "emp@example.com", "password": "pw"},
    )

    assert response.status_code == 200
    payload = decode_access_token(response.json()["access_token"])
    assert payload["sub"] == "emp@example.com"
    assert payload["role"] == "staff"
    assert payload["idp"] == "sap-b1"


@pytest.mark.asyncio
@patch(f"{SAP_CLIENT}.authenticate_identity", new_callable=AsyncMock)
async def test_login_elevates_superuser_to_admin(
    mock_identity: AsyncMock,
    client: AsyncClient,
    validated_sap_config: SAPConfig,
) -> None:
    from app.integrations.sap.service_layer import SAPIdentity

    mock_identity.return_value = SAPIdentity(
        authenticated=True, role="admin", subject="boss@example.com"
    )

    response = await client.post(
        "/auth/login",
        json={"email": "boss@example.com", "password": "pw"},
    )

    assert response.status_code == 200
    payload = decode_access_token(response.json()["access_token"])
    assert payload["role"] == "admin"


@pytest.mark.asyncio
@patch(f"{SAP_CLIENT}.authenticate_identity", new_callable=AsyncMock)
async def test_login_assigns_client_role_for_business_partner(
    mock_identity: AsyncMock,
    client: AsyncClient,
    validated_sap_config: SAPConfig,
) -> None:
    from app.integrations.sap.service_layer import SAPIdentity

    mock_identity.return_value = SAPIdentity(
        authenticated=True, role="client", subject="buyer@example.com"
    )

    response = await client.post(
        "/auth/login",
        json={"email": "buyer@example.com", "password": "pw"},
    )

    assert response.status_code == 200
    payload = decode_access_token(response.json()["access_token"])
    assert payload["role"] == "client"


@pytest.mark.asyncio
@patch(f"{SAP_CLIENT}.authenticate_identity", new_callable=AsyncMock)
async def test_login_rejects_unknown_sap_identity(
    mock_identity: AsyncMock,
    client: AsyncClient,
    validated_sap_config: SAPConfig,
) -> None:
    from app.integrations.sap.service_layer import SAPIdentity

    mock_identity.return_value = SAPIdentity(
        authenticated=False, error="No matching SAP identity"
    )

    response = await client.post(
        "/auth/login",
        json={"email": "ghost@example.com", "password": "pw"},
    )

    assert response.status_code == 401


# -- SAP identity resolution (simulated Service Layer wire responses) -------


@pytest.mark.asyncio
async def test_authenticate_identity_admin_elevation_from_users_object() -> None:
    from app.integrations.sap.service_layer import (
        SAPLoginResult,
        SAPServiceLayerClient,
    )

    client = SAPServiceLayerClient(
        service_layer_url="https://sap.example.com:50000/b1s/v1",
        company_db="SBO_LABISH",
        username="manager",
        password="sap-secret",
    )

    async def fake_get(path, params=None):
        if path == "/EmployeesInfo":
            return {
                "value": [
                    {"eMail": "boss@example.com", "ApplicationUserID": "boss"}
                ]
            }
        if path == "/Users":
            return {"value": [{"UserCode": "boss", "Superuser": "tYES"}]}
        return None

    with patch.object(
        SAPServiceLayerClient,
        "login",
        new=AsyncMock(return_value=SAPLoginResult(success=True)),
    ), patch.object(SAPServiceLayerClient, "_get", new=AsyncMock(side_effect=fake_get)):
        identity = await client.authenticate_identity("boss@example.com", "pw")

    assert identity.authenticated is True
    assert identity.role == "admin"


@pytest.mark.asyncio
async def test_authenticate_identity_business_partner_contact_match() -> None:
    from app.integrations.sap.service_layer import (
        SAPLoginResult,
        SAPServiceLayerClient,
    )

    client = SAPServiceLayerClient(
        service_layer_url="https://sap.example.com:50000/b1s/v1",
        company_db="SBO_LABISH",
        username="manager",
        password="sap-secret",
    )

    async def fake_get(path, params=None):
        if path == "/EmployeesInfo":
            return {"value": []}
        if path == "/BusinessPartners":
            return {
                "value": [
                    {
                        "CardType": "cCustomer",
                        "ContactEmployees": [
                            {"E_Mail": "buyer@example.com", "Password": "pw"}
                        ],
                    }
                ]
            }
        return None

    with patch.object(
        SAPServiceLayerClient,
        "login",
        new=AsyncMock(return_value=SAPLoginResult(success=True)),
    ), patch.object(SAPServiceLayerClient, "_get", new=AsyncMock(side_effect=fake_get)):
        identity = await client.authenticate_identity("buyer@example.com", "pw")

    assert identity.authenticated is True
    assert identity.role == "client"


# -- /settings/sap/status ----------------------------------------------------


@pytest.mark.asyncio
async def test_sap_status_unconfigured(client: AsyncClient) -> None:
    response = await client.get("/settings/sap/status")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "is_validated": False,
        "is_connected": False,
        "fallback_phone_number": None,
    }


@pytest.mark.asyncio
@patch(f"{SAP_CLIENT}.login", new_callable=AsyncMock)
async def test_sap_status_connected(
    mock_login: AsyncMock,
    client: AsyncClient,
    validated_sap_config: SAPConfig,
) -> None:
    from app.integrations.sap.service_layer import SAPLoginResult

    mock_login.return_value = SAPLoginResult(success=True, session_id="s1")

    response = await client.get("/settings/sap/status")

    assert response.status_code == 200
    body = response.json()
    assert body["is_validated"] is True
    assert body["is_connected"] is True


@pytest.mark.asyncio
@patch(f"{SAP_CLIENT}.login", new_callable=AsyncMock)
async def test_sap_status_handles_connection_drop_gracefully(
    mock_login: AsyncMock,
    client: AsyncClient,
    validated_sap_config: SAPConfig,
) -> None:
    mock_login.side_effect = Exception("connection reset by peer")

    response = await client.get("/settings/sap/status")

    assert response.status_code == 200
    body = response.json()
    assert body["is_validated"] is True
    assert body["is_connected"] is False


@pytest.mark.asyncio
@patch(f"{SAP_CLIENT}.login", new_callable=AsyncMock)
async def test_sap_save_persists_fallback_phone_number(
    mock_login: AsyncMock, client: AsyncClient
) -> None:
    from app.integrations.sap.service_layer import SAPLoginResult

    mock_login.return_value = SAPLoginResult(success=True, session_id="s1")

    response = await client.post(
        "/settings/sap/save",
        json={**VALID_PAYLOAD, "fallback_phone_number": "+1 (555) 010-7000"},
    )

    assert response.status_code == 200

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        result = await session.execute(select(SAPConfig))
        config = result.scalars().one()
    assert config.fallback_phone_number == "+1 (555) 010-7000"

    status = await client.get("/settings/sap/status")
    assert status.json()["fallback_phone_number"] == "+1 (555) 010-7000"
