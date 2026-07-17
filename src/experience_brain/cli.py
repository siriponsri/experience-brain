from __future__ import annotations

from pathlib import Path

import typer
import yaml

from .benchmark import (
    analyze,
    build_cost_estimate,
    check_completeness,
    decision_from_analysis,
    preflight,
    prepare,
    reset_run,
    run_stage,
    validate_analysis,
)
from .capsule import build_capsule
from .config import Settings, load_settings
from .consolidation import consolidate as consolidate_store
from .event_store import ingest_events
from .full import check_gate, module_pilot_preflight, record_decision, write_gain_cost_memo
from .hybrid import rebuild_hybrid_index, verify_hybrid_index
from .linting import lint as lint_store
from .reporting import build_report
from .retrieval import retrieve_for_settings
from .source_store import ingest_source
from .wiki import (
    build_wiki_context,
    find_task_leakage,
    ingest_wiki_source,
    maintain_wiki,
    reset_wiki,
)

app = typer.Typer(no_args_is_help=True, add_completion=False)
benchmark_app = typer.Typer(no_args_is_help=True, add_completion=False)
index_app = typer.Typer(no_args_is_help=True, add_completion=False)
full_app = typer.Typer(no_args_is_help=True, add_completion=False)
app.add_typer(benchmark_app, name="benchmark")
app.add_typer(index_app, name="index")
app.add_typer(full_app, name="full")


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
    settings = _settings(root)
    if settings.condition == "c1" and kind == "source" and metadata is not None:
        typer.echo(f"wiki source ingested={ingest_wiki_source(settings, path, metadata)}")
    elif settings.condition == "c1":
        raise typer.BadParameter("C1 accepts only source ingestion with --metadata")
    elif kind == "events":
        added, skipped = ingest_events(settings.root, path)
        typer.echo(f"events added={added} skipped={skipped}")
    elif kind == "source" and metadata is not None:
        typer.echo(f"source ingested={ingest_source(settings.root, path, metadata)}")
    else:
        raise typer.BadParameter("kind must be events or source; source requires --metadata")


@app.command()
def consolidate(
    run_id: str | None = typer.Option(None), root: Path = typer.Option(Path("."))
) -> None:
    settings = _settings(root)
    if settings.condition != "c2":
        raise typer.BadParameter("consolidate is currently available only for condition C2 Lite")
    episodes, skills = consolidate_store(settings, run_id)
    typer.echo(f"episodes={episodes} skills={skills}")


@app.command()
def retrieve(
    task: Path = typer.Option(...), limit: int = 5, root: Path = typer.Option(Path("."))
) -> None:
    settings = _settings(root)
    if settings.condition not in {"c2", "c3"}:
        raise typer.BadParameter("retrieve is available only for C2 Lite or C3 Full")
    items, _ = retrieve_for_settings(settings, task, limit)
    output = [{"id": item["id"], "score": item["score"]} for item in items]
    typer.echo(yaml.safe_dump(output, allow_unicode=True, sort_keys=False))


@app.command()
def capsule(
    task: Path = typer.Option(...),
    budget: int = typer.Option(...),
    root: Path = typer.Option(Path(".")),
) -> None:
    settings = _settings(root)
    if settings.condition not in {"c2", "c3"}:
        raise typer.BadParameter("capsule is available only for C2 Lite or C3 Full")
    typer.echo(build_capsule(settings, task, budget))


@app.command()
def context(task: Path = typer.Option(...), root: Path = typer.Option(Path("."))) -> None:
    settings = _settings(root)
    if settings.condition == "c1":
        typer.echo(build_wiki_context(settings, task, settings.default_budget_tokens))
    elif settings.condition in {"c2", "c3"}:
        typer.echo(build_capsule(settings, task, settings.default_budget_tokens))
    else:
        raise typer.BadParameter("condition C0 has no persistent memory context")


@app.command()
def maintain(manifest: Path = typer.Option(...), root: Path = typer.Option(Path("."))) -> None:
    settings = _settings(root)
    pages, lessons = maintain_wiki(settings, manifest)
    typer.echo(f"wiki pages={pages} lessons={lessons}")


@app.command()
def leakage(task: Path = typer.Option(...), root: Path = typer.Option(Path("."))) -> None:
    settings = _settings(root)
    if settings.condition != "c1":
        raise typer.BadParameter("leakage scan is available only for condition C1")
    matches = find_task_leakage(settings, task)
    if matches:
        for match in matches:
            typer.echo(f"LEAK: {match['marker']} in {match['path']}")
        raise typer.Exit(1)
    typer.echo("no leakage markers found")


