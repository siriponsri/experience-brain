from __future__ import annotations

# ruff: noqa: E501
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..capsule import build_capsule
from ..config import load_settings
from ..consolidation import consolidate
from ..event_store import ingest_events
from ..util import canonical_json, read_yaml, sha256_text, write_yaml
from ..wiki import build_wiki_context, ingest_wiki_source, maintain_wiki, wiki_metrics
from .adapters import adapter_for

CONDITIONS = ("c0", "c1", "c2")
BENCHMARKS = ("skillevolbench", "terminal_bench")
OUTCOME_FIELDS = {
    "run_id",
    "condition",
    "task_id",
    "split",
    "model",
    "reasoning",
    "commit_sha",
    "harness_version",
    "success",
    "verifier_score",
    "foreground_input_tokens",
    "foreground_output_tokens",
    "background_tokens",
    "wall_seconds",
    "skills_retrieved",
    "skills_applied",
    "failure_signature",
}


@dataclass(frozen=True)
class Budget:
    foreground_tokens: int
    foreground_seconds: int
    background_tokens: int
    background_seconds: int


@dataclass(frozen=True)
class Runtime:
    model: str
    reasoning: str
    tools: tuple[str, ...]
    task_data_hash: str
    rate_card: dict[str, Any]
    context_budget_tokens: int
    hash: str


def _evaluations(root: Path) -> Path:
    return root / "evaluations"


def benchmark_home(root: Path) -> Path:
    """Return the mandatory, non-repository benchmark cache root.

    Sources, Docker state, worker environments and raw artifacts are never
    placed in the Git worktree, where a benchmark's private tests or solution
    might otherwise be accidentally committed.
    """
    configured = os.environ.get("BENCHMARK_HOME")
    if not configured:
        raise ValueError("BENCHMARK_HOME must be set to an external directory")
    home = Path(configured).expanduser().resolve()
    repository = root.resolve()
    if home == repository or repository in home.parents:
        raise ValueError("BENCHMARK_HOME must be outside the repository")
    return home


def _json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"missing JSON file: {path}")
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON file: {path}") from error
    if not isinstance(loaded, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return loaded


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(value) + "\n", encoding="utf-8")


def _artifact_reference(root: Path, path: Path) -> dict[str, Any]:
    home = benchmark_home(root)
    resolved = path.resolve()
    if not resolved.is_relative_to(home):
        raise ValueError("raw benchmark artifact must be inside BENCHMARK_HOME")
    return {
        "relative_path": resolved.relative_to(home).as_posix(),
        "sha256": sha256_text(resolved.read_text(encoding="utf-8")),
        "size": resolved.stat().st_size,
    }


def _artifact_exists(root: Path, reference: object) -> bool:
    if not isinstance(reference, dict):
        return False
    relative = reference.get("relative_path")
    if not isinstance(relative, str):
        return False
    home = benchmark_home(root)
    candidate = (home / relative).resolve()
    return (
        candidate.is_file()
        and candidate.is_relative_to(home)
        and reference.get("sha256") == sha256_text(candidate.read_text(encoding="utf-8"))
        and reference.get("size") == candidate.stat().st_size
    )


def _store_hash(path: Path) -> str:
    if not path.exists():
        return sha256_text("")
    entries: list[dict[str, str]] = []
    for candidate in sorted(path.rglob("*")):
        if candidate.is_file() and "solution" not in candidate.parts:
            entries.append({
                "path": candidate.relative_to(path).as_posix(),
                "sha256": sha256_text(candidate.read_text(encoding="utf-8", errors="replace")),
            })
    return sha256_text(canonical_json(entries))


def _manifest_hash(data: dict[str, Any]) -> str:
    return sha256_text(
        canonical_json({key: value for key, value in data.items() if key != "manifest_hash"})
    )


def load_manifest(path: Path) -> tuple[dict[str, Any], str]:
    manifest = _json(path)
    expected = _manifest_hash(manifest)
    if manifest.get("manifest_hash") != expected:
        raise ValueError("task manifest hash does not match canonical content")
    tasks = manifest.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("task manifest must contain tasks")
    identifiers: set[str] = set()
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("task manifest contains a non-object task")
        identifier = str(task.get("task_id", ""))
        benchmark = str(task.get("benchmark", ""))
        if not identifier or benchmark not in BENCHMARKS:
            raise ValueError("each task needs a task_id and supported benchmark")
        if identifier in identifiers:
            raise ValueError(f"duplicate task_id in manifest: {identifier}")
        identifiers.add(identifier)
        selector = task.get("selector")
        # schema v2 is intentionally selector-only: it records identifiers and
        # hashes but never benchmark prompts, tests or solution material.
        if int(manifest.get("schema_version", 1)) >= 2:
            if not isinstance(selector, dict):
                raise ValueError(f"task {identifier} needs a typed selector")
            if not isinstance(task.get("task_tree_hash"), str):
                raise ValueError(f"task {identifier} needs a task_tree_hash")
            if benchmark == "skillevolbench":
                roles = selector.get("roles")
                if not isinstance(selector.get("family_id"), str) or roles != ["T1", "T2", "T3", "T4", "T5", "T6"]:
                    raise ValueError(f"task {identifier} needs a complete SkillEvol T1-T6 selector")
            elif not isinstance(selector.get("task_id"), str):
                raise ValueError(f"task {identifier} needs a Terminal-Bench task selector")
        else:
            contract = task.get("task_contract")
            if not isinstance(contract, dict) or not str(contract.get("goal", "")):
                raise ValueError(f"task {identifier} needs a task_contract goal")
    return manifest, expected


def load_runtime(path: Path) -> Runtime:
    data = read_yaml(path, {})
    if not isinstance(data, dict):
        raise ValueError("runtime config must be a YAML mapping")
    required = ("model", "reasoning", "tools", "task_data_hash", "rate_card")
    missing = [key for key in required if not data.get(key)]
    if missing:
        raise ValueError(f"runtime config missing: {missing}")
    if not isinstance(data["tools"], list) or not isinstance(data["rate_card"], dict):
        raise ValueError("runtime tools must be a list and rate_card must be a mapping")
    return Runtime(
        model=str(data["model"]),
        reasoning=str(data["reasoning"]),
        tools=tuple(str(value) for value in data["tools"]),
        task_data_hash=str(data["task_data_hash"]),
        rate_card=dict(data["rate_card"]),
        context_budget_tokens=int(data.get("context_budget_tokens", 2000)),
        hash=sha256_text(canonical_json(data)),
    )


def _load_lock(path: Path) -> dict[str, Any]:
    lock = read_yaml(path, {})
    if not isinstance(lock, dict) or not isinstance(lock.get("benchmarks"), dict):
        raise ValueError("benchmark lock must contain a benchmarks mapping")
    return lock


def _budget(task: dict[str, Any]) -> Budget:
    defaults = {
        "skillevolbench": Budget(12000, 15 * 60, 3000, 5 * 60),
        "terminal_bench": Budget(30000, 30 * 60, 7500, 5 * 60),
    }
    configured = task.get("budget", {})
    if not isinstance(configured, dict):
        raise ValueError("task budget must be a mapping")
    base = defaults[str(task["benchmark"])]
    budget = Budget(
        foreground_tokens=int(configured.get("foreground_tokens", base.foreground_tokens)),
        foreground_seconds=int(configured.get("foreground_seconds", base.foreground_seconds)),
        background_tokens=int(configured.get("background_tokens", base.background_tokens)),
        background_seconds=int(configured.get("background_seconds", base.background_seconds)),
    )
    if (
        min(
            budget.foreground_tokens,
            budget.foreground_seconds,
            budget.background_tokens,
            budget.background_seconds,
        )
        < 0
    ):
        raise ValueError("task budget values must be non-negative")
    return budget


def _lock_entry(lock: dict[str, Any], benchmark: str) -> dict[str, Any]:
    entry = lock["benchmarks"].get(benchmark)
    if not isinstance(entry, dict):
        raise ValueError(f"benchmark lock has no entry for {benchmark}")
    return entry


def _source_path(root: Path, entry: dict[str, Any]) -> Path:
    home = benchmark_home(root)
    relative = entry.get("source_path")
    if not isinstance(relative, str) or not relative:
        raise ValueError("benchmark lock must define a cache-relative source_path")
    candidate = (home / relative).resolve()
    if not candidate.is_relative_to(home):
        raise ValueError("benchmark source_path must stay inside BENCHMARK_HOME")
    return candidate


def _required_lock_errors(root: Path, lock: dict[str, Any], benchmark: str) -> list[str]:
    entry = _lock_entry(lock, benchmark)
    errors: list[str] = []
    required = ("source_kind", "source_url", "source_path", "source_tree_hash", "worker_python")
    for key in required:
        if not entry.get(key):
            errors.append(f"{benchmark} lock is missing {key}")
    expected_kind = "git_repository" if benchmark == "skillevolbench" else "huggingface_dataset"
    if entry.get("source_kind") and entry.get("source_kind") != expected_kind:
        errors.append(f"{benchmark} has invalid source_kind")
    if benchmark == "skillevolbench" and not entry.get("commit_sha"):
        errors.append("skillevolbench lock is missing commit_sha")
    if benchmark == "terminal_bench" and not entry.get("revision"):
        errors.append("terminal_bench lock is missing revision")
    try:
        source = _source_path(root, entry)
    except ValueError as error:
        errors.append(str(error))
        return errors
    if not source.is_dir():
        errors.append(f"{benchmark} source snapshot is missing: {source}")
    if (
        source.is_dir()
        and entry.get("adapter_mode") != "fixture"
        and entry.get("source_kind") == "git_repository"
        and entry.get("commit_sha")
    ):
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=source,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0 or result.stdout.strip() != str(entry["commit_sha"]):
            errors.append(f"{benchmark} source snapshot does not match pinned commit")
    if entry.get("container_digest") in (None, "", "CONTAINER-DIGEST-REQUIRED"):
        errors.append(f"{benchmark} lock is missing container_digest")
    if entry.get("requires_docker", False):
        result = subprocess.run(
            ["docker", "info"], capture_output=True, text=True, check=False, timeout=15
        )
        if result.returncode != 0:
            errors.append(f"{benchmark} requires a running Docker Engine")
    return errors


def preflight(root: Path, manifest_path: Path, lock_path: Path, runtime_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        benchmark_home(root)
        manifest, _ = load_manifest(manifest_path)
        lock = _load_lock(lock_path)
        load_runtime(runtime_path)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        return [str(error)]
    used = {str(task["benchmark"]) for task in manifest["tasks"]}
    for benchmark in sorted(used):
        try:
            errors.extend(_required_lock_errors(root, lock, benchmark))
        except ValueError as error:
            errors.append(str(error))
    if int(manifest.get("schema_version", 1)) >= 2:
        for task in manifest["tasks"]:
            try:
                adapter_for(str(task["benchmark"])).validate(
                    task, _lock_entry(lock, str(task["benchmark"]))
                )
            except ValueError as error:
                errors.append(str(error))
    prompts = [root / "prompts" / "prompt-01.md", root / "prompts" / "prompt-02.md"]
    if any(not path.is_file() for path in prompts):
        errors.append("C1 requires prompts/prompt-01.md and prompts/prompt-02.md")
    return errors


def prepare(root: Path) -> Path:
    """Create the external cache skeleton without downloading benchmark data.

    Snapshot acquisition is intentionally an explicit operator step: the
    harness refuses to fetch unpinned content during preflight or execution.
    """
    home = benchmark_home(root)
    for relative in ("sources", "runs", "venvs", "docker"):
        (home / relative).mkdir(parents=True, exist_ok=True)
    return home


def _safe_id(value: str) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    if not value or any(character not in allowed for character in value):
        raise ValueError(
            "run, task, and attempt identifiers may contain only letters, digits, dot, underscore, and hyphen"
        )
    return value


def _workspace(root: Path, benchmark: str, run_id: str, condition: str, attempt_id: str) -> Path:
    home = benchmark_home(root)
    return home / "runs" / run_id / "workspaces" / benchmark / condition / attempt_id


def _copy_prompts(root: Path, brain_root: Path) -> None:
    for name in ("prompt-01.md", "prompt-02.md"):
        source = root / "prompts" / name
        destination = brain_root / "prompts" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _prepare_brain(
    root: Path,
    workspace: Path,
    condition: str,
    run_id: str,
    runtime: Runtime,
    store_key: str = "single",
) -> tuple[Path, Path | None]:
    # Persistent stores live outside the repository and do not cross a
    # condition or benchmark boundary. C0 intentionally receives no store.
    if condition == "c0":
        brain_root = workspace / "ephemeral"
    else:
        brain_root = benchmark_home(root) / "runs" / run_id / "stores" / store_key / condition
    directories = ("wiki",) if condition == "c1" else (
        "events",
        "memory/episodes",
        "memory/skills",
        "sources/converted",
        "capsules",
        "reports",
    )
    for relative in directories:
        (brain_root / relative).mkdir(parents=True, exist_ok=True)
    if condition == "c2" and not (brain_root / "memory" / "skills" / "index.yaml").exists():
        write_yaml(brain_root / "memory" / "skills" / "index.yaml", {"skills": {}})
        write_yaml(brain_root / "memory" / "review_queue.yaml", {"items": []})
        (brain_root / "events" / "events.jsonl").write_text("", encoding="utf-8")
    if condition == "c1":
        _copy_prompts(root, brain_root)
    config = {
        "condition": condition,
        "run_id": run_id,
        "tokenizer_encoding": "cl100k_base",
        "default_budget_tokens": runtime.context_budget_tokens,
        "fairness": {
            "model": runtime.model,
            "reasoning": runtime.reasoning,
            "tools": list(runtime.tools),
            "task_data": runtime.task_data_hash,
        },
        "wiki": {"prompt_references": ["prompts/prompt-01.md", "prompts/prompt-02.md"]},
        "verification": {"minimum_successful_episodes": 2, "minimum_verifier_score": 1.0},
    }
    config_path = brain_root / "brain.yaml"
    if not config_path.exists():
        write_yaml(config_path, config)
    return brain_root, None


def _render_command(command: object, values: dict[str, str]) -> list[str]:
    if (
        not isinstance(command, list)
        or not command
        or not all(isinstance(item, str) for item in command)
    ):
        raise ValueError("adapter commands must be non-empty string lists")
    return [str(item).format(**values) for item in command]


def _run_command(
    command: list[str], cwd: Path, timeout: int
) -> tuple[int | None, str, str, bool, float]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, check=False, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr, False, time.monotonic() - started
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout if isinstance(error.stdout, str) else ""
        stderr = error.stderr if isinstance(error.stderr, str) else ""
        return None, stdout, stderr, True, time.monotonic() - started


def _agent_result(stdout: str) -> dict[str, Any]:
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise ValueError("agent command stdout must be a JSON object") from error
    if not isinstance(parsed, dict):
        raise ValueError("agent command stdout must be a JSON object")
    for key in ("input_tokens", "output_tokens"):
        if not isinstance(parsed.get(key), int) or int(parsed[key]) < 0:
            raise ValueError(f"agent result needs non-negative integer {key}")
    return parsed


def _verifier_result(stdout: str) -> dict[str, Any]:
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise ValueError("verifier stdout must be a JSON object") from error
    if not isinstance(parsed, dict) or not isinstance(parsed.get("success"), bool):
        raise ValueError("verifier result needs boolean success")
    if not isinstance(parsed.get("score"), (int, float)):
        raise ValueError("verifier result needs numeric score")
    return parsed


def _outcome_path(root: Path, run_id: str, attempt_id: str) -> Path:
    return _evaluations(root) / "runs" / run_id / "attempts" / f"{attempt_id}.json"


def _write_outcome(root: Path, run_id: str, outcome: dict[str, Any]) -> Path:
    attempt_id = str(outcome["attempt_id"])
    path = _outcome_path(root, run_id, attempt_id)
    if path.exists() and _json(path) != outcome:
        raise ValueError(f"attempt outcome is immutable: {attempt_id}")
    _write_json(path, outcome)
    aggregate = _evaluations(root) / "runs" / run_id / "outcomes.jsonl"
    existing = []
    if aggregate.exists():
        existing = [
            json.loads(line) for line in aggregate.read_text(encoding="utf-8").splitlines() if line
        ]
    if not any(item.get("attempt_id") == attempt_id for item in existing):
        aggregate.parent.mkdir(parents=True, exist_ok=True)
        with aggregate.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical_json(outcome) + "\n")
    return path


