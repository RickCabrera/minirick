"""CLI principal de minirick."""

from __future__ import annotations

import json

import typer
from postgrest.exceptions import APIError
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from minirick import __version__
from minirick.auth import (
    AuthError,
    ensure_session,
    request_otp,
    save_session,
    verify_otp_code,
)
from minirick.auth import (
    logout as auth_logout,
)
from minirick.config import get_cache_dir, get_session_file
from minirick.db import get_client
from minirick.models import Task

app = typer.Typer(
    name="minirick",
    help="Copiloto de terminal con contexto compartido para tu equipo.",
    no_args_is_help=False,
    rich_markup_mode="rich",
    add_completion=False,
)

console = Console()


def _banner() -> Panel:
    title = Text("minirick", style="bold magenta")
    subtitle = Text(f"v{__version__} — copiloto de equipo", style="dim")
    body = Text.assemble(title, "\n", subtitle)
    return Panel(body, border_style="magenta", expand=False)


def _require_session() -> dict:
    """Garantiza que hay sesión activa, si no, imprime error y sale."""
    try:
        session = ensure_session()
    except AuthError as exc:
        console.print(f"[red]✖ {exc}[/red]")
        console.print("Vuelve a iniciar sesión con [bold]minirick login[/bold].")
        raise typer.Exit(code=1) from exc
    if session is None:
        console.print("[yellow]⚠ No hay sesión activa.[/yellow]")
        console.print("Inicia sesión con [bold]minirick login[/bold].")
        raise typer.Exit(code=1)
    return session


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Sin subcomando: abre el dashboard con la tarea activa."""
    if ctx.invoked_subcommand is not None:
        return

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

    console.print("[dim]> minirick dashboard abriendo...[/dim]")
    try:
        from minirick.dashboard import launch_dashboard

        launch_dashboard()
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]✖ No se pudo lanzar el dashboard:[/red] {exc}")
        raise typer.Exit(code=1) from exc


@app.command()
def version() -> None:
    """Muestra la versión instalada."""
    console.print(f"minirick [bold]v{__version__}[/bold]")


@app.command()
def login(
    email: str | None = typer.Option(None, "--email", "-e", help="Tu email de acceso"),
) -> None:
    """Inicia sesión con tu email (código OTP de 6 dígitos)."""
    try:
        session = ensure_session()
    except AuthError:
        session = None

    if session is not None:
        console.print("[green]Ya hay una sesión activa.[/green] Usa [bold]logout[/bold] primero.")
        return

    # Limpiar tokens inválidos si quedaron en disco.
    get_session_file().unlink(missing_ok=True)

    if not email:
        email = Prompt.ask("[bold]Email[/bold]")
    email = email.strip().lower()
    if "@" not in email:
        console.print("[red]✖ Email inválido.[/red]")
        raise typer.Exit(code=1)

    try:
        request_otp(email)
    except AuthError as exc:
        console.print(f"[red]✖ {exc}[/red]")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[green]✓[/green] Código enviado a [bold]{email}[/bold]. "
        "Revisa tu correo (incluido spam)."
    )
    token = Prompt.ask("[bold]Código de un solo uso[/bold]")
    token = token.strip()

    try:
        session = verify_otp_code(email, token)
    except AuthError as exc:
        console.print(f"[red]✖ {exc}[/red]")
        raise typer.Exit(code=1) from exc

    save_session(session)
    console.print(f"[green]✓ Sesión iniciada como {email}.[/green]")


@app.command()
def logout() -> None:
    """Cierra la sesión local."""
    if auth_logout():
        console.print("[green]✓ Sesión cerrada.[/green]")
    else:
        console.print("[yellow]No había sesión activa.[/yellow]")


@app.command(name="list")
def list_tasks() -> None:
    """Lista las tareas disponibles en Supabase."""
    _require_session()
    try:
        response = (
            get_client()
            .table("tasks")
            .select("*")
            .order("updated_at", desc=True)
            .execute()
        )
    except APIError as exc:
        console.print(f"[red]✖ Error al leer tareas:[/red] {exc.message or exc}")
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]✖ Error de conexión:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    rows = response.data or []
    if not rows:
        console.print("[dim]No hay tareas todavía.[/dim]")
        return

    table = Table(title="Tareas del equipo", show_lines=False)
    table.add_column("ID", style="dim", no_wrap=True, overflow="fold")
    table.add_column("Título", style="bold")
    table.add_column("Estado")
    table.add_column("Activa")
    table.add_column("Actualizada", style="dim")

    for row in rows:
        task = Task.from_dict(row)
        active_mark = "[green]✓[/green]" if task.is_active else ""
        table.add_row(
            task.id[:8],
            task.title,
            task.status,
            active_mark,
            (task.updated_at or "")[:19],
        )
    console.print(table)


@app.command()
def new() -> None:
    """Crea una nueva tarea (solo admin). [dim](Fase 5)[/dim]"""
    console.print("[yellow]⚠ new aún no implementado — llega en Fase 5.[/yellow]")


@app.command()
def edit(task_id: str = typer.Argument(..., help="ID de la tarea a editar")) -> None:
    """Edita una tarea existente (solo admin). [dim](Fase 5)[/dim]"""
    console.print(f"[yellow]⚠ edit {task_id} aún no implementado — llega en Fase 5.[/yellow]")


@app.command(name="set-active")
def set_active(task_id: str = typer.Argument(..., help="ID de la tarea")) -> None:
    """Marca una tarea como la activa del equipo (solo admin). [dim](Fase 5)[/dim]"""
    console.print(
        f"[yellow]⚠ set-active {task_id} aún no implementado — llega en Fase 5.[/yellow]"
    )


@app.command()
def sync() -> None:
    """Refresca el cache local de tareas desde Supabase."""
    _require_session()
    try:
        response = (
            get_client()
            .table("tasks")
            .select("*")
            .order("updated_at", desc=True)
            .execute()
        )
    except APIError as exc:
        console.print(f"[red]✖ Error al sincronizar:[/red] {exc.message or exc}")
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]✖ Error de conexión:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    rows = response.data or []
    cache_path = get_cache_dir() / "tasks.json"
    cache_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    console.print(f"[green]✓[/green] {len(rows)} tarea(s) cacheadas en {cache_path}")


if __name__ == "__main__":
    app()
