"""Launcher cross-platform de tools (Mac + Windows)."""

from __future__ import annotations

import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from minirick.models import Tool

IS_MAC = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"

DANGEROUS_CHARS = (";", "&&", "||", "|", ">", "<", "$(", "`", "\n", "\r")


class LaunchError(Exception):
    """Error amigable al intentar lanzar una tool."""


def launch_tool(tool: Tool) -> dict[str, Any]:
    """Lanza una tool. Retorna {'ok': True, 'message': str}
    o {'ok': False, 'error': str}. Nunca levanta excepciones al caller."""
    try:
        message = _dispatch(tool)
        return {"ok": True, "message": message}
    except LaunchError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"Error inesperado: {exc}"}


def _dispatch(tool: Tool) -> str:
    """Dispatcher interno. Retorna mensaje de éxito o levanta LaunchError."""
    handlers = {
        "claude_code": _launch_claude_code,
        "vscode": _launch_vscode,
        "browser": _launch_browser,
        "file": _launch_file,
        "notepad": _launch_notepad,
        "terminal": _launch_terminal,
    }
    handler = handlers.get(tool.type)
    if handler is None:
        raise LaunchError(f"Tipo de tool desconocido: {tool.type}")
    return handler(tool)


def _launch_vscode(tool: Tool) -> str:
    if not tool.path:
        raise LaunchError("vscode requiere `path`")
    if shutil.which("code") is None:
        raise LaunchError(
            "VSCode no está instalado. Descárgalo de https://code.visualstudio.com/"
        )
    path = str(Path(tool.path).expanduser())
    if IS_WINDOWS:
        subprocess.Popen(f'code "{path}"', shell=True)
    else:
        subprocess.Popen(["code", path], shell=False)
    return f"VSCode abierto en {path}"


def _launch_claude_code(tool: Tool) -> str:
    if not tool.path:
        raise LaunchError("claude_code requiere `path`")
    if shutil.which("claude") is None:
        raise LaunchError(
            "Claude Code no está instalado. Instálalo con: "
            "npm install -g @anthropic-ai/claude-code"
        )
    path = str(Path(tool.path).expanduser())
    if IS_WINDOWS:
        subprocess.Popen(
            ["start", "cmd", "/K", f'cd /d "{path}" && claude'],
            shell=True,
        )
    else:
        subprocess.Popen(
            [
                "osascript",
                "-e",
                f'tell app "Terminal" to do script "cd \\"{path}\\" && claude"',
            ],
            shell=False,
        )
    return f"Claude Code abriendo en {path}"


def _launch_browser(tool: Tool) -> str:
    if not tool.url:
        raise LaunchError("browser requiere `url`")
    url = tool.url
    if IS_WINDOWS:
        subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)
    else:
        subprocess.Popen(["open", url], shell=False)
    return f"Navegador abierto en {url}"


def _launch_file(tool: Tool) -> str:
    if not tool.path:
        raise LaunchError("file requiere `path`")
    path = str(Path(tool.path).expanduser())
    if not Path(path).exists():
        raise LaunchError(f"Archivo no existe: {path}")
    if IS_WINDOWS:
        import os

        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["open", path], shell=False)
    return f"Archivo abierto: {path}"


def _launch_notepad(tool: Tool) -> str:
    if tool.content is None:
        raise LaunchError("notepad requiere `content`")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write(tool.content)
        temp_path = f.name
    if IS_WINDOWS:
        subprocess.Popen(["notepad", temp_path], shell=False)
    else:
        subprocess.Popen(["open", "-t", temp_path], shell=False)
    return f"Bloc de notas abierto ({Path(temp_path).name})"


def _launch_terminal(tool: Tool) -> str:
    cwd = tool.cwd or str(Path.home())
    cwd_expanded = str(Path(cwd).expanduser())
    command = (tool.command or "").strip()

    if command:
        for char in DANGEROUS_CHARS:
            if char in command:
                raise LaunchError(
                    "Comando inseguro: contiene caracteres no permitidos"
                )

    if IS_WINDOWS:
        if command:
            full_cmd = f'cd /d "{cwd_expanded}" && {command}'
        else:
            full_cmd = f'cd /d "{cwd_expanded}"'
        subprocess.Popen(
            ["start", "cmd", "/K", full_cmd],
            shell=True,
        )
    else:
        if command:
            script = f'cd "{cwd_expanded}" && {command}'
        else:
            script = f'cd "{cwd_expanded}"'
        subprocess.Popen(
            [
                "osascript",
                "-e",
                f'tell app "Terminal" to do script "{script}"',
            ],
            shell=False,
        )
    return f"Terminal abierta en {cwd_expanded}"
