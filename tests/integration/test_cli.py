from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from experience_brain.cli import app


def test_cli_end_to_end(brain_root: Path, fixtures: Path) -> None:
    runner = CliRunner()
    common = ["--root", str(brain_root)]
    result = runner.invoke(
        app, ["ingest", str(fixtures / "events.jsonl"), "--kind", "events", *common]
    )
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["consolidate", *common])
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["retrieve", "--task", str(fixtures / "task.yaml"), *common])
    assert result.exit_code == 0, result.output
    assert "skill_focused_test_then_patch" in result.output
    result = runner.invoke(
        app, ["capsule", "--task", str(fixtures / "task.yaml"), "--budget", "1000", *common]
    )
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["report", *common])
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["lint", *common])
    assert result.exit_code == 0, result.output


def test_cli_source_ingest(brain_root: Path, fixtures: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "ingest",
            str(fixtures / "untrusted_source.md"),
            "--kind",
            "source",
            "--metadata",
            str(fixtures / "untrusted_source.yaml"),
            "--root",
            str(brain_root),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "src_untrusted_demo" in result.output
