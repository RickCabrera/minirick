"""Bridge Python <-> JavaScript para el dashboard pywebview.

Todos los métodos de DashboardAPI capturan errores y retornan dicts serializables
a JSON. Nunca levantan excepciones al WebView.
"""

from __future__ import annotations

from typing import Any

from minirick import admin
from minirick.dashboard import service
from minirick.launcher import launch_tool


class DashboardAPI:
    """API expuesta al frontend vía pywebview.js_api."""

    def __init__(self) -> None:
        self._window: Any = None  # lo setea window.py después de crear la ventana

    def attach_window(self, window: Any) -> None:
        """Guarda referencia a la ventana pywebview para minimizar/cerrar."""
        self._window = window

    # ---------- Data ----------

    def get_active_task(self) -> dict[str, Any]:
        """Retorna {'ok': True, 'task': dict|None} o {'ok': False, 'error': str}."""
        try:
            task = service.fetch_active_task()
            return {"ok": True, "task": task.to_dict() if task else None}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_current_profile(self) -> dict[str, Any]:
        """Retorna {'ok': True, 'profile': dict|None} o {'ok': False, 'error': str}."""
        try:
            profile = service.fetch_current_profile()
            return {"ok": True, "profile": profile}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def refresh(self) -> dict[str, Any]:
        """Alias de get_active_task para el botón de refresh (si se añade)."""
        return self.get_active_task()

    # ---------- Admin panel ----------

    def list_profiles(self) -> dict[str, Any]:
        """Retorna {'ok': True, 'data': [{id, email, name, role}]} o error."""
        try:
            profiles = admin.list_profiles()
            return {
                "ok": True,
                "error": None,
                "data": [
                    {
                        "id": p.id,
                        "email": p.email,
                        "name": p.name,
                        "role": p.role,
                    }
                    for p in profiles
                ],
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc), "data": []}

    def list_all_tasks(self) -> dict[str, Any]:
        """Retorna todas las tareas visibles al caller (RLS decide)."""
        try:
            tasks = admin.list_all_tasks()
            return {
                "ok": True,
                "error": None,
                "data": [t.to_dict() for t in tasks],
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc), "data": []}

    def set_task_active(
        self, task_id: str, assignee_emails: list[str] | None = None
    ) -> dict[str, Any]:
        """Activa una tarea y opcionalmente reemplaza sus assignees.

        - ``assignee_emails is None`` → solo activa, no toca assignees.
        - ``assignee_emails == []``   → activa + marca como pública.
        - lista con emails           → activa + resuelve emails a uuids.
        """
        try:
            data: dict[str, Any] = {"is_active": True}
            if assignee_emails is not None:
                if not assignee_emails:
                    data["assignees"] = []
                else:
                    data["assignees"] = admin.resolve_assignees(list(assignee_emails))
            task = admin.update_task(task_id, data)
            return {"ok": True, "error": None, "data": task.to_dict()}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc), "data": None}

    def update_task_assignees(
        self, task_id: str, assignee_emails: list[str]
    ) -> dict[str, Any]:
        """Actualiza solo la lista de assignees sin cambiar is_active."""
        try:
            emails = list(assignee_emails or [])
            resolved = admin.resolve_assignees(emails) if emails else []
            task = admin.update_task(task_id, {"assignees": resolved})
            return {"ok": True, "error": None, "data": task.to_dict()}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc), "data": None}

    # ---------- Actions ----------

    def open_tool(self, tool_index: int) -> dict[str, Any]:
        """Lanza la tool en el índice dado de la tarea activa."""
        try:
            task = service.fetch_active_task()
            if task is None:
                return {"ok": False, "error": "No hay tarea activa"}
            tools = task.tools
            if tool_index < 0 or tool_index >= len(tools):
                return {"ok": False, "error": f"Índice fuera de rango: {tool_index}"}
            tool = tools[tool_index]
            return launch_tool(tool)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def open_config(self) -> dict[str, Any]:
        """STUB histórico — el panel admin lo maneja el JS directamente ahora."""
        return {"ok": False, "message": "Configuración llega en Fase 5"}

    # ---------- Window control ----------

    def minimize_window(self) -> dict[str, Any]:
        try:
            if self._window is not None:
                self._window.minimize()
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def close_window(self) -> dict[str, Any]:
        try:
            if self._window is not None:
                self._window.destroy()
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
