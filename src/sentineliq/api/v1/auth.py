from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from sentineliq.api.v1.schemas import LoginRequest, TokenResponse
from sentineliq.auth.passwords import verify_password
from sentineliq.auth.tokens import create_access_token
from sentineliq.db.session import get_db
from sentineliq.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    session: Session = Depends(get_db),
) -> TokenResponse:
    user = session.scalar(
        select(User).where(
            User.email == request.email,
            User.is_active.is_(True),
        )
    )

    if (
        user is None
        or user.password_hash is None
        or not verify_password(
            request.password,
            user.password_hash,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
    )

    return TokenResponse(
        access_token=access_token,
    )
