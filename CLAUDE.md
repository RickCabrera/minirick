# CLAUDE.md — Contexto del proyecto para Claude Code

> Este archivo le da contexto a Claude Code sobre el proyecto `minirick`.
> Si estás leyendo esto como Claude, **lee TODO este archivo antes de hacer cualquier cosa**.

---

## ¿Qué es minirick?

Un **copiloto de terminal con contexto compartido** para un equipo de trabajo.

El flujo:
1. Un **admin** define una tarea desde su terminal: título, resumen, contexto en markdown, y qué herramientas se deben abrir (editor, repo, navegador, etc.). Eso se sube a Supabase.
2. Un **colaborador** corre `minirick` en su terminal → se abre un dashboard GUI flotante pequeño que le muestra la tarea activa + contexto → se lanzan automáticamente las herramientas configuradas.
3. El dashboard queda flotando como guía visual mientras trabaja.

**NO es** un show off de Jarvis. Es una herramienta real para compañeros no muy técnicos que necesitan un copiloto simple.

---

## Stack

| Componente | Tecnología | Por qué |
|---|---|---|
| CLI | Python 3.10+ con **Typer** | Autogenera help bonito, type hints |
| Output bonito en terminal | **Rich** | Panels, colores, tablas |
| Dashboard GUI flotante | **pywebview** | WebView nativo Mac/Windows, HTML/CSS/JS adentro |
| Backend | **Supabase** (Postgres + Auth + Storage) | Plan Free alcanza, RLS nativa |
| Auth | Supabase magic link (email) | Colabs no recuerdan passwords |
| Config local | `platformdirs` + TOML | Cross-platform paths |
| Distribución | **pipx** | Instalación aislada, un solo comando |

**Público objetivo**: compañeros no técnicos. La instalación tiene que ser a prueba de balas.

**Sistemas operativos**: Mezcla Mac + Windows. **Linux NO es target** (pero el código es portable).

---

## Credenciales de Supabase

