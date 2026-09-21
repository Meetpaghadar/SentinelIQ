from pathlib import Path

import pytest

from sentineliq.cli import main
from sentineliq.config import get_settings


def _forbid_server_start(*_args: object, **_kwargs: object) -> None:
    raise AssertionError("uvicorn.run must not be called")


def test_config_command_does_not_start_server(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SENTINELIQ_ENV", raising=False)

    monkeypatch.setattr("sentineliq.cli.uvicorn.run", _forbid_server_start)
    get_settings.cache_clear()
    main(["config"])
    output = capsys.readouterr().out
    assert "environment =" in output
    assert "port =" in output


def test_config_command_shows_environment_from_env(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SENTINELIQ_ENV", "test")
    monkeypatch.setattr("sentineliq.cli.uvicorn.run", _forbid_server_start)
    get_settings.cache_clear()
    main(["config"])
    assert "environment = test" in capsys.readouterr().out


def test_config_command_rejects_invalid_port(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SENTINELIQ_PORT", "not-a-port")
    get_settings.cache_clear()
    with pytest.raises(SystemExit) as exited:
        main(["config"])
    assert exited.value.code == 1
    error = capsys.readouterr().err
    assert "SENTINELIQ_PORT" in error or "port" in error.lower()
    assert "not-a-port" in error or "int" in error.lower() or "type" in error.lower()


def test_unknown_command_does_not_start_server(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("sentineliq.cli.uvicorn.run", _forbid_server_start)
    with pytest.raises(SystemExit) as exited:
        main(["not-a-command"])
    assert exited.value.code == 2
    assert "unknown command" in capsys.readouterr().err


def test_missing_command_does_not_start_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("sentineliq.cli.uvicorn.run", _forbid_server_start)
    with pytest.raises(SystemExit) as exited:
        main([])
    assert exited.value.code == 2
