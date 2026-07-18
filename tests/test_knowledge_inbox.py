from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from typing import Any, cast

from experience_brain.capture import capture_event
from experience_brain.knowledge import list_inbox_status, process_inbox, review_knowledge
from experience_brain.models import (
    Actor,
    Event,
    EventType,
    Experience,
    ExperienceStatus,
    KnowledgeStatus,
)
from experience_brain.retrieve import retrieve_experience, retrieve_knowledge, retrieve_memory
from experience_brain.store import append_experience, lint_store, read_knowledge


def _seed_experience(root: Path) -> None:
    capture_event(
        root,
        Event(
            id="EVT-exp-knowledge-separate",
            type=EventType.outcome,
            actor=Actor.agent,
            project="dual-memory",
            session_id="S-exp",
            content="pytest passed after using the parser fixture.",
            outcome="success",
        ),
    )
    append_experience(
        root,
        Experience(
            id="EXP-dual-parser",
            project="dual-memory",
            source_project="dual-memory",
            status=ExperienceStatus.confirmed,
            lesson="Use the parser fixture when pytest setup fails.",
            evidence_event_ids=["EVT-exp-knowledge-separate"],
            confidence=0.9,
        ),
    )


def test_process_inbox_creates_traceable_knowledge_and_detects_duplicates(
    brain_root: Path,
) -> None:
    inbox = brain_root / "inbox"
    markdown = inbox / "medication-notes.md"
    markdown.write_text(
        "# Medication Notes\n\nWarfarin requires INR monitoring.\nNever store patient name=Jane.",
        encoding="utf-8",
    )
    (inbox / "z-medication-copy.txt").write_text(
        markdown.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (inbox / "table.json").write_text(
        json.dumps({"topic": "inventory", "fact": "Cold-chain items need temperature logs."}),
        encoding="utf-8",
    )
    workbook_factory = cast(Any, import_module("openpyxl")).Workbook
    workbook = workbook_factory()
    sheet = workbook.active
    sheet.title = "Stock"
    sheet.append(["item", "rule"])
    sheet.append(["vaccine", "keep temperature log"])
    workbook.save(inbox / "stock.xlsx")
    (inbox / "scan.bin").write_bytes(b"\x00\x01unsupported")

    before = (brain_root / "data" / "knowledge.jsonl").read_bytes()
    results = process_inbox(brain_root, project="dual-memory")

    assert (brain_root / "data" / "knowledge.jsonl").read_bytes().startswith(before)
    statuses = {result.filename: result.status for result in results}
    assert statuses["medication-notes.md"] == KnowledgeStatus.proposed.value
    assert statuses["z-medication-copy.txt"] == "duplicate"
    assert statuses["table.json"] == KnowledgeStatus.proposed.value
    assert statuses["stock.xlsx"] == KnowledgeStatus.proposed.value
    assert statuses["scan.bin"] == KnowledgeStatus.unsupported.value

    knowledge = read_knowledge(brain_root)
    assert len(knowledge) == 4
    medication = next(item for item in knowledge if item.source_filename == "medication-notes.md")
    assert medication.provenance.redactions
    assert "[REDACTED]" in " ".join([medication.summary, *medication.key_facts])
    assert medication.source_content_hash
    assert medication.extractor.name
    assert list_inbox_status(brain_root)
    assert lint_store(brain_root) == []

    repeated = process_inbox(brain_root, project="dual-memory")
    assert all(result.status == "duplicate" for result in repeated)


def test_knowledge_review_and_unified_retrieval_remain_separate(brain_root: Path) -> None:
    inbox = brain_root / "inbox"
    (inbox / "parser-guide.txt").write_text(
        "Parser guide: fixtures describe valid tokens and setup order.",
        encoding="utf-8",
    )
    processed = process_inbox(brain_root, project="dual-memory")
    knowledge_id = next(result.knowledge_id for result in processed if result.knowledge_id)
    assert knowledge_id is not None
    confirmed = review_knowledge(brain_root, knowledge_id, action="confirm")
    assert confirmed.status == KnowledgeStatus.confirmed

    _seed_experience(brain_root)
    knowledge_results = retrieve_knowledge(
        brain_root, "parser guide valid tokens", project="dual-memory"
    )
    experience_results = retrieve_experience(
        brain_root, "parser fixture pytest", project="dual-memory"
    )
    unified = retrieve_memory(brain_root, "parser fixture guide", project="dual-memory")

    assert knowledge_results
    assert experience_results
    assert unified["knowledge"]
    assert unified["experience"]
    assert "Relevant Knowledge" in unified["briefing"]
    assert "Relevant Experience" in unified["briefing"]
    assert "source_filename" in unified["knowledge"][0]
    assert "evidence_event_ids" in unified["experience"][0]
    assert retrieve_knowledge(brain_root, "warfarin inr bleeding", project="dual-memory") == []
