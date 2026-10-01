"""SAP metadata ingestion engine + management endpoint tests.

External SAP network traffic is simulated by patching the Service Layer
client's HTTP surface with ``unittest.mock.patch``, so the suite never
performs live network calls.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlmodel import SQLModel

from app.core.security import create_access_token, encrypt_secret
from app.db.session import get_async_engine, get_sessionmaker
from app.integrations.sap.service_layer import (
    SAPLoginResult,
    SAPServiceLayerClient,
)
from app.main import app
from app.models import SAPConfig
from app.shared.ingest_sap_metadata import (
    IngestResult,
    compile_typescript,
    ingest_sap_metadata,
    parse_metadata_xml,
    write_dictionary,
)

SAMPLE_METADATA = """<?xml version="1.0" encoding="utf-8"?>
<edmx:Edmx Version="4.0" xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx">
  <edmx:DataServices>
    <Schema Namespace="SAPB1" xmlns="http://docs.oasis-open.org/odata/ns/edm">
      <EntityType Name="BusinessPartners">
        <Key><PropertyRef Name="CardCode"/></Key>
        <Property Name="CardCode" Type="Edm.String" Nullable="false" MaxLength="15"/>
        <Property Name="CardName" Type="Edm.String"/>
        <Property Name="CurrentAccountBalance" Type="Edm.Decimal"/>
        <Property Name="Valid" Type="Edm.Boolean"/>
        <Property Name="CreateDate" Type="Edm.DateTimeOffset"/>
        <Property Name="U_CustomSegment" Type="Edm.String" MaxLength="30"/>
      </EntityType>
      <EntityType Name="Invoices">
        <Key><PropertyRef Name="DocEntry"/></Key>
        <Property Name="DocEntry" Type="Edm.Int32" Nullable="false"/>
        <Property Name="DocTotal" Type="Edm.Decimal"/>
        <Property Name="U_DeliveryWindow" Type="Edm.String"/>
      </EntityType>
      <ComplexType Name="AddressExtension">
        <Property Name="ShipToStreet" Type="Edm.String"/>
        <Property Name="ShipToZipCode" Type="Edm.String"/>
      </ComplexType>
    </Schema>
  </edmx:DataServices>
