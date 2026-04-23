"""Parser simple de frontmatter YAML sobre markdown.

Divide documentos del estilo::

    ---
    title: Algo
    status: todo
    ---

    # Cuerpo en markdown

en (metadata, body) y serializa de vuelta manteniendo un formato consistente.
"""

from __future__ import annotations

from typing import Any

import yaml


class FrontmatterError(Exception):
    """Error al parsear o serializar frontmatter YAML."""


def parse(text: str) -> tuple[dict[str, Any], str]:
    """Divide '---\\nYAML\\n---\\nMARKDOWN' en (metadata, body).

    Si no hay frontmatter válido, retorna ({}, text) sin tocarlo.
    Si el YAML es inválido, lanza FrontmatterError con mensaje claro.
    """
    if not text.startswith("---"):
        return ({}, text)

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ({}, text)

    end_idx: int | None = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return ({}, text)

    yaml_text = "\n".join(lines[1:end_idx])
    body_lines = lines[end_idx + 1 :]
    # Quitar una línea en blanco separadora si existe.
    if body_lines and body_lines[0] == "":
        body_lines = body_lines[1:]
    body = "\n".join(body_lines)

    try:
        metadata = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise FrontmatterError(f"YAML inválido en el frontmatter: {exc}") from exc

    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise FrontmatterError(
            "El frontmatter debe ser un mapping YAML, no una lista o valor simple."
        )
    return (metadata, body)


def dump(metadata: dict[str, Any], body: str) -> str:
    """Serializa metadata como YAML frontmatter + body."""
    try:
        yaml_text = yaml.safe_dump(
            metadata,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )
    except yaml.YAMLError as exc:
        raise FrontmatterError(f"No se pudo serializar el frontmatter: {exc}") from exc

    if not yaml_text.endswith("\n"):
        yaml_text += "\n"
    return f"---\n{yaml_text}---\n\n{body}"
