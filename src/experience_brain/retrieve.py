from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from .models import ExperienceStatus, StoredExperience
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
    ExperienceStatus.proposed.value,
}


def _words(text: str) -> set[str]:
    return {word.casefold() for word in re.findall(r"[A-Za-z0-9_]+", text)}


def _sort_key(item: dict[str, object]) -> tuple[int, str]:
    score = item["score"]
    if not isinstance(score, int):
        raise TypeError("retrieval score must be an integer")
    return -score, str(item["id"])


def retrieve_experience(
    root: Path, query: str, *, project: str | None = None, limit: int = 5
) -> list[dict[str, object]]:
    if limit <= 0:
        raise ValueError("limit must be positive")
    query_words = _words(query)
    scored: list[dict[str, object]] = []
    for experience in read_experiences(root):
        if experience.status.value not in ACTIVE_STATUSES:
            continue
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
    from .models import Experience
    from .store import append_experience

    matches = [item for item in read_experiences(root) if item.id == experience_id]
    if not matches:
        raise ValueError(f"unknown experience: {experience_id}")
    current = matches[-1]
    refined = Experience.model_validate(
        current.model_dump(
            mode="json",
            exclude={"payload_hash", "previous_hash", "record_hash", "ingested_at"},
        )
        | {
            "id": f"{current.id}-USE-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            "updated_at": datetime.now(UTC).isoformat(),
            "last_used_at": datetime.now(UTC).isoformat(),
            "last_used_session_id": session_id,
            "supersedes": current.id,
        }
    )
    append_experience(root, refined)
