"""Pinned, verifier-first adapters for the supported public benchmarks.

The adapters deliberately only construct native runner invocations.  They do
not read a task's ``solution`` directory, and they do not interpret agent
claims as a score.  A small JSON fixture mode is retained for offline contract
tests; it is rejected by production locks.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AdapterInvocation:
    command: list[str]
    verifier_command: list[str] | None
    cwd: Path
    task_reference: str


def _strings(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{label} must be a non-empty list of strings")
    return list(value)


def _render(command: object, values: dict[str, str], label: str) -> list[str]:
    return [part.format(**values) for part in _strings(command, label)]


class BenchmarkAdapter:
    name: str

    def validate(self, task: dict[str, Any], lock: dict[str, Any]) -> None:
        raise NotImplementedError

    def invocation(
        self, task: dict[str, Any], lock: dict[str, Any], values: dict[str, str], source: Path
    ) -> AdapterInvocation:
        raise NotImplementedError


class SkillEvolBenchAdapter(BenchmarkAdapter):
    """Run a selected T1--T6 family through SkillEvolBench's native scheduler."""

    name = "skillevolbench"

    def validate(self, task: dict[str, Any], lock: dict[str, Any]) -> None:
        selector = task.get("selector")
        if not isinstance(selector, dict):
            raise ValueError("SkillEvolBench task requires a family selector")
        family = selector.get("family_id")
        roles = selector.get("roles")
        if not isinstance(family, str) or not family:
            raise ValueError("SkillEvolBench selector requires family_id")
        required_roles = ["T1", "T2", "T3", "T4", "T5", "T6"]
        if not isinstance(roles, list) or [str(role) for role in roles] != required_roles:
            raise ValueError("SkillEvolBench selector roles must be T1 through T6 in native order")
        if lock.get("source_kind") != "git_repository":
            raise ValueError("SkillEvolBench lock must use source_kind git_repository")

    def invocation(
        self, task: dict[str, Any], lock: dict[str, Any], values: dict[str, str], source: Path
    ) -> AdapterInvocation:
        # A command override exists solely so the fake adapter can exercise the
        # same safety boundary without installing Harbor or invoking a model.
        if lock.get("adapter_mode") == "fixture":
            trial = lock.get("trial_command", lock.get("agent_command"))
            return AdapterInvocation(
                _render(trial, values, "fixture trial_command"),
                _render(lock.get("verifier_command"), values, "fixture verifier_command"),
                source,
                str(task["selector"]["family_id"]),
            )
        worker = str(lock.get("worker_python", "python3.12"))
        family = str(task["selector"]["family_id"])
        command = [
            worker,
            "-m",
            "scripts.run",
            "--family-id",
            family,
            "--workspace",
            values["workspace"],
            "--agent-context-file",
            values["context"],
            "--runtime-config",
            values["runtime"],
            "--sequential",
        ]
        role = task["selector"].get("role")
        if isinstance(role, str):
            command.extend(["--include-role", role])
        return AdapterInvocation(command, None, source, family)


class TerminalBenchAdapter(BenchmarkAdapter):
    """Run one frozen Terminal-Bench task via Harbor's local-dataset mode."""

    name = "terminal_bench"

    def validate(self, task: dict[str, Any], lock: dict[str, Any]) -> None:
        selector = task.get("selector")
        if not isinstance(selector, dict) or not isinstance(selector.get("task_id"), str):
            raise ValueError("Terminal-Bench task requires an exact task selector")
        if lock.get("source_kind") != "huggingface_dataset":
            raise ValueError("Terminal-Bench lock must use source_kind huggingface_dataset")

    def invocation(
        self, task: dict[str, Any], lock: dict[str, Any], values: dict[str, str], source: Path
    ) -> AdapterInvocation:
        if lock.get("adapter_mode") == "fixture":
            trial = lock.get("trial_command", lock.get("agent_command"))
            return AdapterInvocation(
                _render(trial, values, "fixture trial_command"),
                _render(lock.get("verifier_command"), values, "fixture verifier_command"),
                source,
                str(task["selector"]["task_id"]),
            )
        worker = str(lock.get("worker_python", "python3.12"))
        task_id = str(task["selector"]["task_id"])
        command = [
            worker,
            "-m",
            "harbor",
            "run",
            "--path",
            str(source),
            "--include-task-name",
            task_id,
            "--workspace",
            values["workspace"],
            "--agent-context-file",
            values["context"],
            "--runtime-config",
            values["runtime"],
        ]
        return AdapterInvocation(command, None, source, task_id)


ADAPTERS: dict[str, BenchmarkAdapter] = {
    "skillevolbench": SkillEvolBenchAdapter(),
    "terminal_bench": TerminalBenchAdapter(),
}


def adapter_for(benchmark: str) -> BenchmarkAdapter:
    try:
        return ADAPTERS[benchmark]
    except KeyError as error:
        raise ValueError(f"unsupported benchmark adapter: {benchmark}") from error
