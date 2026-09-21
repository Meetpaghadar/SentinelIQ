from pathlib import Path

import pytest
from pydantic import ValidationError

from sentineliq import __version__
from sentineliq.config import Settings, get_settings


def test_version() -> None:
    assert __version__ == "0.1.0"


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SENTINELIQ_ENV", raising=False)
    monkeypatch.delenv("SENTINELIQ_PORT", raising=False)
    get_settings.cache_clear()
    settings = Settings()
    assert settings.port == 8000
    assert settings.env == "development"


def test_settings_env_overrides_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.toml").write_text(
        '[app]\nenv = "development"\nport = 8000\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SENTINELIQ_ENV", "test")
    get_settings.cache_clear()
    settings = Settings()
    assert settings.env == "test"
    assert settings.safe_display()["environment"] == "test"


def test_invalid_port_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SENTINELIQ_PORT", "not-a-port")
    get_settings.cache_clear()
    with pytest.raises(ValidationError):
        Settings()
