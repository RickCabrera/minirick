# Fase 4 — Launcher de herramientas

> Hace que los tools del dashboard realmente abran apps (VSCode, browser, etc.) en Mac y Windows. Auto-lanza tools la primera vez que se ve una tarea; después solo con click.

---

## Regla 0 — Antes de escribir código

Responde con:

1. Los archivos que VAS a crear (2 nuevos).
2. Los archivos que VAS a modificar (3 existentes).
3. Los archivos que NO vas a tocar (todos los de fases anteriores que no sean los 3 anteriores).
4. Cómo detectas Mac vs Windows en el código.
5. Qué comandos del sistema usarás para cada tipo de tool en cada SO (tabla resumida).

Espera mi "adelante" antes de codear.

---

## Archivos a tocar

**Crear:**
- `src/minirick/launcher.py` — dispatcher de tools cross-platform.
- `tests/test_launcher.py` — tests con mocks de subprocess/platform.

**Modificar:**
- `src/minirick/dashboard/api.py` — `open_tool()` deja de ser stub.
- `src/minirick/dashboard/window.py` — ganar lógica de auto-launch al abrir.
- `src/minirick/config.py` — añadir helper para leer/escribir `last_auto_launched_task_id` en cache.

**NO tocar:**
- Cualquier otro archivo Python.
- UI (index.html, styles.css, app.js) — el frontend no cambia. Solo los toasts ahora mostrarán mensajes reales de éxito/error.
- Supabase, schema, RLS.

---

## Feature 1 — Launcher de tools

### Tipos soportados

El modelo `Tool` (ya existe en `models.py`) tiene estos `type`:
- `claude_code` — abre Claude Code en `tool.path`.
- `vscode` — abre VSCode en `tool.path`.
- `browser` — abre URL `tool.url` en navegador default.
- `file` — abre archivo `tool.path` con app default del SO.
- `notepad` — crea temp file con `tool.content` y lo abre.
- `terminal` — abre ventana de terminal en `tool.cwd`, opcionalmente ejecutando `tool.command`.

### Comandos por tipo y SO

| Tool | macOS | Windows |
|---|---|---|
| `claude_code` | `claude` (detectar en PATH) con `cwd=path` | igual |
| `vscode` | `code <path>` (detectar en PATH) | igual |
| `browser` | `open <url>` | `start "" <url>` |
| `file` | `open <path>` | `start "" <path>` (o `os.startfile(path)`) |
| `notepad` | `open -t <temp_file>` (TextEdit) | `notepad <temp_file>` |
| `terminal` | `osascript -e 'tell app "Terminal" to do script "cd <cwd>; <command>"'` | `start cmd /K "cd /d <cwd> && <command>"` |

Detecta SO con:
```python
import platform
IS_MAC = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"
```

### Validación de ejecutables

Antes de lanzar, verifica que el binario existe con `shutil.which("code")`, `shutil.which("claude")`, etc. Si `which` retorna `None`:

- `vscode` no encontrado → error con mensaje:
  `"VSCode no está instalado. Descárgalo de https://code.visualstudio.com/"`
- `claude_code` no encontrado → error:
  `"Claude Code no está instalado. Instálalo con: npm install -g @anthropic-ai/claude-code"`

Para `browser`, `file`, `notepad`, `terminal`: no valides `shutil.which` porque son binarios del sistema que siempre están (`open`, `start`, `notepad`, `osascript`, `cmd`). Si fallan, captura y retorna el error.

### Sanitización de `terminal.command`

Bloquea caracteres peligrosos que permitan shell injection o encadenamiento:

```python
DANGEROUS_CHARS = [";", "&&", "||", "|", ">", "<", "$(", "`", "\n", "\r"]
```

Si `tool.command` contiene alguno → retorna error:
`"Comando inseguro: contiene caracteres no permitidos"`

El `cwd` del terminal SÍ puede tener espacios (rutas tipo `C:\Program Files\...`), así que escápalo con comillas en el comando final, no lo sanitices igual.

### Firma del launcher

```python
# src/minirick/launcher.py

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
    except Exception as exc:
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
    # claude es interactivo — en Windows lanzar en nueva terminal para que sea usable
    if IS_WINDOWS:
        subprocess.Popen(
            ["start", "cmd", "/K", f'cd /d "{path}" && claude'],
            shell=True,
        )
    else:  # macOS
        subprocess.Popen(
            ["osascript", "-e",
             f'tell app "Terminal" to do script "cd \\"{path}\\" && claude"'],
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
    # crear temp file con extensión .txt
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
            # cd /d soporta cambiar de drive; comando se ejecuta y deja shell abierta
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
            ["osascript", "-e",
             f'tell app "Terminal" to do script "{script}"'],
            shell=False,
        )
    return f"Terminal abierta en {cwd_expanded}"
