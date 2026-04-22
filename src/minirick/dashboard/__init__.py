"""Dashboard flotante de minirick (GUI pywebview)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


def __getattr__(name: str) -> Callable:
    """Lazy import — solo carga pywebview cuando realmente se pide launch_dashboard."""
    if name == "launch_dashboard":
        from minirick.dashboard.window import launch_dashboard

        return launch_dashboard
    raise AttributeError(f"module 'minirick.dashboard' has no attribute {name!r}")


__all__ = ["launch_dashboard"]
