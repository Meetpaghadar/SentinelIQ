from fastapi.testclient import TestClient

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
