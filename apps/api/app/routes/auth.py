from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.security import (
    create_access_token,
    decrypt_secret,
    verify_password,
)
from app.db.session import get_async_session
from app.integrations.sap.service_layer import SAPServiceLayerClient
from app.models import SAPConfig, User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


async def _get_active_sap_config(session: AsyncSession) -> SAPConfig | None:
    """Return the verified SAP gateway configuration, if one exists."""
    result = await session.execute(
        select(SAPConfig).where(SAPConfig.is_validated == True)  # noqa: E712
    )
    return result.scalars().first()


async def _sap_federated_login(
    config: SAPConfig, credentials: LoginRequest
) -> TokenResponse:
    """Authenticate against SAP B1 as the single source of truth.

    Internal staff are matched via EmployeesInfo (with SuperUser admin
    elevation from the Users object); otherwise the BusinessPartners
    contacts matrix grants a client role for Lead/Customer/Vendor
    contacts.
    """
    client = SAPServiceLayerClient(
        service_layer_url=config.service_layer_url,
        company_db=config.company_db,
        username=config.username,
        password=decrypt_secret(config.password),
    )
    identity = await client.authenticate_identity(
        email=str(credentials.email), password=credentials.password
    )
    if not identity.authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(
        access_token=create_access_token(
            subject=identity.subject or str(credentials.email),
            extra_claims={"role": identity.role, "idp": "sap-b1"},
        )
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest,
    session: AsyncSession = Depends(get_async_session),
) -> TokenResponse:
    # When a verified SAP gateway is active, SAP B1 is the single source
    # of truth for identity: bypass local credential checks entirely.
    sap_config = await _get_active_sap_config(session)
    if sap_config is not None:
        return await _sap_federated_login(sap_config, credentials)

    result = await session.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()

    if (
        user is None
        or not user.is_active
        or not verify_password(credentials.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(access_token=create_access_token(subject=str(user.id)))
