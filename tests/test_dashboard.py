from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from experience_brain.capture import capture_event
from experience_brain.models import Actor, Event, EventType, Experience, ExperienceStatus
from experience_brain.retrieve import retrieve_experience
from experience_brain.store import (
    append_experience,
    current_experiences,
    lint_store,
    pending_review_experiences,
    read_experiences,
    review_experience,
)


def _candidate(root: Path, identifier: str = "EXP-review") -> None:
    capture_event(
        root,
        Event(
            id="EVT-review",
            type=EventType.decision,
            actor=Actor.agent,
            project="demo",
            session_id="SESSION-review",
            content="Run focused tests before changing the parser.",
        ),
    )
    append_experience(
        root,
        Experience(
            id=identifier,
            project="demo",
            source_project="demo",
            situation="Parser tests fail after an input change.",
            goal="Fix parser tests.",
            lesson="Run focused parser tests before changing the parser.",
            evidence_event_ids=["EVT-review"],
        ),
    )


def test_review_queue_and_confirmation_are_append_only(brain_root: Path) -> None:
    _candidate(brain_root)
    path = brain_root / "data" / "experiences.jsonl"
    before = path.read_bytes()
    assert [item.id for item in pending_review_experiences(brain_root)] == ["EXP-review"]

    reviewed = review_experience(brain_root, "EXP-review", action="confirm", run_id="RUN-review")

    assert path.read_bytes().startswith(before)
    assert len(read_experiences(brain_root)) == 2
    assert pending_review_experiences(brain_root) == []
    assert reviewed.status == ExperienceStatus.confirmed
    assert reviewed.owner_confirmed
    assert reviewed.supersedes == "EXP-review"
    assert reviewed.provenance.source == "owner_dashboard"
    assert reviewed.provenance.extra["source_experience_id"] == "EXP-review"
    assert lint_store(brain_root) == []
    assert retrieve_experience(brain_root, "focused parser tests", project="demo")
    assert retrieve_experience(brain_root, "pharmacy inventory colors", project="demo") == []


def test_edit_reject_and_retire_create_new_lineage_heads(brain_root: Path) -> None:
    _candidate(brain_root)
    edited = review_experience(
        brain_root,
        "EXP-review",
        action="edit_confirm",
        lesson="Run the smallest relevant parser test before editing parser code.",
    )
    assert edited.lesson.startswith("Run the smallest")
    retired = review_experience(brain_root, edited.id, action="retire")
    assert retired.status == ExperienceStatus.retired
    assert [item.id for item in current_experiences(brain_root)] == [retired.id]
    assert len(read_experiences(brain_root)) == 3


def test_reject_invalidates_without_deleting_candidate(brain_root: Path) -> None:
    _candidate(brain_root)
    rejected = review_experience(brain_root, "EXP-review", action="invalidate")
    assert rejected.status == ExperienceStatus.invalidated
    assert rejected.invalidates == "EXP-review"
    assert len(read_experiences(brain_root)) == 2
    assert retrieve_experience(brain_root, "focused parser tests", project="demo") == []


def test_dashboard_renders_owner_views_from_isolated_store(brain_root: Path) -> None:
    _candidate(brain_root)
    script = (
        "from pathlib import Path\n"
        "from experience_brain.dashboard import render_dashboard\n"
        f"render_dashboard(Path({str(brain_root)!r}))\n"
    )
    rendered = AppTest.from_string(script).run(timeout=10)
    assert not rendered.exception
    assert [tab.label for tab in rendered.tabs] == [
        "Overview",
        "Review Queue (1)",
        "Inbox",
        "Knowledge",
        "Experiences",
        "Sessions / Events",
    ]
    confirm = next(button for button in rendered.button if button.label == "Confirm")
    rendered = confirm.click().run(timeout=10)
    assert not rendered.exception
    assert pending_review_experiences(brain_root) == []
