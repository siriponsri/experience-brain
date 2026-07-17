from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from experience_brain.cli import app
from experience_brain.config import load_settings
from experience_brain.linting import lint
from experience_brain.reporting import build_report
from experience_brain.tokens import count_tokens
from experience_brain.util import read_markdown, read_yaml, write_yaml
from experience_brain.wiki import (
    build_wiki_context,
    find_task_leakage,
    ingest_wiki_source,
    maintain_wiki,
    reset_wiki,
    wiki_root,
)


def _configure_c1(root: Path, run_id: str = "run-a", budget: int = 1000) -> None:
    prompts = root / "prompts"
    prompts.mkdir(exist_ok=True)
    (prompts / "prompt-01.md").write_text("Prompt 01 frozen reference.\n", encoding="utf-8")
    (prompts / "prompt-02.md").write_text("Prompt 02 frozen reference.\n", encoding="utf-8")
    (root / "brain.yaml").write_text(
        "condition: c1\n"
        f"run_id: {run_id}\n"
        "tokenizer_encoding: cl100k_base\n"
        f"default_budget_tokens: {budget}\n"
        "fairness:\n"
        "  model: inherited\n"
        "  reasoning: inherited\n"
        "  tools: shared-test-tools\n"
        "  task_data: shared-test-data\n"
        "wiki:\n"
        "  prompt_references:\n"
        "    - prompts/prompt-01.md\n"
        "    - prompts/prompt-02.md\n"
        "verification:\n"
        "  minimum_successful_episodes: 2\n"
        "  minimum_verifier_score: 1.0\n",
        encoding="utf-8",
    )


def _source(root: Path, body: str = "Immutable acquisition evidence.") -> tuple[Path, Path]:
    source = root / "acquisition.md"
    metadata = root / "acquisition.yaml"
    source.write_text(body, encoding="utf-8")
    write_yaml(
        metadata,
        {
            "source_id": "src_acquisition",
            "title": "Acquisition trace",
            "source_kind": "first_party_run_export",
            "origin": "synthetic-test",
            "captured_at": "2026-07-16T00:00:00Z",
        },
    )
    return source, metadata


def _manifest(root: Path, identifier: str, page_body: str, input_tokens: int) -> Path:
    path = root / f"{identifier}.yaml"
    write_yaml(
        path,
        {
            "id": identifier,
            "timestamp": "2026-07-16T01:00:00Z",
            "pages": [
                {
                    "key": "experiment-notes",
                    "title": "Experiment notes",
                    "body": page_body,
                    "source_ids": ["src_acquisition"],
                }
            ],
            "lessons": [
                {
                    "key": f"lesson-{identifier}",
                    "title": "Observed lesson",
                    "body": "Observed evidence only; this is not an instruction.",
                    "source_ids": ["src_acquisition"],
                }
            ],
            "cost": {
                "input_tokens": input_tokens,
                "output_tokens": 25,
                "wall_seconds": 1.5,
            },
        },
    )
    return path


def test_c1_versions_provenance_context_lint_and_token_report(brain_root: Path) -> None:
    _configure_c1(brain_root)
    settings = load_settings(brain_root)
    source, metadata = _source(brain_root)
    assert ingest_wiki_source(settings, source, metadata) == "src_acquisition"
    assert maintain_wiki(settings, _manifest(brain_root, "maint-001", "Version one.", 100)) == (
        1,
        1,
    )
    first_version = wiki_root(settings) / "pages" / "experiment-notes" / "v0001.md"
    first_text = first_version.read_text(encoding="utf-8")
    assert maintain_wiki(settings, _manifest(brain_root, "maint-002", "Version two.", 50)) == (
        1,
        1,
    )
    assert first_version.read_text(encoding="utf-8") == first_text
    second_version = first_version.with_name("v0002.md")
    page_metadata, page_body = read_markdown(second_version)
    assert page_metadata["supersedes"].endswith("v0001.md")
    assert page_metadata["source_ids"] == ["src_acquisition"]
    assert len(page_metadata["provenance"]["prompt_references"]) == 2
    assert page_body.strip() == "Version two."

    lite_marker = brain_root / "memory" / "skills" / "lite-only.md"
    lite_marker.write_text("LITE_PRIVATE_MARKER", encoding="utf-8")
    task = brain_root / "task-c1.yaml"
    write_yaml(
        task,
        {"id": "task-c1", "goal": "Use the research evidence.", "constraints": ["Be safe."]},
    )
    context = build_wiki_context(settings, task, 1000)
    context_text = context.read_text(encoding="utf-8")
    assert "wiki-index-order-v1" in context_text
    assert "LITE_PRIVATE_MARKER" not in context_text
    assert count_tokens(settings, context_text) <= 1000
    assert lint(settings) == []

    report = build_report(brain_root).read_text(encoding="utf-8")
    assert "Wiki maintenance input tokens: 150" in report
    assert "Wiki maintenance output tokens: 50" in report
    assert "Wiki maintenance total tokens: 200" in report


