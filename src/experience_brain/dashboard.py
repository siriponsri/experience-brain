from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Literal

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


def _render_page_heading(title: str, count: str | None = None) -> None:
    heading, meta = st.columns([5, 2], vertical_alignment="bottom")
    heading.markdown(f"## {title}")
    if count:
        meta.caption(count)


def _recent_activity(
    events: list[StoredEvent],
    experiences: list[StoredExperience],
    knowledge: list[StoredKnowledge],
    *,
    limit: int = 6,
) -> list[tuple[datetime, str, str, str]]:
    activity: list[tuple[datetime, str, str, str]] = []
    for event in events:
        activity.append(
            (
                event.timestamp,
                "Event",
                event.type.value.replace("_", " ").title(),
                event.project,
            )
        )
    for experience in experiences:
        activity.append(
            (
                experience.ingested_at,
                "Grounded Experience",
                experience.status.value.title(),
                experience.project,
            )
        )
    for item in knowledge:
        activity.append(
            (
                item.ingested_at,
                "Knowledge",
                item.status.value.title(),
                item.source_filename,
            )
        )
    return sorted(activity, key=lambda item: item[0], reverse=True)[:limit]


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
    reusable_knowledge_statuses = {
        KnowledgeStatus.proposed,
        KnowledgeStatus.active,
        KnowledgeStatus.confirmed,
    }
    latest_event = max(events, key=lambda event: event.timestamp) if events else None
    latest_session = latest_event.session_id if latest_event else "None recorded"
    errors = lint_store(root)
    active_count = sum(experience.status in active_statuses for experience in current)
    knowledge_count = sum(
        item.status in reusable_knowledge_statuses for item in current_knowledge_items
    )
    session_count = len({event.session_id for event in events})

    _render_page_heading("Overview", "Canonical local data")
    columns = st.columns(6)
    columns[0].metric("Software", SCHEMA_VERSION)
    columns[1].metric("Store integrity", "Healthy" if not errors else f"{len(errors)} issues")
    columns[2].metric("Grounded Experience", active_count)
    columns[3].metric("Knowledge", knowledge_count)
    columns[4].metric("Pending reviews", len(pending))
    columns[5].metric("Sessions", session_count)

    st.markdown("### Current state")
    details = st.columns([3, 2, 2])
    with details[0].container(border=True):
        st.caption("LATEST SESSION")
        st.markdown(f"**{latest_session}**")
        if latest_event:
            st.caption(f"{latest_event.project} | {latest_event.timestamp.isoformat()}")
    with details[1].container(border=True):
        st.caption("LATEST EXPERIMENT")
        st.markdown(f"**{_latest_experiment(root)}**")
        st.caption("From recorded experiment results")
    with details[2].container(border=True):
        st.caption("REVIEW QUEUE")
        st.markdown(f"**{len(pending)} pending**")
        st.caption("Owner decisions required")

    activity, integrity = st.columns([5, 3])
    with activity:
        st.markdown("### Recent activity")
        recent = _recent_activity(events, experiences, knowledge)
        if not recent:
            st.info("No activity recorded.")
        for timestamp, kind, state, context in recent:
            with st.container(border=True):
                label, summary, when = st.columns([2, 4, 3], vertical_alignment="center")
                colors: dict[
                    str,
                    Literal["red", "orange", "yellow", "blue", "green", "violet", "gray"],
                ] = {"Knowledge": "blue", "Grounded Experience": "violet"}
                label.badge(kind, color=colors.get(kind, "gray"))
                summary.markdown(f"**{state}**")
                summary.caption(context)
                when.caption(timestamp.isoformat())
    with integrity:
        st.markdown("### Store health")
        if errors:
            st.error(f"{len(errors)} integrity issue(s)")
            with st.expander("Integrity issues"):
                for error in errors:
                    st.write(error)
        else:
            st.success("All canonical stores passed integrity checks.")
        with st.expander("Record totals"):
            st.write(f"Events: **{len(events)}**")
            st.write(f"Experience records: **{len(experiences)}**")
            st.write(f"Knowledge records: **{len(knowledge)}**")


