"""Operaciones administrativas: CRUD de tareas + gestión de asignaciones.

Asume que ``ensure_session()`` ya se llamó, así las policies RLS de Supabase
se aplican con el auth.uid correcto. No inyecta service_role en ningún lado.
"""

from __future__ import annotations

from typing import Any

from postgrest.exceptions import APIError

from minirick.db import get_client
from minirick.frontmatter import dump as fm_dump
from minirick.frontmatter import parse as fm_parse
from minirick.models import Profile, Task


class AdminError(Exception):
    """Error genérico de operaciones admin."""


class AdminPermissionError(AdminError):
    """El usuario actual no tiene permisos para esta operación admin."""


NEW_TASK_TEMPLATE = """---
title: Título de la tarea
status: todo
summary: Resumen corto para el dashboard
assignees: []  # lista de emails, vacía = visible para todos
tools:
  - type: vscode
    path: ~/repos/ejemplo
  - type: browser
    url: https://example.com
---

# Contexto

Escribe aquí el contexto en markdown.
Borra las líneas que no uses.
"""


# ---------- Helpers internos ----------


def _wrap_api_error(exc: APIError) -> AdminError:
    msg = getattr(exc, "message", None) or str(exc)
    return AdminError(f"Error de Supabase: {msg}")


def _current_user_id() -> str | None:
    """Retorna el uid del usuario autenticado en el cliente actual, o None."""
    client = get_client()
    try:
        response = client.auth.get_user()
    except Exception:  # noqa: BLE001 — puede fallar si no hay sesión
        return None
    user = getattr(response, "user", None)
    if user is None:
        return None
    return getattr(user, "id", None)


# ---------- API pública ----------


def require_admin() -> Profile:
    """Carga el perfil del usuario actual y valida rol admin|owner."""
    uid = _current_user_id()
    if uid is None:
        raise AdminPermissionError(
            "No se pudo identificar tu sesión. Inicia sesión con minirick login."
        )
    try:
        response = (
            get_client()
            .table("profiles")
            .select("id, email, name, role")
            .eq("id", uid)
            .limit(1)
            .execute()
        )
    except APIError as exc:
        raise _wrap_api_error(exc) from exc

    rows = response.data or []
    if not rows:
        raise AdminPermissionError("No encontré tu perfil en la tabla profiles.")

    profile = Profile.from_dict(rows[0])
    if profile.role not in ("admin", "owner"):
        raise AdminPermissionError(
            "Necesitas rol admin u owner para esta operación."
        )
    return profile


def fetch_task(task_id: str) -> Task:
    """Trae una tarea por id. Lanza AdminError si no existe o RLS la oculta."""
    try:
        response = (
            get_client()
            .table("tasks")
            .select("*")
            .eq("id", task_id)
            .limit(1)
            .execute()
        )
    except APIError as exc:
        raise _wrap_api_error(exc) from exc

    rows = response.data or []
    if not rows:
        raise AdminError(f"No se encontró la tarea con id '{task_id}'.")
    return Task.from_dict(rows[0])


def create_task(data: dict[str, Any]) -> Task:
    """INSERT en tasks. ``data`` debe incluir al menos 'title'."""
    if not data.get("title"):
        raise AdminError("La tarea requiere un título.")
    try:
        response = get_client().table("tasks").insert(data).execute()
    except APIError as exc:
        raise _wrap_api_error(exc) from exc

    rows = response.data or []
    if not rows:
        raise AdminError("Supabase no devolvió la tarea recién creada.")
    return Task.from_dict(rows[0])


def update_task(task_id: str, data: dict[str, Any]) -> Task:
    """UPDATE por id."""
    try:
        response = (
            get_client()
            .table("tasks")
            .update(data)
            .eq("id", task_id)
            .execute()
        )
    except APIError as exc:
        raise _wrap_api_error(exc) from exc

    rows = response.data or []
    if not rows:
        raise AdminError(f"No se encontró la tarea con id '{task_id}'.")
    return Task.from_dict(rows[0])


def set_active_task(task_id: str) -> Task:
    """Marca una tarea como activa (el trigger desactiva las demás)."""
    return update_task(task_id, {"is_active": True})