@app.command()
def reset(
    confirm_run_id: str = typer.Option(..., help="Must exactly match configured run_id"),
    root: Path = typer.Option(Path(".")),
) -> None:
    settings = _settings(root)
    if settings.condition != "c1":
        raise typer.BadParameter("reset currently supports only condition C1")
    if confirm_run_id != settings.run_id:
        raise typer.BadParameter("--confirm-run-id does not match configured run_id")
    typer.echo(f"wiki reset={reset_wiki(settings)} run_id={settings.run_id}")


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


def _benchmark_paths(root: Path) -> tuple[Path, Path, Path]:
    base = _root(root) / "evaluations"
    return (
        base / "benchmark-lock.yaml",
        base / "runtime.yaml",
        base / "approvals" / "pilot-cost-v1.yaml",
    )


@benchmark_app.command("preflight")
def benchmark_preflight(
    manifest: Path = typer.Option(...),
    lock: Path | None = typer.Option(None),
    runtime: Path | None = typer.Option(None),
    root: Path = typer.Option(Path(".")),
) -> None:
    resolved_root = _root(root)
    default_lock, default_runtime, _ = _benchmark_paths(resolved_root)
    errors = preflight(resolved_root, manifest, lock or default_lock, runtime or default_runtime)
    if errors:
        for error in errors:
            typer.echo(f"ERROR: {error}")
        raise typer.Exit(1)
    typer.echo("benchmark preflight passed")


@benchmark_app.command("prepare")
def benchmark_prepare(root: Path = typer.Option(Path("."))) -> None:
    """Create the external cache skeleton; this command never downloads data."""
    typer.echo(prepare(_root(root)))


@benchmark_app.command("smoke")
def benchmark_smoke(
    manifest: Path = typer.Option(...),
    run_id: str = typer.Option(...),
    lock: Path | None = typer.Option(None),
    runtime: Path | None = typer.Option(None),
    root: Path = typer.Option(Path(".")),
) -> None:
    resolved_root = _root(root)
    default_lock, default_runtime, _ = _benchmark_paths(resolved_root)
    outcomes = run_stage(
        resolved_root,
        manifest,
        lock or default_lock,
        runtime or default_runtime,
        run_id,
        "smoke",
    )
    typer.echo(f"smoke attempts={len(outcomes)}")


@benchmark_app.command("estimate")
def benchmark_estimate(
    smoke_run_id: str = typer.Option(...),
    pilot_manifest: Path = typer.Option(...),
    output: Path = typer.Option(Path("evaluations/COST_ESTIMATE.md")),
    runtime: Path | None = typer.Option(None),
    root: Path = typer.Option(Path(".")),
) -> None:
    resolved_root = _root(root)
    _, default_runtime, _ = _benchmark_paths(resolved_root)
    typer.echo(
        build_cost_estimate(
            resolved_root,
            smoke_run_id,
            pilot_manifest,
            runtime or default_runtime,
            resolved_root / output,
        )
    )


@benchmark_app.command("run")
def benchmark_run(
    stage: str = typer.Option(...),
    manifest: Path = typer.Option(...),
    run_id: str = typer.Option(...),
    lock: Path | None = typer.Option(None),
    runtime: Path | None = typer.Option(None),
    approval: Path | None = typer.Option(None),
    estimate: Path | None = typer.Option(None),
    root: Path = typer.Option(Path(".")),
) -> None:
    resolved_root = _root(root)
    default_lock, default_runtime, default_approval = _benchmark_paths(resolved_root)
    outcomes = run_stage(
        resolved_root,
        manifest,
        lock or default_lock,
        runtime or default_runtime,
        run_id,
        stage,
        approval or default_approval,
        estimate or resolved_root / "evaluations" / "COST_ESTIMATE.md",
    )
    typer.echo(f"{stage} attempts={len(outcomes)}")


@benchmark_app.command("completeness")
def benchmark_completeness(
    run_id: str = typer.Option(...),
    expected_attempts: int | None = typer.Option(
        None, help="Deprecated; derived from run manifest"
    ),
    root: Path = typer.Option(Path(".")),
) -> None:
    errors = check_completeness(_root(root), run_id, expected_attempts)
    if errors:
        for error in errors:
            typer.echo(f"ERROR: {error}")
        raise typer.Exit(1)
    typer.echo("benchmark completeness passed")


@benchmark_app.command("reset")
def benchmark_reset(
    run_id: str = typer.Option(...),
    root: Path = typer.Option(Path(".")),
) -> None:
    typer.echo(f"benchmark reset={reset_run(_root(root), run_id)} run_id={run_id}")


