from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from experience_brain.capture import record_event
from experience_brain.consolidate import write_review_report
from experience_brain.models import (
    Actor,
    Authority,
    Event,
    EventType,
    Experience,
    ExperienceStatus,
    Provenance,
)
from experience_brain.retrieve import record_retrieval_usage, retrieve_experience
from experience_brain.store import (
    append_experience,
    ensure_store,
    read_events,
    read_experiences,
    sha256_text,
)

Condition = Literal["C0", "C1", "C2"]

LEAKAGE_PATTERNS = (
    re.compile(r"\bground[_ -]?truth\b", re.IGNORECASE),
    re.compile(r"\bgold[_ -]?answers?\b", re.IGNORECASE),
    re.compile(r"\banswers?\s*:", re.IGNORECASE),
    re.compile(r"\bjudge[_ -]?result\b", re.IGNORECASE),
    re.compile(r"\bis[_ -]?correct\b", re.IGNORECASE),
    re.compile(r"##\s*judge\b", re.IGNORECASE),
    re.compile(r"\breward\s*[:=]", re.IGNORECASE),
)


def assert_no_benchmark_leakage(text: str) -> None:
    for pattern in LEAKAGE_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"benchmark leakage risk matched pattern: {pattern.pattern}")


def _words(text: str) -> set[str]:
    return {word.casefold() for word in re.findall(r"[A-Za-z0-9_]+", text)}


def _event_id(prefix: str, *parts: object) -> str:
    digest = sha256_text(":".join(str(part) for part in parts))[:12].upper()
    return f"{prefix}-{digest}"


def _memory_prompt(memories: list[str], question: str) -> str:
    lines = ["<memory_context>"]
    if memories:
        lines.extend(memories)
    else:
        lines.append("None")
    lines.append("</memory_context>")
    lines.append(f"User: {question}")
    return "\n".join(lines)


@dataclass(frozen=True)
class AdapterProvenance:
    model: str
    reasoning_effort: str
    experiment_id: str
    run_id: str
    memoryarena_commit: str
    dataset_revision: str

    def to_provenance(self) -> Provenance:
        return Provenance(
            agent="memoryarena",
            model=self.model,
            reasoning_effort=self.reasoning_effort,
            experiment_id=self.experiment_id,
            run_id=self.run_id,
            source="memoryarena_adapter",
            extra={
                "memoryarena_commit": self.memoryarena_commit,
                "dataset_revision": self.dataset_revision,
            },
        )


class NoPersistentMemorySystem:
    def add_chunk(self, chunk: str) -> dict[str, object]:
        assert_no_benchmark_leakage(chunk)
        return {"status": "ignored", "condition": "C0"}

    def wrap_user_prompt(self, question: str) -> str:
        return _memory_prompt([], question)

    def diagnostics(self) -> dict[str, object]:
        return {
            "condition": "C0",
            "events_captured": 0,
            "experiences_consolidated": 0,
            "retrieval_count": 0,
            "retrieval_utilization": 0.0,
            "provenance_completeness": 1.0,
        }


