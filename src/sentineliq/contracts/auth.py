from collections.abc import Mapping
from dataclasses import dataclass, field
from uuid import UUID

AttributeValue = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class AuthorizationContext:
    tenant_id: UUID
    user_id: UUID
    roles: frozenset[str] = field(default_factory=frozenset)
    permissions: frozenset[str] = field(default_factory=frozenset)
    attributes: Mapping[str, AttributeValue] = field(default_factory=dict)

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions
