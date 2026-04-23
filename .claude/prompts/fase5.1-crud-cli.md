# Fase 5.1 — CRUD de tareas desde CLI + asignación de colabs + panel admin en dashboard

> **Contexto previo obligatorio**: lee `CLAUDE.md` en la raíz del proyecto antes de este archivo. Asume que Fase 4 está cerrada (launcher cross-platform funcionando, 58 tests passing, ruff limpio).

---

## Regla 0 — Antes de escribir código

Responde con **TODO** lo siguiente antes de tocar el teclado. No abras ningún editor hasta recibir mi "adelante".

1. **Lista exacta de archivos que VAS a crear** (rutas completas desde la raíz del repo).
2. **Lista exacta de archivos que VAS a modificar** (rutas completas).
3. **Lista exacta de archivos que NO vas a tocar** (explícitamente: `launcher.py`, `dashboard/window.py` lógica core, `auth.py`, `db.py`, `config.py`, `models.py` excepto donde se indique abajo).
4. **Confirmación de que tras cada `Edit` harás `Test-Path` + `Get-Content | Select-String` en PowerShell** para verificar que los cambios SÍ quedaron en disco.
5. **SQL exacto del migration** que vas a proponer para agregar `assignees` a `tasks` + su policy RLS + índice GIN. Pégalo en tu respuesta tal cual (NO lo corras, yo lo corro manual en Supabase SQL Editor).
6. **Firma de las funciones públicas** de `admin.py`, `editor.py`, `frontmatter.py`. Tipos exactos, no prosa.
7. **Qué dependencia nueva** vas a agregar a `pyproject.toml` (`pyyaml>=6.0`) y confirmación de que corres `pip install -e ".[dev]"` después.
8. **Qué nuevos comandos Typer** quedan funcionales al final (con su signature) y cuáles mensajes de error amigables en español produce cada flujo de error (sin permisos, tarea no existe, YAML inválido, etc.).
9. **Qué sección nueva** agregas al dashboard HTML/JS, qué archivos tocas de `src/minirick/dashboard/ui/` y cuáles NO tocas.
10. **Confirmación expresa** de que NO vas a correr `minirick new`, `minirick edit`, ni el dashboard por ti mismo (las pruebas en vivo las hago yo en Windows). Tú solo corres `pytest -q` y `ruff check src/ tests/`.

Espera mi "adelante" explícito antes de ejecutar.

---

## Objetivo de la fase

Que Rick (owner/admin) pueda:

1. **Crear una tarea desde terminal** con `minirick new` — se abre editor con template markdown+YAML frontmatter, al guardar+cerrar se sube a Supabase.
2. **Editar una tarea existente** con `minirick edit <id>` — baja la tarea, abre editor, sube cambios.
3. **Activar una tarea** con `minirick set-active <id>` — marca `is_active=true` (el trigger desactiva las demás).
4. **Asignar colaboradores** a una tarea, ya sea por flag (`--assignees email1,email2`) o desde el **panel admin del dashboard** (botón ⚙ existente ahora hace algo).
5. **Invitaciones** NO entran en esta fase — van en 5.2 (Edge Function).

Regla de visibilidad: `assignees = []` o `NULL` → la tarea es visible para todos los colabs. `assignees = [uuid1, uuid2]` → solo esos colabs (+ admins/owners siempre) la ven.

---

## Sub-fase A — Migration de DB (el SQL lo corre Rick, NO tú)

Propón el SQL. Rick lo corre manual en Supabase SQL Editor. NO intentes ejecutar nada contra Supabase desde código de migration automatizado.

Debe incluir:

1. `ALTER TABLE public.tasks ADD COLUMN assignees uuid[] NOT NULL DEFAULT '{}';`
2. Índice GIN: `CREATE INDEX tasks_assignees_idx ON public.tasks USING GIN (assignees);`
3. **Reemplazar** la policy RLS de SELECT sobre `tasks` para que sea:
   ```
   (public.is_admin_or_owner())
   OR (array_length(assignees, 1) IS NULL)   -- array vacío = público
   OR (auth.uid() = ANY(assignees))
   ```
   Si la policy actual se llama `tasks_select_authenticated` o similar, propón `DROP POLICY IF EXISTS ... ; CREATE POLICY ...`. Si no sabes el nombre exacto, pon un comentario en el SQL: `-- TODO Rick: ajusta nombre de policy actual` y deja la shape completa para que Rick la pegue bien.
