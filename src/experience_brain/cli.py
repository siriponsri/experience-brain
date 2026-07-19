from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import typer

from .capture import end_session as capture_end_session
from .capture import record_event
from .capture import start_session as capture_start_session
from .consolidate import consolidate_session
from .knowledge import list_inbox_status, process_inbox
from .models import SCHEMA_VERSION, Actor, Event, EventType, Provenance
from .retrieve import (
    format_briefing,
    format_knowledge_briefing,
    record_retrieval_usage,
    retrieve_experience,
    retrieve_knowledge,
    retrieve_memory,
)
from .store import ensure_store, lint_store, read_events, read_experiences, read_knowledge

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _root(root: Path) -> Path:
    return root.resolve()


@app.command()
def status(root: Path = typer.Option(Path("."))) -> None:
    resolved = _root(root)
    ensure_store(resolved)
    typer.echo(f"Experience Brain {SCHEMA_VERSION}")
    typer.echo(f"events={len(read_events(resolved))}")
    typer.echo(f"experiences={len(read_experiences(resolved))}")
    typer.echo(f"knowledge={len(read_knowledge(resolved))}")


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
        result = record_event(
            resolved,
            event_id=event.id,
            event_type=event.type,
            actor=event.actor,
            project=event.project,
            session_id=event.session_id,
            task_id=event.task_id,
            source=event.source,
            content=event.content,
            tool_name=event.tool_name,
            error_signature=event.error_signature,
            outcome=event.outcome,
            metadata=event.metadata,
            provenance=event.provenance,
        )
        added += int(result.id == event.id)
    typer.echo(f"events imported={added} skipped={skipped}")


def _provenance(
    *,
    agent: str | None,
    model: str | None,
    reasoning_effort: str | None,
    experiment_id: str | None,
    run_id: str | None,
) -> Provenance:
    return Provenance(
        agent=agent,
        model=model,
        reasoning_effort=reasoning_effort,
        experiment_id=experiment_id,
        run_id=run_id,
        source="codex_cli",
    )


@app.command("start-session")
def start_session(
    project: str,
    session_id: str,
    goal: str = typer.Option(""),
    task_id: str | None = typer.Option(None),
    agent: str | None = typer.Option("codex_cli"),
    model: str | None = typer.Option(None),
    reasoning_effort: str | None = typer.Option(None),
    experiment_id: str | None = typer.Option(None),
    run_id: str | None = typer.Option(None),
    retry: bool = typer.Option(False),
    root: Path = typer.Option(Path(".")),
) -> None:
    event = capture_start_session(
        _root(root),
        project=project,
        session_id=session_id,
        goal=goal,
        task_id=task_id,
        provenance=_provenance(
            agent=agent,
            model=model,
            reasoning_effort=reasoning_effort,
            experiment_id=experiment_id,
            run_id=run_id,
        ),
    )
    typer.echo(event.id)


@app.command("end-session")
def end_session(
    project: str,
    session_id: str,
    summary: str = typer.Option(""),
    outcome: str | None = typer.Option(None),
    consolidate: bool = typer.Option(True),
    task_id: str | None = typer.Option(None),
    agent: str | None = typer.Option("codex_cli"),
    model: str | None = typer.Option(None),
    reasoning_effort: str | None = typer.Option(None),
    experiment_id: str | None = typer.Option(None),
    run_id: str | None = typer.Option(None),
    root: Path = typer.Option(Path(".")),
) -> None:
    event = capture_end_session(
        _root(root),
        project=project,
        session_id=session_id,
        summary=summary,
        outcome=outcome,
        task_id=task_id,
        provenance=_provenance(
            agent=agent,
            model=model,
            reasoning_effort=reasoning_effort,
            experiment_id=experiment_id,
            run_id=run_id,
        ),
    )
    typer.echo(event.id)
    if consolidate:
        count, report = consolidate_session(_root(root), session_id)
        typer.echo(f"experiences created={count}")
        typer.echo(f"review report={report}")


