"""SAP gateway configuration endpoints.

Routes validate HTTP payloads and delegate: live connectivity checks go
through the SAP integration client, persistence is a simple CRUD write.
"""

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.security import (
    decode_access_token,
    decrypt_secret,
    encrypt_secret,
)
from app.db.session import get_async_session
from app.integrations.sap.service_layer import SAPServiceLayerClient
from app.models import SAPConfig
from app.shared.ingest_sap_metadata import ingest_sap_metadata

router = APIRouter(prefix="/settings", tags=["settings"])

_bearer_scheme = HTTPBearer(auto_error=False)


def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Security(
        _bearer_scheme
    ),
) -> dict:
    """Guard management endpoints: a valid admin bearer token is required."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges are required",
        )
    return payload


class SAPConnectionRequest(BaseModel):
    service_layer_url: str
    company_db: str
    username: str
    password: str
    fallback_phone_number: str | None = None


class SAPTestResponse(BaseModel):
    success: bool
    detail: str


class SAPSaveResponse(BaseModel):
    success: bool
    is_validated: bool
    detail: str


class SAPStatusResponse(BaseModel):
    """Lightweight system status consumed by frontend fallback banners."""

    is_validated: bool
    is_connected: bool
    fallback_phone_number: str | None = None


class SAPIngestResponse(BaseModel):
    """Summary of a completed metadata ingestion pass."""

    success: bool
    entities: int
    complex_types: int
    dictionary_files: int
    typescript_file: str | None
    detail: str


async def _run_test_login(payload: SAPConnectionRequest) -> tuple[bool, str]:
    """Dynamically initialize the SAP client and issue a live login challenge."""
    client = SAPServiceLayerClient(
        service_layer_url=payload.service_layer_url,
        company_db=payload.company_db,
        username=payload.username,
        password=payload.password,
    )
    result = await client.login()
    if result.success:
        return True, "SAP Service Layer login succeeded"
    return False, result.error or "SAP Service Layer login failed"


@router.post("/sap/test", response_model=SAPTestResponse)
async def test_sap_connection(payload: SAPConnectionRequest) -> SAPTestResponse:
    success, detail = await _run_test_login(payload)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=detail
        )
    return SAPTestResponse(success=True, detail=detail)


@router.post("/sap/save", response_model=SAPSaveResponse)
async def save_sap_connection(
    payload: SAPConnectionRequest,
    session: AsyncSession = Depends(get_async_session),
) -> SAPSaveResponse:
    verified, detail = await _run_test_login(payload)
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Refusing to save unverified SAP credentials: {detail}",
        )

    result = await session.execute(select(SAPConfig))
    config = result.scalars().first()
    if config is None:
        config = SAPConfig(
            service_layer_url=payload.service_layer_url,
            company_db=payload.company_db,
            username=payload.username,
            password=encrypt_secret(payload.password),
            is_validated=True,
            fallback_phone_number=payload.fallback_phone_number,
        )
        session.add(config)
    else:
        config.service_layer_url = payload.service_layer_url
        config.company_db = payload.company_db
        config.username = payload.username
        config.password = encrypt_secret(payload.password)
        config.is_validated = True
        config.fallback_phone_number = payload.fallback_phone_number
        session.add(config)
    await session.commit()

    return SAPSaveResponse(
        success=True,
        is_validated=True,
        detail="SAP configuration verified and saved",
    )


@router.get("/sap/status", response_model=SAPStatusResponse)
async def sap_status(
    session: AsyncSession = Depends(get_async_session),
) -> SAPStatusResponse:
    """Report configuration and live SAP connectivity for the frontend.

    Never raises on SAP connection drops: every network/decryption
    failure degrades gracefully to ``is_connected = False`` so public
    pages keep rendering while the fallback banner takes over.
    """
    result = await session.execute(select(SAPConfig))
    config = result.scalars().first()

    if config is None:
        return SAPStatusResponse(is_validated=False, is_connected=False)

    is_connected = False
    if config.is_validated:
        try:
            client = SAPServiceLayerClient(
                service_layer_url=config.service_layer_url,
                company_db=config.company_db,
                username=config.username,
                password=decrypt_secret(config.password),
            )
            # The client already catches HTTP/transport exceptions and
            # returns a failed result instead of raising.
            login = await client.login()
            is_connected = login.success
        except Exception:
            is_connected = False

    return SAPStatusResponse(
        is_validated=config.is_validated,
        is_connected=is_connected,
        fallback_phone_number=config.fallback_phone_number,
    )


@router.post("/sap/ingest", response_model=SAPIngestResponse)
async def ingest_sap_schema(
    session: AsyncSession = Depends(get_async_session),
    _admin: dict = Depends(require_admin),
) -> SAPIngestResponse:
    """Run the SAP metadata ingestion engine instantly (admin only).

    Pulls the raw OData ``$metadata`` document, regenerates the JSON
    data dictionary under ``app/shared/sap_dictionary/`` and recompiles
    the frontend ``apps/web/src/types/sap.d.ts`` definitions.
    """
    result = await session.execute(
        select(SAPConfig).where(SAPConfig.is_validated == True)  # noqa: E712
    )
    config = result.scalars().first()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No validated SAP configuration is saved",
        )

    client = SAPServiceLayerClient(
        config.service_layer_url,
        config.company_db,
        config.username,
        decrypt_secret(config.password),
    )
    ingest = await ingest_sap_metadata(client)
    if not ingest.success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=ingest.error or "SAP metadata ingestion failed",
        )

    return SAPIngestResponse(
        success=True,
        entities=ingest.entities,
        complex_types=ingest.complex_types,
        dictionary_files=len(ingest.dictionary_files),
        typescript_file=ingest.typescript_file,
        detail=(
            f"Ingested {ingest.entities} entities and "
            f"{ingest.complex_types} complex types; data dictionary and "
            "TypeScript definitions refreshed"
        ),
    )