4. NO toques las policies de INSERT/UPDATE/DELETE — siguen siendo "solo admins/owners".
5. Nota al final del bloque SQL: tareas existentes quedan con `assignees = '{}'` → visibles para todos (backward compatible). Esto es lo que queremos.

Pega el SQL en un bloque ```sql dentro de tu respuesta de Regla 0 punto 5. No lo guardes en un archivo del repo.

---

## Sub-fase B — Módulos Python nuevos

### `src/minirick/frontmatter.py`

Parser simple basado en PyYAML. Una función pública:

```python
def parse(text: str) -> tuple[dict[str, Any], str]:
    """Divide un documento '---\\nYAML\\n---\\nMARKDOWN' en (metadata, body).

    Si no hay frontmatter válido, retorna ({}, text).
    Si el YAML es inválido, lanza FrontmatterError con mensaje claro.
    """
```

Y la inversa:

```python
def dump(metadata: dict[str, Any], body: str) -> str:
    """Serializa metadata como YAML frontmatter + body. Usa yaml.safe_dump con allow_unicode=True y sort_keys=False."""
```

Excepción propia `FrontmatterError(Exception)`. Usa `yaml.safe_load` (NO `yaml.load`).

### `src/minirick/editor.py`

```python
def open_in_editor(initial_content: str, suffix: str = ".md") -> str:
    """Crea un temp file con initial_content, abre el editor del sistema bloqueante,
    espera a que el usuario cierre, lee el contenido final y retorna como str.

    Resolución de editor:
      1. $EDITOR si está seteado y es ejecutable.
      2. Windows: notepad.
      3. macOS: 'open -t -W' (bloqueante con TextEdit).
      4. Si falla todo, EditorError.

    El temp file se borra al final (finally). Usa tempfile.NamedTemporaryFile(delete=False)
    + manual cleanup porque Windows no deja abrir el file mientras está open.
    """
```

Excepción `EditorError(Exception)`. En Windows, `subprocess.run([editor, path])` bloquea hasta que se cierre notepad (es así porque notepad.exe es foreground). Para `$EDITOR` que pueda traer args (ej. `code --wait`), usa `shlex.split` en `$EDITOR` antes de `subprocess.run`.

### `src/minirick/admin.py`

Operaciones de admin contra Supabase. Asume que el cliente ya tiene sesión (la RLS hace el resto).

```python
def require_admin() -> Profile:
    """Carga el perfil actual, valida rol admin|owner. Lanza PermissionError con mensaje en español si no."""

def create_task(data: dict) -> Task:
    """INSERT. data debe tener al menos 'title'. Retorna Task parseado de la response."""

def update_task(task_id: str, data: dict) -> Task:
    """UPDATE por id."""

def set_active_task(task_id: str) -> Task:
    """UPDATE is_active=true (trigger desactiva las demás). Retorna la tarea actualizada."""

def resolve_assignees(emails: list[str]) -> list[str]:
    """Convierte lista de emails en lista de profile.id (uuids).
    Si algún email no existe en profiles → AdminError listando los que faltan."""

def task_to_markdown(task: Task, profiles_by_id: dict[str, Profile]) -> str:
    """Serializa una tarea a '---\\nYAML\\n---\\n# Contexto\\n...' para abrirla en el editor.
    Convierte assignees uuid → emails usando el dict."""

def markdown_to_task_fields(md: str) -> dict:
    """Inversa: parsea un markdown con frontmatter a dict listo para upsert.
    NO resuelve emails → ids (eso lo hace el caller con resolve_assignees)."""
```

Excepciones: `AdminError(Exception)`, `PermissionError` (reusa la stdlib o define propia — tu call, documéntalo).

### Template inicial para `minirick new`

Cuando no hay contenido previo, `open_in_editor` recibe este template:

```markdown
---
title: Título de la tarea
status: todo
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
```

Si el body queda vacío o igual al template sin cambios reales, aborta con mensaje "Tarea vacía, no se creó nada."

---

## Sub-fase C — Modificaciones a archivos existentes

### `src/minirick/models.py`

Agregar campo a `Task`:

```python
assignees: list[str] = field(default_factory=list)   # lista de uuids
```

En `from_dict`: leer `data.get("assignees") or []`.
En `to_dict`: incluir `"assignees": self.assignees`.

Los tests existentes (`test_models.py`) deben seguir pasando. Agrega 1-2 tests nuevos para el campo assignees.

### `src/minirick/cli.py`

Los comandos `new`, `edit`, `set-active` ya no son stubs. Firmas:

```python
@app.command()
def new() -> None: ...

