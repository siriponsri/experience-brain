from __future__ import annotations

from pathlib import Path

import pytest

from experience_brain.benchmark.analysis import (
    _artifact_details,
    _artifact_ok,
    _bootstrap,
    _contract,
    _decision,
    _is_deployment,
    _mde,
    _registry,
    _taxonomy,
    _token_status,
    _total_tokens,
    _validate_row,
    analyze,
    decision_from_analysis,
    validate_analysis,
)
from experience_brain.util import canonical_json, sha256_text, write_yaml


def test_analysis_blocks_without_preregistered_raw_runs(tmp_path: Path) -> None:
    contract = tmp_path / "analysis.yaml"
    write_yaml(
        contract,
        {
            "analysis_id": "main-lite-v1",
            "stage": "main-lite",
            "runs": [
                {"run_id": "c0-r1", "block_id": "b1"},
                {"run_id": "c1-r1", "block_id": "b1"},
                {"run_id": "c2-r1", "block_id": "b1"},
            ],
            "bootstrap": {"seed": 7, "replicates": 10},
            "decision": {"token_reduction_percent": 10},
        },
    )
    output = analyze(tmp_path, contract, tmp_path / "analysis")
    memo = (output / "DECISION_MEMO.md").read_text(encoding="utf-8")
    assert "BLOCKED_MISSING_DATA" in memo
    report = (output / "validation_report.json").read_text(encoding="utf-8")
    assert "missing preregistered run" in report