def _post_memory(condition: str, brain_root: Path, result: dict[str, Any]) -> int:
    memory = result.get("memory", {})
    if memory is None:
        memory = {}
    if not isinstance(memory, dict):
        raise ValueError("agent memory result must be a mapping")
    background = int(result.get("background_input_tokens", 0)) + int(
        result.get("background_output_tokens", 0)
    )
    if background < 0:
        raise ValueError("background tokens must be non-negative")
    settings = load_settings(brain_root)
    if condition == "c0":
        if memory or background:
            raise ValueError("C0 cannot write persistent memory or background tokens")
        return 0
    if condition == "c2" and memory.get("events_jsonl"):
        path = brain_root / str(memory["events_jsonl"])
        ingest_events(brain_root, path)
        consolidate(settings)
    if condition == "c1" and memory:
        source = brain_root / str(memory.get("source_path", ""))
        metadata = brain_root / str(memory.get("source_metadata_path", ""))
        manifest = brain_root / str(memory.get("maintenance_manifest_path", ""))
        if not (source.is_file() and metadata.is_file() and manifest.is_file()):
            raise ValueError(
                "C1 memory requires source, metadata, and maintenance manifest artifacts"
            )
        ingest_wiki_source(settings, source, metadata)
        maintain_wiki(settings, manifest)
        background += int(wiki_metrics(settings)["maintenance_tokens"])
    return background


def _build_context(
    condition: str, brain_root: Path, task_path: Path, runtime: Runtime
) -> Path | None:
    if condition == "c0":
        return None
    settings = load_settings(brain_root)
    if condition == "c1":
        return build_wiki_context(settings, task_path, runtime.context_budget_tokens)
    return build_capsule(settings, task_path, runtime.context_budget_tokens)


