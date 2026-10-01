"""SAP gateway configuration endpoints.

Routes validate HTTP payloads and delegate: live connectivity checks go
through the SAP integration client, persistence is a simple CRUD write.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.security import encrypt_secret
from app.db.session import get_async_session
from app.integrations.sap.service_layer import SAPServiceLayerClient
from app.models import SAPConfig

router = APIRouter(prefix="/settings", tags=["settings"])


class SAPConnectionRequest(BaseModel):
    service_layer_url: str
    company_db: str
    username: str
    password: str


class SAPTestResponse(BaseModel):
    success: bool
    detail: str


class SAPSaveResponse(BaseModel):
    success: bool
    is_validated: bool
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
        )
        session.add(config)
    else:
        config.service_layer_url = payload.service_layer_url
        config.company_db = payload.company_db
        config.username = payload.username
        config.password = encrypt_secret(payload.password)
        config.is_validated = True
        session.add(config)
    await session.commit()

    return SAPSaveResponse(
        success=True,
        is_validated=True,
        detail="SAP configuration verified and saved",
    )
