from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def summarize_logs(
    *,
    condition: str,
    run_id: str,
    task_group_id: str,
    logs: list[dict[str, Any]],
    diagnostics: dict[str, object],
) -> dict[str, Any]:
    correctness = [
        bool(log["is_correct"])
        for log in logs
        if isinstance(log.get("is_correct"), bool | int | float)
    ]
    wall_clock = [float(log["time"]) for log in logs if isinstance(log.get("time"), int | float)]
    input_tokens = [
        int(log["input_tokens"]) for log in logs if isinstance(log.get("input_tokens"), int)
    ]
    output_tokens = [
        int(log["output_tokens"]) for log in logs if isinstance(log.get("output_tokens"), int)
    ]
    total_tokens = [
        int(log["total_tokens"]) for log in logs if isinstance(log.get("total_tokens"), int)
    ]
    successful = sum(1 for item in correctness if item)
    token_total = sum(total_tokens) if total_tokens else None
    return {
        "condition": condition,
        "run_id": run_id,
        "task_group_id": task_group_id,
        "primary": {
            "subtask_accuracy": _mean([1.0 if item else 0.0 for item in correctness]),
            "complete_task_group_success": all(correctness) if correctness else None,
        },
        "supporting": {
            "performance_by_subtask_position": [
                {"position": index, "is_correct": item} for index, item in enumerate(correctness)
            ],
            "errors": [log.get("error") for log in logs if log.get("error")],
            "retries": sum(int(log.get("retries", 0) or 0) for log in logs),
            "tool_failures": sum(int(log.get("tool_failures", 0) or 0) for log in logs),
            "wall_clock_time": sum(wall_clock) if wall_clock else None,
            "input_tokens": sum(input_tokens) if input_tokens else None,
            "output_tokens": sum(output_tokens) if output_tokens else None,
            "total_tokens": token_total,
            "tokens_per_successful_subtask": (
                token_total / successful if token_total is not None and successful else None
            ),
        },
        "experience_brain_diagnostics": diagnostics,
    }


def write_result_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