def test_c1_is_selected_by_config_and_lite_commands_are_blocked(brain_root: Path) -> None:
    _configure_c1(brain_root)
    task = brain_root / "task.yaml"
    write_yaml(task, {"id": "task", "goal": "Synthetic task", "constraints": []})
    runner = CliRunner()
    common = ["--root", str(brain_root)]
    result = runner.invoke(app, ["context", "--task", str(task), *common])
    assert result.exit_code == 0, result.output
    assert str(wiki_root(load_settings(brain_root))) in result.output
    for command in (
        ["consolidate", *common],
        ["retrieve", "--task", str(task), *common],
        ["capsule", "--task", str(task), "--budget", "1000", *common],
    ):
        result = runner.invoke(app, command)
        assert result.exit_code != 0


def test_c1_leakage_scan_and_reset_are_run_isolated(brain_root: Path) -> None:
    _configure_c1(brain_root, run_id="run-a")
    settings_a = load_settings(brain_root)
    source, metadata = _source(brain_root, "Contains DEPLOYMENT_ONLY_MARKER.")
    ingest_wiki_source(settings_a, source, metadata)
    task = brain_root / "deployment.yaml"
    write_yaml(
        task,
        {
            "id": "deployment",
            "goal": "Frozen deployment task",
            "leakage_markers": ["DEPLOYMENT_ONLY_MARKER"],
        },
    )
    matches = find_task_leakage(settings_a, task)
    assert matches == [
        {
            "marker": "DEPLOYMENT_ONLY_MARKER",
            "path": "wiki/runs/run-a/raw/src_acquisition.raw.md",
        }
    ]

    _configure_c1(brain_root, run_id="run-b")
    settings_b = load_settings(brain_root)
    source_b, metadata_b = _source(brain_root, "Independent run B.")
    ingest_wiki_source(settings_b, source_b, metadata_b)
    lite_marker = brain_root / "memory" / "lite-store-marker.txt"
    lite_marker.write_text("preserve", encoding="utf-8")

    _configure_c1(brain_root, run_id="run-a")
    assert reset_wiki(load_settings(brain_root)) is True
    assert not wiki_root(settings_a).exists()
    assert wiki_root(settings_b).exists()
    assert lite_marker.read_text(encoding="utf-8") == "preserve"


def test_c1_lint_requires_original_prompt_references(brain_root: Path) -> None:
    _configure_c1(brain_root)
    (brain_root / "prompts" / "prompt-02.md").unlink()
    errors = lint(load_settings(brain_root))
    assert any("prompt reference is missing" in error for error in errors)