def test_main_lite_analysis_is_paired_and_includes_background(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path.parent / "benchmark-home"
    monkeypatch.setenv("BENCHMARK_HOME", str(home))
    runs: list[dict[str, str]] = []
    for block in ("b1", "b2", "b3"):
        for condition in ("c0", "c1", "c2"):
            run_id = f"{condition}-{block}"
            runs.append({"run_id": run_id, "block_id": block})
            artifact = home / "artifacts" / f"{run_id}.txt"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text('{"success": true, "score": 1.0}', encoding="utf-8")
            reference = {
                "relative_path": artifact.relative_to(home).as_posix(),
                "sha256": sha256_text(artifact.read_text(encoding="utf-8")),
                "size": artifact.stat().st_size,
            }
            outcome = {
                "run_id": run_id,
                "condition": condition,
                "task_id": "E1-LS1-T4",
                "split": "deployment",
                "benchmark": "skillevolbench",
                "attempt_id": f"{run_id}-a0",
                "attempt_status": "completed",
                "success": condition != "c1",
                "failure_signature": "assertion failed" if condition == "c1" else None,
                "foreground_input_tokens": 200 if condition == "c0" else 100,
                "foreground_output_tokens": 20,
                "background_tokens": 40 if condition == "c2" else 0,
                "selector": {"role": "T4"},
                "verifier": {"raw_stdout": reference},
                "infrastructure_failure": None,
            }
            target = tmp_path / "evaluations" / "runs" / run_id / "outcomes.jsonl"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(canonical_json(outcome) + "\n", encoding="utf-8")
    contract = tmp_path / "main.yaml"
    write_yaml(
        contract,
        {
            "analysis_id": "main-lite-v1",
            "stage": "main-lite",
            "runs": runs,
            "bootstrap": {"seed": 3, "replicates": 40},
            "decision": {"token_reduction_percent": 10},
        },
    )
    output = analyze(tmp_path, contract, tmp_path / "analysis")
    assert "GO" in (output / "DECISION_MEMO.md").read_text(encoding="utf-8")
    metrics = (output / "normalized_metrics.jsonl").read_text(encoding="utf-8")
    assert '"total_tokens":160' in metrics
    assert '"failure_taxon":"verifier_requirement_unmet"' in metrics


def test_analysis_failure_and_zero_success_guards() -> None:
    assert _taxonomy({"infrastructure_failure": {"category": "verifier_unavailable"}}) == (
        "infrastructure",
        "verifier",
    )
    assert _taxonomy({"failure_signature": "tool timeout"}) == ("task", "time_or_token_stop")
    assert _taxonomy({"success": True}) == ("task", "passed")
    with pytest.raises(ValueError, match="token"):
        _total_tokens({"foreground_input_tokens": 1, "foreground_output_tokens": 1})
    result = _bootstrap(
        [{"block_id": "b", "c0_success": 0, "c2_success": 1, "c0_tokens": 1, "c2_tokens": 1}],
        4,
        1,
    )
    assert result["zero_success_replicates"] == 4
    assert result["token_reduction_ci"] is None


def test_analysis_contract_and_artifact_guards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    invalid = tmp_path / "invalid.yaml"
    write_yaml(invalid, {"analysis_id": "x"})
    with pytest.raises(ValueError, match="missing"):
        _contract(invalid)
    monkeypatch.setenv("BENCHMARK_HOME", str(tmp_path / "home"))
    assert _artifact_ok(tmp_path, {}) is False
    assert _artifact_ok(tmp_path, {"relative_path": "missing"}) is False
    assert _is_deployment({"benchmark": "terminal_bench"}) is False
    assert _is_deployment({"benchmark": "skillevolbench", "split": "acquisition"}) is False


def test_v2_registry_bundle_and_fail_closed_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path.parent / "benchmark-home-v2"
    monkeypatch.setenv("BENCHMARK_HOME", str(home))
    runs: list[dict[str, str]] = []
    for block in ("b1", "b2", "b3"):
        for condition in ("c0", "c1", "c2"):
            run_id = f"{condition}-{block}"
            runs.append({"run_id": run_id, "block_id": block, "condition": condition})
            artifact = home / "artifacts" / f"{run_id}.txt"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text('{"success": true, "score": 1.0}', encoding="utf-8")
            reference = {
                "relative_path": artifact.relative_to(home).as_posix(),
                "sha256": sha256_text(artifact.read_text(encoding="utf-8")),
                "size": artifact.stat().st_size,
            }
            outcome = {
                "run_id": run_id,
                "condition": condition,
                "task_id": "E1-LS1-T4",
                "split": "deployment",
                "benchmark": "skillevolbench",
                "attempt_id": f"{run_id}-a0",
                "attempt_status": "completed",
                "success": condition != "c1",
                "failure_signature": "assertion failed" if condition == "c1" else None,
                "foreground_input_tokens": 200 if condition == "c0" else 100,
                "foreground_output_tokens": 20,
                "background_tokens": 40 if condition == "c2" else 0,
                "selector": {"role": "T4"},
                "verifier": {"raw_stdout": reference},
                "infrastructure_failure": None,
                "wall_seconds": 1.0,
                "budget": {"foreground_tokens": 1000},
                "stop_reason": None,
                "manifest_hash": "manifest",
                "benchmark_lock_hash": "lock",
                "config_hash": "runtime",
                "model": "test-model",
                "reasoning": "test-reasoning",
                "endpoint_fingerprint": "endpoint-v1",
                "tools": ["tool-v1"],
            }
            run_dir = tmp_path / "evaluations" / "runs" / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "outcomes.jsonl").write_text(
                canonical_json(outcome) + "\n", encoding="utf-8"
            )
            (run_dir / "run.json").write_text(
                canonical_json({"stage": "main-lite"}) + "\n", encoding="utf-8"
            )
    config = tmp_path / "config.yaml"
    registry = tmp_path / "registry.yaml"
    write_yaml(
        config,
        {
            "schema_version": 2,
            "analysis_id": "main-lite-v2",
            "stage": "main-lite",
            "frozen_inputs": {
                "manifest_hash": "manifest",
                "lock_hash": "lock",
                "runtime_hash": "runtime",
            },
            "bootstrap": {"seed": 3, "replicates": 10000},
            "decision": {"token_reduction_percent": 10},
        },
    )
    write_yaml(registry, {"runs": runs})
    output = analyze(tmp_path, config, tmp_path / "analysis-v2", registry)
    assert decision_from_analysis(output) == "go"
    assert (output / "paired_effects.csv").is_file()
    assert (output / "figures" / "tokens_by_condition.svg").is_file()
    assert (output / "figures" / "tokens_by_condition.png").is_file()

    pilot = output / "pilot-only"
    pilot.mkdir()
    (pilot / "validation_report.json").write_text(
        canonical_json({"status": "passed", "stage": "pilot"}), encoding="utf-8"
    )
    (pilot / "decision_memo.md").write_text("Decision: **REDESIGN**\n", encoding="utf-8")
    with pytest.raises(ValueError, match="pilot-only"):
        decision_from_analysis(pilot)


