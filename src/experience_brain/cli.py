from __future__ import annotations

from pathlib import Path

import typer
import yaml

from .capsule import build_capsule
from .config import Settings, load_settings
from .consolidation import consolidate as consolidate_store
from .event_store import ingest_events
from .linting import lint as lint_store
from .reporting import build_report
from .retrieval import retrieve as retrieve_skills
from .source_store import ingest_source

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _root(root: Path | None) -> Path:
    return (root or Path(".")).resolve()


def _settings(root: Path | None) -> Settings:
    return load_settings(_root(root))


@app.command()
def ingest(
    path: Path,
    kind: str = typer.Option(..., help="events or source"),
    metadata: Path | None = typer.Option(None, help="YAML sidecar required for source"),
    root: Path = typer.Option(Path(".")),
) -> None:
    if kind == "events":
        added, skipped = ingest_events(_root(root), path)
        typer.echo(f"events added={added} skipped={skipped}")
    elif kind == "source" and metadata is not None:
        typer.echo(f"source ingested={ingest_source(_root(root), path, metadata)}")
    else:
        raise typer.BadParameter("kind must be events or source; source requires --metadata")


@app.command()
def consolidate(
    run_id: str | None = typer.Option(None), root: Path = typer.Option(Path("."))
) -> None:
    episodes, skills = consolidate_store(_settings(root), run_id)
    typer.echo(f"episodes={episodes} skills={skills}")


@app.command()
def retrieve(
    task: Path = typer.Option(...), limit: int = 5, root: Path = typer.Option(Path("."))
) -> None:
    output = [
        {"id": item["id"], "score": item["score"]}
        for item in retrieve_skills(_root(root), task, limit)
    ]
    typer.echo(yaml.safe_dump(output, allow_unicode=True, sort_keys=False))


@app.command()
def capsule(
    task: Path = typer.Option(...),
    budget: int = typer.Option(...),
    root: Path = typer.Option(Path(".")),
) -> None:
    typer.echo(build_capsule(_settings(root), task, budget))


@app.command()
def report(root: Path = typer.Option(Path("."))) -> None:
    typer.echo(build_report(_root(root)))


@app.command()
def lint(root: Path = typer.Option(Path("."))) -> None:
    errors = lint_store(_settings(root))
    if errors:
        for error in errors:
            typer.echo(f"ERROR: {error}")
        raise typer.Exit(1)
    typer.echo("lint passed")
