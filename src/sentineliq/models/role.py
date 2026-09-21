import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sentineliq.db.base import Base

if TYPE_CHECKING:
    from sentineliq.models.permission import Permission
    from sentineliq.models.tenant import Tenant
    from sentineliq.models.user import User


class Role(Base):
    __tablename__ = "roles"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_roles_tenant_name",
        ),
        UniqueConstraint(
            "id",
            "tenant_id",
            name="uq_roles_id_tenant",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    tenant: Mapped["Tenant"] = relationship(
        back_populates="roles",
    )

    user_assignments: Mapped[list["UserRole"]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
    )

    permission_assignments: Mapped[list["RolePermission"]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
    )


class UserRole(Base):
    __tablename__ = "user_roles"

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            ondelete="CASCADE",
            name="fk_user_roles_user_tenant",
        ),
        ForeignKeyConstraint(
            ["role_id", "tenant_id"],
            ["roles.id", "roles.tenant_id"],
            ondelete="CASCADE",
            name="fk_user_roles_role_tenant",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
    )

    user: Mapped["User"] = relationship(
        back_populates="role_assignments",
    )

    role: Mapped[Role] = relationship(
        back_populates="user_assignments",
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )

    permission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )

    role: Mapped[Role] = relationship(
        back_populates="permission_assignments",
    )

    permission: Mapped["Permission"] = relationship(
        back_populates="role_assignments",
    )