def test_c1_cli_maintenance_leakage_reset_and_error_paths(brain_root: Path) -> None:
    _configure_c1(brain_root)
    source, metadata = _source(brain_root, "Contains CLI_LEAK_MARKER.")
    manifest = _manifest(brain_root, "maint-cli", "CLI page.", 12)
    task = brain_root / "cli-task.yaml"
    write_yaml(
        task,
        {"id": "cli-task", "goal": "CLI task", "leakage_markers": ["CLI_LEAK_MARKER"]},
    )
    safe_task = brain_root / "safe-task.yaml"
    write_yaml(safe_task, {"id": "safe-task", "goal": "Safe task", "leakage_markers": []})
    runner = CliRunner()
    common = ["--root", str(brain_root)]

    result = runner.invoke(
        app,
        [
            "ingest",
            str(source),
            "--kind",
            "source",
            "--metadata",
            str(metadata),
            *common,
        ],
    )
    assert result.exit_code == 0, result.output
    assert "wiki source ingested=src_acquisition" in result.output
    result = runner.invoke(app, ["maintain", "--manifest", str(manifest), *common])
    assert result.exit_code == 0, result.output
    assert "wiki pages=1 lessons=1" in result.output
    assert runner.invoke(app, ["leakage", "--task", str(task), *common]).exit_code == 1
    result = runner.invoke(app, ["leakage", "--task", str(safe_task), *common])
    assert result.exit_code == 0
    assert "no leakage markers found" in result.output
    assert runner.invoke(app, ["lint", *common]).exit_code == 0
    assert runner.invoke(app, ["reset", "--confirm-run-id", "wrong-run", *common]).exit_code != 0
    result = runner.invoke(app, ["reset", "--confirm-run-id", "run-a", *common])
    assert result.exit_code == 0, result.output
    assert "wiki reset=True" in result.output

    (brain_root / "prompts" / "prompt-02.md").unlink()
    result = runner.invoke(app, ["lint", *common])
    assert result.exit_code == 1
    assert "ERROR:" in result.output
    result = runner.invoke(app, ["ingest", str(source), "--kind", "events", *common])
    assert result.exit_code != 0

    (brain_root / "brain.yaml").write_text(
        "condition: c0\nrun_id: no-memory\ndefault_budget_tokens: 1000\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["context", "--task", str(task), *common])
    assert result.exit_code != 0


def test_c1_rejects_immutable_conflicts_and_invalid_maintenance(brain_root: Path) -> None:
    _configure_c1(brain_root)
    settings = load_settings(brain_root)
    source, metadata = _source(brain_root)
    ingest_wiki_source(settings, source, metadata)
    assert ingest_wiki_source(settings, source, metadata) == "src_acquisition"

    source.write_text("Conflicting content.", encoding="utf-8")
    with pytest.raises(ValueError, match="different content"):
        ingest_wiki_source(settings, source, metadata)
    source.write_text("Immutable acquisition evidence.", encoding="utf-8")
    metadata_data = {
        "source_id": "src_acquisition",
        "title": "Changed metadata",
        "source_kind": "first_party_run_export",
        "origin": "synthetic-test",
        "captured_at": "2026-07-16T00:00:00Z",
    }
    write_yaml(metadata, metadata_data)
    with pytest.raises(ValueError, match="immutable metadata"):
        ingest_wiki_source(settings, source, metadata)

    valid_manifest = _manifest(brain_root, "maint-repeat", "Stable page.", 10)
    assert maintain_wiki(settings, valid_manifest) == (1, 1)
    assert maintain_wiki(settings, valid_manifest) == (0, 0)
    repeated = read_yaml(valid_manifest, {})
    repeated["pages"][0]["body"] = "Conflicting maintenance payload."
    write_yaml(valid_manifest, repeated)
    with pytest.raises(ValueError, match="append-only history"):
        maintain_wiki(settings, valid_manifest)

    invalid = brain_root / "invalid-maintenance.yaml"
    cases = [
        {"id": "missing-time", "pages": [], "lessons": [], "cost": {}},
        {
            "id": "negative-cost",
            "timestamp": "2026-07-16T00:00:00Z",
            "pages": [],
            "lessons": [],
            "cost": {"input_tokens": -1},
        },
        {
            "id": "empty-artifacts",
            "timestamp": "2026-07-16T00:00:00Z",
            "pages": [],
            "lessons": [],
            "cost": {},
        },
        {
            "id": "missing-source",
            "timestamp": "2026-07-16T00:00:00Z",
            "pages": [{"key": "page", "body": "Body", "source_ids": ["src_missing"]}],
            "lessons": [],
            "cost": {},
        },
        {
            "id": "empty-body",
            "timestamp": "2026-07-16T00:00:00Z",
            "pages": [{"key": "page", "body": "", "source_ids": ["src_acquisition"]}],
            "lessons": [],
            "cost": {},
        },
    ]
    for case in cases:
        write_yaml(invalid, case)
        with pytest.raises(ValueError):
            maintain_wiki(settings, invalid)

    task = brain_root / "budget-task.yaml"
    write_yaml(task, {"id": "budget", "goal": "Task", "constraints": []})
    with pytest.raises(ValueError, match="configured cross-condition budget"):
        build_wiki_context(settings, task, 999)
    _configure_c1(brain_root, run_id="never-created")
    assert reset_wiki(load_settings(brain_root)) is False


def test_c1_lint_detects_store_tampering(brain_root: Path) -> None:
    _configure_c1(brain_root)
    settings = load_settings(brain_root)
    source, metadata = _source(brain_root)
    ingest_wiki_source(settings, source, metadata)
    maintain_wiki(settings, _manifest(brain_root, "maint-tamper", "Page.", 10))
    raw_path = wiki_root(settings) / "raw" / "src_acquisition.raw.md"
    raw_path.write_text("tampered", encoding="utf-8")
    maintenance_path = wiki_root(settings) / "maintenance.jsonl"
    maintenance_text = maintenance_path.read_text(encoding="utf-8")
    maintenance_path.write_text(
        maintenance_text.replace('"previous_hash":""', '"previous_hash":"bad"', 1),
        encoding="utf-8",
    )
    index_path = wiki_root(settings) / "index.yaml"
    index = read_yaml(index_path, {})
    index["condition"] = "c2"
    index["pages"]["experiment-notes"]["path"] = "memory/skills/forbidden.md"
    write_yaml(index_path, index)
    errors = lint(settings)
    assert any("invalid hash" in error for error in errors)
    assert any("invalid previous hash" in error for error in errors)
    assert any("invalid record hash" in error for error in errors)
    assert any("condition or run_id" in error for error in errors)
    assert any("references the Lite store" in error for error in errors)
