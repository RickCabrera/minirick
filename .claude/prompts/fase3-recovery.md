# Fase 3 — Recuperación de archivos Python faltantes

> **Contexto crítico**: en iteraciones anteriores reportaste haber creado archivos que nunca se escribieron a disco. Verificamos manualmente con `Get-ChildItem` y confirmamos que faltan varios archivos. Este archivo es para recuperar lo que falta, sin tocar lo que sí existe.

---

## Regla 0 — Antes de escribir código

Responde con:

1. La lista exacta de archivos que VAS a crear (deben ser 6 archivos).
2. La lista exacta de archivos que NO vas a tocar (deben ser 2 archivos UI + toda la capa Python fuera de `dashboard/`).
3. La confirmación de que vas a **verificar la existencia de cada archivo creado con `Test-Path`** (o equivalente) después de escribirlo, antes de reportarme que terminaste.

Si no puedes listar estos puntos sin inventar, vuelve a leer este archivo antes de codear.

---

## Estado actual REAL del proyecto

Yo (el usuario) ya verifiqué con PowerShell. Estos son los hechos:

**Archivos que YA EXISTEN y están bien** (NO tocar):
- `src/minirick/dashboard/ui/index.html` (2779 bytes)
- `src/minirick/dashboard/ui/styles.css` (6694 bytes)

**Archivos que FALTAN en disco** (hay que crear):
- `src/minirick/dashboard/__init__.py`
- `src/minirick/dashboard/window.py`
- `src/minirick/dashboard/api.py`
- `src/minirick/dashboard/service.py`
- `src/minirick/dashboard/ui/app.js`
- `tests/test_dashboard_api.py`

**Archivos intactos de Fases 1 y 2** (NO tocar):
- Todo en `src/minirick/` que no sea `dashboard/`: `cli.py`, `auth.py`, `db.py`, `models.py`, `config.py`, `__init__.py`.
- Todo en `tests/` que ya existe: `test_auth.py`, `test_cli_smoke.py`, `test_db.py`, `test_models.py`.

---

## Regla de verificación OBLIGATORIA

Después de escribir cada archivo, **verifica con tu herramienta de lectura de archivos** que el archivo existe en disco y tiene contenido. Si alguno sale vacío o no existe, repórtalo al final honestamente. No asumas éxito sin verificar.

Al final, antes de reportarme, corre literalmente estos comandos y pega el output en tu reporte:

```bash
# Adapta a Windows/PowerShell si el agente corre en Windows
ls src/minirick/dashboard/
ls src/minirick/dashboard/ui/
ls tests/
pytest -v
ruff check src/ tests/
```

Si alguno de los 6 archivos que debiste crear no aparece en el listado, **dímelo explícitamente en el reporte** en lugar de decir "listo".

---

## Archivo 1 — `src/minirick/dashboard/__init__.py`

Propósito: permitir `from minirick.dashboard import launch_dashboard` sin cargar pywebview al importar (porque pywebview no se puede importar en entornos headless como CI).

```python
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
```

---

## Archivo 2 — `src/minirick/dashboard/service.py`

Capa de acceso a datos del dashboard. Usa el cliente Supabase ya configurado (no crea uno nuevo).

```python
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
```

---

## Archivo 3 — `src/minirick/dashboard/api.py`

Bridge Python ↔ JS. Todos los métodos capturan excepciones y retornan dicts serializables. **Nunca** propagan errores al WebView.

```python
"""Bridge Python <-> JavaScript para el dashboard pywebview.

Todos los métodos de DashboardAPI capturan errores y retornan dicts serializables
a JSON. Nunca levantan excepciones al WebView.
"""

from __future__ import annotations

from typing import Any

from minirick.dashboard import service


class DashboardAPI:
    """API expuesta al frontend vía pywebview.js_api."""

    def __init__(self) -> None:
        self._window: Any = None  # lo setea window.py después de crear la ventana

    def attach_window(self, window: Any) -> None:
        """Guarda referencia a la ventana pywebview para minimizar/cerrar."""
        self._window = window

    # ---------- Data ----------

    def get_active_task(self) -> dict[str, Any]:
        """Retorna {'ok': True, 'task': dict|None} o {'ok': False, 'error': str}."""
        try:
            task = service.fetch_active_task()
            return {"ok": True, "task": task.to_dict() if task else None}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_current_profile(self) -> dict[str, Any]:
        """Retorna {'ok': True, 'profile': dict|None} o {'ok': False, 'error': str}."""
        try:
            profile = service.fetch_current_profile()
            return {"ok": True, "profile": profile}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def refresh(self) -> dict[str, Any]:
        """Alias de get_active_task para el botón de refresh (si se añade)."""
        return self.get_active_task()

    # ---------- Actions (stubs hasta Fase 4/5) ----------

    def open_tool(self, tool_index: int) -> dict[str, Any]:
        """STUB de Fase 4 — Launcher real llega en Fase 4."""
        try:
            result = service.fetch_active_task()
            if result is None:
                return {"ok": False, "error": "No hay tarea activa"}
            tools = result.tools
            if tool_index < 0 or tool_index >= len(tools):
                return {"ok": False, "error": f"Índice fuera de rango: {tool_index}"}
            tool = tools[tool_index]
            return {
                "ok": False,
                "message": f"Launcher llega en Fase 4 (tool: {tool.type})",
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def open_config(self) -> dict[str, Any]:
        """STUB de Fase 5 — panel de configuración."""
        return {"ok": False, "message": "Configuración llega en Fase 5"}

    # ---------- Window control ----------

    def minimize_window(self) -> dict[str, Any]:
        try:
            if self._window is not None:
                self._window.minimize()
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def close_window(self) -> dict[str, Any]:
        try:
            if self._window is not None:
                self._window.destroy()
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
```

---

## Archivo 4 — `src/minirick/dashboard/window.py`

Setup de la ventana pywebview. Frameless, always-on-top, 380x620, esquina superior derecha.

```python
"""Ventana flotante del dashboard minirick (pywebview)."""

from __future__ import annotations

from pathlib import Path

import webview

from minirick.dashboard.api import DashboardAPI

WINDOW_WIDTH = 380
WINDOW_HEIGHT = 620
WINDOW_TITLE = "minirick"


def _get_ui_path() -> str:
    """Retorna la ruta absoluta a ui/index.html."""
    ui_dir = Path(__file__).parent / "ui"
    return str(ui_dir / "index.html")


def _position_top_right(window: webview.Window) -> None:
    """Reposiciona la ventana en la esquina superior derecha de la pantalla primaria."""
    try:
        screens = webview.screens
        if not screens:
            return
        screen = screens[0]
        x = max(0, screen.width - WINDOW_WIDTH - 20)
        y = 20
        window.move(x, y)
    except Exception:  # noqa: BLE001 — no crítico si falla
        pass


def launch_dashboard() -> None:
    """Crea y lanza la ventana del dashboard. Bloquea hasta que se cierre."""
    api = DashboardAPI()

    window = webview.create_window(
        title=WINDOW_TITLE,
        url=_get_ui_path(),
        js_api=api,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        frameless=True,
        easy_drag=False,
        on_top=True,
        resizable=False,
        background_color="#0a0e0a",
    )

    api.attach_window(window)

    webview.start(func=_position_top_right, args=(window,))
```

---

## Archivo 5 — `src/minirick/dashboard/ui/app.js`

**IMPORTANTE**: este archivo debe seguir las especificaciones del archivo `.claude/prompts/fase3-dashboard-ui.md` que ya existe en el proyecto. Re-léelo antes de escribir este.

Requerimientos resumidos:
- Esperar evento `pywebviewready` antes de llamar API.
- Estados: loading, error, empty, task (mutuamente excluyentes).
- Render de markdown con `marked` (ya incluido vía CDN en index.html). Fallback a `<pre>` si `marked` no está disponible.
- Función `showToast(msg)` — NO usar `alert()`.
- Secciones CONTEXT y TOOLS colapsables con indicador `▾` / `▸`.
- Click en tool llama `open_tool(index)` y muestra toast con el mensaje retornado.
- Botones header: minimizar, configuración, cerrar.
- Registro de todo el markup de tools con prefix `[>]` (el hover a `[#]` está en CSS, no en JS).

```javascript
/* minirick dashboard — frontend logic (vanilla, no framework) */

(function () {
  'use strict';

  const STATE_IDS = ['state-loading', 'state-error', 'state-empty', 'state-task'];

  function showState(stateId) {
    for (const id of STATE_IDS) {
      const el = document.getElementById(id);
      if (el) el.hidden = id !== stateId;
    }
  }

  function showToast(msg) {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.classList.remove('hidden');
    clearTimeout(showToast._timer);
    showToast._timer = setTimeout(() => t.classList.add('hidden'), 3000);
  }

  function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function renderMarkdown(md) {
    if (!md) return '<em class="dim">(sin contexto)</em>';
    if (typeof marked !== 'undefined' && marked.parse) {
      try {
        return marked.parse(md);
      } catch (e) {
        // fallthrough to pre
      }
    }
    return '<pre>' + escapeHtml(md) + '</pre>';
  }

  function renderStatusBadge(status) {
    const safe = String(status || 'todo').toLowerCase();
    const known = ['todo', 'in_progress', 'done'];
    const cls = known.includes(safe) ? 'status-' + safe : '';
    return '<span class="status-badge ' + cls + '">[' + escapeHtml(safe) + ']</span>';
  }

  function toolDetail(tool) {
    if (tool.url) return tool.url;
    if (tool.path) return tool.path;
    if (tool.cwd) return tool.cwd;
    if (tool.content) return '(inline content)';
    return '';
  }

  function renderTools(tools) {
    if (!tools || tools.length === 0) {
      return '<div class="empty-inline">(sin herramientas)</div>';
    }
    return tools
      .map(function (tool, idx) {
        return (
          '<div class="tool" data-index="' +
          idx +
          '">' +
          '<span class="tool-type">' +
          escapeHtml(tool.type) +
          '</span>' +
          '<span class="tool-detail">' +
          escapeHtml(toolDetail(tool)) +
          '</span>' +
          '</div>'
        );
      })
      .join('');
  }

  function renderTask(task) {
    const titleEl = document.getElementById('task-title');
    const statusEl = document.getElementById('task-status');
    const summaryEl = document.getElementById('task-summary');
    const contextEl = document.getElementById('task-context');
    const toolsEl = document.getElementById('task-tools');
    const toolsCountEl = document.getElementById('tools-count');

    if (titleEl) titleEl.textContent = task.title || '(sin título)';
    if (statusEl) statusEl.innerHTML = renderStatusBadge(task.status);
    if (summaryEl) summaryEl.textContent = task.summary || '(sin resumen)';
    if (contextEl) contextEl.innerHTML = renderMarkdown(task.context_md);
    if (toolsEl) toolsEl.innerHTML = renderTools(task.tools);
    if (toolsCountEl) toolsCountEl.textContent = (task.tools || []).length;

    // Wire tool clicks
    document.querySelectorAll('.tool').forEach(function (el) {
      el.addEventListener('click', function () {
        const idx = parseInt(el.getAttribute('data-index'), 10);
        window.pywebview.api
          .open_tool(idx)
          .then(function (r) {
            if (r && (r.message || r.error)) {
              showToast(r.message || r.error);
            }
          })
          .catch(function (e) {
            showToast('Error: ' + e);
          });
      });
    });
  }

  function renderProfile(profile) {
    const el = document.getElementById('footer-profile');
    if (!el) return;
    if (!profile) {
      el.textContent = '(sin sesión)';
      return;
    }
    el.innerHTML =
      '<span class="footer-email">' +
      escapeHtml(profile.email || '') +
      '</span>' +
      '<span class="footer-sep"> · </span>' +
      '<span class="footer-role">' +
      escapeHtml(profile.role || '') +
      '</span>';
  }

  function wireHeaderButtons() {
    const minBtn = document.getElementById('btn-minimize');
    const cfgBtn = document.getElementById('btn-config');
    const closeBtn = document.getElementById('btn-close');

    if (minBtn) {
      minBtn.addEventListener('click', function () {
        window.pywebview.api.minimize_window();
      });
    }
    if (cfgBtn) {
      cfgBtn.addEventListener('click', function () {
        window.pywebview.api.open_config().then(function (r) {
          showToast((r && r.message) || 'Configuración llega en Fase 5');
        });
      });
    }
    if (closeBtn) {
      closeBtn.addEventListener('click', function () {
        window.pywebview.api.close_window();
      });
    }
  }

  function wireCollapsibles() {
    document.querySelectorAll('.section-header.collapsible').forEach(function (header) {
      header.addEventListener('click', function () {
        const targetId = header.getAttribute('data-target');
        const content = document.getElementById(targetId);
        const indicator = header.querySelector('.collapse-indicator');
        if (!content) return;
        const isCollapsed = content.classList.toggle('collapsed');
        if (indicator) indicator.textContent = isCollapsed ? '▸' : '▾';
      });
    });
  }

  async function init() {
    showState('state-loading');
    wireHeaderButtons();
    wireCollapsibles();

    try {
      const [taskRes, profileRes] = await Promise.all([
        window.pywebview.api.get_active_task(),
        window.pywebview.api.get_current_profile(),
      ]);

      if (profileRes && profileRes.ok) {
        renderProfile(profileRes.profile);
      } else {
        renderProfile(null);
      }

      if (!taskRes || !taskRes.ok) {
        showState('state-error');
        const errMsgEl = document.getElementById('error-detail');
        if (errMsgEl && taskRes && taskRes.error) {
          errMsgEl.textContent = taskRes.error;
        }
        return;
      }
      if (taskRes.task == null) {
        showState('state-empty');
        return;
      }
      renderTask(taskRes.task);
      showState('state-task');
    } catch (e) {
      showState('state-error');
      const errMsgEl = document.getElementById('error-detail');
      if (errMsgEl) errMsgEl.textContent = String(e);
    }
  }

  window.addEventListener('pywebviewready', init);
})();
```