@app.command("record-event")
def record_event_command(
    project: str,
    session_id: str,
    event_type: str,
    actor: str,
    content: str = typer.Option(""),
    task_id: str | None = typer.Option(None),
    tool_name: str | None = typer.Option(None),
    error_signature: str | None = typer.Option(None),
    outcome: str | None = typer.Option(None),
    root: Path = typer.Option(Path(".")),
) -> None:
    event = record_event(
        _root(root),
        project=project,
        session_id=session_id,
        event_type=EventType(event_type),
        actor=Actor(actor),
        content=content,
        task_id=task_id,
        tool_name=tool_name,
        error_signature=error_signature,
        outcome=outcome,
    )
    typer.echo(event.id)


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


@app.command("list-inbox")
def list_inbox(root: Path = typer.Option(Path("."))) -> None:
    for item in list_inbox_status(_root(root)):
        typer.echo(json.dumps(item, ensure_ascii=False, sort_keys=True))


@app.command("process-inbox")
def process_inbox_command(
    project: str = typer.Option("general"),
    agent: str | None = typer.Option("codex_cli"),
    model: str | None = typer.Option(None),
    reasoning_effort: str | None = typer.Option(None),
    experiment_id: str | None = typer.Option("EXP-03.2"),
    run_id: str | None = typer.Option(None),
    retry: bool = typer.Option(False),
    root: Path = typer.Option(Path(".")),
) -> None:
    results = process_inbox(
        _root(root),
        project=project,
        retry=retry,
        provenance=Provenance(
            agent=agent,
            model=model,
            reasoning_effort=reasoning_effort,
            experiment_id=experiment_id,
            run_id=run_id,
            source="process_inbox",
        ),
    )
    typer.echo(f"inbox files processed={len(results)}")
    for result in results:
        typer.echo(
            json.dumps(
                {
                    "filename": result.filename,
                    "status": result.status,
                    "knowledge_id": result.knowledge_id,
                    "duplicate_of": result.duplicate_of,
                    "error": result.error,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )


@app.command("query-knowledge")
def query_knowledge_command(
    question: str,
    project: str | None = typer.Option(None),
    limit: int = typer.Option(5),
    root: Path = typer.Option(Path(".")),
) -> None:
    items = retrieve_knowledge(_root(root), question, project=project, limit=limit)
    typer.echo(format_knowledge_briefing(items))


@app.command("query-memory")
def query_memory_command(
    question: str,
    project: str | None = typer.Option(None),
    limit: int = typer.Option(5),
    root: Path = typer.Option(Path(".")),
) -> None:
    payload = retrieve_memory(_root(root), question, project=project, limit=limit)
    typer.echo(payload["briefing"])


@app.command("record-retrieval-usage")
def record_retrieval_usage_command(
    project: str,
    session_id: str,
    query_text: str,
    retrieved_experience_id: list[str] = typer.Option(...),
    used_experience_id: list[str] = typer.Option([]),
    stage: str = typer.Option("pre_task"),
    outcome: str | None = typer.Option(None),
    retrieval_result: str | None = typer.Option(None),
    usage: str | None = typer.Option(None),
    task_outcome: str | None = typer.Option(None),
    root: Path = typer.Option(Path(".")),
) -> None:
    event = record_retrieval_usage(
        _root(root),
        project=project,
        session_id=session_id,
        query=query_text,
        retrieved_experience_ids=retrieved_experience_id,
        used_experience_ids=used_experience_id,
        stage=stage,
        outcome=outcome,
        retrieval_result=retrieval_result,  # type: ignore[arg-type]
        usage=usage,  # type: ignore[arg-type]
        task_outcome=task_outcome,  # type: ignore[arg-type]
    )
    typer.echo(event.id)


@app.command("review-latest")
def review_latest(root: Path = typer.Option(Path("."))) -> None:
    path = _root(root) / "reports" / "latest.md"
    if not path.exists():
        typer.echo("No review report found.")
        raise typer.Exit(1)
    typer.echo(path.read_text(encoding="utf-8"))


@app.command()
def dashboard(root: Path = typer.Option(Path("."))) -> None:
    script = Path(__file__).with_name("dashboard.py")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(script), "--", "--root", str(_root(root))],
        check=False,
    )


if __name__ == "__main__":
    app()
