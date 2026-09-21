from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from sentineliq import __version__
from sentineliq.app import create_app
from sentineliq.config import Settings


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(create_app()) as test_client:
        yield test_client


def test_version() -> None:
    assert __version__ == "0.1.0"


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SENTINELIQ_ENV", raising=False)
    monkeypatch.delenv("SENTINELIQ_PORT", raising=False)
    settings = Settings()
    assert settings.port == 8000
    assert settings.env == "development"


def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_ok(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_unknown_route_returns_404(client: TestClient) -> None:
    response = client.get("/does-not-exist")
    assert response.status_code == 404


def test_health_rejects_post(client: TestClient) -> None:
    response = client.post("/health")
    assert response.status_code == 405


def test_invalid_port_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SENTINELIQ_PORT", "not-a-port")
    with pytest.raises(ValidationError):
        Settings()
