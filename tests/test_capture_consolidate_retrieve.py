from __future__ import annotations

from pathlib import Path

from experience_brain.capture import capture_event
from experience_brain.consolidate import consolidate_session
from experience_brain.models import Actor, Authority, Event, EventType, Experience, ExperienceStatus
from experience_brain.retrieve import format_briefing, retrieve_experience
from experience_brain.store import append_experience, read_events, read_experiences


def test_capture_redacts_and_records_provenance(brain_root: Path) -> None:
    event = Event(
        id="EVT-secret",
        type=EventType.tool_result,
        actor=Actor.tool,
        project="demo",
        session_id="S-1",
        content="api_key=sk-secretsecretsecret",
    )
    capture_event(brain_root, event)
    stored = read_events(brain_root)[0]
    assert "[REDACTED]" in stored.content
    assert stored.provenance.redactions


def test_consolidate_creates_traceable_candidate_and_report(brain_root: Path) -> None:
    capture_event(
        brain_root,
        Event(
            id="EVT-1",
            type=EventType.user_message,
            actor=Actor.owner,
            project="demo",
            session_id="S-1",
            content="Fix failing tests",
        ),
    )
    capture_event(
        brain_root,
        Event(
            id="EVT-2",
            type=EventType.decision,
            actor=Actor.agent,
            project="demo",
            session_id="S-1",
            content="Run focused tests before patching",
        ),
    )
    capture_event(
        brain_root,
        Event(
            id="EVT-3",
            type=EventType.outcome,
            actor=Actor.agent,
            project="demo",
            session_id="S-1",
            content="Focused test passed",
            outcome="success",
        ),
    )
    count, report = consolidate_session(brain_root, "S-1")
    assert count == 1
    assert report.exists()
    experience = read_experiences(brain_root)[0]
    assert experience.evidence_event_ids == ["EVT-1", "EVT-2", "EVT-3"]
    assert experience.status == ExperienceStatus.active


def test_retrieval_labels_external_project_experience(brain_root: Path) -> None:
    capture_event(
        brain_root,
        Event(
            id="EVT-1",
            type=EventType.outcome,
            actor=Actor.agent,
            project="external",
            session_id="S-1",
            content="Use ruff before pytest",
            outcome="success",
        ),
    )
    append_experience(
        brain_root,
        Experience(
            id="EXP-ext",
            project="external",
            source_project="external",
            status=ExperienceStatus.confirmed,
            authority=Authority.owner,
            lesson="Run ruff before pytest when formatting may fail.",
            evidence_event_ids=["EVT-1"],
            confidence=0.9,
            success_count=2,
        ),
    )
    results = retrieve_experience(brain_root, "ruff formatting pytest", project="demo")
    assert results[0]["label"] == "External Project Experience"
    assert "Evidence events: EVT-1" in format_briefing(results)
