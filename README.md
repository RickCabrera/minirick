# minirick

> Copiloto de terminal con contexto compartido para el equipo.

`minirick` es una herramienta de terminal que al ejecutarla te muestra un
pequeño dashboard flotante con la tarea activa del equipo, el contexto que
estamos usando, y abre automáticamente las herramientas que necesitas para
trabajar (editor, repo, notas, etc.).

---

## Instalación

### 1. Instala Python (si no lo tienes)

Necesitas **Python 3.10 o superior**.

- **Windows**: descarga desde [python.org](https://www.python.org/downloads/).
  ⚠️ Durante la instalación, **marca la casilla "Add Python to PATH"** o no
  funcionará.
- **macOS**: abre Terminal y corre:
  ```bash
  brew install python@3.12
  ```
  (Si no tienes Homebrew, instálalo desde [brew.sh](https://brew.sh) primero.)

Verifica que funciona:
```bash
python --version
```
Debería decir algo como `Python 3.12.x`. En Mac puede ser `python3 --version`.

### 2. Instala pipx

`pipx` instala aplicaciones de Python de forma aislada (así no rompes nada).

- **Windows**: en PowerShell:
  ```powershell
  python -m pip install --user pipx
  python -m pipx ensurepath
  ```
  Cierra y vuelve a abrir PowerShell.

- **macOS**:
  ```bash
  brew install pipx
  pipx ensurepath
  ```

### 3. Instala minirick

```bash
pipx install minirick
```

Verifica:
```bash
minirick version
```

### 4. Inicia sesión

```bash
minirick login
```

Te va a pedir tu email. Recibirás en segundos un **código de 6 dígitos** en tu
correo. Copia el código y pégalo en la terminal cuando lo pida.

Si prefieres un solo paso:

```bash
minirick login --email tucorreo@empresa.com
```

Para cerrar sesión:

```bash
minirick logout
```

---

## Uso diario

```bash
minirick              # Abre el dashboard con la tarea activa (Fase 3)
minirick list         # Lista todas las tareas desde Supabase
minirick sync         # Refresca el cache local desde el servidor
minirick --help       # Ver todos los comandos
```

`minirick list` trae las tareas vivas del equipo ordenadas por última
modificación. `minirick sync` hace lo mismo pero además deja una copia local en
`~/Library/Application Support/minirick/cache/tasks.json` (Mac) o
`%LOCALAPPDATA%\minirick\cache\tasks.json` (Windows) para uso offline del
dashboard.

---

## Solo para admins

```bash
minirick new                # Crear nueva tarea
minirick edit <id>          # Editar tarea existente
minirick set-active <id>    # Marcar una tarea como activa del equipo
```

---

## Problemas comunes

**"comando no encontrado: minirick"** (o `minirick: command not found`)
Corre `pipx ensurepath`, cierra la terminal y vuélvela a abrir.

**"Python no se reconoce como un comando"** (Windows)
Reinstala Python marcando "Add Python to PATH".

**No me llega el código de login**
Revisa spam. Si no aparece en 2 minutos, dile al admin (Rick) que te reenvíe la
invitación.

**"No hay sesión activa"** al correr `list` o `sync`
Corre `minirick login` primero. Si ya lo hiciste y sigue fallando, tu sesión
pudo haber expirado — repite el login.
