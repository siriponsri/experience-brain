from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .util import canonical_json, sha256_text

REQUIRED_EVENT_FIELDS = {
    "id",
    "timestamp",
    "run_id",
    "task_id",
    "type",
    "actor",
    "content",
    "trust",
    "cost",
}
TRUST_VALUES = {"first_party_execution", "untrusted_external_content"}


def _event_path(root: Path) -> Path:
    return root / "events" / "events.jsonl"


def read_events(root: Path) -> list[dict[str, Any]]:
    path = _event_path(root)
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            loaded = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSONL event at line {number}") from error
        if not isinstance(loaded, dict):
            raise ValueError(f"event at line {number} is not an object")
        events.append(loaded)
    return events


def validate_event(event: dict[str, Any]) -> None:
    missing = REQUIRED_EVENT_FIELDS - event.keys()
    if missing:
        raise ValueError(f"event {event.get('id', '<unknown>')} missing {sorted(missing)}")
    if not isinstance(event["id"], str) or not event["id"].strip():
        raise ValueError("event id must be a non-empty string")
    if event["trust"] not in TRUST_VALUES:
        raise ValueError(f"event {event['id']} has invalid trust label")
    if not isinstance(event["cost"], dict):
        raise ValueError(f"event {event['id']} cost must be an object")
    if event["trust"] == "untrusted_external_content" and "skill_candidate" in event:
        raise ValueError("untrusted external content cannot supply a skill candidate")
    if event["type"] == "verifier":
        verifier = event.get("verifier")
        if not isinstance(verifier, dict) or not isinstance(verifier.get("success"), bool):
            raise ValueError(f"verifier event {event['id']} needs verifier.success")
        if not isinstance(verifier.get("score"), (int, float)):
            raise ValueError(f"verifier event {event['id']} needs verifier.score")


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in event.items()
        if key not in {"previous_hash", "record_hash", "payload_hash", "ingested_at"}
    }


def ingest_events(root: Path, input_path: Path) -> tuple[int, int]:
    incoming: list[dict[str, Any]] = []
    for number, line in enumerate(input_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid input JSONL at line {number}") from error
        if not isinstance(event, dict):
            raise ValueError(f"input event at line {number} is not an object")
        validate_event(event)
        incoming.append(event)

    existing = read_events(root)
    by_id = {str(event["id"]): str(event["payload_hash"]) for event in existing}
    staged: list[dict[str, Any]] = []
    seen = dict(by_id)
    for event in incoming:
        payload_hash = sha256_text(canonical_json(_payload(event)))
        identifier = str(event["id"])
        if identifier in seen:
            if seen[identifier] != payload_hash:
                raise ValueError(f"event id {identifier} conflicts with append-only log")
            continue
        seen[identifier] = payload_hash
        staged.append(_payload(event))

    previous_hash = str(existing[-1].get("record_hash", "")) if existing else ""
    records: list[str] = []
    for event in staged:
        record = dict(event)
        record["payload_hash"] = sha256_text(canonical_json(event))
        record["previous_hash"] = previous_hash
        record["ingested_at"] = datetime.now(UTC).isoformat()
        record["record_hash"] = sha256_text(
            canonical_json({key: value for key, value in record.items() if key != "record_hash"})
        )
        previous_hash = record["record_hash"]
        records.append(canonical_json(record))

    if records:
        path = _event_path(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(records) + "\n")
    return len(records), len(incoming) - len(records)
