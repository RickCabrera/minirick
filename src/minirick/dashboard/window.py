"""Ventana flotante del dashboard minirick (pywebview)."""

from __future__ import annotations

from pathlib import Path

import webview

from minirick.dashboard.api import DashboardAPI

WINDOW_WIDTH = 900
WINDOW_HEIGHT = 560
WINDOW_TITLE = "minirick"


def _get_ui_path() -> str:
    """Retorna la ruta absoluta a ui/index.html."""
    ui_dir = Path(__file__).parent / "ui"
    return str(ui_dir / "index.html")


def _position_top_right(window: webview.Window) -> None:
    """Reposiciona la ventana en la esquina superior derecha de la pantalla primaria."""
    try:
        screens = webview.screens
        if not screens:
            return
        screen = screens[0]
        x = max(0, screen.width - WINDOW_WIDTH - 20)
        y = 20
        window.move(x, y)
    except Exception:  # noqa: BLE001 — no crítico si falla
        pass


def _maybe_auto_launch() -> list[dict]:
    """Si la tarea activa cambió desde la última vez, auto-lanza sus tools.

    Retorna lista de resultados de cada lanzamiento (para logging).
    Nunca levanta: si algo falla, retorna lista vacía y el dashboard abre igual.
    """
    from rich.console import Console

    from minirick.config import load_state, save_state
    from minirick.dashboard import service
    from minirick.launcher import launch_tool

    console = Console()

    try:
        task = service.fetch_active_task()
    except Exception:  # noqa: BLE001
        return []

    if task is None or not task.tools:
        return []

    try:
        state = load_state()
    except Exception:  # noqa: BLE001
        state = {}

    last_id = state.get("last_auto_launched_task_id")
    if last_id == task.id:
        return []

    results: list[dict] = []
    for tool in task.tools:
        try:
            result = launch_tool(tool)
        except Exception as exc:  # noqa: BLE001
            result = {"ok": False, "error": f"Error inesperado: {exc}"}
        results.append({"tool": tool.type, **result})

    if results:
        console.print(f"[dim]> auto-launch: {len(results)} tools[/dim]")
        for r in results:
            icon = "✓" if r.get("ok") else "✖"
            color = "green" if r.get("ok") else "red"
            msg = r.get("message") or r.get("error") or ""
            console.print(f"  [{color}]{icon}[/{color}] {r['tool']}: {msg}")

    try:
        state["last_auto_launched_task_id"] = task.id
        save_state(state)
    except Exception:  # noqa: BLE001
        pass

    return results


def launch_dashboard() -> None:
    """Crea y lanza la ventana del dashboard. Bloquea hasta que se cierre."""
    try:
        _maybe_auto_launch()
    except Exception:  # noqa: BLE001 — auto-launch nunca bloquea la apertura del dashboard
        pass

    api = DashboardAPI()

    window = webview.create_window(
        title=WINDOW_TITLE,
        url=_get_ui_path(),
        js_api=api,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        frameless=True,
        easy_drag=False,
        on_top=True,
        resizable=False,
        background_color="#0a0e0a",
    )

    api.attach_window(window)

    webview.start(func=_position_top_right, args=(window,))
