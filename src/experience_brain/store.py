from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel

from .models import (
    SCHEMA_VERSION,
    Authority,
    Event,
    Experience,
    ExperienceStatus,
    Knowledge,
    KnowledgeStatus,
    Provenance,
    StoredEvent,
    StoredExperience,
    StoredKnowledge,
)

T = TypeVar("T", Event, Experience, Knowledge)
S = TypeVar("S", StoredEvent, StoredExperience, StoredKnowledge)


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def data_dir(root: Path) -> Path:
    return root / "data"


def events_path(root: Path) -> Path:
    return data_dir(root) / "events.jsonl"


def experiences_path(root: Path) -> Path:
    return data_dir(root) / "experiences.jsonl"


def knowledge_path(root: Path) -> Path:
    return data_dir(root) / "knowledge.jsonl"


def inbox_dir(root: Path) -> Path:
    return root / "inbox"


def ensure_store(root: Path) -> None:
    data_dir(root).mkdir(parents=True, exist_ok=True)
    for path in (events_path(root), experiences_path(root), knowledge_path(root)):
        if not path.exists():
            path.write_text("", encoding="utf-8")
    (root / "reports").mkdir(parents=True, exist_ok=True)
    inbox_dir(root).mkdir(parents=True, exist_ok=True)


def _payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in record.items()
        if key not in {"payload_hash", "previous_hash", "record_hash", "ingested_at"}
    }


class JsonlStore(Generic[T, S]):
    def __init__(self, path: Path, model: type[T], stored_model: type[S]) -> None:
        self.path = path
        self.model: type[T] = model
        self.stored_model: type[S] = stored_model

    def read(self) -> list[S]:
        return [record for record, _ in self._read_raw()]

    def _read_raw(self) -> list[tuple[S, dict[str, Any]]]:
        if not self.path.exists():
            return []
        records: list[tuple[S, dict[str, Any]]] = []
        for number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                loaded = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSONL at {self.path}:{number}") from error
            if not isinstance(loaded, dict):
                raise ValueError(f"record at {self.path}:{number} is not an object")
            records.append((self.stored_model.model_validate(loaded), loaded))
        return records

    def append(self, items: Iterable[T]) -> tuple[int, int]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existing = self.read()
        by_id = {record.id: record.payload_hash for record in existing}
        previous_hash = existing[-1].record_hash if existing else ""
        lines: list[str] = []
        added = 0
        skipped = 0
        for item in items:
            validated = self.model.model_validate(item)
            payload = _dump_model(validated)
            payload_hash = sha256_text(canonical_json(payload))
            if validated.id in by_id:
                if by_id[validated.id] != payload_hash:
                    raise ValueError(f"record id {validated.id} conflicts with append-only log")
                skipped += 1
                continue
            record = dict(payload)
            record["payload_hash"] = payload_hash
            record["previous_hash"] = previous_hash
            record["ingested_at"] = datetime.now(UTC).isoformat()
            record_without_hash = {
                key: value for key, value in record.items() if key != "record_hash"
            }
            record["record_hash"] = sha256_text(canonical_json(record_without_hash))
            self.stored_model.model_validate(record)
            previous_hash = str(record["record_hash"])
            by_id[validated.id] = payload_hash
            lines.append(canonical_json(record))
            added += 1
        if lines:
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write("\n".join(lines) + "\n")
        return added, skipped


