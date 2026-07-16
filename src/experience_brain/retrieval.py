from __future__ import annotations

from pathlib import Path
from typing import Any

from .util import read_markdown, read_yaml, word_set


def _overlap(left: set[str], right: set[str]) -> float:
    return len(left & right) / max(len(left | right), 1)


def retrieve(root: Path, task_path: Path, limit: int = 5) -> list[dict[str, Any]]:
    task = read_yaml(task_path, {})
    if not isinstance(task, dict):
        raise ValueError("task must be a YAML mapping")
    task_types = {str(value).casefold() for value in task.get("task_types", [])}
    signals = {str(value).casefold() for value in task.get("signals", [])}
    task_words = word_set(str(task.get("goal", "")))
    index = read_yaml(root / "memory" / "skills" / "index.yaml", {"skills": {}})
    results: list[dict[str, Any]] = []
    for skill_id, entry in index.get("skills", {}).items():
        if entry.get("status") != "verified":
            continue
        metadata, _ = read_markdown(root / str(entry["path"]))
        activation = metadata.get("activation", {})
        skill_types = {str(value).casefold() for value in activation.get("task_types", [])}
        skill_signals = {str(value).casefold() for value in activation.get("signals", [])}
        skill_words = word_set(" ".join(map(str, metadata.get("procedure", []))))
        score = (
            5 * _overlap(task_types, skill_types)
            + 3 * _overlap(signals, skill_signals)
            + 2 * _overlap(task_words, skill_words)
        )
        results.append(
            {
                "id": skill_id,
                "score": round(score + float(metadata.get("confidence", 0)), 6),
                "skill": metadata,
            }
        )
    return sorted(results, key=lambda item: (-float(item["score"]), item["id"]))[:limit]
