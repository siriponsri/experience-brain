from __future__ import annotations

# ruff: noqa: E501
import os
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from experience_brain.benchmark import core
from experience_brain.benchmark.core import (
    build_cost_estimate,
    check_completeness,
    preflight,
    reset_run,
    run_stage,
)
from experience_brain.cli import app
from experience_brain.util import canonical_json, sha256_text, write_yaml


@pytest.fixture(autouse=True)
def _external_benchmark_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home = tmp_path.parent / f"benchmark-home-{tmp_path.name}"
    home.mkdir()
    monkeypatch.setenv("BENCHMARK_HOME", str(home))


def _commit_checkout(
    path: Path,
    agent_code: str = "import json\nprint(json.dumps({'input_tokens': 10, 'output_tokens': 5}))\n",
) -> str:
    path.mkdir(parents=True, exist_ok=True)
    (path / "agent.py").write_text(
        agent_code,
        encoding="utf-8",
    )
    (path / "verifier.py").write_text(
        "import json\nprint(json.dumps({'success': True, 'score': 1.0, 'failure_signature': None}))\n",
        encoding="utf-8",
    )
    for command in (
        ["git", "init"],
        ["git", "add", "."],
        [
            "git",
            "-c",
            "user.name=Benchmark Test",
            "-c",
            "user.email=benchmark@example.invalid",
            "commit",
            "-m",
            "fixture",
        ],
    ):
        subprocess.run(command, cwd=path, check=True, capture_output=True, text=True)
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _manifest(path: Path, name: str, tasks: list[dict[str, object]]) -> Path:
    data: dict[str, object] = {"schema_version": 1, "name": name, "tasks": tasks}
    data["manifest_hash"] = sha256_text(canonical_json(data))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(data) + "\n", encoding="utf-8")
    return path


def _task(identifier: str, benchmark: str) -> dict[str, object]:
    task: dict[str, object] = {
        "task_id": identifier,
        "benchmark": benchmark,
        "split": "deployment",
        "task_contract": {"id": identifier, "goal": f"Run {identifier}", "constraints": []},
    }
    task["selector"] = (
        {"family_id": identifier, "roles": ["T1", "T2", "T3", "T4", "T5", "T6"]}
        if benchmark == "skillevolbench"
        else {"task_id": identifier}
    )
    return task


def _fixture_config(root: Path) -> tuple[Path, Path]:
    prompts = root / "prompts"
    prompts.mkdir()
    (prompts / "prompt-01.md").write_text("frozen prompt 1\n", encoding="utf-8")
    (prompts / "prompt-02.md").write_text("frozen prompt 2\n", encoding="utf-8")
    home = Path(os.environ["BENCHMARK_HOME"])
    skill_commit = _commit_checkout(home / "sources" / "skillevolbench")
    terminal_commit = _commit_checkout(home / "sources" / "terminal-bench")
    agent_command = [sys.executable, "{checkout}/agent.py"]
    verifier_command = [sys.executable, "{checkout}/verifier.py"]
    lock_path = root / "evaluations" / "benchmark-lock.yaml"
    write_yaml(
        lock_path,
        {
            "benchmarks": {
                "skillevolbench": {
                    "source_kind": "git_repository",
                    "source_url": "https://official.example/skillevolbench",
                    "source_path": "sources/skillevolbench",
                    "source_tree_hash": "fixture-skill",
                    "commit_sha": skill_commit,
                    "worker_python": sys.executable,
                    "container_digest": "sha256:fixture",
                    "requires_docker": False,
                    "adapter_mode": "fixture",
                    "agent_command": agent_command,
                    "verifier_command": verifier_command,
                },
                "terminal_bench": {
                    "source_kind": "huggingface_dataset",
                    "source_url": "https://official.example/terminal-bench",
                    "source_path": "sources/terminal-bench",
                    "source_tree_hash": "fixture-terminal",
                    "revision": terminal_commit,
                    "worker_python": sys.executable,
                    "container_digest": "sha256:fixture",
                    "requires_docker": False,
                    "adapter_mode": "fixture",
                    "agent_command": agent_command,
                    "verifier_command": verifier_command,
                },
            }
        },
    )
    runtime_path = root / "evaluations" / "runtime.yaml"
    write_yaml(
        runtime_path,
        {
            "model": "test-runtime",
            "reasoning": "high",
            "tools": ["shell"],
            "task_data_hash": "fixture-task-data",
            "context_budget_tokens": 1000,
            "rate_card": {
                "currency": "USD",
                "input_per_million": 1.0,
                "output_per_million": 2.0,
                "thb_per_currency": 35.0,
            },
        },
    )
    return lock_path, runtime_path


