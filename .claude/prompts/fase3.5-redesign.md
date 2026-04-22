# Fase 3.5 — Rediseño horizontal del dashboard

> Reestructuración del layout del dashboard: de vertical 380×620 a horizontal 900×560 con sidebar colapsable + layout de 2 columnas asimétricas + contexto a lo ancho abajo.
>
> **NO se tocan features funcionales.** No se añaden files (eso es Fase 4.5). Solo se reorganiza el layout existente.

---

## Regla 0 — Antes de escribir código

Responde con:

1. La lista exacta de archivos que VAS a modificar (deben ser 3 archivos UI + 1 archivo Python).
2. La lista exacta de archivos que NO vas a tocar.
3. Confirmación de que después de cada archivo modificado vas a verificar con Test-Path y tamaño > 0 antes de seguir.
4. El nuevo tamaño de ventana (valores exactos de width y height).

Si no puedes listarlos, relee este archivo.

---

## Estado actual (confirmado)

El dashboard funciona correctamente. Los 41 tests pasan. La estética verde-retro está bien implementada. Solo falta reorganizar el layout y ajustar el pulido visual que pidió el usuario.

**Archivos que existen y trabajaremos:**
- `src/minirick/dashboard/window.py` — cambiar dimensiones.
- `src/minirick/dashboard/ui/index.html` — nueva estructura de layout.
- `src/minirick/dashboard/ui/styles.css` — reescribir layout manteniendo paleta y efectos visuales.
- `src/minirick/dashboard/ui/app.js` — añadir toggle de sidebar, ajustar referencias si cambian IDs.

**Archivos que NO se tocan:**
- `src/minirick/dashboard/api.py`
- `src/minirick/dashboard/service.py`
- `src/minirick/dashboard/__init__.py`
- `src/minirick/cli.py`
- Toda la capa de models, auth, db, config.
- Ningún test.

---

## Cambio 1 — Dimensiones de ventana

En `src/minirick/dashboard/window.py`:

```python
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 560
```

Todo lo demás (`frameless`, `on_top`, `resizable=False`, `easy_drag=False`, posicionamiento top-right) se mantiene igual.

Ajusta también la función `_position_top_right` si es necesario — debe seguir poniéndola en la esquina superior derecha tomando en cuenta los 900px de ancho nuevos.

---

## Cambio 2 — Nuevo layout en `index.html`

El layout cambia radicalmente. Estructura nueva:

```
┌──────┬───────────────────────────────────────────────┐
│      │                                  [─][⚙][✕]    │  .window-controls (top-right, floating)
│ AVA  │                                                │
│      │ ┌─────────────────────────┬──────────────────┐│
│      │ │ > ACTIVE TASK           │ > TOOLS (N)      ││
│ SIDE │ │ Título tarea            │ [>] vscode ...   ││
│      │ │ [status]                │ [>] browser ...  ││
│      │ │ Summary: ...            │ [>] terminal ... ││
│      │ └─────────────────────────┴──────────────────┘│
│      │ ┌───────────────────────────────────────────┐│
│      │ │ > CONTEXT                                  ││
│ CFG  │ │ (markdown a lo ancho completo)             ││
│      │ │                                            ││
└──────┴───────────────────────────────────────────────┘
│ pingcabra@gmail.com · owner                           │  .footer
└────────────────────────────────────────────────────────┘
```

### Sidebar izquierda

Ancho cuando expandido: **56px**. Cuando colapsado: **0px** (totalmente oculta).

Botón toggle de sidebar: un pequeño ícono `[<]` / `[>]` flotando en el borde derecho de la sidebar (o en la esquina superior izquierda del área principal cuando colapsada). Usa `◀` / `▶` como símbolos.

Iconos en la sidebar, en orden:
- **Arriba**: avatar del usuario — ícono `👤` o una `<div>` con borde verde circular conteniendo las iniciales del email (primera letra del local-part). Al hacer click: toast con info del usuario (`{email} · {role}`).
- **Abajo**: engranaje `⚙` — al hacer click: llama a `open_config()` (stub de Fase 5 existente).

Ambos iconos centrados horizontalmente en la sidebar, uno arriba pegado al top (+padding 12px) y el otro abajo pegado al bottom (+padding 12px). Entre ellos, espacio vacío.

### Window controls (top-right)

Flotando en la esquina superior derecha del área principal (no en la sidebar). Botones `─ ⚙ ✕` con el MISMO estilo que tenían antes.

**Importante**: el botón ⚙ del header se QUEDA donde está (no se duplica con el de la sidebar). El de la sidebar es redundante pero el usuario lo pidió explícitamente así. Mantén AMBOS. El del sidebar también abre config.

En realidad re-leyendo — para evitar redundancia y dado que el usuario pidió sidebar con 2 iconos (avatar + config): **elimina el botón ⚙ del header superior**. El header superior queda solo con: minimizar `─` y cerrar `✕`. Config se accede solo desde la sidebar.

### Área principal — grid de 2 filas

**Fila superior (altura flexible)**: grid de 2 columnas asimétricas.
- Columna izquierda: `grid-template-columns: 65fr 35fr` = `> ACTIVE TASK` + badge + summary.
- Columna derecha: `> TOOLS (N)` con la lista.

**Fila inferior (altura flexible)**: `> CONTEXT` ocupando todo el ancho.

Ambas filas tienen scroll interno si el contenido desborda — NO scroll en la ventana completa.

### Estructura HTML sugerida

```html
<body>
  <div class="app">
    <aside class="sidebar" id="sidebar">
      <button class="sidebar-btn sidebar-avatar" id="btn-avatar" title="Usuario">
        <span id="avatar-initial">?</span>
      </button>
      <button class="sidebar-btn sidebar-config" id="btn-config-side" title="Configuración">⚙</button>
    </aside>

    <button class="sidebar-toggle" id="sidebar-toggle" title="Ocultar sidebar">◀</button>

    <main class="main-area">
      <div class="window-controls">
        <button id="btn-minimize" title="Minimizar">_</button>
        <button id="btn-close" title="Cerrar">✕</button>
      </div>

      <!-- 4 estados (loading, error, empty, task) tal como están -->
      <section id="state-loading" class="state">...</section>
      <section id="state-error" class="state" hidden>...</section>
      <section id="state-empty" class="state" hidden>...</section>

      <section id="state-task" hidden>
        <div class="grid-top">
          <div class="panel panel-task">
            <div class="section-header">ACTIVE TASK</div>
            <div class="task-title" id="task-title"></div>
            <div class="status-badge" id="task-status"></div>
            <div class="section-subheader">SUMMARY</div>
            <div class="task-summary" id="task-summary"></div>
          </div>

          <div class="panel panel-tools">
            <div class="section-header collapsible" data-target="task-tools">
              <span class="section-header-label">TOOLS (<span id="tools-count">0</span>)</span>
              <span class="collapse-indicator">▾</span>
            </div>
            <div class="task-tools" id="task-tools"></div>
          </div>
        </div>

        <div class="panel panel-context">
          <div class="section-header collapsible" data-target="task-context">
            <span class="section-header-label">CONTEXT</span>
            <span class="collapse-indicator">▾</span>
          </div>
          <div class="task-context" id="task-context"></div>
        </div>
      </section>
    </main>
  </div>

  <footer class="footer" id="footer">
    <span id="footer-profile">
      <span class="footer-email" id="footer-email"></span>
      <span class="footer-bullet"> · </span>
      <span class="footer-role" id="footer-role"></span>
    </span>
  </footer>

  <div id="toast" class="toast hidden"></div>
</body>
```

---

## Cambio 3 — Reescritura de `styles.css`

### Paleta y efectos visuales — INTACTOS

- Todas las variables de `:root` se mantienen exactamente igual.
- Scanlines CRT: igual.
- Blinking cursor: igual.
- Glow verde en el borde: igual.
- Hover `[>]` → `[#]` en tools: igual.
- Status badges: iguales (colores por estado).
- Scrollbar custom: igual.
- `[hidden] { display: none !important; }` se mantiene.

### Layout — nuevo

```css
html, body {
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  overflow: hidden;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--mono);
  font-size: 13px;
  border: 1px solid var(--green-faint);
  box-shadow: 0 0 20px rgba(0, 255, 136, 0.15), inset 0 0 60px rgba(0, 255, 136, 0.03);
  display: flex;
  flex-direction: column;
}

.app {
  display: grid;
  grid-template-columns: 56px 1fr;
  flex: 1;
  min-height: 0;
  position: relative;
  transition: grid-template-columns 180ms ease;
}

.app.sidebar-collapsed {
  grid-template-columns: 0 1fr;
}

.sidebar {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-right: 1px solid var(--green-faint);
  overflow: hidden;
  background: var(--bg-elev);
}

.app.sidebar-collapsed .sidebar {
  border-right: none;
}

.sidebar-btn {
  width: 36px;
  height: 36px;
  background: transparent;
  border: 1px solid var(--green-faint);
  color: var(--green-primary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--mono);
  font-size: 14px;
  border-radius: 50%;
  transition: background 120ms, color 120ms, border-color 120ms;
}

.sidebar-btn:hover {
  background: var(--green-faint);
  color: var(--green-accent);
  border-color: var(--green-accent);
}

.sidebar-avatar {
  font-weight: 700;
  text-transform: uppercase;
}

.sidebar-toggle {
  position: absolute;
  top: 50%;
  left: 56px;
  transform: translate(-50%, -50%);
  width: 18px;
  height: 40px;
  background: var(--bg-elev);
  color: var(--green-dim);
  border: 1px solid var(--green-faint);
  cursor: pointer;
  font-family: var(--mono);
  font-size: 10px;
  z-index: 10;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: left 180ms ease, color 120ms;
}

.sidebar-toggle:hover {
  color: var(--green-accent);
}

.app.sidebar-collapsed .sidebar-toggle {
  left: 0;
}

.main-area {
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* header draggable — cubre toda el área menos los botones */
.main-area::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 32px;
  -webkit-app-region: drag;
  pointer-events: none;
  z-index: 1;
}

.window-controls {
  position: absolute;
  top: 8px;
  right: 10px;
  display: flex;
  gap: 6px;
  z-index: 5;
  -webkit-app-region: no-drag;
}

.window-controls button {
  width: 24px;
  height: 24px;
  background: transparent;
  border: 1px solid var(--green-faint);
  color: var(--green-dim);
  cursor: pointer;
  font-family: var(--mono);
  font-size: 12px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.window-controls button:hover {
  background: var(--green-faint);
  color: var(--green-accent);
  border-color: var(--green-accent);
}

/* Task state grid */
#state-task {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 36px 14px 14px; /* top padding accounts for window-controls */
  gap: 10px;
  overflow: hidden;
}

.grid-top {
  display: grid;
  grid-template-columns: 65fr 35fr;
  gap: 10px;
  min-height: 0;
  flex: 1 1 auto;
}

.panel {
  border: 1px solid var(--green-faint);
  background: var(--bg);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.panel-context {
  flex: 1 1 auto;
  min-height: 0;
}

.panel-task,
.panel-tools {
  overflow-y: auto;
}

.task-context {
  overflow-y: auto;
  flex: 1;
  padding-top: 6px;
}

.task-tools {
  overflow-y: auto;
  flex: 1;
  padding-top: 6px;
}

/* Section headers — ahora con prefijo > pegado al label */
.section-header,
.section-subheader {
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--green-primary);
  padding: 0 0 6px 0;
  display: flex;
  align-items: center;
  gap: 8px;
  user-select: none;
  border-bottom: 1px solid var(--green-faint);
  margin-bottom: 6px;
}

.section-header::before,
.section-subheader::before {
  content: '> ';
  color: var(--green-primary);
}

.section-subheader {
  margin-top: 10px;
  font-size: 10px;
  color: var(--green-dim);
  border-bottom-color: transparent;
}

.section-header.collapsible {
  cursor: pointer;
  justify-content: space-between;
}

.section-header.collapsible .collapse-indicator {
  font-size: 10px;
  color: var(--green-dim);
}

.section-header.collapsible:hover .collapse-indicator {
  color: var(--green-accent);
}

/* Estados */
.state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 24px;
  text-align: center;
}

.state-msg {
  color: var(--green-primary);
  font-size: 14px;
  margin-bottom: 8px;
}

.state-msg-error {
  color: var(--red);
}

.state-hint {
  color: var(--text-dim);
  font-size: 12px;
}

/* Footer */
.footer {
  height: 26px;
  border-top: 1px solid var(--green-faint);
  padding: 0 14px;
  display: flex;
  align-items: center;
  font-size: 11px;
  color: var(--text-dim);
  background: var(--bg-elev);
}

.footer-bullet {
  color: var(--green-dim);
}

/* Task content styling */
.task-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--green-primary);
  margin-bottom: 6px;
  line-height: 1.3;
}

.task-summary {
  font-size: 13px;
  color: var(--text);
  line-height: 1.4;
  white-space: pre-wrap;
}

.status-badge {
  font-family: var(--mono);
  font-size: 11px;
  display: inline-block;
  margin-bottom: 8px;
}

.status-todo        { color: var(--gray); }
.status-in_progress { color: var(--yellow); }
.status-done        { color: var(--green-primary); }

/* Tools list */
.tool {
  padding: 5px 10px;
  border-left: 2px solid transparent;
  display: flex;
  flex-direction: column;
  gap: 1px;
  font-size: 12px;
  cursor: pointer;
  transition: background 100ms, border-left-color 100ms;
}

.tool::before {
  content: '[>] ';
  color: var(--green-dim);
}

.tool:hover::before {
  content: '[#] ';
  color: var(--green-accent);
}

.tool:hover {
  background: var(--green-faint);
  border-left-color: var(--green-accent);
}

.tool-type {
  color: var(--green-primary);
  font-weight: 500;
}

.tool-detail {
  color: var(--text-dim);
  font-size: 11px;
  padding-left: 20px;
  word-break: break-all;
}

/* Markdown inside context */
.task-context h1, .task-context h2, .task-context h3 {
  color: var(--green-primary);
  font-size: 13px;
  margin: 6px 0 4px;
}
.task-context p { margin: 4px 0; font-size: 12px; line-height: 1.5; }
.task-context ul, .task-context ol { margin: 4px 0; padding-left: 20px; font-size: 12px; }
.task-context code {
  background: var(--green-faint);
  color: var(--green-accent);
  padding: 1px 4px;
  font-size: 11px;
}
.task-context pre {
  background: var(--bg-elev);
  color: var(--text);
  padding: 8px;
  overflow-x: auto;
  border-left: 2px solid var(--green-faint);
  font-size: 11px;
}
.task-context strong { color: var(--green-accent); }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--green-faint); }
::-webkit-scrollbar-thumb:hover { background: var(--green-dim); }

/* Collapsed content */
.collapsed { display: none; }

/* Toast */
.toast {
  position: fixed;
  bottom: 44px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--bg-elev);
  border: 1px solid var(--green-faint);
  color: var(--green-primary);
  padding: 8px 14px;
  font-family: var(--mono);
  font-size: 12px;
  z-index: 10000;
}
.toast.hidden { display: none; }

[hidden] { display: none !important; }

/* Scanlines (mantén exactamente esto) */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 9999;
  background: repeating-linear-gradient(
    0deg,
    rgba(0, 0, 0, 0.15),
    rgba(0, 0, 0, 0.15) 1px,
    transparent 1px,
    transparent 2px
  );
}

/* Blinking cursor (mantén) */
.cursor::after {
  content: '_';
  color: var(--green-accent);
  animation: blink 1s steps(2) infinite;
  margin-left: 2px;
}
@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
```

