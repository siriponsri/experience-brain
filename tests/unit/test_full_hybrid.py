from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from experience_brain.cli import app
from experience_brain.config import load_settings
from experience_brain.consolidation import consolidate
from experience_brain.event_store import ingest_events
from experience_brain.full import (
    check_gate,
    latest_decision,
    module_pilot_preflight,
    record_decision,
    write_gain_cost_memo,
)
from experience_brain.hybrid import load_hybrid_index, rebuild_hybrid_index, verify_hybrid_index
from experience_brain.retrieval import retrieve, retrieve_for_settings
from experience_brain.util import canonical_json, read_yaml, sha256_text, write_yaml


def _full_config(root: Path, *, requires_gpu: bool = False) -> None:
    program = (
        "import json,sys; payload=json.load(sys.stdin); value=sum(map(ord,payload['text'])); "
        "print(json.dumps({'embedding':[float(value % 11),1.0],"
        "'input_tokens':2,'output_tokens':0}))"
    )
    write_yaml(
        root / "brain.yaml",
        {
            "profile": "full",
            "condition": "c3",
            "run_id": "full-test",
            "tokenizer_encoding": "cl100k_base",
            "verification": {
                "minimum_successful_episodes": 2,
                "minimum_verifier_score": 1.0,
            },
            "full": {
                "modules": {"hybrid_retrieval": True},
                "hybrid": {
                    "embedder": {
                        "command": [sys.executable, "-c", program],
                        "fingerprint": "test-runtime-v1",
                        "dimensions": 2,
                        "requires_gpu": requires_gpu,
                    }
                },
            },
        },
    )


def test_hybrid_index_is_rebuildable_and_lite_retrieval_is_unchanged(
    brain_root: Path, fixtures: Path
) -> None:
    assert ingest_events(brain_root, fixtures / "events.jsonl") == (4, 0)
    lite = load_settings(brain_root)
    assert consolidate(lite) == (2, 1)
    expected_lite = retrieve(brain_root, fixtures / "task.yaml")

    _full_config(brain_root)
    full = load_settings(brain_root)
    first = rebuild_hybrid_index(full)
    index = Path(first["path"])
    original = index.read_bytes()
    index.unlink()
    second = rebuild_hybrid_index(full)
    assert Path(second["path"]).read_bytes() == original
    assert verify_hybrid_index(full)["status"] == "valid"
    hybrid, telemetry = retrieve_for_settings(full, fixtures / "task.yaml")
    assert [item["id"] for item in hybrid] == [item["id"] for item in expected_lite]
    assert telemetry is not None
    assert telemetry["input_tokens"] == 2
    assert hybrid[0]["retrieval_policy_version"] == "full-hybrid-rrf-v1"


def test_hybrid_stale_index_and_gpu_request_fail_closed(brain_root: Path, fixtures: Path) -> None:
    assert ingest_events(brain_root, fixtures / "events.jsonl") == (4, 0)
    lite = load_settings(brain_root)
    consolidate(lite)
    _full_config(brain_root)
    full = load_settings(brain_root)
    rebuild_hybrid_index(full)
    skill = next((brain_root / "memory" / "skills").glob("*.md"))
    skill.write_text(skill.read_text(encoding="utf-8") + "changed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        verify_hybrid_index(full)

    _full_config(brain_root, requires_gpu=True)
    result = CliRunner().invoke(
        app, ["index", "rebuild", "--module", "hybrid_retrieval", "--root", str(brain_root)]
    )
    assert result.exit_code == 1
    request = brain_root / "evaluations" / "gpu-requests" / "hybrid-retrieval.yaml"
    assert request.is_file()


def test_pi_decision_gate_requires_complete_evidence(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="PI decision"):
        check_gate(tmp_path, "consolidation_pruning")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "analysis_provenance.json").write_text("{}\n", encoding="utf-8")
    (evidence / "gain_cost_memo.md").write_text("# Gain/cost\n", encoding="utf-8")
    decision = record_decision(tmp_path, "hybrid_retrieval", "keep", evidence, "pi-role")
    assert decision.is_file()
    assert check_gate(tmp_path, "consolidation_pruning")["status"] == "open"
    with pytest.raises(ValueError, match="evidence"):
        record_decision(tmp_path, "consolidation_pruning", "keep", tmp_path / "missing", "pi-role")


