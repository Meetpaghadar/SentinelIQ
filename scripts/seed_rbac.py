from sqlalchemy import select

from sentineliq.db.session import SessionLocal
from sentineliq.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)

ADMIN_EMAIL = "admin@sentineliq.local"
ROLE_NAME = "admin"
PERMISSION_CODES = {
    "knowledge:query": "Query authorized knowledge",
    "knowledge:classification:internal": "Read internal knowledge",
}


def main() -> None:
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == ADMIN_EMAIL))

        if user is None:
            raise ValueError(f"User not found: {ADMIN_EMAIL}")

        permissions: list[Permission] = []
        for code, description in PERMISSION_CODES.items():
            permission = session.scalar(select(Permission).where(Permission.code == code))
            if permission is None:
                permission = Permission(code=code, description=description)
                session.add(permission)
                session.flush()
            permissions.append(permission)

        role = session.scalar(
            select(Role).where(
                Role.tenant_id == user.tenant_id,
                Role.name == ROLE_NAME,
            )
        )

        if role is None:
            role = Role(
                tenant_id=user.tenant_id,
                name=ROLE_NAME,
                description="Tenant administrator",
            )
            session.add(role)
            session.flush()

        user_role = session.scalar(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == role.id,
                UserRole.tenant_id == user.tenant_id,
            )
        )

        if user_role is None:
            session.add(
                UserRole(
                    user_id=user.id,
                    role_id=role.id,
                    tenant_id=user.tenant_id,
                )
            )

        for permission in permissions:
            role_permission = session.scalar(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == permission.id,
                )
            )
            if role_permission is None:
                session.add(
                    RolePermission(
                        role_id=role.id,
                        permission_id=permission.id,
                    )
                )

        session.commit()

        print(f"User: {user.email}")
        print(f"Role: {role.name}")
        print(f"Permissions: {', '.join(sorted(PERMISSION_CODES))}")
        print("RBAC seeded successfully.")


if __name__ == "__main__":
    main()