def _render_inbox(root: Path) -> None:
    _render_page_heading("Inbox", "Knowledge source intake")
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
    if uploaded and st.button("Save uploads", icon=":material/upload_file:", type="primary"):
        inbox = root / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        for file in uploaded:
            target = inbox / Path(file.name).name
            target.write_bytes(file.getvalue())
        _flash(f"Saved {len(uploaded)} upload{'s' if len(uploaded) != 1 else ''} to inbox.")
    actions = st.columns([1, 1, 4])
    if actions[0].button(
        "Process Inbox", type="primary", icon=":material/play_arrow:", use_container_width=True
    ):
        results = process_inbox(
            root,
            provenance=Provenance(
                agent="owner",
                experiment_id="EXP-03.2",
                source="owner_dashboard_process_inbox",
            ),
        )
        _flash(f"Processed {len(results)} inbox file{'s' if len(results) != 1 else ''}.")
    if actions[1].button("Retry Processing", icon=":material/refresh:", use_container_width=True):
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
    _render_page_heading("Knowledge", "External sources with provenance")
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
            st.badge("Knowledge", icon=":material/menu_book:", color="blue")
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
                    "Confirm",
                    key=f"knowledge-confirm-{item.id}",
                    type="primary",
                    icon=":material/check:",
                    use_container_width=True,
                ):
                    _apply_knowledge_review(item.id, "confirm", root)
                if item.status in {KnowledgeStatus.proposed, KnowledgeStatus.confirmed}:
                    with actions[1].popover(
                        "Invalidate",
                        icon=":material/block:",
                        use_container_width=True,
                        key=f"knowledge-invalidate-popover-{item.id}",
                    ):
                        st.caption("This appends an invalidation record. History is retained.")
                        if st.button(
                            "Confirm invalidation",
                            key=f"knowledge-invalidate-{item.id}",
                            type="primary",
                        ):
                            _apply_knowledge_review(item.id, "invalidate", root)
                if item.status in {KnowledgeStatus.active, KnowledgeStatus.confirmed}:
                    with actions[2].popover(
                        "Retire",
                        icon=":material/archive:",
                        use_container_width=True,
                        key=f"knowledge-retire-popover-{item.id}",
                    ):
                        st.caption("This appends a retired lineage head. History is retained.")
                        if st.button(
                            "Confirm retirement",
                            key=f"knowledge-retire-{item.id}",
                            type="primary",
                        ):
                            _apply_knowledge_review(item.id, "retire", root)


def _render_review_queue(
    root: Path,
    pending: list[StoredExperience],
    events_by_id: dict[str, StoredEvent],
) -> None:
    _render_page_heading("Review Queue", f"{len(pending)} unresolved")
    st.caption(f"{len(pending)} unresolved Experience{'s' if len(pending) != 1 else ''}")
    if not pending:
        st.success("Review queue is clear.")
        return
    for experience in pending:
        sessions = _source_sessions(experience, events_by_id)
        with st.container(border=True):
            heading, state = st.columns([4, 1])
            heading.subheader(experience.id)
            state.badge(experience.status.value.title(), color="orange")
            st.badge("Grounded Experience", icon=":material/verified:", color="violet")
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
            if actions[0].button(
                "Confirm",
                key=f"confirm-{experience.id}",
                type="primary",
                icon=":material/check:",
                use_container_width=True,
            ):
                _apply_review(experience.id, "confirm", root)
            with actions[1].popover(
                "Reject",
                icon=":material/block:",
                use_container_width=True,
                key=f"reject-popover-{experience.id}",
            ):
                st.caption("This appends an invalidation record. Evidence remains available.")
                if st.button("Confirm rejection", key=f"reject-{experience.id}", type="primary"):
                    _apply_review(experience.id, "invalidate", root)
            with st.expander("Edit and confirm"):
                with st.form(f"edit-{experience.id}"):
                    situation = st.text_area("Situation", experience.situation)
                    goal = st.text_area("Goal", experience.goal)
                    lesson = st.text_area("Lesson", experience.lesson, height=140)
                    if st.form_submit_button(
                        "Save and confirm", type="primary", icon=":material/save:"
                    ):
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
    _render_page_heading("Experiences", "Grounded actions and outcomes")
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
            st.badge("Grounded Experience", icon=":material/verified:", color="violet")
            if experience.external_project:
                st.badge("External Project Experience", color="orange")
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
            if experience.id in current_ids and experience.status in {
                ExperienceStatus.active,
                ExperienceStatus.confirmed,
                ExperienceStatus.refined,
            }:
                with st.popover(
                    "Retire Experience",
                    icon=":material/archive:",
                    key=f"retire-popover-{experience.id}",
                ):
                    st.caption("This appends a retired lineage head. History is retained.")
                    if st.button(
                        "Confirm retirement", key=f"retire-{experience.id}", type="primary"
                    ):
                        _apply_review(experience.id, "retire", root)