---

## Cambio 4 — `app.js`

Dos cambios:

**A. Añadir toggle de sidebar.** En la función `init()`, después de `wireHeaderButtons()` y `wireCollapsibles()`, añade:

```javascript
wireSidebar();
```

Y define:

```javascript
function wireSidebar() {
  const toggle = document.getElementById('sidebar-toggle');
  const app = document.querySelector('.app');
  if (!toggle || !app) return;

  toggle.addEventListener('click', function () {
    const collapsed = app.classList.toggle('sidebar-collapsed');
    toggle.textContent = collapsed ? '▶' : '◀';
    toggle.title = collapsed ? 'Mostrar sidebar' : 'Ocultar sidebar';
  });

  // Botón avatar: muestra info del usuario en un toast
  const avatarBtn = document.getElementById('btn-avatar');
  if (avatarBtn) {
    avatarBtn.addEventListener('click', function () {
      const email = document.getElementById('footer-email')?.textContent || '(sin sesión)';
      const role = document.getElementById('footer-role')?.textContent || '';
      showToast(email + (role ? ' · ' + role : ''));
    });
  }

  // Botón config de la sidebar (mismo comportamiento que el antiguo btn-config)
  const cfgSideBtn = document.getElementById('btn-config-side');
  if (cfgSideBtn) {
    cfgSideBtn.addEventListener('click', function () {
      window.pywebview.api.open_config().then(function (r) {
        showToast((r && r.message) || 'Configuración llega en Fase 5');
      });
    });
  }
}
```

