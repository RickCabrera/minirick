"""Gestión de configuración local de minirick.

Guardamos config y credenciales en el directorio de datos del usuario,
siguiendo convenciones de cada SO:
  - macOS:   ~/Library/Application Support/minirick/
  - Windows: C:\\Users\\<user>\\AppData\\Local\\minirick\\
"""

from __future__ import annotations

import json
from pathlib import Path

from platformdirs import user_data_dir

APP_NAME = "minirick"


def get_config_dir() -> Path:
    """Retorna el directorio de configuración del usuario, creándolo si no existe."""
    path = Path(user_data_dir(APP_NAME, appauthor=False))
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_file() -> Path:
    """Path al archivo de configuración principal."""
    return get_config_dir() / "config.toml"


def get_session_file() -> Path:
    """Path al archivo de sesión (tokens)."""
    return get_config_dir() / "session.json"


def get_cache_dir() -> Path:
    """Directorio para cache local de tareas."""
    path = get_config_dir() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_state_file() -> Path:
    """Path al archivo de estado local (cache de última tarea auto-lanzada, etc.)."""
    return get_config_dir() / "state.json"


def load_state() -> dict:
    """Lee el estado local. Retorna dict vacío si no existe o está corrupto."""
    path = get_state_file()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    """Persiste el estado local."""
    get_state_file().write_text(
        json.dumps(state, indent=2), encoding="utf-8"
    )