```

---

## Feature 2 — `api.py` deja de ser stub

En `src/minirick/dashboard/api.py`, modifica `open_tool()` para que llame al launcher real:

```python
# Añadir import
from minirick.launcher import launch_tool

# Reemplazar el método open_tool
def open_tool(self, tool_index: int) -> dict[str, Any]:
    """Lanza la tool en el índice dado de la tarea activa."""
    try:
        task = service.fetch_active_task()
        if task is None:
            return {"ok": False, "error": "No hay tarea activa"}
        tools = task.tools
        if tool_index < 0 or tool_index >= len(tools):
            return {"ok": False, "error": f"Índice fuera de rango: {tool_index}"}
        tool = tools[tool_index]
        return launch_tool(tool)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
```

El JS del dashboard ya pinta el `result.message` o `result.error` en el toast. No hay cambios en UI.

---

## Feature 3 — Auto-launch al abrir `minirick`

### Persistencia en config

En `src/minirick/config.py`, añade dos funciones:

```python
import json

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
```

### Lógica de auto-launch en `window.py`

Modifica `src/minirick/dashboard/window.py` para que ANTES de `webview.start`, verifique si hay que auto-lanzar tools.

Lógica:

```python
# En window.py, añadir función
def _maybe_auto_launch() -> list[dict]:
    """Si la tarea activa cambió desde la última vez, auto-lanza sus tools.
    Retorna lista de resultados de cada lanzamiento (para logging).
    """
    from minirick.config import load_state, save_state
    from minirick.dashboard import service
    from minirick.launcher import launch_tool

    try:
        task = service.fetch_active_task()
    except Exception:
        return []

    if task is None or not task.tools:
        return []

    state = load_state()
    last_id = state.get("last_auto_launched_task_id")

    if last_id == task.id:
        # Ya se auto-lanzó para esta tarea
        return []

    results = []
    for tool in task.tools:
        result = launch_tool(tool)
        results.append({"tool": tool.type, **result})

    # Actualiza estado
    state["last_auto_launched_task_id"] = task.id
    save_state(state)
    return results


def launch_dashboard() -> None:
    """Crea y lanza la ventana del dashboard. Bloquea hasta que se cierre."""
    # Auto-launch ANTES de abrir la ventana (si aplica)
    _maybe_auto_launch()

    api = DashboardAPI()
    window = webview.create_window(
        # ... (config existente)
    )
    api.attach_window(window)
    webview.start(func=_position_top_right, args=(window,))
```

**Importante**: `_maybe_auto_launch` NO debe crashear si algo falla. Captura excepciones internamente, ignora errores, y que el dashboard siempre abra aunque el auto-launch falle.

**Orden importante**: auto-launch ANTES de `webview.start` porque `webview.start` bloquea. Si lo pones después, nunca se ejecuta.

---

## Feature 4 — Un pulido menor en `cli.py`

Cuando corres `minirick` y se abre el dashboard, ahora ya no dice solo `> minirick dashboard abriendo...`. Si hubo auto-launch, queremos ver un resumen en terminal también.

Modifica la parte de `main()` en `cli.py` donde se llama a `launch_dashboard()`:

```python
console.print("[dim]> minirick dashboard abriendo...[/dim]")
try:
    from minirick.dashboard import launch_dashboard
    launch_dashboard()
```

No cambias esto. Los mensajes de auto-launch viven en terminal cuando el usuario pueda verlos — los imprime `_maybe_auto_launch` directamente con `rich.console.Console()` antes de que la ventana se abra.

Actualiza `_maybe_auto_launch` para imprimir:

```python
from rich.console import Console
console = Console()