**NOTA sobre `index.html`**: el archivo ya existe. Si tiene todos los IDs que app.js referencia (`state-loading`, `state-error`, `state-empty`, `state-task`, `task-title`, `task-status`, `task-summary`, `task-context`, `task-tools`, `tools-count`, `footer-profile`, `btn-minimize`, `btn-config`, `btn-close`, `toast`), déjalo como está. Si falta algún ID, **NO reescribas el archivo completo** — hazle edits quirúrgicos para añadir solo los IDs que falten. Reporta qué añadiste.

---

## Archivo 6 — `tests/test_dashboard_api.py`

```python
"""Tests de DashboardAPI — verifica que nunca propaga excepciones al frontend."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from minirick.dashboard import api as api_module
from minirick.dashboard.api import DashboardAPI
from minirick.models import Task, Tool


@pytest.fixture
def sample_task() -> Task:
    return Task(
        id="t-1",
        title="Tarea demo",
        summary="resumen",
        context_md="# contexto",
        tools=[
            Tool(type="vscode", path="~/repos/x"),
            Tool(type="browser", url="https://x.co"),
        ],
        status="in_progress",
        is_active=True,
    )


def test_get_active_task_returns_task_dict(sample_task: Task) -> None:
    with patch.object(api_module.service, "fetch_active_task", return_value=sample_task):
        result = DashboardAPI().get_active_task()
    assert result["ok"] is True
    assert result["task"]["title"] == "Tarea demo"
    assert len(result["task"]["tools"]) == 2


def test_get_active_task_returns_none_when_no_active() -> None:
    with patch.object(api_module.service, "fetch_active_task", return_value=None):
        result = DashboardAPI().get_active_task()
    assert result == {"ok": True, "task": None}


def test_get_active_task_captures_network_error() -> None:
    with patch.object(
        api_module.service, "fetch_active_task", side_effect=RuntimeError("network down")
    ):
        result = DashboardAPI().get_active_task()
    assert result["ok"] is False
    assert "network down" in result["error"]


def test_get_current_profile_returns_dict() -> None:
    fake_profile = {"id": "u1", "email": "a@b.co", "role": "owner"}
    with patch.object(
        api_module.service, "fetch_current_profile", return_value=fake_profile
    ):
        result = DashboardAPI().get_current_profile()
    assert result == {"ok": True, "profile": fake_profile}


def test_refresh_is_alias_of_get_active_task(sample_task: Task) -> None:
    with patch.object(api_module.service, "fetch_active_task", return_value=sample_task):
        result = DashboardAPI().refresh()
    assert result["ok"] is True
    assert result["task"]["title"] == "Tarea demo"


def test_open_tool_returns_stub_message(sample_task: Task) -> None:
    with patch.object(api_module.service, "fetch_active_task", return_value=sample_task):
        result = DashboardAPI().open_tool(0)
    assert result["ok"] is False
    assert "Fase 4" in result["message"]


def test_open_tool_out_of_range(sample_task: Task) -> None:
    with patch.object(api_module.service, "fetch_active_task", return_value=sample_task):
        result = DashboardAPI().open_tool(99)
    assert result["ok"] is False
    assert "rango" in result["error"].lower()


def test_open_tool_no_active_task() -> None:
    with patch.object(api_module.service, "fetch_active_task", return_value=None):
        result = DashboardAPI().open_tool(0)
    assert result["ok"] is False
    assert "activa" in result["error"].lower()


def test_open_config_is_stub() -> None:
    result = DashboardAPI().open_config()
    assert result["ok"] is False
    assert "Fase 5" in result["message"]


def test_minimize_no_window_is_safe() -> None:
    # Sin window attached, no debe crashear
    result = DashboardAPI().minimize_window()
    assert result["ok"] is True


def test_minimize_with_window_calls_it() -> None:
    api = DashboardAPI()
    fake_window = MagicMock()
    api.attach_window(fake_window)
    result = api.minimize_window()
    assert result["ok"] is True
    fake_window.minimize.assert_called_once()


def test_close_window_with_window_calls_destroy() -> None:
    api = DashboardAPI()
    fake_window = MagicMock()
    api.attach_window(fake_window)
    result = api.close_window()
    assert result["ok"] is True
    fake_window.destroy.assert_called_once()
```