def test_module_pilot_preflight_and_full_cli(tmp_path: Path) -> None:
    manifest = tmp_path / "pilot-v1.json"
    payload = {
        "manifest_id": "pilot-v1",
        "tasks": [
            {
                "task_id": "pilot-task",
                "benchmark": "terminal_bench",
                "task_contract": {"goal": "exercise module pilot preflight"},
            }
        ],
    }
    payload["manifest_hash"] = sha256_text(canonical_json(payload))
    manifest.write_text(canonical_json(payload) + "\n", encoding="utf-8")
    ablation = tmp_path / "ablation.yaml"
    write_yaml(
        ablation,
        {
            "module": "hybrid_retrieval",
            "runs_per_arm": 3,
            "arms": [{"name": "lite"}, {"name": "candidate"}],
        },
    )
    result = module_pilot_preflight(tmp_path, "hybrid_retrieval", manifest, ablation)
    assert result["status"].startswith("preflight_passed")
    write_yaml(ablation, {"module": "hybrid_retrieval", "runs_per_arm": 3, "arms": []})
    with pytest.raises(ValueError, match="include lite"):
        module_pilot_preflight(tmp_path, "hybrid_retrieval", manifest, ablation)
    write_yaml(
        ablation,
        {
            "module": "hybrid_retrieval",
            "runs_per_arm": 3,
            "arms": [{"name": "lite"}, {"name": "candidate"}],
        },
    )
    runner = CliRunner()
    gate = runner.invoke(
        app, ["full", "gate", "--next-module", "hybrid_retrieval", "--root", str(tmp_path)]
    )
    assert gate.exit_code == 0, gate.output
    pilot = runner.invoke(
        app,
        [
            "benchmark",
            "run-module",
            "--module",
            "hybrid_retrieval",
            "--manifest",
            str(manifest),
            "--ablation-config",
            str(ablation),
            "--root",
            str(tmp_path),
        ],
    )
    assert pilot.exit_code == 0, pilot.output


def test_full_config_rejects_lite_modules_and_invalid_full_condition(brain_root: Path) -> None:
    write_yaml(
        brain_root / "brain.yaml",
        {"profile": "lite", "condition": "c2", "full": {"modules": {"hybrid_retrieval": True}}},
    )
    with pytest.raises(ValueError, match="Lite profile"):
        load_settings(brain_root)
    write_yaml(brain_root / "brain.yaml", {"profile": "full", "condition": "c2"})
    with pytest.raises(ValueError, match="requires condition"):
        load_settings(brain_root)


