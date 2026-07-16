from __future__ import annotations

from pathlib import Path

from experience_brain.capsule import build_capsule, count_tokens
from experience_brain.config import load_settings
from experience_brain.consolidation import consolidate
from experience_brain.event_store import ingest_events
from experience_brain.linting import lint
from experience_brain.reporting import build_report
from experience_brain.retrieval import retrieve
from experience_brain.util import read_markdown, read_yaml


def test_event_to_episode_to_verified_skill_to_capsule(brain_root: Path, fixtures: Path) -> None:
    settings = load_settings(brain_root)
    assert ingest_events(brain_root, fixtures / "events.jsonl") == (4, 0)
    assert consolidate(settings) == (2, 1)
    assert consolidate(settings) == (0, 0)
    index = read_yaml(brain_root / "memory" / "skills" / "index.yaml", {"skills": {}})
    entry = index["skills"]["skill_focused_test_then_patch"]
    assert entry["status"] == "verified"
    assert len(entry["evidence_episode_ids"]) == 2
    results = retrieve(brain_root, fixtures / "task.yaml")
    assert [item["id"] for item in results] == ["skill_focused_test_then_patch"]
    capsule = build_capsule(settings, fixtures / "task.yaml", 1000)
    metadata, body = read_markdown(capsule)
    assert metadata["estimated_tokens"] <= 1000
    assert count_tokens(settings, capsule.read_text(encoding="utf-8")) <= 1000
    assert body.startswith("# Task contract")
    report = build_report(brain_root)
    assert "skill_focused_test_then_patch" in report.read_text(encoding="utf-8")
    assert lint(settings) == []
