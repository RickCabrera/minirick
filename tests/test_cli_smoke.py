"""Tests básicos de smoke — verifican que el paquete se importa y el CLI responde."""

from __future__ import annotations

from typer.testing import CliRunner

from minirick import __version__
from minirick.cli import app

runner = CliRunner()


def test_package_has_version() -> None:
    assert __version__ == "0.1.0"


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "minirick" in result.stdout
    assert __version__ in result.stdout


def test_help_command() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "minirick" in result.stdout.lower()


def test_root_command_without_session_exits_with_error(monkeypatch, tmp_path):
    """Sin sesión, minirick (sin args) debe salir con error amigable."""
    from minirick import auth

    monkeypatch.setattr(auth, "get_session_file", lambda: tmp_path / "noop.json")
    result = runner.invoke(app, [])
    assert result.exit_code != 0
    assert "login" in result.stdout.lower() or "sesión" in result.stdout.lower()


def test_root_command_with_session_launches_dashboard(monkeypatch, tmp_path):
    """Con sesión, minirick (sin args) debe llamar launch_dashboard."""
    import json

    from minirick import auth

    session_path = tmp_path / "session.json"
    session_path.write_text(
        json.dumps({"access_token": "a", "refresh_token": "b"}), encoding="utf-8"
    )
    monkeypatch.setattr(auth, "get_session_file", lambda: session_path)

    called = {"launched": False}

    def fake_launch():
        called["launched"] = True

    monkeypatch.setattr("minirick.dashboard.window.launch_dashboard", fake_launch)

    from unittest.mock import MagicMock

    monkeypatch.setattr(auth, "get_client", lambda: MagicMock())

    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert called["launched"] is True
