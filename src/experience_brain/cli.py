from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import typer

from .capture import capture_event
from .consolidate import consolidate_session
from .models import Event
from .retrieve import format_briefing, retrieve_experience
from .store import ensure_store, lint_store, read_events, read_experiences

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _root(root: Path) -> Path:
    return root.resolve()


@app.command()
def status(root: Path = typer.Option(Path("."))) -> None:
    resolved = _root(root)
    ensure_store(resolved)
    typer.echo("Experience Brain v0.2.0")
    typer.echo(f"events={len(read_events(resolved))}")
    typer.echo(f"experiences={len(read_experiences(resolved))}")


@app.command("lint")
def lint_command(root: Path = typer.Option(Path("."))) -> None:
    errors = lint_store(_root(root))
    if errors:
        for error in errors:
            typer.echo(f"ERROR: {error}")
        raise typer.Exit(1)
    typer.echo("lint passed")


@app.command("import")
def import_events(path: Path, root: Path = typer.Option(Path("."))) -> None:
    resolved = _root(root)
    added = 0
    skipped = 0
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        loaded = json.loads(line)
        if not isinstance(loaded, dict):
            raise typer.BadParameter(f"line {number} is not an object")
        event = Event.model_validate(loaded)
        result = capture_event(resolved, event)
        added += int(result.id == event.id)
    typer.echo(f"events imported={added} skipped={skipped}")


@app.command("process-session")
def process_session(
    session_id: str | None = typer.Option(None),
    root: Path = typer.Option(Path(".")),
) -> None:
    count, report = consolidate_session(_root(root), session_id)
    typer.echo(f"experiences created={count}")
    typer.echo(f"review report={report}")


@app.command()
def query(
    question: str,
    project: str | None = typer.Option(None),
    limit: int = typer.Option(5),
    root: Path = typer.Option(Path(".")),
) -> None:
    items = retrieve_experience(_root(root), question, project=project, limit=limit)
    typer.echo(format_briefing(items))


@app.command("review-latest")
def review_latest(root: Path = typer.Option(Path("."))) -> None:
    path = _root(root) / "reports" / "latest.md"
    if not path.exists():
        typer.echo("No review report found.")
        raise typer.Exit(1)
    typer.echo(path.read_text(encoding="utf-8"))


@app.command()
def dashboard(root: Path = typer.Option(Path("."))) -> None:
    module = "experience_brain.dashboard"
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "-m", module, "--", "--root", str(_root(root))],
        check=False,
    )


if __name__ == "__main__":
    app()