def test_smoke_harness_writes_verifier_outcomes_and_estimate(tmp_path: Path) -> None:
    lock_path, runtime_path = _fixture_config(tmp_path)
    smoke_manifest = _manifest(
        tmp_path / "evaluations" / "manifests" / "smoke-v1.json",
        "smoke-v1",
        [_task("skill-smoke", "skillevolbench"), _task("terminal-smoke", "terminal_bench")],
    )
    assert preflight(tmp_path, smoke_manifest, lock_path, runtime_path) == []
    outcomes = run_stage(tmp_path, smoke_manifest, lock_path, runtime_path, "smoke-local", "smoke")
    assert len(outcomes) == 6
    assert {item["condition"] for item in outcomes} == {"c0", "c1", "c2"}
    assert all(item["success"] is True for item in outcomes)
    assert all(item["attempt_status"] == "completed" for item in outcomes)
    assert check_completeness(tmp_path, "smoke-local", 6) == []

    pilot_manifest = _manifest(
        tmp_path / "evaluations" / "manifests" / "pilot-v1.json",
        "pilot-v1",
        [
            _task("skill-short", "skillevolbench"),
            _task("skill-medium", "skillevolbench"),
            _task("skill-long", "skillevolbench"),
            _task("terminal-short", "terminal_bench"),
            _task("terminal-medium", "terminal_bench"),
            _task("terminal-long", "terminal_bench"),
        ],
    )
    estimate = build_cost_estimate(
        tmp_path,
        "smoke-local",
        pilot_manifest,
        runtime_path,
        tmp_path / "evaluations" / "COST_ESTIMATE.md",
    )
    text = estimate.read_text(encoding="utf-8")
    assert "Status: UNAPPROVED" in text
    assert "Hard worst case" in text

    sentinel = tmp_path / "memory" / "outside-workspace.txt"
    sentinel.parent.mkdir(exist_ok=True)
    sentinel.write_text("preserve", encoding="utf-8")
    assert reset_run(tmp_path, "smoke-local") is True
    assert not (tmp_path / "evaluations" / "runs" / "smoke-local").exists()
    assert sentinel.read_text(encoding="utf-8") == "preserve"


def test_typed_specialized_smoke_expands_and_excludes_solution(tmp_path: Path) -> None:
    lock_path, runtime_path = _fixture_config(tmp_path)
    tasks: list[dict[str, object]] = []
    for identifier, benchmark in (("family", "skillevolbench"), ("terminal", "terminal_bench")):
        task = _task(identifier, benchmark)
        task.pop("task_contract")
        task["task_tree_hash"] = f"hash-{identifier}"
        tasks.append(task)
    manifest = _manifest(tmp_path / "evaluations" / "manifests" / "smoke-v2.json", "smoke-v2", tasks)
    data = __import__("json").loads(manifest.read_text(encoding="utf-8"))
    data["schema_version"] = 2
    data["manifest_hash"] = sha256_text(canonical_json({k: v for k, v in data.items() if k != "manifest_hash"}))
    manifest.write_text(canonical_json(data) + "\n", encoding="utf-8")
    assert core.prepare(tmp_path).is_dir()
    assert preflight(tmp_path, manifest, lock_path, runtime_path) == []
    outcomes = run_stage(tmp_path, manifest, lock_path, runtime_path, "typed", "smoke")
    assert len(outcomes) == 21
    deployment = [item for item in outcomes if item["selector"].get("role") in {"T4", "T5", "T6"}]
    assert deployment and all(item["memory_before_hash"] for item in deployment)
    assert check_completeness(tmp_path, "typed") == []


