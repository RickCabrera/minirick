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


def launch_dashboard() -> None:
    """Crea y lanza la ventana del dashboard. Bloquea hasta que se cierre."""
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