**B. Actualizar `renderProfile` para setear la inicial del avatar.** Modifica la función existente:

```javascript
function renderProfile(profile) {
  const emailEl = document.getElementById('footer-email');
  const roleEl = document.getElementById('footer-role');
  const avatarEl = document.getElementById('avatar-initial');

  if (!profile) {
    if (emailEl) emailEl.textContent = '(sin sesión)';
    if (roleEl) roleEl.textContent = '';
    if (avatarEl) avatarEl.textContent = '?';
    return;
  }

  const email = profile.email || '';
  const role = profile.role || '';

  if (emailEl) emailEl.textContent = email;
  if (roleEl) roleEl.textContent = role;
  if (avatarEl) avatarEl.textContent = email.length > 0 ? email[0].toUpperCase() : '?';
}
```

**C. Remover la referencia al antiguo `btn-config`** en `wireHeaderButtons()` porque ya no existe en el header (se movió a la sidebar). Solo deja `btn-minimize` y `btn-close`.

```javascript
function wireHeaderButtons() {
  const minBtn = document.getElementById('btn-minimize');
  const closeBtn = document.getElementById('btn-close');

  if (minBtn) {
    minBtn.addEventListener('click', function () {
      window.pywebview.api.minimize_window();
    });
  }
  if (closeBtn) {
    closeBtn.addEventListener('click', function () {
      window.pywebview.api.close_window();
    });
  }
}
```

---

## Cambio 5 — `index.html`

El header viejo con `> minirick_` + cursor + 3 botones **ya no existe en este layout**. La identidad "minirick" en el header se elimina (se va). Queda solo:
- Los `window-controls` flotantes (arriba-derecha, solo 2 botones).
- La sidebar con avatar + config.
- El área principal con estados.
- El footer.

Reemplaza la estructura del `<body>` entera con la estructura del bloque HTML que te pegué arriba ("Estructura HTML sugerida").

**Mantén en el `<head>`** el link al `styles.css`, el script CDN de marked, y el script de `app.js` al final del body.

---

## Checklist final

Antes de reportar, verifica:

- [ ] `window.py` tiene `WINDOW_WIDTH = 900`, `WINDOW_HEIGHT = 560`.
- [ ] `index.html` tiene `<aside class="sidebar">` con dos botones (`btn-avatar`, `btn-config-side`).
- [ ] `index.html` tiene `<button class="sidebar-toggle">` con símbolo `◀`.
- [ ] `index.html` ya NO tiene el header con `> minirick_` ni el elemento `.cursor` del header (si queda un `.cursor` en los estados como loading, está bien — sólo se quita del header global).
- [ ] `index.html` tiene `<div class="grid-top">` con 2 paneles dentro de `#state-task`.
- [ ] `index.html` tiene `<div class="panel panel-context">` fuera del grid pero dentro de `#state-task`.
- [ ] `styles.css` tiene `.app { display: grid; grid-template-columns: 56px 1fr; }`.
- [ ] `styles.css` tiene `.app.sidebar-collapsed { grid-template-columns: 0 1fr; }`.
- [ ] `styles.css` tiene `.grid-top { grid-template-columns: 65fr 35fr; }`.
- [ ] `styles.css` tiene `.section-header::before { content: '> '; }` (prefijo pegado).
- [ ] `styles.css` mantiene scanlines, blinking cursor, `[hidden]`, hover de tools, colores de status.
- [ ] `app.js` tiene función `wireSidebar`.
- [ ] `app.js` setea `avatar-initial` en `renderProfile`.
- [ ] `app.js` ya NO intenta agarrar `btn-config` del header (ese se fue).
- [ ] `pytest` pasa con los 41 tests (no se rompió nada Python).
- [ ] `ruff check` limpio.

## Reporte final

1. Archivos tocados y bytes de cada uno.
2. Output de `pytest -q`.
3. Output de `ruff check src/ tests/`.
4. Confirmación de los checkboxes de arriba.
5. **NO hagas commit. NO corras `minirick`. Yo lo pruebo.**