@app.command()
def edit(task_id: str = typer.Argument(...)) -> None: ...

@app.command(name="set-active")
def set_active(
    task_id: str = typer.Argument(...),
    assignees: str | None = typer.Option(None, "--assignees", "-a", help="Emails separados por coma. Vacío = todos."),
) -> None: ...
```

`set-active` con `--assignees`: parsea CSV, llama `resolve_assignees`, hace UPDATE combinado (is_active=true + assignees=[...]) en una sola llamada. Sin flag: solo activa, no toca assignees.

Todos los errores (AuthError, AdminError, PermissionError, FrontmatterError, EditorError, APIError) → mensaje Rich en español + `raise typer.Exit(1)`. NUNCA traceback crudo.

### Dashboard — panel admin

Agregar al dashboard existente. Archivos:

- `src/minirick/dashboard/api.py` — expón nuevos métodos al JS:
  - `list_profiles()` → lista de `{id, email, name, role}`.
  - `list_all_tasks()` → todas las tareas (admin ve todas, collab ve las suyas, la RLS decide).
  - `set_task_active(task_id, assignee_emails)` → wrapper sobre `set_active_task` + resolución de emails.
  - `update_task_assignees(task_id, assignee_emails)` → actualiza solo assignees sin cambiar is_active.
  - Todos retornan `{"ok": bool, "error": str | None, "data": ...}` — no lances excepciones al JS.
- `src/minirick/dashboard/ui/index.html` — añade un contenedor oculto `<section id="admin-panel" hidden>` con:
  - Heading `> ADMIN PANEL` (estilo verde retro consistente).
  - Lista de tareas (todas las que ve el usuario) con título, estado, botón `[activar]` y multiselect de colabs.
  - Debajo: selector visual de colabs (checkbox list con los profiles del equipo).
  - Botón cerrar `[x]` que vuelve a la vista normal.
- `src/minirick/dashboard/ui/app.js` — el botón ⚙ existente ahora alterna `admin-panel` visible/oculto. Al abrirlo, `pywebview.api.list_profiles()` + `list_all_tasks()`. Al clickear `[activar]` en una tarea, se pasan los emails checkeados al bridge.
- `src/minirick/dashboard/ui/styles.css` — reutiliza vars existentes (`--green-primary`, `--green-dim`, etc.). Añade estilos para `.admin-panel`, `.admin-task-row`, `.assignee-checkbox`. NO rompas layout horizontal 900×560 existente.

**Restricciones UI**:
- Solo mostrar el botón ⚙ si el profile actual tiene rol admin u owner. Collabs no lo ven.
- El panel admin es un overlay/modal dentro de la ventana actual, no una ventana nueva de pywebview.
- Si `list_profiles()` falla (RLS rechaza al collab), el JS muestra un placeholder "No tienes permiso" y listo.

---

## Sub-fase D — Tests

Crear tests que NO toquen Supabase real. Usa `unittest.mock`.

- `tests/test_frontmatter.py` — 4-6 tests: roundtrip, documento sin frontmatter, YAML inválido (lanza FrontmatterError), unicode en valores, lista de tools se preserva.
- `tests/test_editor.py` — 3-4 tests con mock de `subprocess.run` y `tempfile`: $EDITOR override, fallback notepad en Windows, fallback `open -t -W` en macOS, cleanup del temp file.
- `tests/test_admin.py` — 6-8 tests con mock de `get_client()`:
  - `create_task` llama `.table("tasks").insert(...).execute()` con payload correcto.
  - `update_task` llama `.update(...).eq("id", task_id).execute()`.
  - `set_active_task` manda `is_active=True`.
  - `resolve_assignees` con emails válidos retorna uuids.
  - `resolve_assignees` con email inexistente lanza `AdminError` mencionando el email faltante.
  - `require_admin` rechaza si el profile tiene `role=collaborator`.
  - `task_to_markdown` + `markdown_to_task_fields` roundtrip preserva título, status, tools, assignees.
- `tests/test_cli_admin.py` — 3-4 tests con `CliRunner` y mocks:
  - `minirick new` con mock de `open_in_editor` retornando markdown válido → llama `create_task`.
  - `minirick edit <id>` baja, abre, sube.
  - `minirick set-active <id> --assignees a@b.co,c@d.co` resuelve emails y llama update.
  - `minirick new` sin sesión → mensaje "Inicia sesión con minirick login" y exit 1.

Meta: **pasar de 58 a ≥72 tests** con todo verde.

---

## Sub-fase E — Dependencia nueva

En `pyproject.toml`, bloque `dependencies`, agrega:

```
"pyyaml>=6.0",
```

Deja el resto igual. Corre `pip install -e ".[dev]"` después de editar. Verifica con `python -c "import yaml; print(yaml.__version__)"`.

---

## Checklist final (antes de reportar "listo")

Corre esto en PowerShell desde la raíz del repo y confirma cada línea. NO hagas commit, NO corras `minirick`.

```powershell
# 1. Archivos nuevos existen y no están vacíos
foreach ($f in @(
  "src\minirick\frontmatter.py",
  "src\minirick\editor.py",
  "src\minirick\admin.py",
  "tests\test_frontmatter.py",
  "tests\test_editor.py",
  "tests\test_admin.py",
  "tests\test_cli_admin.py"
)) {
  if (Test-Path $f) {
    $size = (Get-Item $f).Length
    Write-Host "$f → $size bytes"
  } else {
    Write-Host "FALTA: $f" -ForegroundColor Red
  }
}

