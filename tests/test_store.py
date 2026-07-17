from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from experience_brain.models import Actor, Event, EventType, Experience
from experience_brain.store import append_event, append_experience, lint_store, read_events


def _event(identifier: str = "EVT-1") -> Event:
    return Event(
        id=identifier,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        type=EventType.user_message,
        actor=Actor.owner,
        project="demo",
        session_id="S-1",
        content="Build the thing",
    )


def test_append_only_duplicate_and_conflict(brain_root: Path) -> None:
    assert append_event(brain_root, _event()) == (1, 0)
    before = (brain_root / "data" / "events.jsonl").read_bytes()
    assert append_event(brain_root, _event()) == (0, 1)
    assert (brain_root / "data" / "events.jsonl").read_bytes() == before
    with pytest.raises(ValueError, match="conflicts"):
        append_event(brain_root, _event().model_copy(update={"content": "different"}))
    assert (brain_root / "data" / "events.jsonl").read_bytes() == before


def test_lint_detects_tampering_and_missing_evidence(brain_root: Path) -> None:
    append_event(brain_root, _event())
    experience = Experience(
        id="EXP-1",
        project="demo",
        source_project="demo",
        lesson="Use the evidence.",
        evidence_event_ids=["EVT-1"],
    )
    append_experience(brain_root, experience)
    assert lint_store(brain_root) == []
    path = brain_root / "data" / "events.jsonl"
    path.write_text(path.read_text(encoding="utf-8").replace("Build", "Break", 1), encoding="utf-8")
    assert any("invalid" in error for error in lint_store(brain_root))


def test_jsonl_schema_validation(brain_root: Path) -> None:
    append_event(brain_root, _event())
    lines = (brain_root / "data" / "events.jsonl").read_text().splitlines()
    rows = [json.loads(line) for line in lines]
    assert rows[0]["previous_hash"] == ""
    assert read_events(brain_root)[0].id == "EVT-1"
