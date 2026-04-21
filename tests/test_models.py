"""Tests de `minirick.models` — serialización Task / Tool / Profile."""

from __future__ import annotations

from minirick.models import Profile, Task, Tool


def test_profile_roundtrip() -> None:
    raw = {
        "id": "uid-1",
        "email": "a@b.co",
        "name": "Rick",
        "role": "owner",
        "created_at": "2026-04-20T00:00:00Z",
        "updated_at": "2026-04-21T00:00:00Z",
    }
    profile = Profile.from_dict(raw)
    assert profile.email == "a@b.co"
    assert profile.role == "owner"
    assert profile.to_dict() == raw


def test_profile_defaults_to_collaborator() -> None:
    profile = Profile.from_dict({"id": "uid", "email": "x@y.co"})
    assert profile.role == "collaborator"


def test_tool_omits_none_fields_in_to_dict() -> None:
    tool = Tool(type="browser", url="https://example.com")
    assert tool.to_dict() == {"type": "browser", "url": "https://example.com"}


def test_tool_from_dict_covers_all_types() -> None:
    payloads = [
        {"type": "claude_code", "path": "~/repos/x"},
        {"type": "vscode", "path": "~/repos/x"},
        {"type": "browser", "url": "https://gh.com/pr/1"},
        {"type": "file", "path": "~/notas.md"},
        {"type": "notepad", "content": "hola"},
        {"type": "terminal", "cwd": "~/repos/x", "command": "npm run dev"},
    ]
    for payload in payloads:
        tool = Tool.from_dict(payload)
        assert tool.type == payload["type"]
        assert tool.to_dict() == payload


def test_task_from_dict_parses_tools() -> None:
    raw = {
        "id": "t1",
        "title": "Arreglar login",
        "summary": "Bug",
        "context_md": "# contexto",
        "tools": [
            {"type": "vscode", "path": "~/repos/app"},
            {"type": "browser", "url": "https://x.co"},
        ],
        "status": "in_progress",
        "is_active": True,
    }
    task = Task.from_dict(raw)
    assert task.title == "Arreglar login"
    assert task.is_active is True
    assert len(task.tools) == 2
    assert task.tools[0].type == "vscode"
    assert task.tools[1].url == "https://x.co"


def test_task_from_dict_tolerates_null_tools() -> None:
    raw = {"id": "t1", "title": "vacia", "tools": None}
    task = Task.from_dict(raw)
    assert task.tools == []


def test_task_to_dict_serializes_tools() -> None:
    task = Task(
        id="t1",
        title="Test",
        tools=[Tool(type="browser", url="https://x.co")],
    )
    out = task.to_dict()
    assert out["tools"] == [{"type": "browser", "url": "https://x.co"}]