Proyecto: `minirick` (spacecabra's Org, plan Free, región us-east-2 Ohio).

- **URL**: `https://ijpwjxujbckmvvdxbmjw.supabase.co`
- **Publishable key (anon)**: `sb_publishable_Pmj2sW2dmcvln4-sBixDYA_cGjaGHIl`
- **Service role key**: NO está aquí. Solo en el dashboard de Supabase. NUNCA la metas en el código de cliente.

Las credenciales anon son **seguras de embeder** en el código porque las tablas tienen RLS. Aun así, se pueden override vía `.env` (ver `.env.example`).

---

## Modelo de datos (ya creado en Supabase)

### Tabla `profiles`
Extiende `auth.users` con rol y nombre. Se crea automáticamente vía trigger cuando un usuario se registra.

```
id          uuid PK (FK a auth.users, cascade delete)
email       text unique
name        text
role        text  -- 'owner' | 'admin' | 'collaborator' (default)
created_at  timestamptz
updated_at  timestamptz  -- trigger auto-update
```

### Tabla `tasks`

```
id           uuid PK
title        text
summary      text            -- corto, para el dashboard
context_md   text            -- markdown completo
tools        jsonb           -- array de objetos tool (ver abajo)
status       text            -- 'todo' | 'in_progress' | 'done'
is_active    boolean         -- solo UNA tarea puede ser active (enforced por trigger)
created_by   uuid FK profiles
updated_by   uuid FK profiles
created_at   timestamptz
updated_at   timestamptz     -- trigger auto-update
```

### Modelo de `tool` (objetos dentro del array `tools` de una task)

```python
{"type": "claude_code", "path": "~/repos/pagos"}
{"type": "vscode", "path": "~/repos/pagos"}
{"type": "browser", "url": "https://github.com/org/repo/pull/42"}
{"type": "file", "path": "~/notas/task.md"}
{"type": "notepad", "content": "Texto a mostrar en bloc de notas"}
{"type": "terminal", "cwd": "~/repos/pagos", "command": "npm run dev"}
```

El `launcher.py` (Fase 4) mapeará cada tipo a un comando de sistema según el SO.

---

## Roles y políticas RLS (ya aplicadas)

| Rol | Lee tareas | Crea/edita/borra | Invita colabs | Cambia roles |
|---|---|---|---|---|
| `owner` | ✅ | ✅ | ✅ | ✅ |
| `admin` | ✅ | ✅ | ✅ | ❌ |
| `collaborator` | ✅ | ❌ | ❌ | ❌ |

- **Owner** es único y no se puede remover vía app (evita quedarte sin acceso a tu propia DB).
- Todo usuario nuevo nace como `collaborator`. Para promover a admin u owner: UPDATE directo a `profiles.role` (solo owner puede, via RLS).
- Funciones helper Postgres disponibles: `public.is_admin_or_owner()`, `public.is_owner()`.

---

## Plan de fases

### ✅ Fase 1 — Esqueleto + CLI (COMPLETADA)
- `pyproject.toml` con entry point `minirick = "minirick.cli:app"`.
- Estructura `src/minirick/` con `__init__`, `cli.py`, `config.py`.
- Comandos registrados como placeholders: `version`, `login`, `logout`, `list`, `new`, `edit`, `set-active`, `sync`.
- Instalable con `pipx install .` o `pip install -e .` para dev.
- **Probado**: `minirick version`, `minirick --help`, `minirick` (raíz) todos funcionan.

### ⏳ Fase 2 — Supabase + Auth (SIGUIENTE)
Implementar:
- `src/minirick/db.py` — cliente Supabase singleton usando URL + anon key.
- `src/minirick/auth.py` — `login` con magic link (OTP via email usando `supabase.auth.sign_in_with_otp({"email": ...})`), persistir sesión en `get_session_file()` (ya definido en `config.py`).
- `src/minirick/models.py` — dataclasses `Task`, `Tool`, `Profile`.
- Actualizar `cli.py`:
  - `minirick login` — pide email, manda OTP, pide código de 6 dígitos, guarda sesión.
  - `minirick logout` — borra `session.json`.
  - `minirick list` — query `SELECT * FROM tasks ORDER BY updated_at DESC`, imprime con Rich Table.
  - `minirick sync` — por ahora solo re-jala tareas y las cachea localmente en `get_cache_dir() / "tasks.json"`.
- Al final de esta fase: que Rick haga su primer login, luego corra este SQL en Supabase para promoverse:
  ```sql
  update public.profiles set role = 'owner' where email = 'EMAIL_DE_RICK';
  ```

### ⏳ Fase 3 — Dashboard GUI flotante (pywebview)
- `src/minirick/dashboard/window.py` — crea ventana pywebview: ~400x600px, sin bordes, always-on-top, posicionada esquina superior derecha.
- `src/minirick/dashboard/ui/` — `index.html`, `styles.css`, `app.js`. Tema oscuro, tipografía limpia, sin dependencias externas.
- `src/minirick/dashboard/api.py` — bridge Python↔JS: expone métodos como `get_active_task()`, `refresh()`, `open_tool(tool_id)`.
- Layout del dashboard:
  - Header: nombre app + botón ⚙️ (configuración, queda stub para Fase 5) + botón X (cerrar).
  - Sección "Tarea activa": título grande, status badge, resumen.
  - Sección "Contexto": render básico del markdown (puede ser `<pre>` simple al inicio).
  - Sección "Herramientas": lista de tools con icono + nombre + botón "Abrir" (stub, lanza en Fase 4).
- Solo lectura al principio.

### ⏳ Fase 4 — Launcher de herramientas
- `src/minirick/launcher.py` — dispatcher por `tool.type` con branches Mac/Windows.
- Detectar SO con `platform.system()`.
- Mapeos:
  - `claude_code` → `claude` en PATH (validar antes) con `cwd=tool.path`.
  - `vscode` → `code <path>`.
  - `browser` → `open <url>` (Mac) / `start <url>` (Win).
  - `file` → abrir con app default del sistema.
  - `notepad` → crear temp file con contenido y abrir.
  - `terminal` → nueva ventana de terminal con `cwd` y opcionalmente corriendo `command`.
- Al correr `minirick` (sin subcomando): primero abre dashboard, luego lanza tools de la tarea activa en paralelo.

### ⏳ Fase 5 — Admin panel (CRUD + invitaciones)
- `minirick new` → abre editor ($EDITOR o notepad/TextEdit) con template markdown precargado, parsea frontmatter YAML para metadata, sube a Supabase.
- `minirick edit <id>` → descarga, abre editor, sube cambios.
- `minirick set-active <id>` → UPDATE `is_active=true` (el trigger se encarga de desactivar las otras).
- Botón ⚙️ del dashboard → vista de configuración con:
  - Lista de usuarios + sus roles (solo owner puede editar).
  - Input para invitar colab por email.
- **Invitaciones requieren Edge Function** (porque solo `service_role` puede invitar): crear `supabase/functions/invite-user/index.ts` que recibe `{email}` y llama a `supabase.auth.admin.inviteUserByEmail()`. Autorizar solo si el caller es admin/owner.

### ⏳ Fase 6 — Empaquetado y distribución
- Publicar en PyPI o GitHub release.
- README con screenshots y troubleshooting.
- Script one-shot de instalación (PowerShell para Windows, bash para Mac).

---

## Decisiones tomadas (no re-discutir sin razón fuerte)

1. **Supabase > Firebase**: SDK Python más limpio, RLS nativa, Postgres real.
2. **pywebview > Tkinter/Textual**: se ve más profesional en Mac/Windows, el cliente final es un "dashboard" no una TUI.
3. **pipx > pip global**: aislamiento, no contamina el Python del sistema del colab.
4. **Magic link OTP > password**: los colabs no recuerdan passwords.
5. **Owner role inmutable desde app**: Rick siempre mantiene acceso aunque un admin se equivoque.
6. **Una sola tarea activa**: enforced a nivel DB con trigger, no lógica de app.
7. **Invitaciones vía Edge Function (Fase 5)**: `service_role` jamás en cliente.
8. **NO v1**: tracking de tiempo, chat, historial estilo git, activación por voz, real-time websockets. Todo eso es v2+.

---

## Cosas que el sistema **NO** hace (para no confundirse)

- No sincroniza archivos locales del colaborador con otros colabs.
- No ejecuta código arbitrario del admin en la máquina del colab automáticamente (las `tools` abren apps estándar, no corren scripts opacos).
- No tiene notificaciones push.
- No tiene chat interno.
- No edita código por ti — solo muestra contexto y lanza herramientas.

---

## Convenciones de código

- Python 3.10+ (usa type hints modernos: `list[str]`, `dict[str, Any]`, `X | None`).
- `from __future__ import annotations` en todos los módulos.
- Ruff con config en `pyproject.toml` (line-length 100).
- Docstrings cortos en español, código (nombres) en inglés.
- Mensajes al usuario final en **español** (es el idioma del equipo de Rick).
- Usar `rich.console.Console` para toda la salida de terminal — nunca `print()` crudo.
- Errores de Supabase: capturar `postgrest.exceptions.APIError` y mostrar mensaje amigable con Rich, nunca traceback crudo al usuario.

---

## Paths importantes

```
<config_dir>/         # via platformdirs.user_data_dir("minirick")
├── config.toml       # config del usuario
├── session.json      # tokens de Supabase (jwt + refresh)
└── cache/
    └── tasks.json    # cache de tareas
```

- Mac: `~/Library/Application Support/minirick/`
- Windows: `C:\Users\<user>\AppData\Local\minirick\`

Helpers ya implementados en `src/minirick/config.py`:
- `get_config_dir()`, `get_config_file()`, `get_session_file()`, `get_cache_dir()`.

---

## Cómo correr el proyecto en dev

```bash
# Windows (PowerShell):
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"

# macOS:
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Probar:
minirick version
minirick --help
minirick
```

## Cómo correr tests (cuando existan)

```bash
pytest
```

## Lint

```bash
ruff check .
ruff format .
```

---

## Si eres Claude Code retomando este proyecto

1. **Lee este archivo completo.** En serio. Aquí está todo.
2. **Verifica en qué fase estás** revisando qué archivos existen en `src/minirick/`:
   - Si solo hay `__init__.py`, `cli.py`, `config.py` → estás entrando a Fase 2.
   - Si hay `db.py`, `auth.py`, `models.py` → estás entrando a Fase 3.
   - Y así sucesivamente.
3. **Antes de implementar algo nuevo**, corre `minirick --help` y `pytest` para confirmar que el estado actual está sano.
4. **No inventes features**. Apégate a las fases de arriba. Si Rick pide algo fuera del scope, pregúntale si es para v1 o v2.
5. **Credenciales**: la URL y publishable key son públicas (protegidas por RLS). Puedes embederlas como default en `db.py` y dejar override vía env vars.
6. **Mensajes al usuario siempre en español**. Código en inglés.
7. **Idiomas de los commits**: libres, pero preferir español para continuidad con Rick.
