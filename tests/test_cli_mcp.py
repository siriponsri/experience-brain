from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from experience_brain.cli import app
from experience_brain.mcp_server import SERVER_NAME


def test_cli_help_and_status(brain_root: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "process-session" in result.output
    result = runner.invoke(app, ["status", "--root", str(brain_root)])
    assert result.exit_code == 0
    assert "events=0" in result.output


def test_mcp_server_name() -> None:
    assert SERVER_NAME == "experience-brain"