def test_native_adapter_contracts_are_command_only(tmp_path: Path) -> None:
    from experience_brain.benchmark.adapters import adapter_for

    source = tmp_path / "source"
    source.mkdir()
    values = {"workspace": "W", "context": "C", "runtime": "R"}
    skill = {"selector": {"family_id": "f", "roles": ["T1", "T2", "T3", "T4", "T5", "T6"], "role": "T1"}}
    skill_lock = {"source_kind": "git_repository", "worker_python": "py312"}
    adapter_for("skillevolbench").validate(skill, skill_lock)
    assert "scripts.run" in adapter_for("skillevolbench").invocation(skill, skill_lock, values, source).command
    terminal = {"selector": {"task_id": "t"}}
    terminal_lock = {"source_kind": "huggingface_dataset", "worker_python": "py312"}
    adapter_for("terminal_bench").validate(terminal, terminal_lock)
    assert "--include-task-name" in adapter_for("terminal_bench").invocation(terminal, terminal_lock, values, source).command


def test_specialized_adapter_and_external_cache_guards(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from experience_brain.benchmark.adapters import adapter_for

    monkeypatch.delenv("BENCHMARK_HOME")
    with pytest.raises(ValueError, match="BENCHMARK_HOME"):
        core.benchmark_home(tmp_path)
    monkeypatch.setenv("BENCHMARK_HOME", str(tmp_path))
    with pytest.raises(ValueError, match="outside"):
        core.benchmark_home(tmp_path)
    with pytest.raises(ValueError, match="unsupported"):
        adapter_for("other")
    with pytest.raises(ValueError, match="family selector"):
        adapter_for("skillevolbench").validate({}, {"source_kind": "git_repository"})
    with pytest.raises(ValueError, match="T1 through T6"):
        adapter_for("skillevolbench").validate(
            {"selector": {"family_id": "f", "roles": []}}, {"source_kind": "git_repository"}
        )
    with pytest.raises(ValueError, match="git_repository"):
        adapter_for("skillevolbench").validate(
            {"selector": {"family_id": "f", "roles": ["T1", "T2", "T3", "T4", "T5", "T6"]}},
            {"source_kind": "wrong"},
        )
    with pytest.raises(ValueError, match="exact task"):
        adapter_for("terminal_bench").validate({}, {"source_kind": "huggingface_dataset"})
    with pytest.raises(ValueError, match="huggingface_dataset"):
        adapter_for("terminal_bench").validate(
            {"selector": {"task_id": "t"}}, {"source_kind": "wrong"}
        )


def test_lock_snapshot_digest_and_docker_guards(tmp_path: Path) -> None:
    lock_path, _ = _fixture_config(tmp_path)
    lock = core._load_lock(lock_path)
    entry = lock["benchmarks"]["skillevolbench"]
    entry.pop("adapter_mode")
    entry["commit_sha"] = "not-the-actual-commit"
    entry["container_digest"] = None
    entry["requires_docker"] = True
    errors = core._required_lock_errors(tmp_path, lock, "skillevolbench")
    assert any("does not match" in error for error in errors)
    assert any("container_digest" in error for error in errors)
    assert any("Docker Engine" in error for error in errors)


def test_completeness_rejects_duplicate_unscored_and_solution_records(tmp_path: Path) -> None:
    directory = tmp_path / "evaluations" / "runs" / "bad"
    directory.mkdir(parents=True)
    bad = {
        "attempt_id": "same",
        "attempt_status": "infrastructure_failure",
        "success": True,
        "verifier": {},
        "solution": "forbidden",
    }
    (directory / "outcomes.jsonl").write_text(
        canonical_json(bad) + "\n" + canonical_json(bad) + "\n", encoding="utf-8"
    )
    errors = check_completeness(tmp_path, "bad")
    assert any("duplicate" in error for error in errors)
    assert any("protocol fields" in error for error in errors)
    assert any("must not have" in error for error in errors)
    assert any("solution" in error for error in errors)


def test_preflight_fails_closed_without_frozen_prompts(tmp_path: Path) -> None:
    lock_path, runtime_path = _fixture_config(tmp_path)
    (tmp_path / "prompts" / "prompt-02.md").unlink()
    manifest = _manifest(
        tmp_path / "evaluations" / "manifests" / "smoke-v1.json",
        "smoke-v1",
        [_task("skill-smoke", "skillevolbench"), _task("terminal-smoke", "terminal_bench")],
    )
    errors = preflight(tmp_path, manifest, lock_path, runtime_path)
    assert any("C1 requires" in error for error in errors)
    with pytest.raises(ValueError, match="preflight failed"):
        run_stage(tmp_path, manifest, lock_path, runtime_path, "blocked", "smoke")


def test_harness_schema_and_protocol_guards(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(ValueError, match="missing JSON"):
        core._json(missing)
    invalid = tmp_path / "invalid.json"
    invalid.write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        core._json(invalid)
    invalid.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain an object"):
        core._json(invalid)

    bad_manifest = tmp_path / "bad.json"
    bad_manifest.write_text('{"manifest_hash":"wrong","tasks":[]}', encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        core.load_manifest(bad_manifest)
    _manifest(bad_manifest, "bad", [])
    with pytest.raises(ValueError, match="tasks"):
        core.load_manifest(bad_manifest)
    bad_task_sets: list[list[object]] = [
        ["bad"],
        [{"task_id": "x", "benchmark": "unknown", "task_contract": {"goal": "x"}}],
        [{"task_id": "x", "benchmark": "skillevolbench", "task_contract": {}}],
        [
            {"task_id": "x", "benchmark": "skillevolbench", "task_contract": {"goal": "x"}},
            {"task_id": "x", "benchmark": "skillevolbench", "task_contract": {"goal": "x"}},
        ],
    ]
    for tasks in bad_task_sets:
        payload: dict[str, object] = {"schema_version": 1, "name": "bad", "tasks": tasks}
        payload["manifest_hash"] = sha256_text(canonical_json(payload))
        bad_manifest.write_text(canonical_json(payload) + "\n", encoding="utf-8")
        with pytest.raises(ValueError):
            core.load_manifest(bad_manifest)

    runtime = tmp_path / "runtime.yaml"
    write_yaml(runtime, {"model": "only"})
    with pytest.raises(ValueError, match="missing"):
        core.load_runtime(runtime)
    write_yaml(
        runtime,
        {
            "model": "m",
            "reasoning": "r",
            "tools": "bad",
            "task_data_hash": "x",
            "rate_card": {"x": 1},
        },
    )
    with pytest.raises(ValueError, match="tools"):
        core.load_runtime(runtime)
    with pytest.raises(ValueError, match="benchmarks"):
        core._load_lock(tmp_path / "missing-lock.yaml")
    with pytest.raises(ValueError, match="budget"):
        core._budget({"benchmark": "skillevolbench", "budget": []})
    with pytest.raises(ValueError, match="non-negative"):
        core._budget({"benchmark": "skillevolbench", "budget": {"foreground_tokens": -1}})
    with pytest.raises(ValueError, match="non-empty"):
        core._render_command([], {})
    with pytest.raises(ValueError, match="JSON object"):
        core._agent_result("not json")
    with pytest.raises(ValueError, match="input_tokens"):
        core._agent_result('{"input_tokens": -1, "output_tokens": 0}')
    with pytest.raises(ValueError, match="verifier"):
        core._verifier_result('{"success": true}')

    timeout_code, _, _, timed_out, _ = core._run_command(
        [sys.executable, "-c", "import time; time.sleep(2)"], tmp_path, 1
    )
    assert timeout_code is None
    assert timed_out is True


def test_benchmark_cli_exercises_local_smoke_lifecycle(tmp_path: Path) -> None:
    lock_path, runtime_path = _fixture_config(tmp_path)
    smoke = _manifest(
        tmp_path / "evaluations" / "manifests" / "smoke-v1.json",
        "smoke-v1",
        [_task("skill-smoke", "skillevolbench"), _task("terminal-smoke", "terminal_bench")],
    )
    pilot = _manifest(
        tmp_path / "evaluations" / "manifests" / "pilot-v1.json",
        "pilot-v1",
        [
            _task("skill-short", "skillevolbench"),
            _task("skill-medium", "skillevolbench"),
            _task("skill-long", "skillevolbench"),
            _task("terminal-short", "terminal_bench"),
            _task("terminal-medium", "terminal_bench"),
            _task("terminal-long", "terminal_bench"),
        ],
    )
    runner = CliRunner()
    common = ["--root", str(tmp_path)]
    result = runner.invoke(
        app,
        [
            "benchmark",
            "preflight",
            "--manifest",
            str(smoke),
            "--lock",
            str(lock_path),
            "--runtime",
            str(runtime_path),
            *common,
        ],
    )
    assert result.exit_code == 0, result.output
    result = runner.invoke(
        app,
        [
            "benchmark",
            "smoke",
            "--manifest",
            str(smoke),
            "--run-id",
            "cli-smoke",
            "--lock",
            str(lock_path),
            "--runtime",
            str(runtime_path),
            *common,
        ],
    )
    assert result.exit_code == 0, result.output
    result = runner.invoke(
        app,
        ["benchmark", "completeness", "--run-id", "cli-smoke", "--expected-attempts", "6", *common],
    )
    assert result.exit_code == 0, result.output
    result = runner.invoke(
        app,
        [
            "benchmark",
            "estimate",
            "--smoke-run-id",
            "cli-smoke",
            "--pilot-manifest",
            str(pilot),
            "--runtime",
            str(runtime_path),
            *common,
        ],
    )
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["benchmark", "reset", "--run-id", "cli-smoke", *common])
    assert result.exit_code == 0, result.output


def test_infrastructure_retry_and_pilot_gates(tmp_path: Path) -> None:
    lock_path, runtime_path = _fixture_config(tmp_path)
    checkout = Path(os.environ["BENCHMARK_HOME"]) / "sources" / "skillevolbench"
    commit = _commit_checkout(checkout, "raise SystemExit(2)\n")
    lock = core._load_lock(lock_path)
    lock["benchmarks"]["skillevolbench"]["commit_sha"] = commit
    write_yaml(lock_path, lock)
    manifest = _manifest(
        tmp_path / "evaluations" / "manifests" / "smoke-v1.json",
        "smoke-v1",
        [_task("skill-smoke", "skillevolbench"), _task("terminal-smoke", "terminal_bench")],
    )
    outcomes = run_stage(tmp_path, manifest, lock_path, runtime_path, "infra-local", "smoke")
    assert len(outcomes) == 9
    skill_outcomes = [item for item in outcomes if item["benchmark"] == "skillevolbench"]
    assert all(item["attempt_status"] == "infrastructure_failure" for item in skill_outcomes)
    assert all(item["success"] is None for item in skill_outcomes)
    assert any(item["retry_of"] for item in skill_outcomes)
    assert check_completeness(tmp_path, "infra-local", 9) == []

    pilot = _manifest(
        tmp_path / "evaluations" / "manifests" / "pilot-v1.json",
        "pilot-v1",
        [
            _task("skill-short", "skillevolbench"),
            _task("skill-medium", "skillevolbench"),
            _task("skill-long", "skillevolbench"),
            _task("terminal-short", "terminal_bench"),
            _task("terminal-medium", "terminal_bench"),
            _task("terminal-long", "terminal_bench"),
        ],
    )
    estimate = tmp_path / "evaluations" / "COST_ESTIMATE.md"
    build_cost_estimate(tmp_path, "infra-local", pilot, runtime_path, estimate)
    runtime_hash = core.load_runtime(runtime_path).hash
    _, manifest_hash = core.load_manifest(pilot)
    approval = tmp_path / "evaluations" / "approvals" / "pilot-cost-v1.yaml"
    write_yaml(
        approval,
        {
            "approved": True,
            "estimate_hash": sha256_text(estimate.read_text(encoding="utf-8")),
            "manifest_hash": manifest_hash,
            "runtime_hash": runtime_hash,
        },
    )
    with pytest.raises(ValueError, match="protocol gate failed"):
        run_stage(
            tmp_path,
            pilot,
            lock_path,
            runtime_path,
            "pilot-blocked",
            "pilot",
            approval,
            estimate,
        )
    with pytest.raises(ValueError, match="stage"):
        run_stage(tmp_path, manifest, lock_path, runtime_path, "bad-stage", "invalid")


def test_memory_protocol_and_completeness_corruption(tmp_path: Path) -> None:
    lock_path, runtime_path = _fixture_config(tmp_path)
    runtime = core.load_runtime(runtime_path)
    workspace = tmp_path / "workspace"
    brain_root, _ = core._prepare_brain(tmp_path, workspace, "c0", "run", runtime)
    with pytest.raises(ValueError, match="C0"):
        core._post_memory(
            "c0", brain_root, {"input_tokens": 0, "output_tokens": 0, "memory": {"x": 1}}
        )

    c1_workspace = tmp_path / "workspace-c1"
    c1_brain, _ = core._prepare_brain(tmp_path, c1_workspace, "c1", "run", runtime)
    with pytest.raises(ValueError, match="C1 memory"):
        core._post_memory(
            "c1",
            c1_brain,
            {"input_tokens": 0, "output_tokens": 0, "memory": {"source_path": "missing"}},
        )

    manifest = _manifest(
        tmp_path / "evaluations" / "manifests" / "smoke-v1.json",
        "smoke-v1",
        [_task("skill-smoke", "skillevolbench"), _task("terminal-smoke", "terminal_bench")],
    )
    run_stage(tmp_path, manifest, lock_path, runtime_path, "complete-local", "smoke")
    path = tmp_path / "evaluations" / "runs" / "complete-local" / "outcomes.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    corrupted = __import__("json").loads(lines[0])
    corrupted["attempt_status"] = "unknown"
    corrupted["verifier"]["raw_stdout_path"] = "missing"
    lines[0] = canonical_json(corrupted)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    errors = check_completeness(tmp_path, "complete-local", 7)
    assert any("expected" in error for error in errors)
    assert any("terminal status" in error for error in errors)
    assert any("missing verifier artifact" in error for error in errors)


def test_lock_agent_verifier_memory_and_outcome_guards(tmp_path: Path) -> None:
    lock_path, runtime_path = _fixture_config(tmp_path)
    runtime = core.load_runtime(runtime_path)
    lock = core._load_lock(lock_path)
    with pytest.raises(ValueError, match="no entry"):
        core._lock_entry(lock, "missing")
    broken = {"benchmarks": {"skillevolbench": {"checkout": ".benchmarks/missing"}}}
    lock_errors = core._required_lock_errors(tmp_path, broken, "skillevolbench")
    assert any("missing source_url" in error for error in lock_errors)
    assert any("source_path" in error for error in lock_errors)
    assert (
        any(
            "pinned commit" in error
            for error in core._required_lock_errors(tmp_path, lock, "skillevolbench")
        )
        is False
    )

    with pytest.raises(ValueError, match="JSON object"):
        core._agent_result("[]")
    with pytest.raises(ValueError, match="JSON object"):
        core._verifier_result("not-json")
    with pytest.raises(ValueError, match="boolean success"):
        core._verifier_result('{"success": "yes", "score": 1}')

    brain_root, _ = core._prepare_brain(tmp_path, tmp_path / "c2", "c2", "run", runtime)
    assert (
        core._post_memory("c2", brain_root, {"input_tokens": 0, "output_tokens": 0, "memory": None})
        == 0
    )
    with pytest.raises(ValueError, match="mapping"):
        core._post_memory("c2", brain_root, {"input_tokens": 0, "output_tokens": 0, "memory": []})
    with pytest.raises(ValueError, match="non-negative"):
        core._post_memory(
            "c2", brain_root, {"input_tokens": 0, "output_tokens": 0, "background_input_tokens": -1}
        )
    event = {
        "id": "evt",
        "timestamp": "2026-07-16T00:00:00Z",
        "run_id": "run",
        "task_id": "task",
        "type": "action",
        "actor": "agent",
        "content": "event",
        "trust": "first_party_execution",
        "cost": {},
    }
    (brain_root / "events.jsonl").write_text(canonical_json(event) + "\n", encoding="utf-8")
    assert (
        core._post_memory(
            "c2",
            brain_root,
            {"input_tokens": 0, "output_tokens": 0, "memory": {"events_jsonl": "events.jsonl"}},
        )
        == 0
    )

    outcome = {"attempt_id": "immutable"}
    core._write_outcome(tmp_path, "outcomes", outcome)
    with pytest.raises(ValueError, match="immutable"):
        core._write_outcome(tmp_path, "outcomes", {"attempt_id": "immutable", "changed": True})
