"""Abre el editor del sistema de forma bloqueante sobre un buffer temporal.

Resolución de editor:
  1. ``$EDITOR`` si está seteado y es ejecutable.
  2. Windows: ``notepad`` (foreground, bloquea hasta que se cierre).
  3. macOS: ``open -t -W`` (bloquea hasta que TextEdit cierre el archivo).
  4. Fallback por si algo sale mal: EditorError con instrucción clara.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


class EditorError(Exception):
    """No se pudo abrir o ejecutar el editor del sistema."""


def open_in_editor(initial_content: str, suffix: str = ".md") -> str:
    """Escribe initial_content en un temp file, abre el editor, retorna el contenido editado.

    El temp file se borra en el bloque finally. Usa delete=False + cleanup manual
    porque en Windows no se puede reabrir un NamedTemporaryFile mientras está open.
    """
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=suffix,
        delete=False,
    )
    tmp_path = Path(tmp.name)
    try:
        tmp.write(initial_content)
        tmp.close()

        cmd = _resolve_editor_cmd(str(tmp_path))
        try:
            subprocess.run(cmd, check=True)
        except FileNotFoundError as exc:
            raise EditorError(
                f"No pude ejecutar el editor: {cmd[0]}. "
                "Define $EDITOR o instala notepad/TextEdit."
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise EditorError(
                f"El editor salió con error (código {exc.returncode})."
            ) from exc

        return tmp_path.read_text(encoding="utf-8")
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


def _resolve_editor_cmd(path: str) -> list[str]:
    """Decide qué comando lanzar para abrir ``path`` en un editor bloqueante."""
    env_editor = os.environ.get("EDITOR", "").strip()
    if env_editor:
        parts = shlex.split(env_editor)
        if parts and shutil.which(parts[0]):
            return parts + [path]

    if sys.platform == "win32":
        return ["notepad", path]

    if sys.platform == "darwin":
        return ["open", "-t", "-W", path]

    # Fallback razonable si alguien corre Linux en dev.
    for candidate in ("nano", "vim", "vi"):
        if shutil.which(candidate):
            return [candidate, path]

    raise EditorError(
        "No encontré un editor disponible. Define $EDITOR o instala notepad/TextEdit."
    )
