from __future__ import annotations

from pathlib import Path

from experience_brain.config import load_settings
from experience_brain.event_store import ingest_events
from experience_brain.linting import lint


def test_lint_detects_event_tampering(brain_root: Path, fixtures: Path) -> None:
    ingest_events(brain_root, fixtures / "events.jsonl")
    path = brain_root / "events" / "events.jsonl"
    path.write_text(
        path.read_text(encoding="utf-8").replace("focused test", "tampered test", 1),
        encoding="utf-8",
    )
    assert any("invalid record hash" in error for error in lint(load_settings(brain_root)))