# Dentro de _maybe_auto_launch, después del for loop:
if results:
    console.print(f"[dim]> auto-launch: {len(results)} tools[/dim]")
    for r in results:
        icon = "✓" if r["ok"] else "✖"
        color = "green" if r["ok"] else "red"
        msg = r.get("message") or r.get("error") or ""
        console.print(f"  [{color}]{icon}[/{color}] {r['tool']}: {msg}")
```

---

## Tests

### `tests/test_launcher.py`

Mockea `platform.system`, `shutil.which`, `subprocess.Popen`. Cubre:

1. `launch_tool` con tool tipo desconocido → `{ok: False, error: "Tipo de tool desconocido: ..."}`.
2. `vscode` sin `code` en PATH → error con mensaje de instalación.
3. `vscode` con `code` en PATH → llama a `subprocess.Popen(["code", path])`.
4. `browser` sin URL → error `"browser requiere url"`.
5. `browser` en Mac → Popen con `["open", url]`.
6. `browser` en Windows → Popen con `["cmd", "/c", "start", "", url]`.
7. `file` con path inexistente → error.
8. `notepad` sin content → error.
9. `terminal` con `command` conteniendo `;` → error de sanitización.
10. `terminal` con `command` conteniendo `&&` → error.
11. `terminal` con command limpio y cwd válido en Mac → Popen con osascript.
12. `terminal` con command limpio en Windows → Popen con cmd /K.
13. `claude_code` sin `claude` en PATH → error con mensaje npm install.

Usa `pytest.fixture` para parametrizar macOS vs Windows reseteando `IS_MAC` / `IS_WINDOWS` del módulo (con `monkeypatch.setattr(launcher, "IS_MAC", True)`).

### `tests/test_dashboard_api.py` — actualizar

El test `test_open_tool_returns_stub_message` ya NO debería pasar porque `open_tool` dejó de ser stub. Reemplázalo por:

```python
def test_open_tool_calls_launcher(sample_task, monkeypatch):
    """open_tool debe delegar a launch_tool con la tool correcta."""
    fake_result = {"ok": True, "message": "VSCode abierto en /x"}
    called = {}
    def fake_launch(tool):
        called["tool"] = tool
        return fake_result
    monkeypatch.setattr("minirick.dashboard.api.launch_tool", fake_launch)
    with patch.object(api_module.service, "fetch_active_task", return_value=sample_task):
        result = DashboardAPI().open_tool(0)
    assert result == fake_result
    assert called["tool"].type == "vscode"
```

Los demás tests (índice fuera de rango, no hay tarea activa) siguen igual.

### `tests/test_config.py` — crear nuevo

Solo 2 tests:

1. `load_state` retorna `{}` si no existe el archivo.
2. `save_state` + `load_state` roundtrip con un dict.

Usa `tmp_path` + monkeypatch de `get_config_dir`.

---

## Checklist final

Antes de reportar, verifica:

- [ ] `launcher.py` existe y tiene las 6 funciones `_launch_*`.
- [ ] `launcher.py` importa correctamente `Tool` de models.
- [ ] `api.py` ya NO tiene el string `"Fase 4"` en `open_tool`.
- [ ] `api.py` importa `launch_tool`.
- [ ] `window.py` tiene `_maybe_auto_launch` y lo llama antes de `webview.start`.
- [ ] `config.py` tiene `get_state_file`, `load_state`, `save_state`.
- [ ] `test_launcher.py` tiene los 13 casos listados.
- [ ] `test_config.py` existe con sus 2 tests.
- [ ] `test_dashboard_api.py` actualizado (el test de stub reemplazado).
- [ ] `pytest -q` pasa con 55+ tests (42 previos + ~13 de launcher + 2 de config - 1 del stub reemplazado).
- [ ] `ruff check src/ tests/` limpio.
- [ ] Windows/Mac detectados correctamente con `platform.system()`.
- [ ] Sanitización de comandos implementada en `_launch_terminal`.

---

## Reporte final

1. Archivos nuevos + modificados con tamaños.
2. Output de pytest (debe decir 55+ passed).
3. Output de ruff.
4. Diff cortos (5-8 líneas) de `api.py` `open_tool` y `window.py` `launch_dashboard`.
5. NO commit. NO correr minirick.
