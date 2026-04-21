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


def test_root_command_shows_banner() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "minirick" in result.stdout.lower()
