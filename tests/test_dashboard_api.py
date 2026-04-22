"""Tests de DashboardAPI — verifica que nunca propaga excepciones al frontend."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from minirick.dashboard import api as api_module
from minirick.dashboard.api import DashboardAPI
from minirick.models import Task, Tool


@pytest.fixture
def sample_task() -> Task:
    return Task(
        id="t-1",
        title="Tarea demo",
        summary="resumen",
        context_md="# contexto",
        tools=[
            Tool(type="vscode", path="~/repos/x"),
            Tool(type="browser", url="https://x.co"),
        ],
        status="in_progress",
        is_active=True,
    )


def test_get_active_task_returns_task_dict(sample_task: Task) -> None:
    with patch.object(api_module.service, "fetch_active_task", return_value=sample_task):
        result = DashboardAPI().get_active_task()
    assert result["ok"] is True
    assert result["task"]["title"] == "Tarea demo"
    assert len(result["task"]["tools"]) == 2


def test_get_active_task_returns_none_when_no_active() -> None:
    with patch.object(api_module.service, "fetch_active_task", return_value=None):
        result = DashboardAPI().get_active_task()
    assert result == {"ok": True, "task": None}


def test_get_active_task_captures_network_error() -> None:
    with patch.object(
        api_module.service, "fetch_active_task", side_effect=RuntimeError("network down")
    ):
        result = DashboardAPI().get_active_task()
    assert result["ok"] is False
    assert "network down" in result["error"]


def test_get_current_profile_returns_dict() -> None:
    fake_profile = {"id": "u1", "email": "a@b.co", "role": "owner"}
    with patch.object(
        api_module.service, "fetch_current_profile", return_value=fake_profile
    ):
        result = DashboardAPI().get_current_profile()
    assert result == {"ok": True, "profile": fake_profile}


def test_refresh_is_alias_of_get_active_task(sample_task: Task) -> None:
    with patch.object(api_module.service, "fetch_active_task", return_value=sample_task):
        result = DashboardAPI().refresh()
    assert result["ok"] is True
    assert result["task"]["title"] == "Tarea demo"


def test_open_tool_returns_stub_message(sample_task: Task) -> None:
    with patch.object(api_module.service, "fetch_active_task", return_value=sample_task):
        result = DashboardAPI().open_tool(0)
    assert result["ok"] is False
    assert "Fase 4" in result["message"]


def test_open_tool_out_of_range(sample_task: Task) -> None:
    with patch.object(api_module.service, "fetch_active_task", return_value=sample_task):
        result = DashboardAPI().open_tool(99)
    assert result["ok"] is False
    assert "rango" in result["error"].lower()


def test_open_tool_no_active_task() -> None:
    with patch.object(api_module.service, "fetch_active_task", return_value=None):
        result = DashboardAPI().open_tool(0)
    assert result["ok"] is False
    assert "activa" in result["error"].lower()


def test_open_config_is_stub() -> None:
    result = DashboardAPI().open_config()
    assert result["ok"] is False
    assert "Fase 5" in result["message"]


def test_minimize_no_window_is_safe() -> None:
    # Sin window attached, no debe crashear
    result = DashboardAPI().minimize_window()
    assert result["ok"] is True


def test_minimize_with_window_calls_it() -> None:
    api = DashboardAPI()
    fake_window = MagicMock()
    api.attach_window(fake_window)
    result = api.minimize_window()
    assert result["ok"] is True
    fake_window.minimize.assert_called_once()


def test_close_window_with_window_calls_destroy() -> None:
    api = DashboardAPI()
    fake_window = MagicMock()
    api.attach_window(fake_window)
    result = api.close_window()
    assert result["ok"] is True
    fake_window.destroy.assert_called_once()
