from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.sql.elements import ColumnElement

from sentineliq.contracts import (
    AuthorizationContext,
)
from sentineliq.models import Document


@dataclass(frozen=True, slots=True)
class RetrievalAccessScope:
    tenant_id: UUID

    allowed_classifications: frozenset[str] | None = None

    allowed_document_ids: frozenset[UUID] | None = None


def scope_from_authorization(
    authorization: AuthorizationContext,
) -> RetrievalAccessScope:
    return RetrievalAccessScope(
        tenant_id=authorization.tenant_id,
    )


def build_access_predicates(
    scope: RetrievalAccessScope,
) -> list[ColumnElement[bool]]:
    predicates: list[ColumnElement[bool]] = [Document.tenant_id == scope.tenant_id]

    if scope.allowed_classifications is not None:
        if not scope.allowed_classifications:
            return [Document.id.is_(None)]

        predicates.append(Document.classification.in_(scope.allowed_classifications))

    if scope.allowed_document_ids is not None:
        if not scope.allowed_document_ids:
            return [Document.id.is_(None)]

        predicates.append(Document.id.in_(scope.allowed_document_ids))

    return predicates
