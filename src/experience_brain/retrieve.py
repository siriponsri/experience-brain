from __future__ import annotations

import re
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

from .capture import record_event
from .models import (
    Actor,
    Event,
    EventType,
    Experience,
    ExperienceStatus,
    KnowledgeStatus,
    Provenance,
    StoredExperience,
    StoredKnowledge,
)
from .store import current_experiences, current_knowledge

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
RETRIEVABLE_KNOWLEDGE_STATUSES = {
    KnowledgeStatus.proposed.value,
    KnowledgeStatus.active.value,
    KnowledgeStatus.confirmed.value,
}


def _words(text: str) -> set[str]:
    return {word.casefold() for word in re.findall(r"[A-Za-z0-9_]+", text)}


def _sort_key(item: dict[str, object]) -> tuple[int, str]:
    score = item["score"]
    if not isinstance(score, int):
        raise TypeError("retrieval score must be an integer")
    return -score, str(item["id"])


def effective_experiences(root: Path) -> list[StoredExperience]:
    return [
        experience
        for experience in current_experiences(root)
        if experience.status.value in ACTIVE_STATUSES
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


def retrieve_knowledge(
    root: Path, query: str, *, project: str | None = None, limit: int = 5
) -> list[dict[str, object]]:
    if limit <= 0:
        raise ValueError("limit must be positive")
    query_words = _words(query)
    scored: list[dict[str, object]] = []
    for knowledge in current_knowledge(root):
        if knowledge.status.value not in RETRIEVABLE_KNOWLEDGE_STATUSES:
            continue
        text = " ".join(
            [
                knowledge.title,
                knowledge.summary,
                " ".join(knowledge.key_facts),
                knowledge.suggested_applicability,
                " ".join(knowledge.tags),
                knowledge.source_filename,
            ]
        )
        overlap = len(query_words & _words(text))
        if overlap == 0:
            continue
        project_score = 8 if project and knowledge.project == project else 0
        external_penalty = 2 if project and knowledge.project not in {project, "general"} else 0
        status_bonus = 8 if knowledge.status == KnowledgeStatus.confirmed else 4
        score = overlap * 4 + project_score + status_bonus - external_penalty
        label = (
            "Project Knowledge"
            if project and knowledge.project == project
            else "General Knowledge"
            if knowledge.project == "general"
            else "External Project Knowledge"
        )
        scored.append(
            {
                "id": knowledge.id,
                "score": score,
                "knowledge": knowledge,
                "label": label,
                "source": knowledge.source_filename,
                "source_content_hash": knowledge.source_content_hash,
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


def format_knowledge_briefing(items: list[dict[str, object]]) -> str:
    if not items:
        return "No relevant knowledge found."
    lines: list[str] = []
    for item in items:
        score = item["score"]
        if not isinstance(score, int):
            raise TypeError("retrieval score must be an integer")
        knowledge = item["knowledge"]
        assert isinstance(knowledge, StoredKnowledge)
        facts = "; ".join(knowledge.key_facts[:3]) or "No key facts recorded."
        lines.extend(
            [
                f"### {item['label']}: {knowledge.id}",
                f"- Score: {score}",
                f"- Source: {knowledge.source_filename}",
                f"- Source hash: {knowledge.source_content_hash}",
                f"- Digest: {knowledge.summary}",
                f"- Key facts: {facts}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def format_unified_briefing(
    knowledge_items: list[dict[str, object]],
    experience_items: list[dict[str, object]],
) -> str:
    return "\n\n".join(
        [
            "## Relevant Knowledge",
            format_knowledge_briefing(knowledge_items),
            "## Relevant Experience",
            format_briefing(experience_items),
        ]
    )


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
    retrieval_result: Literal["match", "no_match"] | None = None,
    usage: Literal["used", "not_used", "unavailable"] | None = None,
    task_outcome: Literal["success", "failure", "unknown"] | None = None,
    task_id: str | None = None,
    provenance: Provenance | None = None,
) -> Event:
    used = used_experience_ids or []
    resolved_result = retrieval_result or ("match" if retrieved_experience_ids else "no_match")
    resolved_usage = usage or (
        "used" if used else "not_used" if retrieved_experience_ids else "unavailable"
    )
    if resolved_result == "no_match" and retrieved_experience_ids:
        raise ValueError("no_match cannot include retrieved Experience IDs")
    if resolved_result == "match" and not retrieved_experience_ids:
        raise ValueError("match requires at least one retrieved Experience ID")
    if resolved_usage == "used" and not used:
        raise ValueError("used requires at least one used Experience ID")
    if resolved_usage == "unavailable" and retrieved_experience_ids:
        raise ValueError("unavailable cannot include retrieved Experience IDs")
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
            f"Retrieval {resolved_result} at {stage}; usage {resolved_usage}; "
            f"task outcome {task_outcome or outcome or 'unknown'}."
        ),
        tool_name="query_experience",
        outcome=task_outcome or outcome or "unknown",
        metadata={
            "kind": "retrieval_usage",
            "query": query,
            "stage": stage,
            "retrieval_result": resolved_result,
            "usage": resolved_usage,
            "task_outcome": task_outcome or outcome or "unknown",
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


def knowledge_payload(items: list[dict[str, object]]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for item in items:
        knowledge = item["knowledge"]
        assert isinstance(knowledge, StoredKnowledge)
        payload.append(
            {
                "id": knowledge.id,
                "score": item["score"],
                "label": item["label"],
                "title": knowledge.title,
                "summary": knowledge.summary,
                "key_facts": knowledge.key_facts,
                "suggested_applicability": knowledge.suggested_applicability,
                "status": knowledge.status.value,
                "source_filename": knowledge.source_filename,
                "source_content_hash": knowledge.source_content_hash,
                "source_type": knowledge.source_type,
                "source_mime_type": knowledge.source_mime_type,
                "project": knowledge.project,
                "provenance": knowledge.provenance.model_dump(mode="json"),
            }
        )
    return payload


def retrieve_memory(
    root: Path, query: str, *, project: str | None = None, limit: int = 5
) -> dict[str, Any]:
    knowledge_items = retrieve_knowledge(root, query, project=project, limit=limit)
    experience_items = retrieve_experience(root, query, project=project, limit=limit)
    return {
        "retrieval_result": ("match" if knowledge_items or experience_items else "no_match"),
        "briefing": format_unified_briefing(knowledge_items, experience_items),
        "knowledge": knowledge_payload(knowledge_items),
        "experience": retrieval_payload(experience_items),
    }
