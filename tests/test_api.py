from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from sentineliq.api.v1 import query as query_module
from sentineliq.api.v1.schemas import QueryRequest
from sentineliq.auth.dependencies import AuthenticatedUser
from sentineliq.contracts import AuthorizationContext
from sentineliq.logging import CORRELATION_ID_HEADER
from sentineliq.main import create_app


def test_health_returns_200(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "SentinelIQ"}


def test_ready_returns_200(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_health_includes_generated_correlation_id(client: TestClient) -> None:
    response = client.get("/health")
    correlation_id = response.headers.get(CORRELATION_ID_HEADER)
    assert correlation_id
    assert correlation_id != "-"


def test_supplied_correlation_id_is_returned(client: TestClient) -> None:
    response = client.get("/health", headers={CORRELATION_ID_HEADER: "test-correlation-id"})
    assert response.headers.get(CORRELATION_ID_HEADER) == "test-correlation-id"


def test_unknown_route_returns_404_without_traceback(client: TestClient) -> None:
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    body = response.text
    assert "Traceback" not in body
    assert response.headers.get(CORRELATION_ID_HEADER)


def test_query_api_cannot_bypass_authentication(client: TestClient) -> None:
    response = client.post("/api/v1/query", json={"question": "What is the policy?"})
    assert response.status_code in {401, 403}


def test_query_api_rejects_excessive_limit_before_execution(client: TestClient) -> None:
    response = client.post(
        "/api/v1/query",
        json={"question": "What is the policy?", "limit": 21},
    )
    assert response.status_code in {401, 403, 422}


def test_query_api_forwards_authorization_and_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid4()
    user_id = uuid4()
    captured: dict[str, object] = {}

    class FakeRAGService:
        def __init__(self, _retrieval_service: object) -> None:
            pass

        def answer(self, **kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(
                answer="No evidence",
                citations=[],
                degraded=False,
                degradation_reason=None,
            )

    monkeypatch.setattr(query_module, "EmbeddingService", lambda: object())
    monkeypatch.setattr(query_module, "RetrievalService", lambda _embedding: object())
    monkeypatch.setattr(query_module, "RAGService", FakeRAGService)

    current_user = AuthenticatedUser(
        user_id=user_id,
        tenant_id=tenant_id,
        roles=frozenset({"reader"}),
        permissions=frozenset({"knowledge:query", "knowledge:classification:internal"}),
        attributes={"department": "security"},
    )
    query_module.query_knowledge(
        request=QueryRequest(question="What is the policy?", limit=12),
        current_user=current_user,
        session=MagicMock(),
    )

    authorization = captured["authorization"]
    assert isinstance(authorization, AuthorizationContext)
    assert authorization.tenant_id == tenant_id
    assert authorization.user_id == user_id
    assert authorization.roles == current_user.roles
    assert authorization.permissions == current_user.permissions
    assert authorization.attributes == current_user.attributes
    assert captured["limit"] == 12


def test_unhandled_error_hides_internals() -> None:
    application = create_app()

    @application.get("/boom")
    def boom() -> None:
        raise RuntimeError("internal-secret-detail")

    with TestClient(application, raise_server_exceptions=False) as test_client:
        response = test_client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "internal-secret-detail" not in response.text
    assert "Traceback" not in response.text
    assert "RuntimeError" not in response.text
    assert response.headers.get(CORRELATION_ID_HEADER)
