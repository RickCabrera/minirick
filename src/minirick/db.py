"""Cliente Supabase singleton.

Las credenciales anon por defecto son seguras de embeder (protegidas por RLS).
Se pueden override con variables de entorno `SUPABASE_URL` y `SUPABASE_KEY`, o
vía un archivo `.env` en el cwd.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client

DEFAULT_SUPABASE_URL = "https://ijpwjxujbckmvvdxbmjw.supabase.co"
DEFAULT_SUPABASE_KEY = "sb_publishable_Pmj2sW2dmcvln4-sBixDYA_cGjaGHIl"

_client: Client | None = None
_dotenv_loaded = False


def _ensure_dotenv_loaded() -> None:
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    _dotenv_loaded = True


def get_supabase_url() -> str:
    """Retorna la URL de Supabase (env o default)."""
    _ensure_dotenv_loaded()
    return os.environ.get("SUPABASE_URL", DEFAULT_SUPABASE_URL)


def get_supabase_key() -> str:
    """Retorna la anon/publishable key (env o default)."""
    _ensure_dotenv_loaded()
    return os.environ.get("SUPABASE_KEY", DEFAULT_SUPABASE_KEY)


def get_client() -> Client:
    """Retorna el cliente Supabase singleton, creándolo en la primera llamada."""
    global _client
    if _client is None:
        _client = create_client(get_supabase_url(), get_supabase_key())
    return _client


def reset_client() -> None:
    """Resetea el singleton — útil para tests y para forzar reconexión tras logout."""
    global _client, _dotenv_loaded
    _client = None
    _dotenv_loaded = False