def _dump_model(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json", exclude_none=True)


def event_store(root: Path) -> JsonlStore[Event, StoredEvent]:
    ensure_store(root)
    return JsonlStore(events_path(root), Event, StoredEvent)


def experience_store(root: Path) -> JsonlStore[Experience, StoredExperience]:
    ensure_store(root)
    return JsonlStore(experiences_path(root), Experience, StoredExperience)


def knowledge_store(root: Path) -> JsonlStore[Knowledge, StoredKnowledge]:
    ensure_store(root)
    return JsonlStore(knowledge_path(root), Knowledge, StoredKnowledge)


def append_event(root: Path, event: Event) -> tuple[int, int]:
    return event_store(root).append([event])


def append_experience(root: Path, experience: Experience) -> tuple[int, int]:
    return experience_store(root).append([experience])


def append_knowledge(root: Path, knowledge: Knowledge) -> tuple[int, int]:
    return knowledge_store(root).append([knowledge])


def read_events(root: Path) -> list[StoredEvent]:
    return event_store(root).read()


def read_experiences(root: Path) -> list[StoredExperience]:
    return experience_store(root).read()


def read_knowledge(root: Path) -> list[StoredKnowledge]:
    return knowledge_store(root).read()


def current_experiences(root: Path) -> list[StoredExperience]:
    """Return current lineage heads while retaining all records in the JSONL log."""
    experiences = read_experiences(root)
    replaced = {
        replaced_id
        for experience in experiences
        for replaced_id in (experience.supersedes, experience.invalidates)
        if replaced_id
    }
    return [experience for experience in experiences if experience.id not in replaced]


def current_knowledge(root: Path) -> list[StoredKnowledge]:
    """Return current Knowledge lineage heads while retaining full JSONL history."""
    knowledge_items = read_knowledge(root)
    replaced = {
        replaced_id
        for knowledge in knowledge_items
        for replaced_id in (knowledge.supersedes, knowledge.invalidates)
        if replaced_id
    }
    return [knowledge for knowledge in knowledge_items if knowledge.id not in replaced]


def pending_review_experiences(root: Path) -> list[StoredExperience]:
    return [
        experience
        for experience in current_experiences(root)
        if experience.status == ExperienceStatus.proposed
    ]


def reviewable_knowledge(root: Path) -> list[StoredKnowledge]:
    return [
        knowledge
        for knowledge in current_knowledge(root)
        if knowledge.status == KnowledgeStatus.proposed
    ]


ReviewAction = Literal["confirm", "edit_confirm", "invalidate", "retire"]


def review_experience(
    root: Path,
    experience_id: str,
    *,
    action: ReviewAction,
    situation: str | None = None,
    goal: str | None = None,
    lesson: str | None = None,
    run_id: str | None = None,
) -> Experience:
    """Append an owner review decision as a new Experience lineage record."""
    matches = [
        experience for experience in current_experiences(root) if experience.id == experience_id
    ]
    if not matches:
        raise ValueError(f"unknown or non-current experience: {experience_id}")
    current = matches[0]
    now = datetime.now(UTC)
    timestamp = now.strftime("%Y%m%d%H%M%S%f")
    digest = sha256(f"{experience_id}:{action}:{timestamp}".encode()).hexdigest()[:8].upper()
    revision_id = f"{experience_id}-REV-{timestamp}-{digest}"
    status = {
        "confirm": ExperienceStatus.confirmed,
        "edit_confirm": ExperienceStatus.confirmed,
        "invalidate": ExperienceStatus.invalidated,
        "retire": ExperienceStatus.retired,
    }[action]
    metadata = dict(current.metadata)
    metadata.update(
        {
            "lineage_root": metadata.get("lineage_root", current.id),
            "review_action": action,
            "reviewed_experience_id": current.id,
        }
    )
    updates: dict[str, Any] = {
        "id": revision_id,
        "schema_version": SCHEMA_VERSION,
        "updated_at": now.isoformat(),
        "status": status.value,
        "authority": (
            Authority.owner.value
            if action in {"confirm", "edit_confirm"}
            else current.authority.value
        ),
        "owner_confirmed": action in {"confirm", "edit_confirm"},
        "supersedes": current.id if action != "invalidate" else None,
        "invalidates": current.id if action == "invalidate" else None,
        "metadata": metadata,
        "provenance": Provenance(
            agent="owner",
            experiment_id="EXP-03.1",
            run_id=run_id or f"RUN-{timestamp}",
            source="owner_dashboard",
            extra={
                "review_action": action,
                "source_record_hash": current.record_hash,
                "source_experience_id": current.id,
            },
        ).model_dump(mode="json"),
    }
    if action == "edit_confirm":
        for field, value in {"situation": situation, "goal": goal, "lesson": lesson}.items():
            if value is not None:
                updates[field] = value.strip()
        if not str(updates.get("lesson", current.lesson)).strip():
            raise ValueError("lesson must be non-empty")
    payload = current.model_dump(
        mode="json",
        exclude={"payload_hash", "previous_hash", "record_hash", "ingested_at"},
    )
    reviewed = Experience.model_validate(payload | updates)
    append_experience(root, reviewed)
    return reviewed


def lint_store(root: Path) -> list[str]:
    errors: list[str] = []
    for label, store in (
        ("event", event_store(root)),
        ("experience", experience_store(root)),
        ("knowledge", knowledge_store(root)),
    ):
        previous = ""
        ids: set[str] = set()
        for record, raw_record in store._read_raw():
            payload = _payload(raw_record)
            if record.id in ids:
                errors.append(f"{label} {record.id} is duplicated")
            ids.add(record.id)
            expected_payload = sha256_text(canonical_json(payload))
            if record.payload_hash != expected_payload:
                errors.append(f"{label} {record.id} has invalid payload hash")
            if record.previous_hash != previous:
                errors.append(f"{label} {record.id} has invalid previous hash")
            expected_record = sha256_text(
                canonical_json(
                    {key: value for key, value in raw_record.items() if key != "record_hash"}
                )
            )
            if record.record_hash != expected_record:
                errors.append(f"{label} {record.id} has invalid record hash")
            previous = record.record_hash
    event_ids = {event.id for event in read_events(root)}
    for experience in read_experiences(root):
        missing = sorted(set(experience.evidence_event_ids) - event_ids)
        if missing:
            errors.append(f"experience {experience.id} references missing events: {missing}")
    return errors
