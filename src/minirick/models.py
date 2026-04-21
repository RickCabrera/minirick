"""Modelos de datos del dominio minirick.

Mapeo 1:1 con las tablas `profiles` y `tasks` de Supabase, más `Tool` para los
objetos dentro del jsonb `tasks.tools`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

TaskStatus = str  # 'todo' | 'in_progress' | 'done'
UserRole = str  # 'owner' | 'admin' | 'collaborator'


@dataclass
class Profile:
    """Perfil de usuario (tabla `profiles`)."""

    id: str
    email: str
    name: str | None = None
    role: UserRole = "collaborator"
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Profile:
        return cls(
            id=data["id"],
            email=data.get("email", ""),
            name=data.get("name"),
            role=data.get("role", "collaborator"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class Tool:
    """Herramienta asociada a una tarea (elemento del array `tasks.tools`).

    `type` define qué abre el launcher; el resto de campos dependen del tipo.
    """

    type: str
    path: str | None = None
    url: str | None = None
    content: str | None = None
    cwd: str | None = None
    command: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Tool:
        return cls(
            type=data["type"],
            path=data.get("path"),
            url=data.get("url"),
            content=data.get("content"),
            cwd=data.get("cwd"),
            command=data.get("command"),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"type": self.type}
        for key in ("path", "url", "content", "cwd", "command"):
            value = getattr(self, key)
            if value is not None:
                out[key] = value
        return out


@dataclass
class Task:
    """Tarea del equipo (tabla `tasks`)."""

    id: str
    title: str
    summary: str = ""
    context_md: str = ""
    tools: list[Tool] = field(default_factory=list)
    status: TaskStatus = "todo"
    is_active: bool = False
    created_by: str | None = None
    updated_by: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        raw_tools = data.get("tools") or []
        tools = [Tool.from_dict(t) for t in raw_tools]
        return cls(
            id=data["id"],
            title=data.get("title", ""),
            summary=data.get("summary", "") or "",
            context_md=data.get("context_md", "") or "",
            tools=tools,
            status=data.get("status", "todo"),
            is_active=bool(data.get("is_active", False)),
            created_by=data.get("created_by"),
            updated_by=data.get("updated_by"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "context_md": self.context_md,
            "tools": [t.to_dict() for t in self.tools],
            "status": self.status,
            "is_active": self.is_active,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
