import uuid
from collections.abc import Generator

import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from sentineliq.api.v1.auth import login
from sentineliq.api.v1.schemas import LoginRequest
from sentineliq.auth.dependencies import resolve_authenticated_user
from sentineliq.auth.passwords import hash_password
from sentineliq.config import get_settings
from sentineliq.contracts import AuthorizationContext
from sentineliq.db.session import engine
from sentineliq.models import (
    Chunk,
    Document,
    DocumentVersion,
    ParentChunk,
    Permission,
    Role,
    RolePermission,
    Tenant,
    User,
    UserRole,
)
from sentineliq.retrieval.access import resolve_access_scope, scope_from_authorization
from sentineliq.retrieval.models import RetrievalResult
from sentineliq.retrieval.parent_expansion import ParentExpander
from sentineliq.retrieval.sparse import BM25Retriever


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


def _document(
    db: Session,
    tenant: Tenant,
    *,
    title: str,
    classification: str = "public",
    access_policy: str | None = None,
) -> tuple[Document, DocumentVersion, Chunk]:
    document = Document(
        tenant=tenant,
        title=title,
        source_type="test",
        classification=classification,
        access_policy=access_policy,
    )
    version = DocumentVersion(
        document=document,
        version_number=1,
        content_hash=uuid.uuid4().hex,
        storage_path=f"test/{uuid.uuid4()}",
        mime_type="text/plain",
        status="active",
    )
    chunk = Chunk(
        document_version=version,
        chunk_index=0,
        content=f"unique-foundation-evidence {title}",
    )
    db.add(document)
    db.flush()
    return document, version, chunk


def test_sparse_retrieval_enforces_tenant_classification_and_policy(db: Session) -> None:
    tenant_a = Tenant(name="Scope A", slug=f"scope-a-{uuid.uuid4()}")
    tenant_b = Tenant(name="Scope B", slug=f"scope-b-{uuid.uuid4()}")
    db.add_all([tenant_a, tenant_b])
    db.flush()

    public, _, _ = _document(db, tenant_a, title="authorized-public")
    _document(db, tenant_a, title="denied-internal", classification="internal")
    _document(db, tenant_a, title="denied-policy", access_policy='{"roles":["admin"]}')
    _document(db, tenant_b, title="denied-cross-tenant")

    scope = scope_from_authorization(
        AuthorizationContext(tenant_id=tenant_a.id, user_id=uuid.uuid4())
    )
    results = BM25Retriever().search(
        db,
        tenant_id=tenant_a.id,
        query="unique foundation evidence",
        candidate_k=20,
        access_scope=scope,
    )

    assert {result.document_id for result in results} == {public.id}

    internal_scope = scope_from_authorization(
        AuthorizationContext(
            tenant_id=tenant_a.id,
            user_id=uuid.uuid4(),
            permissions=frozenset({"knowledge:classification:internal"}),
        )
    )
    internal_results = BM25Retriever().search(
        db,
        tenant_id=tenant_a.id,
        query="unique foundation evidence",
        candidate_k=20,
        access_scope=internal_scope,
    )
    assert {result.document_title for result in internal_results} == {
        "authorized-public",
        "denied-internal",
    }

    role_scope = resolve_access_scope(
        db,
        AuthorizationContext(
            tenant_id=tenant_a.id,
            user_id=uuid.uuid4(),
            roles=frozenset({"admin"}),
        ),
    )
    role_results = BM25Retriever().search(
        db,
        tenant_id=tenant_a.id,
        query="unique foundation evidence",
        candidate_k=20,
        access_scope=role_scope,
    )
    assert {result.document_title for result in role_results} == {
        "authorized-public",
        "denied-policy",
    }


def test_parent_expansion_uses_parent_identity_and_rejects_cross_version(db: Session) -> None:
    tenant = Tenant(name="Parents", slug=f"parents-{uuid.uuid4()}")
    db.add(tenant)
    db.flush()
    document, version, child = _document(db, tenant, title="parent-source")
    parent = ParentChunk(
        document_version=version,
        parent_index=0,
        content="authorized parent content",
    )
    child.parent_chunk = parent
    db.flush()

    result = RetrievalResult(
        chunk_id=child.id,
        document_id=document.id,
        document_title=document.title,
        document_version_id=version.id,
        version_number=1,
        page_number=None,
        content=child.content,
        similarity=0.8,
    )
    scope = scope_from_authorization(
        AuthorizationContext(tenant_id=tenant.id, user_id=uuid.uuid4())
    )
    expanded = ParentExpander().expand(db, children=[result], access_scope=scope)
    assert expanded[0].chunk_id == parent.id
    assert expanded[0].child_chunk_id == child.id
    assert expanded[0].content == "authorized parent content"

    _, other_version, _ = _document(db, tenant, title="other-version")
    parent.document_version = other_version
    db.flush()
    rejected = ParentExpander().expand(db, children=[result], access_scope=scope)
    assert rejected == [result]

    parent.document_version = version
    document.access_policy = '{"roles":["admin"]}'
    db.flush()
    restricted_scope = resolve_access_scope(
        db,
        AuthorizationContext(tenant_id=tenant.id, user_id=uuid.uuid4()),
    )
    unauthorized = ParentExpander().expand(
        db,
        children=[result],
        access_scope=restricted_scope,
    )
    assert unauthorized == [result]


def test_runtime_authorization_populates_roles_and_permissions(db: Session) -> None:
    tenant = Tenant(name="Authorization", slug=f"authorization-{uuid.uuid4()}")
    user = User(
        tenant=tenant,
        email="authorized@example.test",
        display_name="Authorized",
    )
    role = Role(tenant=tenant, name="knowledge-reader")
    permission = Permission(
        code=f"knowledge:query:{uuid.uuid4()}",
        description="Query knowledge",
    )
    db.add_all([tenant, user, role, permission])
    db.flush()
    db.add_all(
        [
            UserRole(user_id=user.id, role_id=role.id, tenant_id=tenant.id),
            RolePermission(role_id=role.id, permission_id=permission.id),
        ]
    )
    db.flush()

    authenticated = resolve_authenticated_user(
        db,
        user_id=user.id,
        tenant_id=tenant.id,
    )
    authorization = authenticated.authorization_context()

    assert authorization.roles == frozenset({"knowledge-reader"})
    assert authorization.permissions == frozenset({permission.code})
    assert authorization.attributes == {}


def test_login_requires_tenant_when_email_exists_in_multiple_tenants(db: Session) -> None:
    settings = get_settings()
    assert settings.jwt_secret_key is not None
    tenant_a = Tenant(name="Login A", slug=f"login-a-{uuid.uuid4()}")
    tenant_b = Tenant(name="Login B", slug=f"login-b-{uuid.uuid4()}")
    password = "correct horse battery staple"
    db.add_all(
        [
            User(
                tenant=tenant_a,
                email="shared-login@example.test",
                display_name="A",
                password_hash=hash_password(password),
            ),
            User(
                tenant=tenant_b,
                email="shared-login@example.test",
                display_name="B",
                password_hash=hash_password(password),
            ),
        ]
    )
    db.flush()

    token = login(
        LoginRequest(
            tenant=tenant_b.slug,
            email="shared-login@example.test",
            password=password,
        ),
        db,
    ).access_token
    claims = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert claims["tenant_id"] == str(tenant_b.id)

    with pytest.raises(HTTPException) as exc_info:
        login(
            LoginRequest(
                tenant="not-a-tenant",
                email="shared-login@example.test",
                password=password,
            ),
            db,
        )
    assert exc_info.value.status_code == 401
