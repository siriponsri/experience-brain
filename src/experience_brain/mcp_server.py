from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .capture import end_session as capture_end_session
from .capture import make_event_id, record_event
from .capture import start_session as capture_start_session
from .consolidate import consolidate_session
from .models import Actor, EventType, Provenance
from .retrieve import (
    format_briefing,
    retrieval_payload,
    retrieve_experience,
)
from .retrieve import (
    record_retrieval_usage as capture_retrieval_usage,
)

SERVER_NAME = "experience-brain"


def _provenance(
    *,
    agent: str | None = None,
    model: str | None = None,
    reasoning_effort: str | None = None,
    experiment_id: str | None = None,
    run_id: str | None = None,
    source: str = "codex_cli_mcp",
) -> Provenance:
    return Provenance(
        agent=agent,
        model=model,
        reasoning_effort=reasoning_effort,
        experiment_id=experiment_id,
        run_id=run_id,
        source=source,
    )


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def create_server(root: Path | str = ".") -> Any:
    resolved_root = Path(root).resolve()
    mcp = FastMCP(SERVER_NAME)

    @mcp.tool(name="start_session")
    def start_session(
        project: str,
        session_id: str,
        goal: str = "",
        task_id: str | None = None,
        agent: str | None = "codex_cli",
        model: str | None = None,
        reasoning_effort: str | None = None,
        experiment_id: str | None = None,
        run_id: str | None = None,
    ) -> str:
        event = capture_start_session(
            resolved_root,
            project=project,
            session_id=session_id,
            goal=goal,
            task_id=task_id,
            provenance=_provenance(
                agent=agent,
                model=model,
                reasoning_effort=reasoning_effort,
                experiment_id=experiment_id,
                run_id=run_id,
            ),
        )
        return _json({"event_id": event.id, "session_id": session_id, "project": project})

    @mcp.tool(name="end_session")
    def end_session(
        project: str,
        session_id: str,
        summary: str = "",
        outcome: str | None = None,
        task_id: str | None = None,
        consolidate: bool = True,
        agent: str | None = "codex_cli",
        model: str | None = None,
        reasoning_effort: str | None = None,
        experiment_id: str | None = None,
        run_id: str | None = None,
    ) -> str:
        event = capture_end_session(
            resolved_root,
            project=project,
            session_id=session_id,
            summary=summary,
            outcome=outcome,
            task_id=task_id,
            provenance=_provenance(
                agent=agent,
                model=model,
                reasoning_effort=reasoning_effort,
                experiment_id=experiment_id,
                run_id=run_id,
            ),
        )
        response: dict[str, object] = {"event_id": event.id, "session_id": session_id}
        if consolidate:
            count, report = consolidate_session(resolved_root, session_id)
            response.update({"experiences_created": count, "review_report": str(report)})
        return _json(response)

    @mcp.tool(name="record_event")
    def record_event_tool(
        project: str,
        session_id: str,
        event_type: str,
        actor: str,
        content: str = "",
        event_id: str | None = None,
        task_id: str | None = None,
        source: str = "mcp",
        tool_name: str | None = None,
        error_signature: str | None = None,
        outcome: str | None = None,
        metadata: dict[str, Any] | None = None,
        agent: str | None = "codex_cli",
        model: str | None = None,
        reasoning_effort: str | None = None,
        experiment_id: str | None = None,
        run_id: str | None = None,
    ) -> str:
        event = record_event(
            resolved_root,
            event_id=event_id
            or make_event_id("EVT", project=project, session_id=session_id, content=content),
            event_type=EventType(event_type),
            actor=Actor(actor),
            project=project,
            session_id=session_id,
            task_id=task_id,
            source=source,
            content=content,
            tool_name=tool_name,
            error_signature=error_signature,
            outcome=outcome,
            metadata=metadata,
            provenance=_provenance(
                agent=agent,
                model=model,
                reasoning_effort=reasoning_effort,
                experiment_id=experiment_id,
                run_id=run_id,
            ),
        )
        return _json(
            {
                "event_id": event.id,
                "redactions": [redaction.model_dump() for redaction in event.provenance.redactions],
            }
        )

    @mcp.tool(name="process_session")
    def process_session(session_id: str | None = None) -> str:
        count, report = consolidate_session(resolved_root, session_id)
        return _json({"experiences_created": count, "review_report": str(report)})

    @mcp.tool(name="query_experience")
    def query_experience(question: str, project: str | None = None, limit: int = 5) -> str:
        items = retrieve_experience(resolved_root, question, project=project, limit=limit)
        return _json({"briefing": format_briefing(items), "items": retrieval_payload(items)})

    @mcp.tool(name="review_latest")
    def review_latest() -> str:
        path = resolved_root / "reports" / "latest.md"
        if not path.exists():
            return "No review report found."
        return path.read_text(encoding="utf-8")

    @mcp.tool(name="record_retrieval_usage")
    def record_retrieval_usage(
        project: str,
        session_id: str,
        query: str,
        retrieved_experience_ids: list[str],
        used_experience_ids: list[str] | None = None,
        stage: str = "pre_task",
        outcome: str | None = None,
        task_id: str | None = None,
        agent: str | None = "codex_cli",
        model: str | None = None,
        reasoning_effort: str | None = None,
        experiment_id: str | None = None,
        run_id: str | None = None,
    ) -> str:
        event = capture_retrieval_usage(
            resolved_root,
            project=project,
            session_id=session_id,
            task_id=task_id,
            query=query,
            retrieved_experience_ids=retrieved_experience_ids,
            used_experience_ids=used_experience_ids,
            stage=stage,
            outcome=outcome,
            provenance=_provenance(
                agent=agent,
                model=model,
                reasoning_effort=reasoning_effort,
                experiment_id=experiment_id,
                run_id=run_id,
            ),
        )
        return _json({"event_id": event.id, "used_experience_ids": used_experience_ids or []})

    @mcp.tool(name="record_outcome_feedback")
    def record_outcome_feedback(
        project: str,
        session_id: str,
        content: str,
        outcome: str | None = None,
        experience_id: str | None = None,
        task_id: str | None = None,
        agent: str | None = "codex_cli",
        model: str | None = None,
        reasoning_effort: str | None = None,
        experiment_id: str | None = None,
        run_id: str | None = None,
    ) -> str:
        event = record_event(
            resolved_root,
            event_type=EventType.feedback,
            actor=Actor.owner,
            project=project,
            session_id=session_id,
            task_id=task_id,
            content=content,
            outcome=outcome,
            metadata={"kind": "outcome_feedback", "experience_id": experience_id},
            provenance=_provenance(
                agent=agent,
                model=model,
                reasoning_effort=reasoning_effort,
                experiment_id=experiment_id,
                run_id=run_id,
            ),
        )
        return _json({"event_id": event.id, "experience_id": experience_id})

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    create_server(args.root).run()


if __name__ == "__main__":
    main()
