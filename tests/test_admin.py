"""Tests de `minirick.admin` — CRUD de tareas + resolución de assignees."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from minirick.admin import (
    AdminError,
    AdminPermissionError,
    create_task,
    markdown_to_task_fields,
    require_admin,
    resolve_assignees,
    set_active_task,
    task_to_markdown,
    update_task,
)
from minirick.models import Profile, Task, Tool


def _insert_client(response_rows: list[dict[str, Any]]) -> tuple[MagicMock, dict[str, Any]]:
    """Mock de client.table('tasks').insert(payload).execute() con captura."""
    captured: dict[str, Any] = {}
    client = MagicMock()
    table = client.table.return_value

    def insert_spy(payload):
        captured["payload"] = payload
        result = MagicMock()
        result.execute.return_value = MagicMock(data=response_rows)
        return result

    table.insert.side_effect = insert_spy
    return client, captured


def _update_client(response_rows: list[dict[str, Any]]) -> tuple[MagicMock, dict[str, Any]]:
    """Mock encadenado para .update(payload).eq('id', tid).execute()."""
    captured: dict[str, Any] = {}
    client = MagicMock()
    table = client.table.return_value

    def update_spy(payload):
        captured["payload"] = payload
        eq_proxy = MagicMock()

        def eq_spy(col, val):
            captured["col"] = col
            captured["id"] = val
            exec_proxy = MagicMock()
            exec_proxy.execute.return_value = MagicMock(data=response_rows)
            return exec_proxy

        eq_proxy.eq.side_effect = eq_spy
        return eq_proxy

    table.update.side_effect = update_spy
    return client, captured


def test_create_task_sends_payload_to_tasks_table() -> None:
    client, captured = _insert_client([{"id": "t1", "title": "Hola"}])
    with patch("minirick.admin.get_client", return_value=client):
        task = create_task({"title": "Hola", "status": "todo"})
    assert task.id == "t1"
    assert captured["payload"] == {"title": "Hola", "status": "todo"}
    client.table.assert_called_with("tasks")


def test_create_task_without_title_raises() -> None:
    with patch("minirick.admin.get_client", return_value=MagicMock()):
        with pytest.raises(AdminError):
            create_task({"status": "todo"})


def test_update_task_uses_eq_id() -> None:
    client, captured = _update_client([{"id": "t1", "title": "Nuevo"}])
    with patch("minirick.admin.get_client", return_value=client):
        task = update_task("t1", {"title": "Nuevo"})
    assert task.title == "Nuevo"
    assert captured["col"] == "id"
    assert captured["id"] == "t1"
    assert captured["payload"] == {"title": "Nuevo"}


def test_set_active_task_sends_is_active_true() -> None:
    client, captured = _update_client(
        [{"id": "t1", "title": "x", "is_active": True}]
    )
    with patch("minirick.admin.get_client", return_value=client):
        set_active_task("t1")
    assert captured["payload"] == {"is_active": True}


def test_resolve_assignees_returns_uuids_in_input_order() -> None:
    client = MagicMock()
    chain = client.table.return_value.select.return_value.in_.return_value
    chain.execute.return_value = MagicMock(
        data=[
            {"id": "u1", "email": "a@b.co"},
            {"id": "u2", "email": "c@d.co"},
        ]
    )
    with patch("minirick.admin.get_client", return_value=client):
        ids = resolve_assignees(["c@d.co", "a@b.co"])
    assert ids == ["u2", "u1"]


def test_resolve_assignees_missing_email_raises_listing_it() -> None:
    client = MagicMock()
    chain = client.table.return_value.select.return_value.in_.return_value
    chain.execute.return_value = MagicMock(data=[{"id": "u1", "email": "a@b.co"}])
    with patch("minirick.admin.get_client", return_value=client):
        with pytest.raises(AdminError) as exc:
            resolve_assignees(["a@b.co", "ghost@nope.co"])
    assert "ghost@nope.co" in str(exc.value)


def test_require_admin_rejects_collaborator() -> None:
    client = MagicMock()
    client.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
    chain = client.table.return_value.select.return_value.eq.return_value.limit.return_value
    chain.execute.return_value = MagicMock(
        data=[{"id": "u1", "email": "x@y.co", "role": "collaborator"}]
    )
    with patch("minirick.admin.get_client", return_value=client):
        with pytest.raises(AdminPermissionError):
            require_admin()


def test_require_admin_accepts_owner() -> None:
    client = MagicMock()
    client.auth.get_user.return_value = MagicMock(user=MagicMock(id="u1"))
    chain = client.table.return_value.select.return_value.eq.return_value.limit.return_value
    chain.execute.return_value = MagicMock(
        data=[{"id": "u1", "email": "rick@x.co", "role": "owner"}]
    )
    with patch("minirick.admin.get_client", return_value=client):
        profile = require_admin()
    assert profile.role == "owner"


def test_task_markdown_roundtrip_preserves_core_fields() -> None:
    task = Task(
        id="t1",
        title="Arreglar login",
        status="in_progress",
        summary="bug crítico",
        context_md="# Notas\n\npaso 1\n",
        tools=[Tool(type="vscode", path="~/app")],
        assignees=["u1"],
    )
    profiles = {"u1": Profile(id="u1", email="a@b.co", role="collaborator")}
    md = task_to_markdown(task, profiles)
    fields = markdown_to_task_fields(md)

    assert fields["title"] == "Arreglar login"
    assert fields["status"] == "in_progress"
    assert fields["summary"] == "bug crítico"
    assert fields["tools"] == [{"type": "vscode", "path": "~/app"}]
    assert fields["_assignee_emails"] == ["a@b.co"]
    assert "paso 1" in fields["context_md"]
