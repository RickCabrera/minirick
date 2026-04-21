"""CLI principal de minirick."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from minirick import __version__

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


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Sin subcomando: abre el dashboard con la tarea activa."""
    if ctx.invoked_subcommand is not None:
        return
    console.print(_banner())
    console.print(
        "[yellow]⚠ Dashboard aún no implementado (llega en Fase 3).[/yellow]\n"
        "Prueba [bold]minirick --help[/bold] para ver comandos disponibles."
    )


@app.command()
def version() -> None:
    """Muestra la versión instalada."""
    console.print(f"minirick [bold]v{__version__}[/bold]")


@app.command()
def login() -> None:
    """Autentícate con tu email (magic link). [dim](Fase 2)[/dim]"""
    console.print("[yellow]⚠ login aún no implementado — llega en Fase 2.[/yellow]")


@app.command()
def logout() -> None:
    """Cierra sesión local. [dim](Fase 2)[/dim]"""
    console.print("[yellow]⚠ logout aún no implementado — llega en Fase 2.[/yellow]")


@app.command(name="list")
def list_tasks() -> None:
    """Lista las tareas disponibles. [dim](Fase 2)[/dim]"""
    console.print("[yellow]⚠ list aún no implementado — llega en Fase 2.[/yellow]")


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
    """Fuerza refresh del cache local. [dim](Fase 2)[/dim]"""
    console.print("[yellow]⚠ sync aún no implementado — llega en Fase 2.[/yellow]")


if __name__ == "__main__":
    app()