def _run_attempt(
    root: Path,
    task: dict[str, Any],
    condition: str,
    run_id: str,
    attempt_id: str,
    manifest_hash: str,
    lock_hash: str,
    runtime: Runtime,
    lock_entry: dict[str, Any],
    store_key: str,
    maintenance_allowed: bool,
    retry_of: str | None = None,
) -> dict[str, Any]:
    budget = _budget(task)
    workspace = _workspace(root, str(task["benchmark"]), run_id, condition, attempt_id)
    if workspace.exists():
        raise ValueError(f"workspace already exists for immutable attempt {attempt_id}")
    workspace.mkdir(parents=True)
    brain_root, _ = _prepare_brain(root, workspace, condition, run_id, runtime, store_key)
    memory_before_hash = _store_hash(brain_root)
    task_contract = dict(task.get("task_contract", {}))
    if not task_contract:
        task_contract = {
            "id": str(task["task_id"]),
            "benchmark": str(task["benchmark"]),
            "selector": task["selector"],
            "task_tree_hash": task["task_tree_hash"],
        }
    task_contract.setdefault("id", str(task["task_id"]))
    task_path = workspace / "task.yaml"
    write_yaml(task_path, task_contract)
    context = _build_context(condition, brain_root, task_path, runtime)
    source = _source_path(root, lock_entry)
    values = {
        "checkout": str(source),
        "source": str(source),
        "workspace": str(workspace.resolve()),
        "task": str(task_path.resolve()),
        "context": str(context.resolve()) if context else "",
        "runtime": str(runtime_path := (workspace / "runtime.json").resolve()),
        "condition": condition,
        "foreground_tokens": str(budget.foreground_tokens),
        "foreground_seconds": str(budget.foreground_seconds),
    }
    _write_json(runtime_path, {
        "model": runtime.model, "reasoning": runtime.reasoning, "tools": list(runtime.tools),
        "foreground_tokens": budget.foreground_tokens, "foreground_seconds": budget.foreground_seconds,
    })
    artifacts = workspace / "artifacts"
    artifacts.mkdir()
    invocation = adapter_for(str(task["benchmark"])).invocation(task, lock_entry, values, source)
    command = invocation.command
    returncode, stdout, stderr, timed_out, wall_seconds = _run_command(
        command, workspace, budget.foreground_seconds
    )
    (artifacts / "agent.stdout").write_text(stdout, encoding="utf-8")
    (artifacts / "agent.stderr").write_text(stderr, encoding="utf-8")
    infrastructure: dict[str, Any] | None = None
    stop_reason: str | None = "foreground_timeout" if timed_out else None
    result: dict[str, Any] = {"input_tokens": 0, "output_tokens": 0}
    if not timed_out and returncode == 0:
        try:
            result = _agent_result(stdout)
        except ValueError as error:
            infrastructure = {
                "category": "agent_protocol",
                "message": str(error),
                "retryable": False,
            }
    elif not timed_out:
        infrastructure = {
            "category": "agent_command",
            "message": f"agent command exited {returncode}",
            "retryable": True,
        }
    foreground = int(result.get("input_tokens", 0)) + int(result.get("output_tokens", 0))
    if foreground > budget.foreground_tokens:
        stop_reason = "foreground_token_budget"
    background = 0
    if infrastructure is None and not timed_out and maintenance_allowed:
        try:
            background = _post_memory(condition, brain_root, result)
            if background > budget.background_tokens:
                stop_reason = "background_token_budget"
        except ValueError as error:
            infrastructure = {
                "category": "memory_protocol",
                "message": str(error),
                "retryable": False,
            }
    verifier_code: int | None
    if invocation.verifier_command is None:
        # Native adapters write Harbor's verifier result into this explicit
        # contract file. It is still parsed by the harness, never inferred from
        # the agent transcript.
        verifier_path = workspace / "verifier-result.json"
        verifier_code = 0 if verifier_path.is_file() else 1
        verifier_stdout = verifier_path.read_text(encoding="utf-8") if verifier_path.is_file() else ""
        verifier_stderr = "" if verifier_path.is_file() else "Harbor verifier result was not produced"
        verifier_timeout = False
        verifier_seconds = 0.0
    else:
        verifier_code, verifier_stdout, verifier_stderr, verifier_timeout, verifier_seconds = _run_command(
            invocation.verifier_command, workspace, min(300, budget.foreground_seconds)
        )
    (artifacts / "verifier.stdout").write_text(verifier_stdout, encoding="utf-8")
    (artifacts / "verifier.stderr").write_text(verifier_stderr, encoding="utf-8")
    verifier: dict[str, Any] | None = None
    if verifier_timeout or verifier_code != 0:
        infrastructure = {
            "category": "verifier_unavailable",
            "message": "verifier timed out"
            if verifier_timeout
            else f"verifier exited {verifier_code}",
            "retryable": True,
        }
    else:
        try:
            verifier = _verifier_result(verifier_stdout)
        except ValueError as error:
            infrastructure = {
                "category": "verifier_protocol",
                "message": str(error),
                "retryable": False,
            }
    status = (
        "infrastructure_failure"
        if infrastructure
        else "graceful_stop"
        if stop_reason
        else "completed"
    )
    outcome: dict[str, Any] = {
        "run_id": run_id,
        "condition": condition,
        "task_id": str(task["task_id"]),
        "split": str(task.get("split", "deployment")),
        "model": runtime.model,
        "reasoning": runtime.reasoning,
        "commit_sha": _git_commit(root),
        "harness_version": "benchmark-harness-v1",
        "success": verifier["success"] if verifier and not infrastructure else None,
        "verifier_score": verifier["score"] if verifier and not infrastructure else None,
        "foreground_input_tokens": int(result.get("input_tokens", 0)),
        "foreground_output_tokens": int(result.get("output_tokens", 0)),
        "background_tokens": background,
        "wall_seconds": round(wall_seconds + verifier_seconds, 6),
        "skills_retrieved": list(result.get("skills_retrieved", [])),
        "skills_applied": list(result.get("skills_applied", [])),
        "failure_signature": verifier.get("failure_signature") if verifier else None,
        "benchmark": str(task["benchmark"]),
        "attempt_id": attempt_id,
        "attempt_status": status,
        "stop_reason": stop_reason,
        "manifest_hash": manifest_hash,
        "config_hash": runtime.hash,
        "benchmark_lock_hash": lock_hash,
        "source_hash": str(lock_entry.get("source_tree_hash", "")),
        "task_tree_hash": str(task.get("task_tree_hash", "")),
        "selector": task.get("selector", {}),
        "memory_before_hash": memory_before_hash,
        "memory_after_hash": _store_hash(brain_root),
        "token_breakdown": {
            "foreground_input": int(result.get("input_tokens", 0)),
            "foreground_output": int(result.get("output_tokens", 0)),
            "maintenance_input": int(result.get("background_input_tokens", 0)),
            "maintenance_output": int(result.get("background_output_tokens", 0)),
        },
        "budget": {
            "foreground_tokens": budget.foreground_tokens,
            "foreground_seconds": budget.foreground_seconds,
            "background_tokens": budget.background_tokens,
            "background_seconds": budget.background_seconds,
        },
        "verifier": {
            "raw_stdout_path": _artifact_reference(root, artifacts / "verifier.stdout"),
            "raw_stderr_path": _artifact_reference(root, artifacts / "verifier.stderr"),
        },
        "infrastructure_failure": infrastructure,
        "retry_of": retry_of,
    }
    if not OUTCOME_FIELDS <= outcome.keys():
        raise ValueError("outcome schema is incomplete")
    _write_outcome(root, run_id, outcome)
    return outcome


