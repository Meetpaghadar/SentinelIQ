import json
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session
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
    policies_resolved: bool = False


def scope_from_authorization(
    authorization: AuthorizationContext,
) -> RetrievalAccessScope:
    classifications = {"public"}
    classifications.update(
        permission.removeprefix("knowledge:classification:")
        for permission in authorization.permissions
        if permission.startswith("knowledge:classification:")
    )

    configured_classifications = authorization.attributes.get("allowed_classifications")
    if isinstance(configured_classifications, str):
        classifications.update(
            item.strip().casefold()
            for item in configured_classifications.split(",")
            if item.strip()
        )

    document_ids: frozenset[UUID] | None = None
    configured_document_ids = authorization.attributes.get("allowed_document_ids")
    if isinstance(configured_document_ids, str):
        try:
            document_ids = frozenset(
                UUID(item.strip()) for item in configured_document_ids.split(",") if item.strip()
            )
        except ValueError:
            document_ids = frozenset()

    return RetrievalAccessScope(
        tenant_id=authorization.tenant_id,
        allowed_classifications=frozenset(classifications),
        allowed_document_ids=document_ids,
    )


def resolve_access_scope(
    session: Session,
    authorization: AuthorizationContext,
) -> RetrievalAccessScope:
    base_scope = scope_from_authorization(authorization)
    statement = select(
        Document.id,
        Document.access_policy,
    ).where(
        Document.tenant_id == authorization.tenant_id,
    )

    if base_scope.allowed_classifications is not None:
        if not base_scope.allowed_classifications:
            return RetrievalAccessScope(
                tenant_id=authorization.tenant_id,
                allowed_classifications=frozenset(),
                allowed_document_ids=frozenset(),
                policies_resolved=True,
            )
        statement = statement.where(
            Document.classification.in_(base_scope.allowed_classifications),
        )

    if base_scope.allowed_document_ids is not None:
        if not base_scope.allowed_document_ids:
            return RetrievalAccessScope(
                tenant_id=authorization.tenant_id,
                allowed_classifications=base_scope.allowed_classifications,
                allowed_document_ids=frozenset(),
                policies_resolved=True,
            )
        statement = statement.where(Document.id.in_(base_scope.allowed_document_ids))

    allowed_document_ids = frozenset(
        document_id
        for document_id, access_policy in session.execute(statement)
        if _policy_allows(access_policy, authorization)
    )

    return RetrievalAccessScope(
        tenant_id=authorization.tenant_id,
        allowed_classifications=base_scope.allowed_classifications,
        allowed_document_ids=allowed_document_ids,
        policies_resolved=True,
    )


def _policy_allows(
    raw_policy: str | None,
    authorization: AuthorizationContext,
) -> bool:
    if raw_policy is None or not raw_policy.strip():
        return True

    try:
        policy = json.loads(raw_policy)
    except json.JSONDecodeError:
        return False

    if not isinstance(policy, dict):
        return False
    if not set(policy).issubset({"roles", "permissions", "attributes"}):
        return False

    roles = policy.get("roles", [])
    permissions = policy.get("permissions", [])
    attributes = policy.get("attributes", {})

    if not _string_list(roles) or not _string_list(permissions):
        return False
    if not isinstance(attributes, dict):
        return False
    if not all(
        isinstance(key, str) and isinstance(value, str) for key, value in attributes.items()
    ):
        return False

    if roles and authorization.roles.isdisjoint(roles):
        return False
    if permissions and not set(permissions).issubset(authorization.permissions):
        return False

    return all(
        key in authorization.attributes and str(authorization.attributes[key]) == value
        for key, value in attributes.items()
    )


def _string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def build_access_predicates(
    scope: RetrievalAccessScope,
) -> list[ColumnElement[bool]]:
    predicates: list[ColumnElement[bool]] = [Document.tenant_id == scope.tenant_id]

    if not scope.policies_resolved:
        predicates.append(or_(Document.access_policy.is_(None), Document.access_policy == ""))

    if scope.allowed_classifications is not None:
        if not scope.allowed_classifications:
            return [Document.id.is_(None)]

        predicates.append(Document.classification.in_(scope.allowed_classifications))

    if scope.allowed_document_ids is not None:
        if not scope.allowed_document_ids:
            return [Document.id.is_(None)]

        predicates.append(Document.id.in_(scope.allowed_document_ids))

    return predicates