class ExperienceBrainMemorySystem:
    def __init__(
        self,
        *,
        root: Path,
        condition: Condition,
        user_id: str,
        task_group_id: str,
        provenance: AdapterProvenance,
        top_k: int = 3,
    ) -> None:
        if condition == "C0":
            raise ValueError("use NoPersistentMemorySystem for C0")
        self.root = root
        self.condition = condition
        self.user_id = user_id
        self.task_group_id = task_group_id
        self.project = f"memoryarena:{task_group_id}"
        self.provenance = provenance
        self.top_k = top_k
        self._chunk_index = 0
        self._experiences_consolidated = 0
        self._retrieval_requests = 0
        self._retrieved_items = 0
        ensure_store(self.root)

    def add_chunk(self, chunk: str) -> dict[str, object]:
        assert_no_benchmark_leakage(chunk)
        self._chunk_index += 1
        session_id = f"{self.provenance.run_id}-{self.user_id}-S{self._chunk_index:03d}"
        event = self._capture_episode_event(session_id, chunk)
        response: dict[str, object] = {
            "status": "ok",
            "condition": self.condition,
            "event_id": event.id,
        }
        if self.condition == "C2":
            experience = self._consolidate_episode(session_id, chunk, event)
            response["experience_id"] = experience.id
        return response

    def wrap_user_prompt(self, question: str) -> str:
        assert_no_benchmark_leakage(question)
        self._retrieval_requests += 1
        if self.condition == "C1":
            memories = self._retrieve_raw_episodes(question)
        else:
            memories = self._retrieve_experiences(question)
        self._retrieved_items += len(memories)
        return _memory_prompt(memories, question)

    def diagnostics(self) -> dict[str, object]:
        experiences = read_experiences(self.root)
        events = read_events(self.root)
        evidence_complete = [
            set(experience.evidence_event_ids) <= {event.id for event in events}
            for experience in experiences
        ]
        utilization = (
            self._retrieved_items / self._retrieval_requests if self._retrieval_requests else 0.0
        )
        return {
            "condition": self.condition,
            "events_captured": len(events),
            "experience_records": len(experiences),
            "experiences_consolidated": self._experiences_consolidated,
            "retrieval_count": self._retrieval_requests,
            "retrieval_items": self._retrieved_items,
            "retrieval_utilization": utilization,
            "provenance_completeness": (
                sum(evidence_complete) / len(evidence_complete) if evidence_complete else 1.0
            ),
        }

    def _capture_episode_event(self, session_id: str, chunk: str) -> Event:
        return record_event(
            self.root,
            event_id=_event_id("EVT-MA", self.provenance.run_id, session_id, chunk),
            project=self.project,
            session_id=session_id,
            task_id=self.task_group_id,
            event_type=EventType.agent_message,
            actor=Actor.agent,
            content=chunk,
            metadata={
                "kind": "memoryarena_raw_episode",
                "condition": self.condition,
                "task_group_id": self.task_group_id,
                "chunk_index": self._chunk_index,
            },
            provenance=self.provenance.to_provenance(),
        )

    def _consolidate_episode(self, session_id: str, chunk: str, event: Event) -> Experience:
        experience = Experience(
            id=_event_id("EXP-MA", self.provenance.run_id, session_id, event.id),
            project=self.project,
            source_project=self.project,
            status=ExperienceStatus.active,
            authority=Authority.outcome_feedback,
            situation=f"MemoryArena {self.task_group_id} prior subtask episode",
            goal="Carry useful prior subtask context into later subtasks without gold answers.",
            action=chunk,
            outcome="Episode captured without judge feedback or gold answer.",
            lesson=f"Prior subtask episode: {chunk[:1000]}",
            evidence_event_ids=[event.id],
            confidence=0.6,
            success_count=0,
            failure_count=0,
            provenance=self.provenance.to_provenance(),
            metadata={
                "condition": self.condition,
                "task_group_id": self.task_group_id,
                "automated_benchmark_consolidation": True,
                "no_owner_intervention": True,
                "gold_or_judge_feedback_stored": False,
                "created_at_utc": datetime.now(UTC).isoformat(),
            },
        )
        append_experience(self.root, experience)
        self._experiences_consolidated += 1
        write_review_report(self.root, [experience])
        return experience

    def _retrieve_raw_episodes(self, question: str) -> list[str]:
        query_words = _words(question)
        scored: list[tuple[int, Event]] = []
        for event in read_events(self.root):
            if event.metadata.get("kind") != "memoryarena_raw_episode":
                continue
            overlap = len(query_words & _words(event.content))
            if overlap:
                scored.append((overlap, event))
        scored.sort(key=lambda item: (-item[0], item[1].id))
        memories = [
            f'<memory source_event_id="{event.id}">{event.content}</memory>'
            for _score, event in scored[: self.top_k]
        ]
        if memories:
            record_event(
                self.root,
                project=self.project,
                session_id=f"{self.provenance.run_id}-{self.user_id}-RETRIEVE",
                task_id=self.task_group_id,
                event_type=EventType.tool_result,
                actor=Actor.agent,
                content=f"Retrieved {len(memories)} raw episode(s) for MemoryArena prompt.",
                tool_name="raw_episode_retrieval",
                metadata={
                    "kind": "memoryarena_raw_retrieval_usage",
                    "condition": self.condition,
                    "task_group_id": self.task_group_id,
                },
                provenance=self.provenance.to_provenance(),
            )
        return memories

    def _retrieve_experiences(self, question: str) -> list[str]:
        results = retrieve_experience(self.root, question, project=self.project, limit=self.top_k)
        ids = [str(item["id"]) for item in results]
        if ids:
            record_retrieval_usage(
                self.root,
                project=self.project,
                session_id=f"{self.provenance.run_id}-{self.user_id}-RETRIEVE",
                task_id=self.task_group_id,
                query=question,
                retrieved_experience_ids=ids,
                used_experience_ids=ids,
                stage="memoryarena_prompt_wrap",
                outcome="unknown",
                provenance=self.provenance.to_provenance(),
            )
        memories: list[str] = []
        for item in results:
            experience = item["experience"]
            assert isinstance(experience, Experience)
            evidence = ",".join(experience.evidence_event_ids)
            memories.append(
                f'<memory experience_id="{experience.id}" evidence_event_ids="{evidence}">'
                f"{experience.lesson}</memory>"
            )
        return memories
