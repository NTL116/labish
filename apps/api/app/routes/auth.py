from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.security import create_access_token, verify_password
from app.db.session import get_async_session
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest,
    session: AsyncSession = Depends(get_async_session),
) -> TokenResponse:
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
