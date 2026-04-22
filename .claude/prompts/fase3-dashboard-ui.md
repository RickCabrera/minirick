# Fase 3 — Corrección UI del dashboard

> Este archivo contiene las instrucciones exactas para corregir la UI del dashboard de minirick.
> La **capa Python** (pywebview window, API bridge, service layer, tests) ya está bien hecha — **NO la toques**.
> Solo necesitas **rehacer los 3 archivos de UI** porque se desviaron del diseño pedido.

---

## Regla 0 — Antes de escribir código

Antes de tocar nada, **repíteme en tu respuesta** con tus propias palabras:

1. Qué paleta de colores vas a usar (con los hex exactos).
2. Qué 5 efectos visuales específicos vas a implementar.
3. Qué 3 archivos vas a modificar y cuáles NO vas a tocar.

Si no puedes listar estos puntos sin inventar, **no leíste bien este archivo**. Vuelve a leerlo antes de codear. No quiero que improvises estética.

---

## Regla 1 — Qué NO tocar

**Estos archivos están bien y no se modifican:**
- `src/minirick/dashboard/__init__.py`
- `src/minirick/dashboard/window.py`
- `src/minirick/dashboard/api.py`
- `src/minirick/dashboard/service.py`
- `src/minirick/cli.py`
- Cualquier archivo en `tests/`

**NO añadas tests nuevos.** Los 37 existentes están bien.
**NO hagas commits.** Solo edita.
**NO refactorices Python** aunque veas algo que te gustaría cambiar.

---

## Regla 2 — Qué SÍ hacer

Reescribir **desde cero** estos tres archivos para que implementen la estética terminal/hacker retro verde sobre negro:

- `src/minirick/dashboard/ui/index.html`
- `src/minirick/dashboard/ui/styles.css`
- `src/minirick/dashboard/ui/app.js`

Los tres deben ser vanilla HTML/CSS/JS. Sin frameworks. Sin dependencias npm. Una sola librería externa permitida vía CDN: `marked` para renderizar el markdown del contexto.

---

## Paleta de colores (usa exactamente estos valores en :root)

```css
:root {
  --bg: #0a0e0a;
  --bg-elev: #0f1410;
  --green-primary: #00ff88;
  --green-accent: #39ff14;
  --green-dim: #5a8c5a;
  --green-faint: #1a3d1a;
  --text: #b8ffb8;
  --text-dim: #7a9a7a;
  --red: #ff5555;
  --yellow: #f0d060;
  --gray: #808080;
  --mono: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Monaco', monospace;
}
```

**NO uses púrpura, azul, magenta ni ningún otro color fuera de esta paleta.** Si algo necesita énfasis, usa `--green-accent`. Si algo necesita verse tenue, usa `--green-dim` o `--text-dim`.

---

## Efectos visuales obligatorios (los 5)

### 1. Scanlines CRT

Un overlay fijo sobre todo el body que simula líneas de scan de monitor CRT viejo. Usa `repeating-linear-gradient` en un pseudo-elemento `::before` del body, con `z-index` muy alto y `pointer-events: none`.

```css
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
```

### 2. Blinking cursor

Al lado del texto `> minirick` en el header, debe haber un cursor `_` parpadeante en color `--green-accent`.

