from __future__ import annotations

import re
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from .capture import record_event
from .models import (
    Actor,
    Event,
    EventType,
    Experience,
    ExperienceStatus,
    Provenance,
    StoredExperience,
)
from .store import read_experiences

AUTHORITY_WEIGHT = {
    "owner": 40,
    "project_rule": 30,
    "outcome_feedback": 20,
    "repeated_success": 10,
}
ACTIVE_STATUSES = {
    ExperienceStatus.active.value,
    ExperienceStatus.confirmed.value,
    ExperienceStatus.refined.value,
}


def _words(text: str) -> set[str]:
    return {word.casefold() for word in re.findall(r"[A-Za-z0-9_]+", text)}


def _sort_key(item: dict[str, object]) -> tuple[int, str]:
    score = item["score"]
    if not isinstance(score, int):
        raise TypeError("retrieval score must be an integer")
    return -score, str(item["id"])


def effective_experiences(root: Path) -> list[StoredExperience]:
    experiences = read_experiences(root)
    replaced = {
        value
        for experience in experiences
        for value in (experience.supersedes, experience.invalidates)
        if value
    }
    return [
        experience
        for experience in experiences
        if experience.id not in replaced and experience.status.value in ACTIVE_STATUSES
    ]


def retrieve_experience(
    root: Path, query: str, *, project: str | None = None, limit: int = 5
) -> list[dict[str, object]]:
    if limit <= 0:
        raise ValueError("limit must be positive")
    query_words = _words(query)
    scored: list[dict[str, object]] = []
    for experience in effective_experiences(root):
        text = " ".join(
            [
                experience.situation,
                experience.goal,
                experience.action,
                experience.tool_context or "",
                experience.decision or "",
                experience.outcome or "",
                experience.feedback or "",
                experience.lesson,
            ]
        )
        overlap = len(query_words & _words(text))
        if overlap == 0:
            continue
        project_score = 8 if project and experience.project == project else 0
        external_penalty = 3 if project and experience.project != project else 0
        score = (
            overlap * 4
            + project_score
            + AUTHORITY_WEIGHT[experience.authority.value]
            + int(experience.confidence * 10)
            + experience.success_count * 2
            - experience.failure_count
            - external_penalty
        )
        scored.append(
            {
                "id": experience.id,
                "score": score,
                "experience": experience,
                "label": (
                    "External Project Experience"
                    if project and experience.project != project
                    else "Project Experience"
                ),
                "evidence_event_ids": experience.evidence_event_ids,
            }
        )
    scored.sort(key=_sort_key)
    return scored[:limit]


def format_briefing(items: list[dict[str, object]]) -> str:
    if not items:
        return "No relevant experience found."
    lines: list[str] = []
    for item in items:
        score = item["score"]
        if not isinstance(score, int):
            raise TypeError("retrieval score must be an integer")
        experience = item["experience"]
        assert isinstance(experience, StoredExperience)
        lines.extend(
            [
                f"### {item['label']}: {experience.id}",
                f"- Score: {score}",
                f"- Lesson: {experience.lesson}",
                f"- Evidence events: {', '.join(experience.evidence_event_ids)}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def mark_retrieved(root: Path, experience_id: str, session_id: str) -> None:
    from .store import append_experience

    matches = [item for item in effective_experiences(root) if item.id == experience_id]
    if not matches:
        raise ValueError(f"unknown experience: {experience_id}")
    current = matches[-1]
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    digest = sha256(f"{experience_id}:{session_id}:{timestamp}".encode()).hexdigest()[:8].upper()
    metadata = dict(current.metadata)
    metadata["lineage_root"] = metadata.get("lineage_root", current.id)
    refined = Experience.model_validate(
        current.model_dump(
            mode="json",
            exclude={"payload_hash", "previous_hash", "record_hash", "ingested_at"},
        )
        | {
            "id": f"{current.id}-USE-{timestamp}-{digest}",
            "updated_at": datetime.now(UTC).isoformat(),
            "last_used_at": datetime.now(UTC).isoformat(),
            "last_used_session_id": session_id,
            "supersedes": current.id,
            "metadata": metadata,
        }
    )
    append_experience(root, refined)


def record_retrieval_usage(
    root: Path,
    *,
    project: str,
    session_id: str,
    query: str,
    retrieved_experience_ids: list[str],
    used_experience_ids: list[str] | None = None,
    stage: str = "pre_task",
    outcome: str | None = None,
    task_id: str | None = None,
    provenance: Provenance | None = None,
) -> Event:
    used = used_experience_ids or []
    known = {experience.id for experience in effective_experiences(root)}
    unknown = sorted(set(retrieved_experience_ids + used) - known)
    if unknown:
        raise ValueError(f"unknown experience IDs: {unknown}")
    event = record_event(
        root,
        event_type=EventType.tool_result,
        actor=Actor.agent,
        project=project,
        session_id=session_id,
        task_id=task_id,
        content=(
            f"Retrieved {len(retrieved_experience_ids)} experience(s) at {stage}; used {len(used)}."
        ),
        tool_name="query_experience",
        outcome=outcome,
        metadata={
            "kind": "retrieval_usage",
            "query": query,
            "stage": stage,
            "retrieved_experience_ids": retrieved_experience_ids,
            "used_experience_ids": used,
        },
        provenance=provenance,
    )
    for experience_id in used:
        mark_retrieved(root, experience_id, session_id)
    return event


def retrieval_payload(items: list[dict[str, object]]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for item in items:
        experience = item["experience"]
        assert isinstance(experience, StoredExperience)
        payload.append(
            {
                "id": experience.id,
                "score": item["score"],
                "label": item["label"],
                "lesson": experience.lesson,
                "evidence_event_ids": experience.evidence_event_ids,
                "source_project": experience.source_project,
                "last_used_session_id": experience.last_used_session_id,
            }
        )
    return payload
