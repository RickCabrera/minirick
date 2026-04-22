# Fase 3.6 — Bugfixes de auth y UX

> 4 fixes pequeños en `cli.py` y `auth.py`. No tocar layout ni dashboard. No añadir features.

---

## Regla 0 — Antes de escribir código

Responde con:

1. Los 4 archivos que VAS a modificar (2 código + 2 tests).
2. Qué NO vas a tocar (layout, dashboard, models, db, config, Supabase).
3. Confirmación de que después de cada edit harás Test-Path y verás el patch aplicado.

Espera mi "adelante" antes de ejecutar.

---

## Bug A — Login bloquea con tokens inválidos

**Archivo**: `src/minirick/cli.py`, función `login()`.

**Estado actual**: hay una línea tipo `if load_session() is not None: return` que bloquea relogin aunque los tokens guardados ya no sirvan.

**Fix**: cambiar ese check para que intente `ensure_session()`. Si retorna un dict válido → bloquear con el mensaje "Ya hay una sesión activa". Si retorna `None` o levanta `AuthError` → borrar el `session.json` viejo si existe (con `get_session_file().unlink(missing_ok=True)`) y proceder con el login normal.

Pseudocódigo:

```python
try:
    session = ensure_session()
except AuthError:
    session = None

if session is not None:
    console.print("[green]Ya hay una sesión activa.[/green] Usa [bold]logout[/bold] primero.")
    return

# Limpiar tokens inválidos si existen
get_session_file().unlink(missing_ok=True)

# ... resto del flujo de login
```

Importa `get_session_file` desde `minirick.config` si no está ya importado.

---

## Bug B — Refresh token rotation no se persiste

**Archivo**: `src/minirick/auth.py`, función `ensure_session()`.

**Problema**: Supabase rota el refresh token en cada uso. Cuando `client.auth.set_session(access, refresh)` corre y la librería renueva internamente, los nuevos tokens quedan en memoria del cliente pero NO se escriben de vuelta a `session.json`. La próxima vez que se lee el disco, el refresh token guardado ya está consumido y da "Invalid Refresh Token: Already Used".

**Fix**: después de `set_session`, leer la sesión vigente del cliente con `client.auth.get_session()`. Si los tokens cambiaron respecto a los del disco, serializar con `_session_to_dict` y guardar con `save_session`.

Pseudocódigo:

```python
def ensure_session() -> dict[str, Any] | None:
    session = load_session()
    if session is None:
        return None
    access_token = session.get("access_token")
    refresh_token = session.get("refresh_token")
    if not access_token or not refresh_token:
        return None
    try:
        client = get_client()
        client.auth.set_session(access_token, refresh_token)
    except Exception as exc:
        raise AuthError(f"Sesión expirada o inválida: {exc}") from exc

    # NUEVO: capturar tokens rotados
    try:
        fresh = client.auth.get_session()
        fresh_session = getattr(fresh, "session", fresh)  # supabase devuelve un wrapper
        if fresh_session is not None:
            new_access = getattr(fresh_session, "access_token", None)
            new_refresh = getattr(fresh_session, "refresh_token", None)
            if new_access and new_refresh and (
                new_access != access_token or new_refresh != refresh_token
            ):
                updated = _session_to_dict(fresh_session)
                save_session(updated)
                return updated
    except Exception:
        # No crítico — la sesión ya está en el cliente aunque no se pueda persistir
        pass

    return session
```

Asegúrate de que `_session_to_dict` ya maneja el objeto que devuelve `get_session()`. Si la API de supabase-py 2.x difiere, adapta pero mantén la semántica: comparar tokens actuales contra los guardados y persistir si cambiaron.

---

## Bug C — Mensaje "6 dígitos" incorrecto

**Archivo**: `src/minirick/cli.py`, función `login()`.

**Cambios**:

- `Prompt.ask("[bold]Código de 6 dígitos[/bold]")` → `Prompt.ask("[bold]Código de un solo uso[/bold]")`
- `console.print(f"[green]✓[/green] Te mandamos un código a [bold]{email}[/bold].")` → `console.print(f"[green]✓[/green] Código enviado a [bold]{email}[/bold]. Revisa tu correo (incluido spam).")`

---

## Bug D — Banner siempre aparece aunque se abra dashboard

**Archivo**: `src/minirick/cli.py`, función `main()` (el callback raíz con `@app.callback(invoke_without_command=True)`).

**Estado actual**: imprime el banner con `console.print(_banner())` antes de llamar `_require_session()` y `launch_dashboard()`. Eso hace ruido innecesario cuando el usuario solo quiere el dashboard.

**Fix**: reemplazar la impresión del banner por un mensaje discreto. El banner completo solo se muestra cuando NO hay sesión (como hint visual antes del "Inicia sesión con minirick login").

Pseudocódigo del nuevo `main()`:

```python
@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Sin subcomando: abre el dashboard con la tarea activa."""
    if ctx.invoked_subcommand is not None:
        return

    # Verificar sesión SIN imprimir banner todavía
    try:
        session = ensure_session()
    except AuthError as exc:
        console.print(_banner())
        console.print(f"[red]✖ {exc}[/red]")
        console.print("Vuelve a iniciar sesión con [bold]minirick login[/bold].")
        raise typer.Exit(code=1) from exc

    if session is None:
        console.print(_banner())
        console.print("[yellow]⚠ No hay sesión activa.[/yellow]")
        console.print("Inicia sesión con [bold]minirick login[/bold].")
        raise typer.Exit(code=1)

    # Hay sesión → solo mensaje discreto + dashboard
    console.print("[dim]> minirick dashboard abriendo...[/dim]")
    try:
        from minirick.dashboard import launch_dashboard

        launch_dashboard()
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]✖ No se pudo lanzar el dashboard:[/red] {exc}")
        raise typer.Exit(code=1) from exc
```

Nota: mantén la lógica equivalente a `_require_session()` pero inline para controlar el orden del banner. Si prefieres mantener `_require_session()` como función separada, asegúrate de que NO imprima banner internamente y que el `main()` decida cuándo mostrarlo.

---

## Tests a actualizar

**`tests/test_auth.py`**: añadir 1 test que verifique Bug B. Usa mocks de supabase — el test debe:

1. Guardar un `session.json` con tokens `{access: "old_a", refresh: "old_r"}`.
2. Mockear `get_client()` para devolver un cliente donde:
   - `auth.set_session(...)` no hace nada.
   - `auth.get_session()` retorna un objeto con tokens nuevos `access_token="new_a"`, `refresh_token="new_r"`.
3. Llamar `ensure_session()`.
4. Verificar que `session.json` ahora contiene `new_a` y `new_r` (no los viejos).

**`tests/test_cli_smoke.py`**: si algún test chequeaba el string exacto del banner o "Código de 6 dígitos", actualízalo al nuevo texto. Si nada rompe, déjalo como está.

---

## Verificación final obligatoria

Al terminar, corre:

```bash
pytest -q
ruff check src/ tests/
```

Reporta:

1. Los 4 archivos tocados con sus tamaños (antes vs después).
2. Diffs MUY cortos (5-8 líneas) de los cambios en `cli.py` y `auth.py`.
3. Output de pytest (número de tests que pasan).
4. Output de ruff.
5. Test nuevo añadido en `test_auth.py` (nombre de la función).
6. NO hagas commit. NO corras minirick.

Si algún fix te parece ambiguo, PAUSA y pregunta antes de improvisar.