def _render_sessions(root: Path, events: list[StoredEvent]) -> None:
    _render_page_heading("Sessions / Events", "Human-readable episode timeline")
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
        /* Hallmark | designed-as-app | design system: DESIGN.md | modern-minimal */
        :root {
            --eb-canvas: #f4f6fb;
            --eb-surface: #ffffff;
            --eb-header: #20232d;
            --eb-text: #171a21;
            --eb-secondary: #667085;
            --eb-muted: #98a2b3;
            --eb-border: #e1e5ec;
            --eb-violet: #716fe5;
            --eb-violet-soft: #eeedff;
            --eb-blue: #4d7fc7;
            --eb-blue-soft: #eaf1fb;
            --eb-warm: #c9872f;
            --eb-warm-soft: #fff3e2;
            --eb-success: #3f8f78;
            --eb-danger: #c85b63;
            --eb-focus: #514fb1;
            --eb-radius: 8px;
        }
        html, body { overflow-x: clip; }
        .stApp {
            background: var(--eb-canvas);
            color: var(--eb-text);
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
                "Segoe UI", sans-serif;
        }
        [data-testid="stHeader"], [data-testid="stToolbar"],
        [data-testid="stDecoration"], [data-testid="stStatusWidget"] {
            display: none;
        }
        .block-container {
            max-width: 1480px;
            padding-top: 1.25rem;
            padding-bottom: 3rem;
        }
        h1, h2, h3, p { letter-spacing: 0 !important; }
        h2 { font-size: 1.55rem !important; margin-bottom: 0.5rem !important; }
        h3 { font-size: 1.05rem !important; margin-top: 1.1rem !important; }
        .eb-header {
            align-items: center;
            background: var(--eb-header);
            border: 1px solid #2f3440;
            border-radius: var(--eb-radius);
            color: #f8fafc;
            display: flex;
            justify-content: space-between;
            margin-bottom: 1rem;
            min-height: 78px;
            padding: 1rem 1.25rem;
        }
        .eb-brand { font-size: 1.3rem; font-weight: 700; }
        .eb-brand-rule {
            background: var(--eb-violet);
            display: inline-block;
            height: 22px;
            margin-right: 12px;
            vertical-align: -4px;
            width: 4px;
        }
        .eb-subtitle { color: #bac1cf; font-size: 0.82rem; margin-top: 0.2rem; }
        .eb-meta { color: #d8dce5; font-size: 0.78rem; text-align: right; }
        div[data-testid="stMetric"] {
            background: var(--eb-surface);
            border: 1px solid var(--eb-border);
            border-radius: var(--eb-radius);
            min-height: 116px;
            padding: 0.9rem 1rem;
        }
        div[data-testid="stMetric"] label { color: var(--eb-secondary); }
        div[data-testid="stMetricValue"] { color: var(--eb-text); font-size: 1.55rem; }
        div[data-baseweb="tab-list"] {
            background: var(--eb-surface);
            border: 1px solid var(--eb-border);
            border-radius: var(--eb-radius);
            gap: 0.2rem;
            padding: 0.3rem;
        }
        button[data-baseweb="tab"] {
            border-radius: 6px;
            min-height: 42px;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            background: var(--eb-violet-soft);
            color: var(--eb-focus);
        }
        div[data-baseweb="tab-highlight"] { background-color: var(--eb-violet); }
        button[data-baseweb="tab"][aria-selected="true"] p { color: var(--eb-focus); }
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--eb-surface);
            border-color: var(--eb-border) !important;
            border-radius: var(--eb-radius);
        }
        div[data-testid="stMetric"] {
            box-shadow: 0 1px 2px rgba(23, 26, 33, 0.04);
        }
        [data-testid="stExpander"] {
            background: var(--eb-surface);
            border-color: var(--eb-border);
            border-radius: var(--eb-radius);
        }
        .stButton > button, [data-testid="stPopover"] > button,
        [data-testid="stFormSubmitButton"] > button {
            border-radius: 6px;
            min-height: 40px;
        }
        .stButton > button[kind="primary"],
        [data-testid="stFormSubmitButton"] > button[kind="primary"] {
            background: var(--eb-violet);
            border-color: var(--eb-violet);
            color: #ffffff;
        }
        .stButton > button:focus-visible, [data-testid="stPopover"] > button:focus-visible,
        [data-testid="stFormSubmitButton"] > button:focus-visible,
        button[data-baseweb="tab"]:focus-visible {
            outline: 3px solid var(--eb-focus);
            outline-offset: 2px;
        }
        [data-testid="stFileUploaderDropzone"] {
            background: var(--eb-surface);
            border-color: var(--eb-border);
            border-radius: var(--eb-radius);
        }
        [data-testid="stDataFrame"] { border-radius: var(--eb-radius); overflow: hidden; }
        code { overflow-wrap: anywhere; }
        @media (max-width: 768px) {
            .block-container { padding-left: 0.8rem; padding-right: 0.8rem; }
            .eb-header { align-items: flex-start; flex-direction: column; gap: 0.6rem; }
            .eb-meta { text-align: left; }
            div[data-baseweb="tab-list"] { overflow-x: auto; }
            button[data-baseweb="tab"] { white-space: nowrap; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    store_name = html.escape(root.name or str(root))
    st.markdown(
        f"""
        <div class="eb-header">
          <div>
            <div class="eb-brand"><span class="eb-brand-rule"></span>Experience Brain</div>
            <div class="eb-subtitle">Local owner workspace</div>
          </div>
          <div class="eb-meta">{SCHEMA_VERSION}<br>Store: {store_name}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if message := st.session_state.pop("review_flash", None):
        st.success(message)
    events = read_events(root)
    experiences = read_experiences(root)
    knowledge = read_knowledge(root)
    current = current_experiences(root)
    current_knowledge_items = current_knowledge(root)
    pending = pending_review_experiences(root)
    events_by_id = {event.id: event for event in events}
    tab_labels = [
        "Overview",
        f"Review Queue ({len(pending)})",
        "Inbox",
        "Knowledge",
        "Experiences",
        "Sessions / Events",
    ]
    view_defaults = {
        "overview": tab_labels[0],
        "review": tab_labels[1],
        "inbox": tab_labels[2],
        "knowledge": tab_labels[3],
        "experiences": tab_labels[4],
        "sessions": tab_labels[5],
    }
    requested_view = st.query_params.get("view", "overview").strip().lower()
    default_view = view_defaults.get(requested_view, tab_labels[0])
    tab_overview, tab_review, tab_inbox, tab_knowledge, tab_experiences, tab_sessions = st.tabs(
        tab_labels,
        default=default_view,
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
