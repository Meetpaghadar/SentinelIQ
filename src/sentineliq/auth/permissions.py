from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from sentineliq.auth.dependencies import (
    AuthenticatedUser,
    get_current_user,
)
from sentineliq.db.session import get_db
from sentineliq.models import Permission, RolePermission, UserRole


def require_permission(
    permission_code: str,
) -> Callable[..., AuthenticatedUser]:
    def dependency(
        current_user: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_db),
    ) -> AuthenticatedUser:
        permission_id = session.scalar(
            select(Permission.id)
            .join(
                RolePermission,
                RolePermission.permission_id == Permission.id,
            )
            .join(
                UserRole,
                UserRole.role_id == RolePermission.role_id,
            )
            .where(
                UserRole.user_id == current_user.user_id,
                UserRole.tenant_id == current_user.tenant_id,
                Permission.code == permission_code,
            )
            .limit(1)
        )

        if permission_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current_user

    return dependency
