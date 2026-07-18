from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import streamlit as st

from experience_brain.knowledge import list_inbox_status, process_inbox, review_knowledge
from experience_brain.models import (
    SCHEMA_VERSION,
    ExperienceStatus,
    KnowledgeStatus,
    Provenance,
    StoredEvent,
    StoredExperience,
    StoredKnowledge,
)
from experience_brain.store import (
    current_experiences,
    current_knowledge,
    ensure_store,
    lint_store,
    pending_review_experiences,
    read_events,
    read_experiences,
    read_knowledge,
    review_experience,
)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--root", default=".")
    parsed, _ = parser.parse_known_args()
    return parsed


def _source_sessions(
    experience: StoredExperience, events_by_id: dict[str, StoredEvent]
) -> list[str]:
    return sorted(
        {
            events_by_id[event_id].session_id
            for event_id in experience.evidence_event_ids
            if event_id in events_by_id
        }
    )


def _latest_experiment(root: Path) -> str:
    latest: tuple[str, str] | None = None
    for path in (root / "experiments").glob("*/results.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        experiment_id = str(payload.get("experiment_id", path.parent.name))
        for run in payload.get("runs", []):
            if not isinstance(run, dict):
                continue
            timestamp = str(run.get("ended_at") or run.get("started_at") or "")
            candidate = (timestamp, experiment_id)
            if latest is None or candidate > latest:
                latest = candidate
    return latest[1] if latest else "None recorded"


def _flash(message: str) -> None:
    st.session_state["review_flash"] = message
    st.rerun()


def _apply_review(experience_id: str, action: str, root: Path, **edits: str) -> None:
    try:
        reviewed = review_experience(root, experience_id, action=action, **edits)  # type: ignore[arg-type]
    except ValueError as error:
        st.error(str(error))
        return
    labels = {
        "confirm": "Confirmed",
        "edit_confirm": "Edited and confirmed",
        "invalidate": "Rejected and invalidated",
        "retire": "Retired",
    }
    _flash(f"{labels[action]} {experience_id}. New record: {reviewed.id}")


def _apply_knowledge_review(knowledge_id: str, action: str, root: Path) -> None:
    try:
        reviewed = review_knowledge(root, knowledge_id, action=action)
    except ValueError as error:
        st.error(str(error))
        return
    labels = {"confirm": "Confirmed", "invalidate": "Invalidated", "retire": "Retired"}
    _flash(f"{labels[action]} Knowledge {knowledge_id}. New record: {reviewed.id}")


def _render_evidence(experience: StoredExperience, events_by_id: dict[str, StoredEvent]) -> None:
    st.markdown("**Evidence**")
    for event_id in experience.evidence_event_ids:
        event = events_by_id.get(event_id)
        if event is None:
            st.error(f"Missing Event: {event_id}")
            continue
        with st.expander(f"{event.type.value.replace('_', ' ').title()} | {event.id}"):
            st.caption(
                f"Session {event.session_id} | {event.timestamp.isoformat()} | "
                f"Actor: {event.actor.value}"
            )
            st.write(event.content or "No text content recorded.")
            if event.tool_name:
                st.write(f"Tool: `{event.tool_name}`")
            if event.outcome:
                st.write(f"Outcome: `{event.outcome}`")


def _render_overview(
    root: Path,
    events: list[StoredEvent],
    experiences: list[StoredExperience],
    current: list[StoredExperience],
    pending: list[StoredExperience],
    knowledge: list[StoredKnowledge],
    current_knowledge_items: list[StoredKnowledge],
) -> None:
    active_statuses = {
        ExperienceStatus.active,
        ExperienceStatus.confirmed,
        ExperienceStatus.refined,
    }
    latest_session = max(events, key=lambda event: event.timestamp).session_id if events else "None"
    columns = st.columns(6)
    columns[0].metric("Software", SCHEMA_VERSION)
    columns[1].metric("Events", len(events))
    columns[2].metric("Experience records", len(experiences))
    columns[3].metric("Knowledge records", len(knowledge))
    columns[4].metric("Pending reviews", len(pending))
    columns[5].metric(
        "Confirmed / active", sum(experience.status in active_statuses for experience in current)
    )
    st.divider()
    details = st.columns(2)
    details[0].subheader("Latest session")
    details[0].code(latest_session)
    details[1].subheader("Latest experiment")
    details[1].code(_latest_experiment(root))
    errors = lint_store(root)
    if errors:
        st.error(f"Store integrity: {len(errors)} issue(s)")
        with st.expander("View integrity issues"):
            for error in errors:
                st.write(error)
    else:
        st.success("Store integrity passed")


def _render_inbox(root: Path) -> None:
    uploaded = st.file_uploader(
        "Upload files",
        accept_multiple_files=True,
        type=[
            "md",
            "txt",
            "json",
            "jsonl",
            "yaml",
            "yml",
            "csv",
            "py",
            "js",
            "ts",
            "tsx",
            "jsx",
            "html",
            "css",
            "toml",
            "ini",
            "cfg",
            "sh",
            "ps1",
            "bat",
            "sql",
            "xml",
            "pdf",
            "docx",
            "xlsx",
        ],
    )
    if uploaded and st.button("Save uploads"):
        inbox = root / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        for file in uploaded:
            target = inbox / Path(file.name).name
            target.write_bytes(file.getvalue())
        _flash(f"Saved {len(uploaded)} upload{'s' if len(uploaded) != 1 else ''} to inbox.")
    actions = st.columns([1, 1, 4])
    if actions[0].button("Process Inbox", type="primary"):
        results = process_inbox(
            root,
            provenance=Provenance(
                agent="owner",
                experiment_id="EXP-03.2",
                source="owner_dashboard_process_inbox",
            ),
        )
        _flash(f"Processed {len(results)} inbox file{'s' if len(results) != 1 else ''}.")
    if actions[1].button("Retry Processing"):
        results = process_inbox(
            root,
            retry=True,
            provenance=Provenance(
                agent="owner",
                experiment_id="EXP-03.2",
                source="owner_dashboard_retry_inbox",
            ),
        )
        _flash(f"Retried {len(results)} inbox file{'s' if len(results) != 1 else ''}.")
    statuses = list_inbox_status(root)
    st.caption(f"{len(statuses)} file{'s' if len(statuses) != 1 else ''} in inbox")
    if statuses:
        st.dataframe(statuses, use_container_width=True, hide_index=True)
        for item in statuses:
            if item.get("error"):
                with st.expander(f"Error: {item['filename']}"):
                    st.write(item["error"])
    else:
        st.info("No files in inbox.")


def _render_knowledge(
    root: Path,
    knowledge: list[StoredKnowledge],
    current_items: list[StoredKnowledge],
) -> None:
    controls = st.columns([2, 2, 3])
    status = controls[0].selectbox(
        "Status", ["All", *[item.value for item in KnowledgeStatus]], key="knowledge-status"
    )
    projects = sorted({item.project for item in knowledge})
    project = controls[1].selectbox("Project", ["All", *projects], key="knowledge-project")
    include_history = controls[2].checkbox("Include superseded history", value=False)
    pool = knowledge if include_history else current_items
    filtered = [
        item
        for item in pool
        if (status == "All" or item.status.value == status)
        and (project == "All" or item.project == project)
    ]
    st.caption(f"{len(filtered)} Knowledge record{'s' if len(filtered) != 1 else ''}")
    current_ids = {item.id for item in current_items}
    for item in reversed(filtered):
        with st.expander(f"{item.id} | {item.status.value.title()} | {item.source_filename}"):
            st.write(item.summary or "No digest recorded.")
            if item.key_facts:
                st.markdown("**Key Facts / Claims**")
                for fact in item.key_facts:
                    st.write(f"- {fact}")
            st.write(f"**Applicability:** {item.suggested_applicability or 'Not recorded'}")
            facts = st.columns(4)
            facts[0].write(f"**Project:** {item.project}")
            facts[1].write(f"**Type:** {item.source_type}")
            facts[2].write(f"**Source:** {item.source_filename}")
            facts[3].write(f"**Hash:** `{item.source_content_hash[:12]}`")
            with st.expander("Provenance and source"):
                st.json(
                    {
                        "source_filename": item.source_filename,
                        "source_content_hash": item.source_content_hash,
                        "source_location": (
                            item.source_location.model_dump(mode="json", exclude_none=True)
                            if item.source_location
                            else None
                        ),
                        "extractor": item.extractor.model_dump(mode="json"),
                        "provenance": item.provenance.model_dump(mode="json"),
                        "supersedes": item.supersedes,
                        "invalidates": item.invalidates,
                        "record_hash": item.record_hash,
                    }
                )
            if item.id in current_ids:
                actions = st.columns([1, 1, 1, 5])
                if item.status == KnowledgeStatus.proposed and actions[0].button(
                    "Confirm", key=f"knowledge-confirm-{item.id}", type="primary"
                ):
                    _apply_knowledge_review(item.id, "confirm", root)
                if item.status in {KnowledgeStatus.proposed, KnowledgeStatus.confirmed} and actions[
                    1
                ].button("Invalidate", key=f"knowledge-invalidate-{item.id}"):
                    _apply_knowledge_review(item.id, "invalidate", root)
                if item.status in {KnowledgeStatus.active, KnowledgeStatus.confirmed} and actions[
                    2
                ].button("Retire", key=f"knowledge-retire-{item.id}"):
                    _apply_knowledge_review(item.id, "retire", root)


def _render_review_queue(
    root: Path,
    pending: list[StoredExperience],
    events_by_id: dict[str, StoredEvent],
) -> None:
    st.caption(f"{len(pending)} unresolved Experience{'s' if len(pending) != 1 else ''}")
    if not pending:
        st.success("Review queue is clear.")
        return
    for experience in pending:
        sessions = _source_sessions(experience, events_by_id)
        with st.container(border=True):
            heading, state = st.columns([4, 1])
            heading.subheader(experience.id)
            state.markdown(f"**{experience.status.value.title()}**")
            st.write(experience.lesson)
            context = st.columns(4)
            context[0].caption("PROJECT")
            context[0].write(experience.project)
            context[1].caption("SOURCE SESSION")
            context[1].write(", ".join(sessions) or "Unknown")
            context[2].caption("CONFIDENCE")
            context[2].write(f"{experience.confidence:.0%}")
            context[3].caption("EVIDENCE EVENTS")
            context[3].write(len(experience.evidence_event_ids))
            with st.expander("Situation, goal, and evidence"):
                st.markdown("**Situation**")
                st.write(experience.situation or "Not recorded")
                st.markdown("**Goal**")
                st.write(experience.goal or "Not recorded")
                _render_evidence(experience, events_by_id)
            actions = st.columns([1, 1, 4])
            if actions[0].button("Confirm", key=f"confirm-{experience.id}", type="primary"):
                _apply_review(experience.id, "confirm", root)
            if actions[1].button("Reject", key=f"reject-{experience.id}"):
                _apply_review(experience.id, "invalidate", root)
            with st.expander("Edit and confirm"):
                with st.form(f"edit-{experience.id}"):
                    situation = st.text_area("Situation", experience.situation)
                    goal = st.text_area("Goal", experience.goal)
                    lesson = st.text_area("Lesson", experience.lesson, height=140)
                    if st.form_submit_button("Save and confirm", type="primary"):
                        _apply_review(
                            experience.id,
                            "edit_confirm",
                            root,
                            situation=situation,
                            goal=goal,
                            lesson=lesson,
                        )


def _render_experiences(
    root: Path,
    experiences: list[StoredExperience],
    current: list[StoredExperience],
    events_by_id: dict[str, StoredEvent],
) -> None:
    controls = st.columns([2, 2, 3])
    status = controls[0].selectbox(
        "Status", ["All", *[item.value for item in ExperienceStatus]], key="experience-status"
    )
    projects = sorted({experience.project for experience in experiences})
    project = controls[1].selectbox("Project", ["All", *projects], key="experience-project")
    scope = controls[2].radio(
        "Source",
        ["All", "Internal", "External Project Experience"],
        horizontal=True,
        key="experience-scope",
    )
    include_history = st.checkbox(
        "Include superseded history", value=False, key="experience-include-history"
    )
    pool = experiences if include_history else current
    filtered = [
        experience
        for experience in pool
        if (status == "All" or experience.status.value == status)
        and (project == "All" or experience.project == project)
        and (scope == "All" or (scope == "Internal" and not experience.external_project))
        and (scope != "External Project Experience" or experience.external_project)
    ]
    st.caption(f"{len(filtered)} Experience record{'s' if len(filtered) != 1 else ''}")
    current_ids = {experience.id for experience in current}
    for experience in reversed(filtered):
        label = "External Project Experience" if experience.external_project else "Internal"
        with st.expander(f"{experience.id} | {experience.status.value.title()} | {label}"):
            st.write(experience.lesson)
            details = st.columns(3)
            details[0].write(f"**Project:** {experience.project}")
            details[1].write(f"**Confidence:** {experience.confidence:.0%}")
            details[2].write(
                f"**Owner confirmed:** {'Yes' if experience.owner_confirmed else 'No'}"
            )
            st.write(f"**Situation:** {experience.situation or 'Not recorded'}")
            st.write(f"**Goal:** {experience.goal or 'Not recorded'}")
            _render_evidence(experience, events_by_id)
            with st.expander("Provenance and lineage"):
                st.json(
                    {
                        "provenance": experience.provenance.model_dump(mode="json"),
                        "supersedes": experience.supersedes,
                        "invalidates": experience.invalidates,
                        "record_hash": experience.record_hash,
                        "previous_hash": experience.previous_hash,
                    }
                )
            if (
                experience.id in current_ids
                and experience.status
                in {ExperienceStatus.active, ExperienceStatus.confirmed, ExperienceStatus.refined}
                and st.button("Retire", key=f"retire-{experience.id}")
            ):
                _apply_review(experience.id, "retire", root)


def _render_sessions(root: Path, events: list[StoredEvent]) -> None:
    grouped: dict[str, list[StoredEvent]] = defaultdict(list)
    for event in events:
        grouped[event.session_id].append(event)
    if not grouped:
        st.info("No sessions recorded.")
        return
    session_ids = sorted(
        grouped,
        key=lambda session_id: max(event.timestamp for event in grouped[session_id]),
        reverse=True,
    )
    session_id = st.selectbox("Session", session_ids)
    selected = sorted(grouped[session_id], key=lambda event: event.timestamp)
    st.caption(f"{selected[0].project} | {len(selected)} Events")
    for event in selected:
        with st.container(border=True):
            title, timestamp = st.columns([3, 2])
            title.markdown(f"**{event.type.value.replace('_', ' ').title()}**")
            timestamp.caption(event.timestamp.isoformat())
            st.write(event.content or "No text content recorded.")
            facts = [f"Actor: {event.actor.value}", f"Event: {event.id}"]
            if event.tool_name:
                facts.append(f"Tool: {event.tool_name}")
            if event.outcome:
                facts.append(f"Outcome: {event.outcome}")
            st.caption(" | ".join(facts))
            with st.expander("Raw Event JSON"):
                st.json(event.model_dump(mode="json"))
    latest = root / "reports" / "latest.md"
    with st.expander("Latest session review report"):
        st.markdown(latest.read_text(encoding="utf-8") if latest.exists() else "No report yet.")


def render_dashboard(root: Path) -> None:
    ensure_store(root)
    st.set_page_config(
        page_title="Experience Brain", page_icon=":material/neurology:", layout="wide"
    )
    st.markdown(
        """
        <style>
        :root { --review-teal: #16766f; --review-ink: #202a2e; --review-amber: #b86b12; }
        .stApp { color: var(--review-ink); }
        h1, h2, h3 { letter-spacing: 0 !important; }
        div[data-testid="stMetric"] {
            border-top: 3px solid var(--review-teal);
            padding-top: 0.65rem;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 6px; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("Experience Brain")
    st.caption("Owner review ledger")
    if message := st.session_state.pop("review_flash", None):
        st.success(message)
    events = read_events(root)
    experiences = read_experiences(root)
    knowledge = read_knowledge(root)
    current = current_experiences(root)
    current_knowledge_items = current_knowledge(root)
    pending = pending_review_experiences(root)
    events_by_id = {event.id: event for event in events}
    tab_overview, tab_review, tab_inbox, tab_knowledge, tab_experiences, tab_sessions = st.tabs(
        [
            "Overview",
            f"Review Queue ({len(pending)})",
            "Inbox",
            "Knowledge",
            "Experiences",
            "Sessions / Events",
        ]
    )
    with tab_overview:
        _render_overview(
            root,
            events,
            experiences,
            current,
            pending,
            knowledge,
            current_knowledge_items,
        )
    with tab_review:
        _render_review_queue(root, pending, events_by_id)
    with tab_inbox:
        _render_inbox(root)
    with tab_knowledge:
        _render_knowledge(root, knowledge, current_knowledge_items)
    with tab_experiences:
        _render_experiences(root, experiences, current, events_by_id)
    with tab_sessions:
        _render_sessions(root, events)


def main() -> None:
    render_dashboard(Path(_args().root).resolve())


if __name__ == "__main__":
    main()
