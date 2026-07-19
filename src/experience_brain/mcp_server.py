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
from .knowledge import (
    content_hash,
    extract_inbox_file,
    list_inbox_status,
    process_inbox,
    relative_inbox_name,
    save_knowledge_digest,
)
from .models import Actor, EventType, Provenance
from .retrieve import (
    format_briefing,
    format_knowledge_briefing,
    knowledge_payload,
    retrieval_payload,
    retrieve_experience,
    retrieve_knowledge,
    retrieve_memory,
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

    @mcp.tool(name="list_inbox_files")
    def list_inbox_files() -> str:
        return _json({"files": list_inbox_status(resolved_root)})

    @mcp.tool(name="inspect_inbox_file")
    def inspect_inbox_file(filename: str) -> str:
        path = (resolved_root / "inbox" / filename).resolve()
        if not path.is_relative_to((resolved_root / "inbox").resolve()):
            raise ValueError("inbox filename must stay inside inbox/")
        return _json(
            {
                "filename": relative_inbox_name(resolved_root, path),
                "size": path.stat().st_size,
                "content_hash": content_hash(path),
                "suffix": path.suffix.casefold(),
            }
        )

    @mcp.tool(name="extract_inbox_file")
    def extract_file(filename: str) -> str:
        return _json(extract_inbox_file(resolved_root, filename))

    @mcp.tool(name="process_inbox")
    def process_inbox_tool(
        project: str = "general",
        agent: str | None = "codex_cli",
        model: str | None = None,
        reasoning_effort: str | None = None,
        experiment_id: str | None = "EXP-03.2",
        run_id: str | None = None,
        retry: bool = False,
    ) -> str:
        results = process_inbox(
            resolved_root,
            project=project,
            retry=retry,
            provenance=_provenance(
                agent=agent,
                model=model,
                reasoning_effort=reasoning_effort,
                experiment_id=experiment_id,
                run_id=run_id,
                source="process_inbox_mcp",
            ),
        )
        return _json(
            {
                "processed": [
                    {
                        "filename": result.filename,
                        "content_hash": result.content_hash,
                        "status": result.status,
                        "duplicate_of": result.duplicate_of,
                        "knowledge_id": result.knowledge_id,
                        "error": result.error,
                    }
                    for result in results
                ]
            }
        )

    @mcp.tool(name="save_knowledge_digest")
    def save_digest(
        title: str,
        summary: str,
        key_facts: list[str],
        suggested_applicability: str,
        tags: list[str],
        source_filename: str,
        source_content_hash: str,
        source_type: str,
        source_mime_type: str | None = None,
        project: str = "general",
        agent: str | None = "codex_cli",
        model: str | None = None,
        reasoning_effort: str | None = None,
        experiment_id: str | None = "EXP-03.2",
        run_id: str | None = None,
    ) -> str:
        knowledge = save_knowledge_digest(
            resolved_root,
            title=title,
            summary=summary,
            key_facts=key_facts,
            suggested_applicability=suggested_applicability,
            tags=tags,
            source_filename=source_filename,
            source_content_hash=source_content_hash,
            source_type=source_type,
            source_mime_type=source_mime_type,
            project=project,
            provenance=_provenance(
                agent=agent,
                model=model,
                reasoning_effort=reasoning_effort,
                experiment_id=experiment_id,
                run_id=run_id,
                source="agent_knowledge_digest",
            ),
        )
        return _json({"knowledge_id": knowledge.id, "status": knowledge.status.value})

    @mcp.tool(name="query_experience")
    def query_experience(question: str, project: str | None = None, limit: int = 5) -> str:
        items = retrieve_experience(resolved_root, question, project=project, limit=limit)
        return _json(
            {
                "retrieval_result": "match" if items else "no_match",
                "briefing": format_briefing(items),
                "items": retrieval_payload(items),
            }
        )

    @mcp.tool(name="query_knowledge")
    def query_knowledge(question: str, project: str | None = None, limit: int = 5) -> str:
        items = retrieve_knowledge(resolved_root, question, project=project, limit=limit)
        return _json(
            {
                "retrieval_result": "match" if items else "no_match",
                "briefing": format_knowledge_briefing(items),
                "items": knowledge_payload(items),
            }
        )

    @mcp.tool(name="query_memory")
    def query_memory(question: str, project: str | None = None, limit: int = 5) -> str:
        return _json(retrieve_memory(resolved_root, question, project=project, limit=limit))

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
        retrieval_result: str | None = None,
        usage: str | None = None,
        task_outcome: str | None = None,
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
            retrieval_result=retrieval_result,  # type: ignore[arg-type]
            usage=usage,  # type: ignore[arg-type]
            task_outcome=task_outcome,  # type: ignore[arg-type]
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
                "retrieval_result": event.metadata["retrieval_result"],
                "usage": event.metadata["usage"],
                "task_outcome": event.metadata["task_outcome"],
                "used_experience_ids": used_experience_ids or [],
            }
        )

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
