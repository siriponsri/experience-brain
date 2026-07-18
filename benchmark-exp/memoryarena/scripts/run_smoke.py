from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
MEMORYARENA_DIR = SCRIPT_DIR.parent
BENCHMARK_DIR = MEMORYARENA_DIR.parent
if str(MEMORYARENA_DIR) not in sys.path:
    sys.path.insert(0, str(MEMORYARENA_DIR))

from adapter import (  # noqa: E402
    ExperienceBrainMemorySystem,
    NoPersistentMemorySystem,
    condition_store_root,
    summarize_logs,
    validate_store_isolation,
    write_result_json,
)
from adapter.experience_brain_memory import AdapterProvenance  # noqa: E402


def _load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return loaded


def _memory_for_condition(
    *,
    condition: str,
    base_run_dir: Path,
    task_group_id: str,
    run_id: str,
    config: dict[str, Any],
) -> object:
    if condition == "C0":
        return NoPersistentMemorySystem()
    provenance = AdapterProvenance(
        model=str(config["model"]["name"]),
        reasoning_effort=str(config["model"]["reasoning_effort"]),
        experiment_id=str(config["experiment_id"]),
        run_id=run_id,
        memoryarena_commit=str(config["upstream"]["memoryarena_commit"]),
        dataset_revision=str(config["dataset"]["revision"]),
    )
    return ExperienceBrainMemorySystem(
        root=condition_store_root(base_run_dir, condition, task_group_id),
        condition=condition,  # type: ignore[arg-type]
        user_id=run_id,
        task_group_id=task_group_id,
        provenance=provenance,
        top_k=int(config["memory"]["top_k"]),
    )


def run_dry_smoke(config: dict[str, Any], output: Path) -> dict[str, Any]:
    task_ids = [int(task_id) for task_id in config["smoke_subset"]["selected_task_ids"]]
    task_group_id = str(config["dataset"]["subset"])
    base_run_dir = output / "runs" / str(config["experiment_id"])
    store_roots = [
        condition_store_root(base_run_dir, condition, task_group_id)
        for condition in config["conditions"]
        if condition != "C0"
    ]
    validate_store_isolation(store_roots)

    results: list[dict[str, Any]] = []
    for condition in config["conditions"]:
        run_id = str(config["run_ids"][condition])
        memory = _memory_for_condition(
            condition=condition,
            base_run_dir=base_run_dir,
            task_group_id=task_group_id,
            run_id=run_id,
            config=config,
        )
        logs: list[dict[str, Any]] = []
        for position, task_id in enumerate(task_ids):
            question = f"Dry-run prompt for MemoryArena task group {task_id} position {position}."
            prompt = memory.wrap_user_prompt(question)  # type: ignore[attr-defined]
            memory.add_chunk(  # type: ignore[attr-defined]
                f"## Task: dry-run task group {task_id}\n"
                f"## solution: simulated agent response for position {position}\n"
                "## Tool Calls Info: none\n"
            )
            logs.append(
                {
                    "query_id": position,
                    "task_group_id": task_id,
                    "memory_context": prompt,
                    "response": "dry-run response",
                    "is_correct": None,
                    "time": 0.0,
                }
            )
        diagnostics = memory.diagnostics()  # type: ignore[attr-defined]
        summary = summarize_logs(
            condition=condition,
            run_id=run_id,
            task_group_id=task_group_id,
            logs=logs,
            diagnostics=diagnostics,
        )
        results.append(summary)
        write_result_json(output / "results" / f"{run_id}.json", summary)
    payload = {
        "experiment_id": config["experiment_id"],
        "dry_run": True,
        "real_benchmark_inference_run": False,
        "selected_task_ids": task_ids,
        "conditions": results,
    }
    write_result_json(output / "results" / "dry_smoke_summary.json", payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default=str(MEMORYARENA_DIR / "configs" / "smoke_formal_reasoning_math_5.json"),
    )
    parser.add_argument("--output", default=str(MEMORYARENA_DIR))
    parser.add_argument("--dry-run", action="store_true", required=True)
    args = parser.parse_args()
    payload = run_dry_smoke(_load_json(Path(args.config)), Path(args.output))
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
