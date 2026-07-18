from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

MEMORYARENA_PATH = Path(__file__).resolve().parents[1] / "benchmark-exp" / "memoryarena"
sys.path.insert(0, str(MEMORYARENA_PATH))

from adapter import (  # noqa: E402
    ExperienceBrainMemorySystem,
    NoPersistentMemorySystem,
    condition_store_root,
    scan_store_for_forbidden_terms,
    summarize_logs,
    validate_store_isolation,
    write_result_json,
)
from adapter.experience_brain_memory import AdapterProvenance  # noqa: E402

from experience_brain.store import lint_store, read_events, read_experiences  # noqa: E402


def _provenance(run_id: str = "EXP04-FRMATH-SMOKE-C2-RUN001") -> AdapterProvenance:
    return AdapterProvenance(
        model="gpt-5-mini",
        reasoning_effort="medium",
        experiment_id="EXP-04",
        run_id=run_id,
        memoryarena_commit="6cd9de14b71915e39ac742a20dc33785e14b6aab",
        dataset_revision="da1a37c8b19280e18627ca01cf368195a5e1d92e",
    )


def test_c0_no_persistent_memory_does_not_create_store(tmp_path: Path) -> None:
    memory = NoPersistentMemorySystem()
    response = memory.add_chunk("## Task: prior dry run\n## solution: model response")
    assert response["status"] == "ignored"
    prompt = memory.wrap_user_prompt("current formal reasoning prompt")
    assert "<memory_context>\nNone\n</memory_context>" in prompt
    assert not (tmp_path / "data").exists()


def test_c1_raw_episode_memory_stores_events_without_experiences(tmp_path: Path) -> None:
    memory = ExperienceBrainMemorySystem(
        root=tmp_path,
        condition="C1",
        user_id="user-a",
        task_group_id="formal_reasoning_math",
        provenance=_provenance("EXP04-FRMATH-SMOKE-C1-RUN001"),
    )
    response = memory.add_chunk("## Task: use lemma A\n## solution: derived intermediate result")
    assert response["condition"] == "C1"
    prompt = memory.wrap_user_prompt("lemma A is useful now")
    assert "source_event_id" in prompt
    assert read_events(tmp_path)
    assert read_experiences(tmp_path) == []
    assert lint_store(tmp_path) == []
    diagnostics = memory.diagnostics()
    assert diagnostics["events_captured"] == 2
    assert diagnostics["experiences_consolidated"] == 0


def test_c2_full_experience_brain_creates_traceable_experience(tmp_path: Path) -> None:
    memory = ExperienceBrainMemorySystem(
        root=tmp_path,
        condition="C2",
        user_id="user-b",
        task_group_id="formal_reasoning_math",
        provenance=_provenance(),
    )
    response = memory.add_chunk("## Task: use theorem B\n## solution: established bound")
    assert "experience_id" in response
    prompt = memory.wrap_user_prompt("theorem B bound needed")
    assert "experience_id" in prompt
    assert "evidence_event_ids" in prompt
    events = read_events(tmp_path)
    experiences = read_experiences(tmp_path)
    assert len(events) >= 2
    assert len(experiences) >= 2
    source_event_ids = {event.id for event in events}
    assert set(experiences[0].evidence_event_ids) <= source_event_ids
    assert experiences[0].provenance.extra["memoryarena_commit"].startswith("6cd9de14")
    assert any(event.metadata.get("kind") == "retrieval_usage" for event in events)
    assert lint_store(tmp_path) == []


def test_leakage_and_store_isolation_checks(tmp_path: Path) -> None:
    c1 = condition_store_root(tmp_path, "C1", "formal_reasoning_math")
    c2 = condition_store_root(tmp_path, "C2", "formal_reasoning_math")
    validate_store_isolation([c1, c2])
    with pytest.raises(ValueError, match="nested"):
        validate_store_isolation([tmp_path / "stores", tmp_path / "stores" / "C1"])

    memory = ExperienceBrainMemorySystem(
        root=c1,
        condition="C1",
        user_id="user-c",
        task_group_id="formal_reasoning_math",
        provenance=_provenance("EXP04-FRMATH-SMOKE-C1-RUN001"),
    )
    with pytest.raises(ValueError, match="benchmark leakage"):
        memory.add_chunk("ground_truth: do not store this")
    memory.add_chunk("## Task: safe\n## solution: safe agent output")
    assert scan_store_for_forbidden_terms(c1, ["ground_truth", "gold_answer"]) == []


def test_result_serialization_uses_only_available_metrics(tmp_path: Path) -> None:
    payload = summarize_logs(
        condition="C2",
        run_id="EXP04-FRMATH-SMOKE-C2-RUN001",
        task_group_id="formal_reasoning_math",
        logs=[
            {
                "is_correct": True,
                "time": 1.5,
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
            },
            {
                "is_correct": False,
                "time": 2.0,
                "input_tokens": 8,
                "output_tokens": 4,
                "total_tokens": 12,
            },
        ],
        diagnostics={"events_captured": 3},
    )
    assert payload["primary"]["subtask_accuracy"] == 0.5
    assert payload["primary"]["complete_task_group_success"] is False
    assert payload["supporting"]["tokens_per_successful_subtask"] == 27
    path = tmp_path / "result.json"
    write_result_json(path, payload)
    assert json.loads(path.read_text(encoding="utf-8"))["condition"] == "C2"
