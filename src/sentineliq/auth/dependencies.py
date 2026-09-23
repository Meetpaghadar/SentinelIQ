from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from sentineliq.config import get_settings
from sentineliq.db.session import get_db
from sentineliq.models import User


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: UUID
    tenant_id: UUID


bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: Session = Depends(get_db),
) -> AuthenticatedUser:
    settings = get_settings()

    if settings.jwt_secret_key is None:
        raise RuntimeError("SENTINELIQ_JWT_SECRET_KEY is required")

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        user_id = UUID(payload["sub"])
        token_tenant_id = UUID(payload["tenant_id"])

    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from exc

    user = session.get(User, user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not active",
        )

    if user.tenant_id != token_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid tenant context",
        )

    return AuthenticatedUser(
        user_id=user.id,
        tenant_id=user.tenant_id,
    )