def _expanded_attempts(manifest: dict[str, Any]) -> list[tuple[dict[str, Any], str, bool]]:
    """Expand selectors into primary verifier trials in deterministic order."""
    expanded: list[tuple[dict[str, Any], str, bool]] = []
    typed = int(manifest.get("schema_version", 1)) >= 2
    for item in manifest["tasks"]:
        if typed and item["benchmark"] == "skillevolbench":
            selector = dict(item["selector"])
            for role in selector["roles"]:
                trial = dict(item)
                trial["selector"] = {**selector, "role": role}
                trial["task_id"] = f"{item['task_id']}-{role.casefold()}"
                expanded.append((trial, str(item["task_id"]), role in {"T1", "T2", "T3"}))
        else:
            expanded.append((item, str(item["task_id"]), True))
    return expanded


def _git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _approval_errors(
    root: Path, manifest_hash: str, runtime_hash: str, estimate_path: Path, approval_path: Path
) -> list[str]:
    if not estimate_path.is_file() or not approval_path.is_file():
        return ["full pilot requires COST_ESTIMATE.md and approval YAML"]
    approval = read_yaml(approval_path, {})
    if not isinstance(approval, dict):
        return ["approval file must be a YAML mapping"]
    estimate_hash = sha256_text(estimate_path.read_text(encoding="utf-8"))
    required = {
        "approved": True,
        "estimate_hash": estimate_hash,
        "manifest_hash": manifest_hash,
        "runtime_hash": runtime_hash,
    }
    return [
        f"approval mismatch for {key}"
        for key, value in required.items()
        if approval.get(key) != value
    ]


