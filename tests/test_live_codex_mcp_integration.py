from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, cast

from experience_brain.mcp_server import create_server
from experience_brain.retrieve import effective_experiences
from experience_brain.store import lint_store, read_events, read_experiences


def _text(blocks: object) -> str:
    if isinstance(blocks, tuple):
        blocks = blocks[0]
    if not isinstance(blocks, list):
        raise TypeError("MCP result must be a list of content blocks")
    return "".join(str(getattr(block, "text", "")) for block in blocks)


async def _call(server: Any, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(_text(await server.call_tool(name, arguments)))
    if not isinstance(payload, dict):
        raise TypeError("MCP JSON response must be an object")
    return cast(dict[str, Any], payload)


def test_live_codex_mcp_three_session_workflow(brain_root: Path) -> None:
    async def scenario() -> None:
        server = create_server(brain_root)
        tools = {tool.name for tool in await server.list_tools()}
        assert {
            "start_session",
            "end_session",
            "record_event",
            "process_session",
            "query_experience",
            "review_latest",
            "record_retrieval_usage",
            "record_outcome_feedback",
            "list_inbox_files",
            "inspect_inbox_file",
            "extract_inbox_file",
            "process_inbox",
            "save_knowledge_digest",
            "query_knowledge",
            "query_memory",
        } <= tools

        provenance: dict[str, Any] = {
            "agent": "codex_cli",
            "model": "gpt-5.5",
            "reasoning_effort": "medium",
            "experiment_id": "EXP-03",
        }

        await _call(
            server,
            "start_session",
            {
                **provenance,
                "run_id": "RUN-001",
                "project": "live-codex-example",
                "session_id": "RUN-001",
                "goal": "Fix calculator pytest failure by patching the add helper.",
            },
        )
        before_more_events = (brain_root / "data" / "events.jsonl").read_bytes()
        events_to_record: list[dict[str, Any]] = [
            {
                "event_type": "user_message",
                "actor": "owner",
                "content": "The calculator add test fails; make it pass.",
            },
            {
                "event_type": "decision",
                "actor": "agent",
                "content": "Run pytest first, patch the add helper, then rerun pytest.",
            },
            {
                "event_type": "tool_call",
                "actor": "agent",
                "tool_name": "pytest",
                "content": "python -m pytest -q",
            },
            {
                "event_type": "tool_result",
                "actor": "tool",
                "tool_name": "pytest",
                "outcome": "failure",
                "content": "FAILED calculator test; api_key=sk-secretsecretsecret",
                "metadata": {"stdout": "patient name=Example Person"},
            },
            {
                "event_type": "file_change",
                "actor": "agent",
                "content": "Changed calculator.add to return a + b.",
            },
            {
                "event_type": "outcome",
                "actor": "agent",
                "outcome": "success",
                "content": "pytest passed after calculator.add patch.",
            },
        ]
        for event in events_to_record:
            await _call(
                server,
                "record_event",
                {
                    **provenance,
                    "run_id": "RUN-001",
                    "project": "live-codex-example",
                    "session_id": "RUN-001",
                    **event,
                },
            )
        end = await _call(
            server,
            "end_session",
            {
                **provenance,
                "run_id": "RUN-001",
                "project": "live-codex-example",
                "session_id": "RUN-001",
                "summary": "Calculator pytest failure fixed.",
                "outcome": "success",
                "consolidate": True,
            },
        )
        assert end["experiences_created"] == 1
        assert (brain_root / "data" / "events.jsonl").read_bytes().startswith(before_more_events)

        events = read_events(brain_root)
        assert any("[REDACTED]" in event.content for event in events)
        assert any(event.provenance.redactions for event in events)
        assert any(event.metadata.get("stdout") == "[REDACTED]" for event in events)

        experiences = read_experiences(brain_root)
        assert len(experiences) == 1
        experience = experiences[0]
        assert set(experience.evidence_event_ids) <= {event.id for event in events}
        assert experience.provenance.model == "gpt-5.5"
        assert experience.provenance.reasoning_effort == "medium"
        assert experience.provenance.run_id == "RUN-001"

        review = _text(await server.call_tool("review_latest", {}))
        assert experience.id in review
        assert "Evidence events:" in review

        await _call(
            server,
            "start_session",
            {
                **provenance,
                "run_id": "RUN-002",
                "project": "live-codex-example",
                "session_id": "RUN-002",
                "goal": "Handle another calculator pytest failure.",
            },
        )
        related = await _call(
            server,
            "query_experience",
            {
                "project": "live-codex-example",
                "question": "calculator pytest failure patch add helper",
            },
        )
        assert related["items"]
        assert related["retrieval_result"] == "match"
        assert related["items"][0]["label"] == "Project Experience"
        used_id = str(related["items"][0]["id"])
        await _call(
            server,
            "record_retrieval_usage",
            {
                **provenance,
                "run_id": "RUN-002",
                "project": "live-codex-example",
                "session_id": "RUN-002",
                "query": "calculator pytest failure patch add helper",
                "retrieved_experience_ids": [used_id],
                "used_experience_ids": [used_id],
                "stage": "pre_task",
                "outcome": "success",
            },
        )
        await _call(
            server,
            "record_outcome_feedback",
            {
                **provenance,
                "run_id": "RUN-002",
                "project": "live-codex-example",
                "session_id": "RUN-002",
                "experience_id": used_id,
                "content": "Retrieved pytest lesson was useful for the later calculator task.",
                "outcome": "success",
            },
        )
        usage_events = [
            event
            for event in read_events(brain_root)
            if event.metadata.get("kind") == "retrieval_usage"
        ]
        assert usage_events
        assert usage_events[-1].metadata["used_experience_ids"] == [used_id]
        assert usage_events[-1].metadata["retrieval_result"] == "match"
        assert usage_events[-1].metadata["usage"] == "used"
        assert usage_events[-1].metadata["task_outcome"] == "success"
        assert any(exp.last_used_session_id == "RUN-002" for exp in read_experiences(brain_root))

        await _call(
            server,
            "start_session",
            {
                **provenance,
                "run_id": "RUN-003",
                "project": "docs-example",
                "session_id": "RUN-003",
                "goal": "Update README license wording.",
            },
        )
        unrelated = await _call(
            server,
            "query_experience",
            {"project": "docs-example", "question": "README license wording"},
        )
        assert unrelated["items"] == []
        assert unrelated["retrieval_result"] == "no_match"
        assert unrelated["briefing"] == "No relevant experience found."

        no_match_usage = await _call(
            server,
            "record_retrieval_usage",
            {
                **provenance,
                "run_id": "RUN-003",
                "project": "docs-example",
                "session_id": "RUN-003",
                "query": "README license wording",
                "retrieved_experience_ids": [],
                "stage": "pre_task",
                "task_outcome": "unknown",
            },
        )
        assert no_match_usage["retrieval_result"] == "no_match"
        assert no_match_usage["usage"] == "unavailable"
        assert no_match_usage["task_outcome"] == "unknown"

        external = await _call(
            server,
            "query_experience",
            {"project": "external-calculator", "question": "calculator pytest add helper"},
        )
        assert external["items"]
        assert external["items"][0]["label"] == "External Project Experience"

        current = effective_experiences(brain_root)
        assert len(current) >= 1
        assert lint_store(brain_root) == []

    asyncio.run(scenario())