</edmx:Edmx>
"""


# -- parser / compiler units ------------------------------------------------


def test_parse_metadata_extracts_entities_and_complex_types():
    parsed = parse_metadata_xml(SAMPLE_METADATA)
    assert set(parsed) == {"BusinessPartners", "Invoices", "AddressExtension"}

    bp = parsed["BusinessPartners"]
    assert bp["kind"] == "EntityType"
    assert bp["physical_table"] == "ocrd"
    assert bp["key_fields"] == ["CardCode"]
    by_name = {p["name"]: p for p in bp["properties"]}
    assert by_name["CardCode"]["nullable"] is False
    assert by_name["CardCode"]["is_key"] is True
    assert by_name["CardCode"]["max_length"] == "15"
    assert by_name["U_CustomSegment"]["is_udf"] is True
    assert by_name["CardName"]["is_udf"] is False

    assert parsed["Invoices"]["physical_table"] == "oinv"
    assert parsed["AddressExtension"]["kind"] == "ComplexType"


def test_parse_metadata_maps_odata_primitives_to_typescript():
    parsed = parse_metadata_xml(SAMPLE_METADATA)
    props = {p["name"]: p for p in parsed["BusinessPartners"]["properties"]}
    assert props["CardCode"]["typescript_type"] == "string"
    assert props["CurrentAccountBalance"]["typescript_type"] == "number"
    assert props["Valid"]["typescript_type"] == "boolean"
    assert props["CreateDate"]["typescript_type"] == "string"
    inv = {p["name"]: p for p in parsed["Invoices"]["properties"]}
    assert inv["DocEntry"]["typescript_type"] == "number"


def test_write_dictionary_dumps_physical_table_json(tmp_path: Path):
    parsed = parse_metadata_xml(SAMPLE_METADATA)
    files = write_dictionary(parsed, tmp_path)
    names = {f.name for f in files}
    assert names == {"ocrd.json", "oinv.json", "addressextension.json"}
    ocrd = json.loads((tmp_path / "ocrd.json").read_text())
    assert ocrd["entity"] == "BusinessPartners"
    assert any(p["name"] == "U_CustomSegment" for p in ocrd["properties"])


def test_compile_typescript_emits_strict_interfaces(tmp_path: Path):
    parsed = parse_metadata_xml(SAMPLE_METADATA)
    output = compile_typescript(parsed, tmp_path / "sap.d.ts")
    content = output.read_text()
    assert "export interface BusinessPartners {" in content
    assert "CardCode: string;" in content
    assert "CardName?: string | null;" in content
    assert "CurrentAccountBalance?: number | null;" in content
    assert "Valid?: boolean | null;" in content
    assert "AUTO-GENERATED" in content


@pytest.mark.asyncio
async def test_ingest_sap_metadata_full_pass(tmp_path: Path):
    client = SAPServiceLayerClient(
        service_layer_url="https://sap.example.com:50000/b1s/v2",
        company_db="SBODEMO",
    )
    with (
        patch.object(
            SAPServiceLayerClient,
            "login",
            AsyncMock(
                return_value=SAPLoginResult(success=True, session_id="s")
            ),
        ),
        patch.object(
            SAPServiceLayerClient,
            "get_metadata_xml",
            AsyncMock(return_value=SAMPLE_METADATA),
        ),
    ):
        result = await ingest_sap_metadata(
            client,
            dictionary_dir=tmp_path / "dict",
            typescript_output=tmp_path / "sap.d.ts",
        )
    assert result.success is True
    assert result.entities == 2
    assert result.complex_types == 1
    assert len(result.dictionary_files) == 3
    assert (tmp_path / "sap.d.ts").exists()


@pytest.mark.asyncio
async def test_ingest_fails_gracefully_when_login_rejected(tmp_path: Path):
    client = SAPServiceLayerClient(
        service_layer_url="https://sap.example.com:50000/b1s/v2",
        company_db="SBODEMO",
    )
    with patch.object(
        SAPServiceLayerClient,
        "login",
        AsyncMock(return_value=SAPLoginResult(success=False, error="down")),
    ):
        result = await ingest_sap_metadata(
            client,
            dictionary_dir=tmp_path,
            typescript_output=tmp_path / "sap.d.ts",
        )
    assert result.success is False
    assert result.error == "down"


# -- management endpoint ------------------------------------------------------


@pytest_asyncio.fixture
async def db() -> None:
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def saved_sap_config(db: None) -> SAPConfig:
    config = SAPConfig(
        service_layer_url="https://sap.example.com:50000/b1s/v2",
        company_db="SBODEMO",
        username="manager",
        password=encrypt_secret("sap-secret"),
        is_validated=True,
    )
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        session.add(config)
        await session.commit()
        await session.refresh(config)
    return config


def _auth_headers(role: str = "admin") -> dict[str, str]:
    token = create_access_token(
        subject=f"{role}@example.com", extra_claims={"role": role}
    )
    scheme = "Bearer"
    return {"Authorization": f"{scheme} {token}"}


@pytest.mark.asyncio
async def test_ingest_endpoint_requires_authentication(
    client: AsyncClient, db: None
):
    response = await client.post("/settings/sap/ingest")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ingest_endpoint_rejects_non_admin(
    client: AsyncClient, db: None
):
    response = await client.post(
        "/settings/sap/ingest", headers=_auth_headers(role="staff")
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ingest_endpoint_conflicts_without_saved_config(
    client: AsyncClient, db: None
):
    response = await client.post(
        "/settings/sap/ingest", headers=_auth_headers()
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_ingest_endpoint_runs_engine_with_saved_config(
    client: AsyncClient, saved_sap_config: SAPConfig
):
    ingest_result = IngestResult(
        success=True,
        entities=2,
        complex_types=1,
        dictionary_files=("a.json", "b.json", "c.json"),
        typescript_file="apps/web/src/types/sap.d.ts",
    )
    with patch(
        "app.routes.settings.ingest_sap_metadata",
        AsyncMock(return_value=ingest_result),
    ):
        response = await client.post(
            "/settings/sap/ingest", headers=_auth_headers()
        )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["entities"] == 2
    assert body["dictionary_files"] == 3


@pytest.mark.asyncio
async def test_ingest_endpoint_surfaces_engine_failures(
    client: AsyncClient, saved_sap_config: SAPConfig
):
    with patch(
        "app.routes.settings.ingest_sap_metadata",
        AsyncMock(
            return_value=IngestResult(success=False, error="SAP offline")
        ),
    ):
        response = await client.post(
            "/settings/sap/ingest", headers=_auth_headers()
        )
    assert response.status_code == 502
    assert "SAP offline" in response.json()["detail"]


def test_sync_sap_metadata_task_is_registered():
    from app.tasks.sap_sync import sync_sap_metadata_task

    assert sync_sap_metadata_task.actor_name == "sync_sap_metadata_task"
