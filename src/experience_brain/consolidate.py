from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from .models import SCHEMA_VERSION, Authority, Experience, ExperienceStatus, Provenance, StoredEvent
from .store import append_experience, read_events, read_experiences, sha256_text


def _experience_id(session_id: str, evidence: list[str]) -> str:
    return f"EXP-{sha256_text(session_id + ':' + ':'.join(evidence))[:10].upper()}"


def _event_summary(events: list[StoredEvent], event_type: str) -> str | None:
    for event in reversed(events):
        if event.type.value == event_type and event.content:
            return event.content
    return None


def consolidate_session(root: Path, session_id: str | None = None) -> tuple[int, Path]:
    events = read_events(root)
    if session_id is not None:
        events = [event for event in events if event.session_id == session_id]
    grouped: dict[str, list[StoredEvent]] = defaultdict(list)
    for event in events:
        grouped[event.session_id].append(event)

    existing_ids = {experience.id for experience in read_experiences(root)}
    created: list[Experience] = []
    for current_session, session_events in sorted(grouped.items()):
        if not session_events:
            continue
        evidence = [event.id for event in session_events]
        experience_id = _experience_id(current_session, evidence)
        if experience_id in existing_ids:
            continue
        project = session_events[0].project
        goal = _event_summary(session_events, "user_message") or session_events[0].task_id or ""
        outcome = _event_summary(session_events, "outcome")
        feedback = _event_summary(session_events, "feedback")
        decision = _event_summary(session_events, "decision")
        error = _event_summary(session_events, "error")
        tool_names = sorted({event.tool_name for event in session_events if event.tool_name})
        success_count = 1 if any(event.outcome == "success" for event in session_events) else 0
        failure_count = 1 if any(event.outcome == "failure" for event in session_events) else 0
        lesson_source = feedback or decision or outcome or error or goal or "Review this session."
        status = (
            ExperienceStatus.active
            if success_count and (feedback or outcome)
            else ExperienceStatus.proposed
        )
        confidence = 0.75 if status == ExperienceStatus.active else 0.45
        created.append(
            Experience(
                id=experience_id,
                project=project,
                source_project=project,
                status=status,
                authority=Authority.outcome_feedback,
                situation=error or goal,
                goal=goal,
                action=decision or _event_summary(session_events, "agent_message") or "",
                tool_context=", ".join(tool_names) if tool_names else None,
                decision=decision,
                outcome=outcome,
                feedback=feedback,
                lesson=lesson_source,
                evidence_event_ids=evidence,
                confidence=confidence,
                success_count=success_count,
                failure_count=failure_count,
                provenance=Provenance(
                    source="consolidate_session",
                    software_version=SCHEMA_VERSION,
                    run_id=session_events[0].provenance.run_id,
                    agent=session_events[0].provenance.agent,
                    model=session_events[0].provenance.model,
                    reasoning_effort=session_events[0].provenance.reasoning_effort,
                ),
            )
        )
    if created:
        for experience in created:
            append_experience(root, experience)
    return len(created), write_review_report(root, created)


def write_review_report(root: Path, experiences: list[Experience]) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / f"review-{timestamp}.md"
    lines = ["# Experience Review", "", f"Generated: {datetime.now(UTC).isoformat()}", ""]
    if not experiences:
        lines.append("No new candidate experiences were created.")
    for experience in experiences:
        lines.extend(
            [
                f"## {experience.id}",
                "",
                f"- Status: `{experience.status.value}`",
                f"- Project: `{experience.project}`",
                f"- Confidence: `{experience.confidence}`",
                f"- Evidence events: {', '.join(experience.evidence_event_ids)}",
                "",
                experience.lesson,
                "",
            ]
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    latest = reports / "latest.md"
    latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return path
