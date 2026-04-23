"""Tests de `minirick.editor` — resolución de editor y cleanup de temp files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from minirick import editor as editor_module
from minirick.editor import EditorError, open_in_editor


class _FakeCompleted:
    returncode = 0


def _make_run_spy(captured: dict[str, Any], content_to_write: str = "edited content"):
    def fake_run(cmd, check=True):  # noqa: ARG001
        captured["cmd"] = list(cmd)
        captured["path"] = Path(cmd[-1])
        captured["path"].write_text(content_to_write, encoding="utf-8")
        return _FakeCompleted()

    return fake_run


def test_env_editor_overrides_platform_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EDITOR", "myeditor --wait")
    monkeypatch.setattr(editor_module.shutil, "which", lambda name: "/usr/bin/" + name)
    captured: dict[str, Any] = {}
    monkeypatch.setattr(editor_module.subprocess, "run", _make_run_spy(captured))

    result = open_in_editor("initial text")

    assert result == "edited content"
    assert captured["cmd"][0] == "myeditor"
    assert captured["cmd"][1] == "--wait"


def test_windows_fallback_uses_notepad(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setattr("sys.platform", "win32")
    captured: dict[str, Any] = {}
    monkeypatch.setattr(editor_module.subprocess, "run", _make_run_spy(captured, "hi"))

    result = open_in_editor("x")

    assert result == "hi"
    assert captured["cmd"][0] == "notepad"


def test_macos_fallback_uses_open_dash_t_dash_w(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setattr("sys.platform", "darwin")
    captured: dict[str, Any] = {}
    monkeypatch.setattr(editor_module.subprocess, "run", _make_run_spy(captured, "m"))

    open_in_editor("x")

    assert captured["cmd"][:3] == ["open", "-t", "-W"]


def test_temp_file_is_cleaned_up(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setattr("sys.platform", "win32")
    captured: dict[str, Any] = {}
    monkeypatch.setattr(editor_module.subprocess, "run", _make_run_spy(captured, "y"))

    open_in_editor("seed")

    assert "path" in captured
    assert not captured["path"].exists(), "temp file debió borrarse en finally"


def test_editor_not_found_wraps_in_editor_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EDITOR", "inexistente-xyz")
    monkeypatch.setattr(editor_module.shutil, "which", lambda name: "/usr/bin/" + name)

    def boom(cmd, check=True):  # noqa: ARG001
        raise FileNotFoundError("no such file")

    monkeypatch.setattr(editor_module.subprocess, "run", boom)
    with pytest.raises(EditorError):
        open_in_editor("x")
