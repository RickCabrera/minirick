"""Tests del launcher cross-platform de tools."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from minirick import launcher
from minirick.models import Tool

# ---------- Helpers ----------


@pytest.fixture
def mac_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fuerza el módulo a comportarse como macOS."""
    monkeypatch.setattr(launcher, "IS_MAC", True)
    monkeypatch.setattr(launcher, "IS_WINDOWS", False)


@pytest.fixture
def windows_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fuerza el módulo a comportarse como Windows."""
    monkeypatch.setattr(launcher, "IS_MAC", False)
    monkeypatch.setattr(launcher, "IS_WINDOWS", True)


# ---------- 1. Tipo desconocido ----------


def test_launch_tool_unknown_type_returns_error() -> None:
    # Tool.type es str libre; forzamos uno no soportado.
    tool = Tool(type="supercalifragilistico", path="/x")
    result = launcher.launch_tool(tool)
    assert result["ok"] is False
    assert "desconocido" in result["error"].lower()
    assert "supercalifragilistico" in result["error"]


# ---------- 2 y 3. vscode ----------


def test_vscode_without_which_returns_install_error(mac_env) -> None:
    tool = Tool(type="vscode", path="~/repos/x")
    with patch.object(launcher.shutil, "which", return_value=None):
        result = launcher.launch_tool(tool)
    assert result["ok"] is False
    assert "VSCode no está instalado" in result["error"]
    assert "code.visualstudio.com" in result["error"]


def test_vscode_uses_list_on_mac(mac_env) -> None:
    raw_path = "/tmp/repo"
    expected_path = str(Path(raw_path).expanduser())
    tool = Tool(type="vscode", path=raw_path)
    fake_popen = MagicMock()
    with patch.object(launcher.shutil, "which", return_value="/usr/local/bin/code"), \
         patch.object(launcher.subprocess, "Popen", fake_popen):
        result = launcher.launch_tool(tool)
    assert result["ok"] is True
    fake_popen.assert_called_once()
    args, kwargs = fake_popen.call_args
    assert args[0] == ["code", expected_path]
    assert isinstance(args[0], list)
    assert kwargs.get("shell") is False


def test_vscode_uses_shell_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launcher, "IS_MAC", False)
    monkeypatch.setattr(launcher, "IS_WINDOWS", True)
    monkeypatch.setattr(launcher.shutil, "which", lambda name: r"C:\fake\code.CMD")
    popen_mock = MagicMock()
    monkeypatch.setattr(launcher.subprocess, "Popen", popen_mock)
    result = launcher.launch_tool(Tool(type="vscode", path="C:/x"))
    assert result["ok"] is True
    args, kwargs = popen_mock.call_args
    assert kwargs.get("shell") is True
    assert isinstance(args[0], str)
    assert "code" in args[0]


# ---------- 4. browser sin URL ----------


def test_browser_without_url_returns_error(mac_env) -> None:
    tool = Tool(type="browser")
    result = launcher.launch_tool(tool)
    assert result["ok"] is False
    assert "url" in result["error"].lower()


# ---------- 5 y 6. browser por SO ----------


def test_browser_on_mac_uses_open(mac_env) -> None:
    tool = Tool(type="browser", url="https://example.com")
    fake_popen = MagicMock()
    with patch.object(launcher.subprocess, "Popen", fake_popen):
        result = launcher.launch_tool(tool)
    assert result["ok"] is True
    fake_popen.assert_called_once()
    args, _ = fake_popen.call_args
    assert args[0] == ["open", "https://example.com"]


def test_browser_on_windows_uses_cmd_start(windows_env) -> None:
    tool = Tool(type="browser", url="https://example.com")
    fake_popen = MagicMock()
    with patch.object(launcher.subprocess, "Popen", fake_popen):
        result = launcher.launch_tool(tool)
    assert result["ok"] is True
    fake_popen.assert_called_once()
    args, _ = fake_popen.call_args
    assert args[0] == ["cmd", "/c", "start", "", "https://example.com"]


# ---------- 7. file inexistente ----------


def test_file_with_nonexistent_path_returns_error(mac_env, tmp_path: Path) -> None:
    missing = tmp_path / "no-such-file.txt"
    tool = Tool(type="file", path=str(missing))
    result = launcher.launch_tool(tool)
    assert result["ok"] is False
    assert "no existe" in result["error"].lower()


# ---------- 8. notepad sin content ----------


def test_notepad_without_content_returns_error(mac_env) -> None:
    tool = Tool(type="notepad")
    result = launcher.launch_tool(tool)
    assert result["ok"] is False
    assert "content" in result["error"].lower()


# ---------- 9 y 10. terminal con caracteres peligrosos ----------


def test_terminal_rejects_semicolon_in_command(mac_env) -> None:
    tool = Tool(type="terminal", cwd="/tmp", command="ls ; rm -rf /")
    result = launcher.launch_tool(tool)
    assert result["ok"] is False
    assert "inseguro" in result["error"].lower()


def test_terminal_rejects_double_amp_in_command(mac_env) -> None:
    tool = Tool(type="terminal", cwd="/tmp", command="ls && whoami")
    result = launcher.launch_tool(tool)
    assert result["ok"] is False
    assert "inseguro" in result["error"].lower()


# ---------- 11 y 12. terminal exitoso por SO ----------


def test_terminal_clean_command_on_mac_uses_osascript(mac_env) -> None:
    raw_cwd = "/tmp/work"
    expected_cwd = str(Path(raw_cwd).expanduser())
    tool = Tool(type="terminal", cwd=raw_cwd, command="npm run dev")
    fake_popen = MagicMock()
    with patch.object(launcher.subprocess, "Popen", fake_popen):
        result = launcher.launch_tool(tool)
    assert result["ok"] is True
    fake_popen.assert_called_once()
    args, kwargs = fake_popen.call_args
    assert args[0][0] == "osascript"
    assert args[0][1] == "-e"
    assert f'cd "{expected_cwd}"' in args[0][2]
    assert "npm run dev" in args[0][2]
    assert kwargs.get("shell") is False


def test_terminal_clean_command_on_windows_uses_cmd_k(windows_env) -> None:
    tool = Tool(type="terminal", cwd="C:/work", command="npm run dev")
    fake_popen = MagicMock()
    with patch.object(launcher.subprocess, "Popen", fake_popen):
        result = launcher.launch_tool(tool)
    assert result["ok"] is True
    fake_popen.assert_called_once()
    args, kwargs = fake_popen.call_args
    assert args[0][0] == "start"
    assert args[0][1] == "cmd"
    assert args[0][2] == "/K"
    assert "cd /d" in args[0][3]
    assert "npm run dev" in args[0][3]
    assert kwargs.get("shell") is True


# ---------- 13. claude_code sin which ----------


def test_claude_code_without_which_returns_error(mac_env) -> None:
    tool = Tool(type="claude_code", path="~/repos/x")
    with patch.object(launcher.shutil, "which", return_value=None):
        result = launcher.launch_tool(tool)
    assert result["ok"] is False
    assert "Claude Code no está instalado" in result["error"]
    assert "npm install -g @anthropic-ai/claude-code" in result["error"]