def test_analysis_validation_helpers_cover_edge_cases(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.yaml"
    write_yaml(invalid, {"analysis_id": "x", "stage": "bad", "bootstrap": {}, "decision": {}})
    with pytest.raises(ValueError, match="stage"):
        _contract(invalid)
    write_yaml(invalid, {"analysis_id": "x", "stage": "pilot", "bootstrap": [], "decision": {}})
    with pytest.raises(ValueError, match="mappings"):
        _contract(invalid)
    write_yaml(invalid, {"runs": []})
    with pytest.raises(ValueError, match="enumerate"):
        _registry(invalid, {})
    write_yaml(invalid, [{"run_id": "one"}])
    assert _registry(invalid, {})[1] == [{"run_id": "one"}]

    assert _artifact_details(tmp_path, None, "agent")[1]["status"] == "missing"
    assert _artifact_details(tmp_path, {"relative_path": "nope"}, "agent")[1]["status"] == "invalid"
    assert (
        _taxonomy({"infrastructure_failure": {"category": "docker_failure"}})[1]
        == "docker_or_container"
    )
    assert (
        _taxonomy({"infrastructure_failure": {"category": "worker_failure"}})[1]
        == "worker_or_harness"
    )
    assert (
        _taxonomy({"infrastructure_failure": {"category": "telemetry_failure"}})[1]
        == "artifact_or_telemetry"
    )
    assert (
        _taxonomy({"infrastructure_failure": {"category": "memory_protocol"}})[1]
        == "memory_protocol"
    )
    assert _taxonomy({"contamination": True})[0] == "contamination"
    assert _taxonomy({"failure_signature": "dependency build error"})[1] == "dependency_or_build"
    assert _taxonomy({"failure_signature": "wrong output"})[1] == "wrong_state_or_output"
    assert _taxonomy({"failure_signature": "retrieval absent"})[1] == "retrieval_omission"
    assert _taxonomy({"failure_signature": "unrecognised"})[1] == "unknown_unclassified"

    detailed = {
        "foreground_input_tokens": 5,
        "foreground_output_tokens": 3,
        "background_tokens": 4,
        "maintenance_input_tokens": 2,
        "maintenance_output_tokens": 2,
    }
    assert _total_tokens(detailed) == 12
    assert (
        _token_status({"foreground_input_tokens": 1, "foreground_output_tokens": 1})
        == "lower_bound"
    )
    assert _token_status(detailed) == "complete"
    assert _mde([])["mde_95_percent_pp"] is None
    assert _mde([{"c0_success": 1, "c2_success": 1}])["mde_95_percent_pp"] is None

    pair = {
        "c0_success": 1,
        "c2_success": 1,
        "c0_repeated_failure": 1,
        "c2_repeated_failure": 0,
    }
    ok = {
        "missing_token_replicate_fraction": 0,
        "success_pp_ci": [0, 1],
        "token_reduction_ci": [10, 20],
        "repeated_failure_pp_ci": [-100, -1],
    }
    assert _decision("main-lite", [], [], [], ok, 10) == "blocked_missing_data"
    assert _decision("pilot", [{}], [], [pair], ok, 10) == "redesign"
    assert _decision("main-lite", [{}], ["bad"], [pair], ok, 10) == "redesign"
    assert _decision("main-lite", [{}], [], [pair], ok, 10) == "go"
    assert _decision("main-lite", [{}], [], [pair], {**ok, "success_pp_ci": [-3, 1]}, 10) == "stop"
    assert (
        _decision(
            "main-lite", [{}], [], [pair], {**ok, "missing_token_replicate_fraction": 0.1}, 10
        )
        == "redesign"
    )
    assert (
        _decision(
            "main-lite",
            [{}],
            [],
            [{**pair, "c0_repeated_failure": 0}],
            {**ok, "token_reduction_ci": [1, 2], "repeated_failure_pp_ci": [0, 0]},
            10,
        )
        == "redesign"
    )

    errors: list[str] = []
    deviations: list[dict[str, object]] = []
    artifacts: list[dict[str, object]] = []
    _validate_row(
        {
            "attempt_id": "bad",
            "attempt_status": "infrastructure_failure",
            "success": True,
            "foreground_input_tokens": -1,
            "foreground_output_tokens": 1,
            "wall_seconds": -1,
            "stop_reason": "budget",
            "verifier": {"raw_stdout_path": {"relative_path": "missing"}},
            "artifacts": {"agent": {"relative_path": "missing"}},
        },
        {"schema_version": 2, "frozen_inputs": {"manifest_hash": "expected"}},
        "run",
        errors,
        deviations,
        artifacts,
        tmp_path,
    )
    assert any("mismatch" in error for error in errors)
    assert any("infrastructure failure" in error for error in errors)

    contract = tmp_path / "duplicate.yaml"
    write_yaml(
        contract,
        {
            "analysis_id": "x",
            "stage": "main-lite",
            "runs": [{}, {"run_id": "missing"}, {"run_id": "missing"}],
            "bootstrap": {"seed": 1, "replicates": 2},
            "decision": {},
        },
    )
    report = analyze(tmp_path, contract, tmp_path / "duplicate-out") / "validation_report.json"
    assert "duplicate preregistered run" in report.read_text(encoding="utf-8")
    assert validate_analysis(tmp_path, contract, contract, tmp_path / "validate-out").is_dir()
