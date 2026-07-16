from __future__ import annotations

import json
from pathlib import Path

import pytest

from experience_brain.event_store import ingest_events, read_events


def test_append_only_duplicate_and_conflict(brain_root: Path, fixtures: Path) -> None:
    added, skipped = ingest_events(brain_root, fixtures / "events.jsonl")
    assert (added, skipped) == (4, 0)
    prefix = (brain_root / "events" / "events.jsonl").read_bytes()
    assert ingest_events(brain_root, fixtures / "events.jsonl") == (0, 4)
    assert (brain_root / "events" / "events.jsonl").read_bytes() == prefix
    event = json.loads((fixtures / "events.jsonl").read_text(encoding="utf-8").splitlines()[0])
    event["content"] = "different"
    conflict = brain_root / "conflict.jsonl"
    conflict.write_text(json.dumps(event) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="conflicts"):
        ingest_events(brain_root, conflict)
    assert (brain_root / "events" / "events.jsonl").read_bytes() == prefix
    assert len(read_events(brain_root)) == 4