---

## Integración con `cli.py`

**IMPORTANTE**: `cli.py` ya existe y tiene la lógica del comando raíz (`main`). **NO reescribas `cli.py` completo.** Hazle un edit quirúrgico para que el `main()` (el callback de Typer con `invoke_without_command=True`) ahora llame `launch_dashboard()` cuando hay sesión activa.

Comportamiento esperado del comando raíz `minirick`:

1. Si ya hay subcomando invocado, no hacer nada extra (dejar pasar).
2. Verificar sesión con `ensure_session()` de `minirick.auth`. Si no hay sesión → imprimir mensaje amigable + salir con exit 1.
3. Si hay sesión → `from minirick.dashboard import launch_dashboard` dentro de la función (lazy), luego `launch_dashboard()`.
4. Si `launch_dashboard()` levanta una excepción (ej. pywebview falla), capturar con try/except, imprimir error amigable con Rich (no traceback crudo), exit 1.

Si el `main()` actual ya hace algo similar pero incompleto, pártelo mínimo. Reporta qué líneas modificaste.

**NO toques** las funciones de `login`, `logout`, `list_tasks`, `new`, `edit`, `set_active`, `sync`.

---

## Test de CLI actualizado

El archivo `tests/test_cli_smoke.py` ya existe con 4 tests. Verifica si el test `test_root_command_shows_banner` necesita actualizarse ahora que `main` llama a `launch_dashboard`.

Si ese test falla después de tu edit de `cli.py`, **actualízalo así**: reemplaza el test por dos nuevos:

```python
def test_root_command_without_session_exits_with_error(monkeypatch, tmp_path):
    """Sin sesión, minirick (sin args) debe salir con error amigable."""
    from minirick import auth

    # Apunta el session file a uno que no existe
    monkeypatch.setattr(auth, "get_session_file", lambda: tmp_path / "noop.json")
    result = runner.invoke(app, [])
    assert result.exit_code != 0
    assert "login" in result.stdout.lower() or "sesión" in result.stdout.lower()


def test_root_command_with_session_launches_dashboard(monkeypatch, tmp_path):
    """Con sesión, minirick (sin args) debe llamar launch_dashboard."""
    import json

    from minirick import auth

    session_path = tmp_path / "session.json"
    session_path.write_text(
        json.dumps({"access_token": "a", "refresh_token": "b"}), encoding="utf-8"
    )
    monkeypatch.setattr(auth, "get_session_file", lambda: session_path)

    called = {"launched": False}

    def fake_launch():
        called["launched"] = True

    # Parchea tanto el módulo como el atributo en cli si lo importa directamente
    monkeypatch.setattr("minirick.dashboard.window.launch_dashboard", fake_launch)

    # El cliente Supabase se mockea para set_session no falle
    from unittest.mock import MagicMock

    monkeypatch.setattr(auth, "get_client", lambda: MagicMock())

    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert called["launched"] is True
```

Si el test original ya estaba escrito de esta forma, déjalo. Si solo requiere pequeño ajuste, hazlo.

---

## Checklist final OBLIGATORIO

Antes de decirme "listo", verifica con Test-Path (o equivalente) que estos 6 archivos EXISTEN en disco:

- [ ] `src/minirick/dashboard/__init__.py`
- [ ] `src/minirick/dashboard/window.py`
- [ ] `src/minirick/dashboard/api.py`
- [ ] `src/minirick/dashboard/service.py`
- [ ] `src/minirick/dashboard/ui/app.js`
- [ ] `tests/test_dashboard_api.py`

Luego corre:

```bash
pytest -v
ruff check src/ tests/
```

**Esperado**:
- `pytest` debe reportar **alrededor de 40 tests pasando** (29 previos + ~12 de dashboard_api). Si el número que ves es <37, algún archivo no se escribió — reporta.
- `ruff check` debe estar limpio.

En tu reporte final incluye:

1. El listado `ls` de `src/minirick/dashboard/` y `src/minirick/dashboard/ui/` y `tests/` para que yo vea que los archivos están ahí.
2. El número EXACTO de tests pasando que reporta pytest.
3. Output de `ruff check`.
4. Qué líneas modificaste de `cli.py` (si es que lo modificaste).
5. Si NO pudiste crear algún archivo, dilo honestamente y por qué.

**NO corras `minirick`. NO hagas commit.**
