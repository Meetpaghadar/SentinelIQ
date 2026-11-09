from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from sentineliq.config import get_settings
from sentineliq.contracts import AuthorizationContext
from sentineliq.db.session import get_db
from sentineliq.models import Permission, Role, RolePermission, User, UserRole


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: UUID
    tenant_id: UUID
    roles: frozenset[str]
    permissions: frozenset[str]
    attributes: dict[str, str]

    def authorization_context(self) -> AuthorizationContext:
        return AuthorizationContext(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            roles=self.roles,
            permissions=self.permissions,
            attributes=self.attributes,
        )


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

    return resolve_authenticated_user(
        session,
        user_id=user_id,
        tenant_id=token_tenant_id,
    )


def resolve_authenticated_user(
    session: Session,
    *,
    user_id: UUID,
    tenant_id: UUID,
) -> AuthenticatedUser:
    user = session.get(User, user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not active",
        )

    if user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid tenant context",
        )

    role_names = frozenset(
        session.scalars(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == user.id,
                UserRole.tenant_id == user.tenant_id,
                Role.tenant_id == user.tenant_id,
            )
        ).all()
    )
    permission_codes = frozenset(
        session.scalars(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(
                UserRole.user_id == user.id,
                UserRole.tenant_id == user.tenant_id,
            )
        ).all()
    )

    return AuthenticatedUser(
        user_id=user.id,
        tenant_id=user.tenant_id,
        roles=role_names,
        permissions=permission_codes,
        attributes={},
    )