def test_full_fail_closed_negative_paths(brain_root: Path, fixtures: Path) -> None:
    with pytest.raises(ValueError, match="unknown"):
        latest_decision(brain_root, "unknown")
    with pytest.raises(ValueError, match="not enabled"):
        load_hybrid_index(load_settings(brain_root))
    with pytest.raises(ValueError, match="unknown"):
        check_gate(brain_root, "unknown")
    decisions = brain_root / "evaluations" / "module-decisions"
    decisions.mkdir(parents=True)
    write_yaml(decisions / "hybrid_retrieval-v1.yaml", {"module": "wrong"})
    with pytest.raises(ValueError, match="invalid decision artifact"):
        latest_decision(brain_root, "hybrid_retrieval")
    write_yaml(
        decisions / "hybrid_retrieval-v1.yaml", {"module": "hybrid_retrieval", "decision": "bad"}
    )
    with pytest.raises(ValueError, match="invalid decision value"):
        latest_decision(brain_root, "hybrid_retrieval")
    with pytest.raises(ValueError, match="decision must"):
        record_decision(brain_root, "hybrid_retrieval", "maybe", brain_root, "pi-role")
    with pytest.raises(ValueError, match="approved_by"):
        record_decision(brain_root, "hybrid_retrieval", "keep", brain_root, "")

    assert ingest_events(brain_root, fixtures / "events.jsonl") == (4, 0)
    consolidate(load_settings(brain_root))
    _full_config(brain_root)
    full = load_settings(brain_root)
    with pytest.raises(ValueError, match="missing"):
        load_hybrid_index(full)
    rebuild_hybrid_index(full)
    index = brain_root / ".indexes" / "hybrid" / "index.json"
    index.write_text("not-json", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        verify_hybrid_index(full)


def test_hybrid_runtime_and_index_integrity_guards(brain_root: Path, fixtures: Path) -> None:
    assert ingest_events(brain_root, fixtures / "events.jsonl") == (4, 0)
    consolidate(load_settings(brain_root))
    _full_config(brain_root)
    full = load_settings(brain_root)
    rebuild_hybrid_index(full)
    index_path = brain_root / ".indexes" / "hybrid" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["module"] = "wrong"
    index_path.write_text(json.dumps(index), encoding="utf-8")
    with pytest.raises(ValueError, match="schema"):
        load_hybrid_index(full)
    rebuild_hybrid_index(full)
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["embedder_fingerprint"] = "wrong"
    index_path.write_text(json.dumps(index), encoding="utf-8")
    with pytest.raises(ValueError, match="fingerprint"):
        load_hybrid_index(full)
    _full_config(brain_root)
    broken = read_yaml(brain_root / "brain.yaml", {})
    broken["full"]["hybrid"]["embedder"]["command"] = [sys.executable, "-c", "print('bad')"]
    write_yaml(brain_root / "brain.yaml", broken)
    with pytest.raises(ValueError, match="stdout"):
        rebuild_hybrid_index(load_settings(brain_root))


def test_full_decision_cli_and_pilot_validation_errors(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "analysis_provenance.json").write_text("{}\n", encoding="utf-8")
    (evidence / "gain_cost_memo.md").write_text("# Gain/cost\n", encoding="utf-8")
    decision = CliRunner().invoke(
        app,
        [
            "full",
            "decision",
            "--module",
            "hybrid_retrieval",
            "--decision",
            "remove",
            "--evidence",
            str(evidence),
            "--approved-by",
            "pi-role",
            "--root",
            str(tmp_path),
        ],
    )
    assert decision.exit_code == 0, decision.output
    malformed = tmp_path / "ablation.yaml"
    write_yaml(malformed, {"module": "hybrid_retrieval", "runs_per_arm": 2, "arms": []})
    manifest = tmp_path / "missing.json"
    result = CliRunner().invoke(
        app,
        [
            "benchmark",
            "run-module",
            "--module",
            "hybrid_retrieval",
            "--manifest",
            str(manifest),
            "--ablation-config",
            str(malformed),
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1


def test_module_analysis_writes_blocked_gain_cost_memo(tmp_path: Path) -> None:
    config = tmp_path / "analysis.yaml"
    registry = tmp_path / "registry.yaml"
    runs = [{"run_id": f"{condition}-b1", "block_id": "b1"} for condition in ("c0", "c1", "c2")]
    write_yaml(
        config,
        {
            "analysis_id": "hybrid-pilot",
            "stage": "main-lite",
            "bootstrap": {"seed": 1, "replicates": 10},
            "decision": {"token_reduction_percent": 10},
        },
    )
    write_yaml(registry, {"runs": runs})
    output = tmp_path / "module-analysis"
    result = CliRunner().invoke(
        app,
        [
            "benchmark",
            "analyze-module",
            "--module",
            "hybrid_retrieval",
            "--registry",
            str(registry),
            "--config",
            str(config),
            "--output",
            str(output),
            "--root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "BLOCKED_MISSING_DATA" in (output / "gain_cost_memo.md").read_text(encoding="utf-8")
    assert write_gain_cost_memo(output, "hybrid_retrieval").is_file()


def test_full_config_and_gain_cost_memo_guards(brain_root: Path, tmp_path: Path) -> None:
    write_yaml(brain_root / "brain.yaml", {"profile": "unknown"})
    with pytest.raises(ValueError, match="profile"):
        load_settings(brain_root)
    write_yaml(brain_root / "brain.yaml", {"profile": "full", "condition": "c3", "full": []})
    with pytest.raises(ValueError, match="full must"):
        load_settings(brain_root)
    write_yaml(
        brain_root / "brain.yaml",
        {"profile": "full", "condition": "c3", "full": {"modules": []}},
    )
    with pytest.raises(ValueError, match="modules"):
        load_settings(brain_root)
    write_yaml(
        brain_root / "brain.yaml",
        {"profile": "full", "condition": "c3", "full": {"modules": {"hybrid_retrieval": "yes"}}},
    )
    with pytest.raises(ValueError, match="boolean"):
        load_settings(brain_root)

    with pytest.raises(ValueError, match="unknown"):
        write_gain_cost_memo(tmp_path, "unknown")
    with pytest.raises(ValueError, match="requires"):
        write_gain_cost_memo(tmp_path, "hybrid_retrieval")
    (tmp_path / "validation_report.json").write_text("[]\n", encoding="utf-8")
    (tmp_path / "analysis_provenance.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        write_gain_cost_memo(tmp_path, "hybrid_retrieval")
