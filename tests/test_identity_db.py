import uuid
from collections.abc import Generator

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sentineliq.db.session import engine
from sentineliq.models import Permission, Role, RolePermission, Tenant, User, UserRole


@pytest.fixture
def db() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def test_tenant_user_role_permission_flow(db: Session) -> None:
    tenant = Tenant(name="Acme", slug=f"acme-{uuid.uuid4()}")
    user = User(
        email="admin@acme.test",
        display_name="Admin",
        tenant=tenant,
    )
    role = Role(
        name="admin",
        description="Tenant administrator",
        tenant=tenant,
    )
    permission = Permission(
        code=f"documents:read:{uuid.uuid4()}",
        description="Read documents",
    )

    db.add_all([tenant, user, role, permission])
    db.flush()

    db.add(
        UserRole(
            user_id=user.id,
            role_id=role.id,
            tenant_id=tenant.id,
        )
    )
    db.add(
        RolePermission(
            role_id=role.id,
            permission_id=permission.id,
        )
    )
    db.flush()

    assert user.tenant_id == tenant.id
    assert role.tenant_id == tenant.id
    assert role.permission_assignments[0].permission.code == permission.code


def test_same_email_allowed_across_tenants(db: Session) -> None:
    tenant_a = Tenant(name="Tenant A", slug=f"tenant-a-{uuid.uuid4()}")
    tenant_b = Tenant(name="Tenant B", slug=f"tenant-b-{uuid.uuid4()}")

    db.add_all(
        [
            User(
                email="shared@example.com",
                display_name="User A",
                tenant=tenant_a,
            ),
            User(
                email="shared@example.com",
                display_name="User B",
                tenant=tenant_b,
            ),
        ]
    )

    db.flush()


def test_duplicate_email_rejected_within_tenant(db: Session) -> None:
    tenant = Tenant(name="Tenant", slug=f"tenant-{uuid.uuid4()}")

    db.add_all(
        [
            User(
                email="duplicate@example.com",
                display_name="First",
                tenant=tenant,
            ),
            User(
                email="duplicate@example.com",
                display_name="Second",
                tenant=tenant,
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        db.flush()


def test_cross_tenant_role_assignment_rejected(db: Session) -> None:
    tenant_a = Tenant(name="Tenant A", slug=f"tenant-a-{uuid.uuid4()}")
    tenant_b = Tenant(name="Tenant B", slug=f"tenant-b-{uuid.uuid4()}")

    user = User(
        email="user@a.test",
        display_name="Tenant A User",
        tenant=tenant_a,
    )

    role = Role(
        name="admin",
        description="Tenant B administrator",
        tenant=tenant_b,
    )

    db.add_all([tenant_a, tenant_b, user, role])
    db.flush()

    db.add(
        UserRole(
            user_id=user.id,
            role_id=role.id,
            tenant_id=tenant_a.id,
        )
    )

    with pytest.raises(IntegrityError):
        db.flush()