# 2. Patterns clave en archivos
Select-String -Path src\minirick\frontmatter.py -Pattern "yaml.safe_load"
Select-String -Path src\minirick\editor.py -Pattern "shlex.split"
Select-String -Path src\minirick\admin.py -Pattern "def require_admin"
Select-String -Path src\minirick\admin.py -Pattern "def resolve_assignees"
Select-String -Path src\minirick\cli.py -Pattern "open_in_editor"
Select-String -Path src\minirick\models.py -Pattern "assignees"
Select-String -Path pyproject.toml -Pattern "pyyaml"

# 3. Dashboard
Select-String -Path src\minirick\dashboard\api.py -Pattern "list_profiles"
Select-String -Path src\minirick\dashboard\api.py -Pattern "set_task_active"
Select-String -Path src\minirick\dashboard\ui\index.html -Pattern "admin-panel"
Select-String -Path src\minirick\dashboard\ui\app.js -Pattern "list_profiles"

# 4. Pytest verde
.venv\Scripts\python.exe -m pytest -q
# Esperado: ≥72 passed, 0 failed

# 5. Ruff limpio
.venv\Scripts\python.exe -m ruff check src/ tests/
# Esperado: All checks passed

# 6. Instalación de pyyaml verificable
.venv\Scripts\python.exe -c "import yaml; print('pyyaml', yaml.__version__)"

# 7. Confirmación de NO side effects
# NO debe existir tarea nueva en Supabase creada por ti.
# NO debe haber commits nuevos en git log.
git status
# Esperado: modificaciones staged/unstaged pero SIN commits.
```

---

## Reporte final esperado

Cuando termines, pégame en el chat:

1. Output completo del checklist de arriba.
2. SQL exacto del migration (copiado del punto 5 de la Regla 0, sin cambios).
3. Lista de nuevos tests con nombre y qué verifica cada uno (una línea c/u).
4. Screenshots/pegados de las líneas clave de `index.html` nuevo (sección `admin-panel`) y de `app.js` (handler del botón ⚙).
5. Confirmación explícita: "No corrí `minirick new`, `minirick edit`, ni abrí el dashboard."

Yo corro el SQL en Supabase, luego pruebo en vivo. Si algo falla en vivo, te reporto y lo arreglamos con un patch quirúrgico — no rehagas la fase.

---

## Qué NO hacer en esta fase (importante)

- NO implementar invitaciones de usuarios (eso es 5.2 con Edge Function).
- NO tocar `launcher.py`, `auth.py`, `db.py`, `config.py`.
- NO cambiar la paleta de colores del dashboard ni el layout 900×560 horizontal.
- NO agregar otra librería más allá de PyYAML.
- NO escribir lógica de "una sola activa" en Python — el trigger de Postgres ya lo hace.
- NO hacer commits. NO push. NO correr `minirick` en vivo.
- NO crear Edge Functions todavía.
- NO alterar las policies RLS de INSERT/UPDATE/DELETE de `tasks`, solo la de SELECT.