```css
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

### 3. Prefijo `>` antes de cada sección

Cada encabezado de sección (ACTIVE TASK, CONTEXT, TOOLS) debe empezar con `> ` en color `--green-primary`, simulando un prompt de terminal.

Implementa esto con un `::before` en `.section-header` con `content: '> ';`, no hardcodeado en el HTML. Así el prefijo hereda el color correcto.

### 4. Hover `[>]` → `[#]` en tools

Cada tool se renderiza con un prefijo `[>]` que al hacer hover cambia a `[#]`, como seleccionar algo en un menú de terminal.

```css
.tool::before { content: '[>] '; color: var(--green-dim); }
.tool:hover::before { content: '[#] '; color: var(--green-accent); }
.tool:hover { background: var(--green-faint); cursor: pointer; }
```

### 5. Glow verde sutil en el borde de la ventana

```css
body {
  border: 1px solid var(--green-faint);
  box-shadow: 0 0 20px rgba(0, 255, 136, 0.15), inset 0 0 60px rgba(0, 255, 136, 0.03);
}
```

---

## Tipografía

Todo el body debe usar `var(--mono)`. Sin excepciones. No Helvetica, no Inter, no system-ui. Es un dashboard estilo terminal — **todo monospace**.

Pesos: `font-weight: 400` para texto normal, `500` para títulos de sección, `700` solo para el título de la tarea. No uses pesos intermedios.

Tamaños:
- Body default: `13px`.
- Título de tarea activa: `18px`.
- Headers de sección: `11px`, `text-transform: uppercase`, `letter-spacing: 1px`.
- Footer: `11px`.

---

## Layout exacto (`index.html`)

```
┌───────────────────────────────────────┐
│ > minirick_          [🗕] [⚙] [✕]    │  .header (draggable)
├───────────────────────────────────────┤
│                                       │
│ > ACTIVE TASK                         │  .section-header
│                                       │
│ Título de la tarea                    │  .task-title
│ [in_progress]                         │  .status-badge
│                                       │
│ > SUMMARY                             │  .section-header
│ resumen texto...                      │  .task-summary
│                                       │
├───────────────────────────────────────┤
│ > CONTEXT                    [▾]      │  .section-header collapsible
│ (markdown renderizado)                │  .task-context (inicialmente visible)
├───────────────────────────────────────┤
│ > TOOLS (N)                  [▾]      │  .section-header collapsible
│ [>] claude_code ~/repos/x             │  .tool
│ [>] vscode      ~/repos/x             │  .tool
│ [>] browser     https://...           │  .tool
├───────────────────────────────────────┤
│ pingcabra@gmail.com · owner           │  .footer (sticky bottom)
└───────────────────────────────────────┘
```

### Header — 3 botones, en este orden de izquierda a derecha

1. **🗕 Minimizar** — llama `window.pywebview.api.minimize_window()`
2. **⚙ Configuración** — llama `open_config()`, muestra el mensaje stub en un pequeño toast verde o alert estilizado.
3. **✕ Cerrar** — llama `close_window()`.

**NO incluyas botón de refresh en el header.** Si quieres un refresh, ponlo como link pequeño en el footer tipo `[refresh]`. Pero no es obligatorio.

### Drag del header

Usa `-webkit-app-region: drag` en el div `.header` y `-webkit-app-region: no-drag` en los botones individuales. Esto funciona con pywebview (Edge WebView2 / WKWebView).

```css
.header { -webkit-app-region: drag; }
.header button { -webkit-app-region: no-drag; }
```

### Status badges

Formato `[status]` en minúsculas, entre corchetes, monoespaciado.

```css
.status-badge { font-family: var(--mono); }
.status-todo        { color: var(--gray); }
.status-in_progress { color: var(--yellow); }
.status-done        { color: var(--green-primary); }
```

El texto debe literalmente verse así (con corchetes): `[todo]`, `[in_progress]`, `[done]`. El valor raw viene del field `status` de la tarea. Si viene algo que no es uno de los 3, muéstralo igual con clase `.status-badge` genérica sin color especial.

### Estados del dashboard

El JS debe manejar estos 4 estados mutuamente excluyentes:

1. **Loading** — mientras la primera llamada a la API responde. Muestra centrado: `> fetching active task...` con cursor parpadeante.
2. **Error** — si la API retorna `{ok: false}`. Muestra en rojo: `> connection error` + debajo en tenue: `run 'minirick sync' in terminal`.
3. **Empty** — si no hay tarea activa. Muestra centrado: `> no active task` + debajo en tenue: `ask your admin to set one`.
4. **Task** — cuando hay data. Renderiza todo el layout.

Cada estado es una sección `<section id="state-loading">`, `<section id="state-error">`, etc. JS les pone/quita `hidden`.

### Secciones colapsables

CONTEXT y TOOLS son colapsables con click en su header. Indicador `▾` cuando expandido, `▸` cuando colapsado. Inicial: ambas expandidas.

No uses `<details>/<summary>` nativos (se ven mal con el tema). Implementa con JS y una clase `.collapsed` que hace `display: none` al contenido.

---

## Comportamiento del JS (`app.js`)

1. Esperar evento `pywebviewready` antes de hacer cualquier llamada a la API.
2. Al cargar: mostrar estado Loading, llamar `get_active_task()` y `get_current_profile()` en paralelo con `Promise.all`.
3. Renderizar según el resultado.
4. Registrar handlers de botones (minimize, config, close) y collapsibles.
5. Para markdown: incluir en index.html `<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>` y llamar `marked.parse(task.context_md)` al insertar. Si `marked` no cargó por alguna razón, fallback a `<pre>` con el texto raw — no crashees.
6. Click en un `.tool` llama `open_tool(index)` y muestra el mensaje retornado en un pequeño toast verde abajo (que se auto-oculta en 3s). **No uses `alert()` nativo**, se ve horrible con el tema.

### Toast mínimo

```html
<div id="toast" class="toast hidden"></div>
```

```css
.toast {
  position: fixed; bottom: 40px; left: 50%; transform: translateX(-50%);
  background: var(--bg-elev); border: 1px solid var(--green-faint);
  color: var(--green-primary); padding: 8px 14px; font-family: var(--mono);
  font-size: 12px; z-index: 10000;
}
.toast.hidden { display: none; }
```

```js
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.remove('hidden');
  setTimeout(() => t.classList.add('hidden'), 3000);
}
```

---

## Footer

Muestra `{email} · {role}` leído de `get_current_profile()`. El `·` (bullet medio) en color `--green-dim`. El email y el role en color `--text-dim`.

Sticky al fondo del viewport, altura 28px, separado del contenido con un `border-top: 1px solid var(--green-faint)`.

---

## Scrollbar custom

```css
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--green-faint); }
::-webkit-scrollbar-thumb:hover { background: var(--green-dim); }
```

---

## Padding, spacing, bordes

- Body padding: 0 (el ::before de scanlines necesita full viewport).
- `.header` altura 36px, padding horizontal 12px, `border-bottom: 1px solid var(--green-faint)`.
- Secciones: padding 12px, `border-bottom: 1px solid var(--green-faint)` entre ellas.
- Botones del header: 24x24px, fondo transparente, borde 1px `--green-faint`, hover con fondo `--green-faint` y color `--green-accent`.
- Tools: padding 6px 12px, cada uno con `border-left: 2px solid transparent` que en hover se vuelve `--green-accent`.

---

## Checklist de verificación al terminar

Antes de decirme que terminaste, verifica tú mismo abriendo los archivos que:

- [ ] `styles.css` contiene `--green-primary: #00ff88` literal.
- [ ] `styles.css` contiene `repeating-linear-gradient` (scanlines).
- [ ] `styles.css` contiene `@keyframes blink` (cursor parpadeante).
- [ ] `styles.css` contiene selector `:hover::before` con `content: '[#]'` (hover tools).
- [ ] `styles.css` define `--mono` y la aplica al body.
- [ ] `index.html` contiene literalmente el texto `minirick` dentro de un elemento con clase `.cursor`.
- [ ] `index.html` tiene los 4 estados (`#state-loading`, `#state-error`, `#state-empty`, `#state-task`).
- [ ] `index.html` NO tiene botón de refresh en el header — el header tiene exactamente 3 botones.
- [ ] `app.js` usa `pywebviewready` event.
- [ ] `app.js` tiene función `showToast`.
- [ ] `app.js` NO usa `alert()`.
- [ ] No hay ni un hex de color fuera de la paleta definida arriba (grep rápido: no debe haber `#purple`, `#blue`, ni hexes raros).

Si algún checkbox no se cumple, **corrígelo antes de reportarme**.

---

## Al terminar

1. Confirma que `pytest` sigue en 37 passing (no tocaste tests ni Python, así que debe estar igual).
2. Confirma `ruff check .` limpio.
3. Dime qué archivos tocaste exactamente y pega un snippet de cada uno para que yo vea que contiene los efectos clave (paleta, scanlines, blink, hover).
4. **NO corras `minirick`** tú mismo (Windows headless no va a renderizar bien en tu ambiente). Yo lo corro en mi máquina.
5. **NO hagas commit.**
