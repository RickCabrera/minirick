"""Capa de datos del dashboard — consultas a Supabase."""

from __future__ import annotations

from typing import Any

from minirick.db import get_client
from minirick.models import Task


def fetch_active_task() -> Task | None:
    """Retorna la tarea con is_active=true, o None si no hay ninguna."""
    client = get_client()
    response = (
        client.table("tasks")
        .select("*")
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    rows: list[dict[str, Any]] = response.data or []
    if not rows:
        return None
    return Task.from_dict(rows[0])


def fetch_current_profile() -> dict[str, Any] | None:
    """Retorna el profile del usuario logueado (email, name, role) o None.

    Requiere que ensure_session() se haya llamado antes (set_session en el cliente).
    """
    client = get_client()
    user_response = client.auth.get_user()
    user = getattr(user_response, "user", None)
    if user is None:
        return None
    user_id = getattr(user, "id", None)
    if not user_id:
        return None

    profile_response = (
        client.table("profiles")
        .select("id, email, name, role")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    rows = profile_response.data or []
    if not rows:
        return None
    return rows[0]
