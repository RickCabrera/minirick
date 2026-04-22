"""Bridge Python <-> JavaScript para el dashboard pywebview.

Todos los métodos de DashboardAPI capturan errores y retornan dicts serializables
a JSON. Nunca levantan excepciones al WebView.
"""

from __future__ import annotations

from typing import Any

from minirick.dashboard import service


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

    # ---------- Actions (stubs hasta Fase 4/5) ----------

    def open_tool(self, tool_index: int) -> dict[str, Any]:
        """STUB de Fase 4 — Launcher real llega en Fase 4."""
        try:
            result = service.fetch_active_task()
            if result is None:
                return {"ok": False, "error": "No hay tarea activa"}
            tools = result.tools
            if tool_index < 0 or tool_index >= len(tools):
                return {"ok": False, "error": f"Índice fuera de rango: {tool_index}"}
            tool = tools[tool_index]
            return {
                "ok": False,
                "message": f"Launcher llega en Fase 4 (tool: {tool.type})",
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def open_config(self) -> dict[str, Any]:
        """STUB de Fase 5 — panel de configuración."""
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