def resolve_assignees(emails: list[str]) -> list[str]:
    """Convierte emails → lista de profile.id (uuid). Lanza AdminError si faltan."""
    cleaned: list[str] = []
    for raw in emails:
        if not raw:
            continue
        email = raw.strip().lower()
        if email:
            cleaned.append(email)
    if not cleaned:
        return []

    try:
        response = (
            get_client()
            .table("profiles")
            .select("id, email")
            .in_("email", cleaned)
            .execute()
        )
    except APIError as exc:
        raise _wrap_api_error(exc) from exc

    rows = response.data or []
    by_email: dict[str, str] = {
        str(row["email"]).lower(): row["id"] for row in rows if row.get("email")
    }
    missing = [email for email in cleaned if email not in by_email]
    if missing:
        raise AdminError(
            "Emails no registrados: "
            + ", ".join(missing)
            + ". Pídeles que hagan login primero."
        )
    # Mantener el orden que pidió el caller, eliminando duplicados.
    seen: set[str] = set()
    result: list[str] = []
    for email in cleaned:
        uid = by_email[email]
        if uid not in seen:
            seen.add(uid)
            result.append(uid)
    return result


def list_profiles() -> list[Profile]:
    """Lista todos los perfiles accesibles al caller (RLS decide)."""
    try:
        response = (
            get_client()
            .table("profiles")
            .select("id, email, name, role")
            .order("email")
            .execute()
        )
    except APIError as exc:
        raise _wrap_api_error(exc) from exc
    return [Profile.from_dict(row) for row in (response.data or [])]


def list_all_tasks() -> list[Task]:
    """Lista todas las tareas accesibles al caller (RLS filtra por assignees)."""
    try:
        response = (
            get_client()
            .table("tasks")
            .select("*")
            .order("updated_at", desc=True)
            .execute()
        )
    except APIError as exc:
        raise _wrap_api_error(exc) from exc
    return [Task.from_dict(row) for row in (response.data or [])]


# ---------- Markdown <-> Task ----------


def task_to_markdown(task: Task, profiles_by_id: dict[str, Profile]) -> str:
    """Serializa una tarea a markdown con frontmatter YAML, convirtiendo uuids a emails."""
    assignee_emails: list[str] = []
    for uid in task.assignees:
        profile = profiles_by_id.get(uid)
        if profile and profile.email:
            assignee_emails.append(profile.email)
        else:
            # Fallback: mantener el uuid para no perderlo silenciosamente.
            assignee_emails.append(uid)

    metadata: dict[str, Any] = {
        "title": task.title,
        "status": task.status,
        "summary": task.summary,
        "assignees": assignee_emails,
        "tools": [tool.to_dict() for tool in task.tools],
    }
    body = task.context_md if task.context_md else "# Contexto\n\n"
    return fm_dump(metadata, body)


def markdown_to_task_fields(md: str) -> dict[str, Any]:
    """Parsea markdown con frontmatter a dict listo para insert/update.

    Devuelve solo las claves que el usuario definió en el frontmatter, más
    ``context_md`` con el body. Emails de ``assignees`` se devuelven bajo
    la llave especial ``_assignee_emails``; el caller decide si resolverlos.
    """
    metadata, body = fm_parse(md)
    fields: dict[str, Any] = {}

    if "title" in metadata:
        title = metadata["title"]
        fields["title"] = "" if title is None else str(title).strip()
    if "status" in metadata:
        status = metadata["status"]
        fields["status"] = str(status) if status is not None else "todo"
    if "summary" in metadata:
        summary = metadata["summary"]
        fields["summary"] = "" if summary is None else str(summary)
    if "tools" in metadata:
        tools = metadata["tools"] or []
        if not isinstance(tools, list):
            raise AdminError("El campo 'tools' del frontmatter debe ser una lista.")
        fields["tools"] = tools
    if "assignees" in metadata:
        assignees = metadata["assignees"] or []
        if not isinstance(assignees, list):
            raise AdminError(
                "El campo 'assignees' del frontmatter debe ser una lista de emails."
            )
        fields["_assignee_emails"] = [str(e) for e in assignees]

    stripped_body = body.strip()
    fields["context_md"] = (stripped_body + "\n") if stripped_body else ""
    return fields
