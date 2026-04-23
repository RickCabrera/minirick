"""Tests de los comandos CLI admin (new / edit / set-active) con mocks."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from minirick.cli import app
from minirick.models import Task

runner = CliRunner()


def _fake_task(**kwargs) -> Task:
    base = {
        "id": "t-1",
        "title": "Placeholder",
        "summary": "",
        "context_md": "",
        "tools": [],
        "status": "todo",
        "is_active": False,
        "assignees": [],
    }
    base.update(kwargs)
    return Task.from_dict(base)


def _seed_session(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    session_path = tmp_path / "session.json"
    session_path.write_text(
        json.dumps({"access_token": "a", "refresh_token": "b"}),
        encoding="utf-8",
    )
    monkeypatch.setattr("minirick.auth.get_session_file", lambda: session_path)
    monkeypatch.setattr("minirick.auth.get_client", lambda: MagicMock())


def test_new_without_session_exits(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(
        "minirick.auth.get_session_file", lambda: tmp_path / "none.json"
    )
    result = runner.invoke(app, ["new"])
    assert result.exit_code != 0
    output = result.stdout.lower() + result.output.lower()
    assert "login" in output or "sesión" in output


def test_new_creates_task_from_editor_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _seed_session(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "minirick.admin.require_admin", lambda: MagicMock(role="admin")
    )
    fake_md = (
        "---\n"
        "title: Tarea nueva\n"
        "status: todo\n"
        "summary: algo\n"
        "assignees: []\n"
        "tools: []\n"
        "---\n\n"
        "# Contexto\n\ncontenido real\n"
    )
    monkeypatch.setattr(
        "minirick.cli.editor.open_in_editor",
        lambda content, suffix=".md": fake_md,
    )
    captured: dict[str, object] = {}

    def fake_create(data):
        captured["data"] = data
        return _fake_task(id="t-new", title=data["title"])

    monkeypatch.setattr("minirick.cli.admin.create_task", fake_create)

    result = runner.invoke(app, ["new"])
    assert result.exit_code == 0, result.output
    assert captured["data"]["title"] == "Tarea nueva"
    assert captured["data"]["status"] == "todo"


def test_edit_downloads_opens_and_updates(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _seed_session(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "minirick.admin.require_admin", lambda: MagicMock(role="admin")
    )

    existing = _fake_task(id="t1", title="Antes", status="todo")
    monkeypatch.setattr("minirick.cli.admin.fetch_task", lambda tid: existing)
    monkeypatch.setattr("minirick.cli.admin.list_profiles", lambda: [])

    edited_md = "---\ntitle: Después\nstatus: done\n---\n\n# nuevo body"
    monkeypatch.setattr(
        "minirick.cli.editor.open_in_editor",
        lambda content, suffix=".md": edited_md,
    )

    captured: dict[str, object] = {}

    def fake_update(tid, data):
        captured["tid"] = tid
        captured["data"] = data
        return _fake_task(id=tid, title=data.get("title", ""))

    monkeypatch.setattr("minirick.cli.admin.update_task", fake_update)

    result = runner.invoke(app, ["edit", "t1"])
    assert result.exit_code == 0, result.output
    assert captured["tid"] == "t1"
    assert captured["data"]["title"] == "Después"
    assert captured["data"]["status"] == "done"


def test_set_active_with_assignees_resolves_emails(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _seed_session(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "minirick.admin.require_admin", lambda: MagicMock(role="admin")
    )
    monkeypatch.setattr(
        "minirick.cli.admin.resolve_assignees",
        lambda emails: [f"uid-{e}" for e in emails],
    )

    captured: dict[str, object] = {}

    def fake_update(tid, data):
        captured["tid"] = tid
        captured["data"] = data
        return _fake_task(id=tid, title="x", is_active=True)

    monkeypatch.setattr("minirick.cli.admin.update_task", fake_update)

    result = runner.invoke(
        app,
        ["set-active", "t-xyz", "--assignees", "a@b.co,c@d.co"],
    )
    assert result.exit_code == 0, result.output
    assert captured["tid"] == "t-xyz"
    assert captured["data"]["is_active"] is True
    assert captured["data"]["assignees"] == ["uid-a@b.co", "uid-c@d.co"]


def test_set_active_empty_assignees_marks_public(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _seed_session(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "minirick.admin.require_admin", lambda: MagicMock(role="admin")
    )

    captured: dict[str, object] = {}

    def fake_update(tid, data):
        captured["tid"] = tid
        captured["data"] = data
        return _fake_task(id=tid, title="x", is_active=True)

    monkeypatch.setattr("minirick.cli.admin.update_task", fake_update)

    result = runner.invoke(app, ["set-active", "t-xyz", "--assignees", ""])
    assert result.exit_code == 0, result.output
    assert captured["data"]["is_active"] is True
    assert captured["data"]["assignees"] == []


def test_set_active_without_flag_does_not_touch_assignees(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _seed_session(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "minirick.admin.require_admin", lambda: MagicMock(role="admin")
    )

    captured: dict[str, object] = {}

    def fake_update(tid, data):
        captured["data"] = data
        return _fake_task(id=tid, title="x", is_active=True)

    monkeypatch.setattr("minirick.cli.admin.update_task", fake_update)

    result = runner.invoke(app, ["set-active", "t-xyz"])
    assert result.exit_code == 0, result.output
    assert captured["data"] == {"is_active": True}
    assert "assignees" not in captured["data"]