def _protocol_tag_errors(root: Path, manifest_path: Path) -> list[str]:
    try:
        relative = manifest_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return ["pilot manifest must be inside the repository"]
    result = subprocess.run(
        ["git", "show", f"protocol-v1:{relative}"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return ["protocol-v1 tag does not contain the pilot manifest"]
    if result.stdout != manifest_path.read_bytes():
        return ["pilot manifest differs from protocol-v1"]
    return []


def run_stage(
    root: Path,
    manifest_path: Path,
    lock_path: Path,
    runtime_path: Path,
    run_id: str,
    stage: str,
    approval_path: Path | None = None,
    estimate_path: Path | None = None,
) -> list[dict[str, Any]]:
    if stage not in {"smoke", "pilot"}:
        raise ValueError("stage must be smoke or pilot")
    _safe_id(run_id)
    errors = preflight(root, manifest_path, lock_path, runtime_path)
    if errors:
        raise ValueError("preflight failed: " + "; ".join(errors))
    manifest, manifest_hash = load_manifest(manifest_path)
    runtime = load_runtime(runtime_path)
    if stage == "smoke" and len(manifest["tasks"]) != 2:
        raise ValueError("smoke manifest must contain exactly two tasks")
    if stage == "pilot":
        if len(manifest["tasks"]) != 6:
            raise ValueError("pilot manifest must contain exactly six tasks")
        if approval_path is None or estimate_path is None:
            raise ValueError("pilot stage requires approval and estimate paths")
        approval_errors = _approval_errors(
            root, manifest_hash, runtime.hash, estimate_path, approval_path
        )
        if approval_errors:
            raise ValueError("pilot cost gate failed: " + "; ".join(approval_errors))
        tag_errors = _protocol_tag_errors(root, manifest_path)
        if tag_errors:
            raise ValueError("pilot protocol gate failed: " + "; ".join(tag_errors))
    lock = _load_lock(lock_path)
    lock_hash = sha256_text(canonical_json(lock))
    run_descriptor = {
        "run_id": run_id,
        "stage": stage,
        "manifest_hash": manifest_hash,
        "benchmark_lock_hash": lock_hash,
        "runtime_hash": runtime.hash,
        "expected_primary_attempts": len(_expanded_attempts(manifest)) * len(CONDITIONS),
    }
    _write_json(_evaluations(root) / "runs" / run_id / "run.json", run_descriptor)
    outcomes: list[dict[str, Any]] = []
    retry_queue: list[tuple[dict[str, Any], str, str, str, bool]] = []
    # Condition-major scheduling preserves a family store while keeping all
    # acquisition roles before the frozen deployment roles.
    for condition in CONDITIONS:
        for task, store_key, maintenance_allowed in _expanded_attempts(manifest):
            attempt_id = _safe_id(f"{task['benchmark']}_{task['task_id']}_{condition}_r0")
            outcome = _run_attempt(
                root,
                task,
                condition,
                run_id,
                attempt_id,
                manifest_hash,
                lock_hash,
                runtime,
                _lock_entry(lock, str(task["benchmark"])),
                store_key,
                maintenance_allowed,
            )
            outcomes.append(outcome)
            if (
                outcome["attempt_status"] == "infrastructure_failure"
                and outcome["infrastructure_failure"]["retryable"]
            ):
                retry_queue.append((task, condition, attempt_id, store_key, maintenance_allowed))
    for task, condition, prior_id, store_key, maintenance_allowed in retry_queue:
        attempt_id = _safe_id(f"{task['benchmark']}_{task['task_id']}_{condition}_r1")
        outcomes.append(
            _run_attempt(
                root,
                task,
                condition,
                run_id,
                attempt_id,
                manifest_hash,
                lock_hash,
                runtime,
                _lock_entry(lock, str(task["benchmark"])),
                store_key,
                maintenance_allowed,
                retry_of=prior_id,
            )
        )
    return outcomes


def _outcomes(root: Path, run_id: str) -> list[dict[str, Any]]:
    path = _evaluations(root) / "runs" / run_id / "outcomes.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def check_completeness(root: Path, run_id: str, expected_attempts: int | None = None) -> list[str]:
    outcomes = _outcomes(root, run_id)
    errors: list[str] = []
    descriptor_path = _evaluations(root) / "runs" / run_id / "run.json"
    descriptor = _json(descriptor_path) if descriptor_path.is_file() else {}
    primary_expected = int(descriptor.get("expected_primary_attempts", expected_attempts or 0))
    primary = [outcome for outcome in outcomes if outcome.get("retry_of") is None]
    if primary_expected and len(primary) != primary_expected:
        errors.append(f"expected {primary_expected} primary outcomes, found {len(primary)}")
    if expected_attempts is not None and len(outcomes) != expected_attempts:
        errors.append(f"expected {expected_attempts} outcomes, found {len(outcomes)}")
    identifiers: set[str] = set()
    for outcome in outcomes:
        identifier = str(outcome.get("attempt_id", ""))
        if not identifier or identifier in identifiers:
            errors.append(f"duplicate or missing attempt id: {identifier}")
        identifiers.add(identifier)
        missing = OUTCOME_FIELDS - outcome.keys()
        if missing:
            errors.append(f"outcome {identifier} missing protocol fields: {sorted(missing)}")
        if outcome.get("attempt_status") not in {
            "completed",
            "graceful_stop",
            "infrastructure_failure",
        }:
            errors.append(f"outcome {identifier} has invalid terminal status")
        if (
            outcome.get("attempt_status") == "infrastructure_failure"
            and outcome.get("success") is not None
        ):
            errors.append(f"infrastructure outcome {identifier} must not have a score")
        verifier = outcome.get("verifier", {})
        for key in ("raw_stdout_path", "raw_stderr_path"):
            if not _artifact_exists(root, verifier.get(key)):
                errors.append(f"outcome {identifier} has missing verifier artifact {key}")
        if "solution" in canonical_json(outcome).casefold():
            errors.append(f"outcome {identifier} contains a forbidden solution marker")
    return errors


def build_cost_estimate(
    root: Path, smoke_run_id: str, pilot_manifest_path: Path, runtime_path: Path, output_path: Path
) -> Path:
    pilot, manifest_hash = load_manifest(pilot_manifest_path)
    runtime = load_runtime(runtime_path)
    outcomes = _outcomes(root, smoke_run_id)
    if not outcomes:
        raise ValueError("cannot estimate cost without smoke outcomes")
    input_tokens = sum(int(item["foreground_input_tokens"]) for item in outcomes)
    output_tokens = sum(int(item["foreground_output_tokens"]) for item in outcomes)
    background = sum(int(item["background_tokens"]) for item in outcomes)
    per_attempt = (input_tokens + output_tokens + background) / len(outcomes)
    full_attempts = len(_expanded_attempts(pilot)) * len(CONDITIONS)
    base_tokens = int(round(per_attempt * full_attempts))
    expected_tokens = int(round(base_tokens * 1.1))
    worst_tokens = base_tokens * 2
    rate = runtime.rate_card
    input_rate = float(rate.get("input_per_million", 0))
    output_rate = float(rate.get("output_per_million", 0))
    thb_per_currency = float(rate.get("thb_per_currency", 0))
    average_input_share = input_tokens / max(input_tokens + output_tokens + background, 1)
    base_cost = (base_tokens * average_input_share / 1_000_000 * input_rate) + (
        base_tokens * (1 - average_input_share) / 1_000_000 * output_rate
    )
    currency = str(rate.get("currency", "USD"))
    by_condition = {
        condition: sum(
            int(item["foreground_input_tokens"]) + int(item["foreground_output_tokens"]) + int(item["background_tokens"])
            for item in outcomes if item.get("condition") == condition
        )
        for condition in CONDITIONS
    }
    c1_maintenance = sum(int(item["background_tokens"]) for item in outcomes if item.get("condition") == "c1")
    document = "\n".join(
        [
            "# COST_ESTIMATE",
            "",
            "Status: UNAPPROVED",
            f"Smoke run: `{smoke_run_id}`",
            f"Pilot manifest hash: `{manifest_hash}`",
            f"Runtime hash: `{runtime.hash}`",
            f"Model: `{runtime.model}`",
            f"Benchmark lock hash: `{sha256_text(canonical_json(_load_lock(root / 'evaluations' / 'benchmark-lock.yaml'))) if (root / 'evaluations' / 'benchmark-lock.yaml').is_file() else 'unavailable'}`",
            "",
            "| Scenario | Attempts | Estimated tokens | Estimated cost |",
            "|---|---:|---:|---:|",
            f"| Base | {full_attempts} | {base_tokens} | {base_cost:.4f} {currency} |",
            f"| Expected (+10% infrastructure reserve) | {full_attempts} | {expected_tokens} | {base_cost * 1.1:.4f} {currency} |",
            f"| Hard worst case (one retry per attempt) | {full_attempts * 2} | {worst_tokens} | {base_cost * 2:.4f} {currency} |",
            "",
            f"THB conversion at configured rate: {thb_per_currency:g} THB/{currency}.",
            "",
            "| Smoke condition | Measured total tokens |",
            "|---|---:|",
            *[f"| {condition.upper()} | {by_condition[condition]} |" for condition in CONDITIONS],
            f"| C1 wiki maintenance only | {c1_maintenance} |",
            "Full pilot is forbidden until an approval YAML matches the hashes above.",
            "",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return output_path


def reset_run(root: Path, run_id: str) -> bool:
    _safe_id(run_id)
    targets = [
        _evaluations(root) / "runs" / run_id,
        benchmark_home(root) / "runs" / run_id,
    ]
    home = benchmark_home(root).resolve()
    changed = False
    for target in targets:
        resolved = target.resolve()
        if target != targets[0] and not resolved.is_relative_to(home):
            raise ValueError("refusing reset path outside BENCHMARK_HOME")
        if target.is_symlink():
            raise ValueError("refusing to reset a symlink")
        if target.exists():
            shutil.rmtree(target)
            changed = True
    return changed