@benchmark_app.command("analyze")
def benchmark_analyze(
    config: Path | None = typer.Option(None, help="Frozen analysis configuration YAML"),
    registry: Path | None = typer.Option(None, help="Complete frozen run registry YAML"),
    contract: Path | None = typer.Option(None, help="Deprecated combined config and registry YAML"),
    output: Path = typer.Option(..., help="Analysis output directory"),
    root: Path = typer.Option(Path(".")),
) -> None:
    """Generate raw-derived validation, effects, taxonomy, and decision artifacts."""
    if config is None and contract is None:
        raise typer.BadParameter("--config and --registry are required (or use legacy --contract)")
    if config is None:
        config = contract
    if config is None:
        raise typer.BadParameter("missing analysis config")
    typer.echo(analyze(_root(root), config, _root(root) / output, registry))


@benchmark_app.command("validate-analysis")
def benchmark_validate_analysis(
    registry: Path = typer.Option(..., help="Complete frozen run registry YAML"),
    config: Path = typer.Option(..., help="Frozen analysis configuration YAML"),
    output: Path = typer.Option(..., help="Validation output directory"),
    root: Path = typer.Option(Path(".")),
) -> None:
    typer.echo(validate_analysis(_root(root), config, registry, _root(root) / output))


@benchmark_app.command("decision")
def benchmark_decision(
    analysis_dir: Path = typer.Option(..., help="Completed analysis output directory"),
) -> None:
    try:
        typer.echo(decision_from_analysis(analysis_dir))
    except (OSError, ValueError) as error:
        typer.echo(f"ERROR: {error}")
        raise typer.Exit(1) from error


@benchmark_app.command("run-module")
def benchmark_run_module(
    module: str = typer.Option(...),
    manifest: Path = typer.Option(...),
    ablation_config: Path = typer.Option(...),
    root: Path = typer.Option(Path(".")),
) -> None:
    """Preflight a frozen C3 module pilot; official runs remain operator-controlled."""
    try:
        typer.echo(
            yaml.safe_dump(module_pilot_preflight(_root(root), module, manifest, ablation_config))
        )
    except ValueError as error:
        typer.echo(f"ERROR: {error}")
        raise typer.Exit(1) from error


@benchmark_app.command("analyze-module")
def benchmark_analyze_module(
    module: str = typer.Option(...),
    registry: Path = typer.Option(...),
    config: Path = typer.Option(...),
    output: Path = typer.Option(...),
    root: Path = typer.Option(Path(".")),
) -> None:
    """Analyze a frozen module registry and emit a PI decision memo."""
    resolved_root = _root(root)
    try:
        analysis_dir = analyze(resolved_root, config, resolved_root / output, registry)
        typer.echo(write_gain_cost_memo(analysis_dir, module))
    except (OSError, ValueError) as error:
        typer.echo(f"ERROR: {error}")
        raise typer.Exit(1) from error


@index_app.command("rebuild")
def index_rebuild(module: str = typer.Option(...), root: Path = typer.Option(Path("."))) -> None:
    settings = _settings(root)
    try:
        if module != "hybrid_retrieval":
            raise ValueError("only hybrid_retrieval is available before its PI gate")
        typer.echo(yaml.safe_dump(rebuild_hybrid_index(settings), sort_keys=False))
    except ValueError as error:
        typer.echo(f"ERROR: {error}")
        raise typer.Exit(1) from error


@index_app.command("verify")
def index_verify(module: str = typer.Option(...), root: Path = typer.Option(Path("."))) -> None:
    settings = _settings(root)
    try:
        if module != "hybrid_retrieval":
            raise ValueError("only hybrid_retrieval is available before its PI gate")
        typer.echo(yaml.safe_dump(verify_hybrid_index(settings), sort_keys=False))
    except ValueError as error:
        typer.echo(f"ERROR: {error}")
        raise typer.Exit(1) from error


@full_app.command("decision")
def full_decision(
    module: str = typer.Option(...),
    decision: str = typer.Option(...),
    evidence: Path = typer.Option(...),
    approved_by: str = typer.Option(...),
    root: Path = typer.Option(Path(".")),
) -> None:
    try:
        typer.echo(record_decision(_root(root), module, decision, evidence, approved_by))
    except ValueError as error:
        typer.echo(f"ERROR: {error}")
        raise typer.Exit(1) from error


@full_app.command("gate")
def full_gate(next_module: str = typer.Option(...), root: Path = typer.Option(Path("."))) -> None:
    try:
        typer.echo(yaml.safe_dump(check_gate(_root(root), next_module), sort_keys=False))
    except ValueError as error:
        typer.echo(f"ERROR: {error}")
        raise typer.Exit(1) from error
