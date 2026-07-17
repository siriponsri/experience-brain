from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import Settings
from .hybrid import hybrid_scores
from .util import read_markdown, read_yaml, word_set


def _overlap(left: set[str], right: set[str]) -> float:
    return len(left & right) / max(len(left | right), 1)


def _task(task_path: Path) -> dict[str, Any]:
    task = read_yaml(task_path, {})
    if not isinstance(task, dict):
        raise ValueError("task must be a YAML mapping")
    return task


def _lexical(root: Path, task: dict[str, Any]) -> list[dict[str, Any]]:
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
    return sorted(results, key=lambda item: (-float(item["score"]), item["id"]))


def retrieve(root: Path, task_path: Path, limit: int = 5) -> list[dict[str, Any]]:
    """The unchanged C2 lexical retrieval interface."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    return _lexical(root, _task(task_path))[:limit]


def retrieve_for_settings(
    settings: Settings, task_path: Path, limit: int = 5
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Dispatch Full hybrid retrieval without changing Lite output behavior."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    task = _task(task_path)
    lexical = _lexical(settings.root, task)
    if settings.profile != "full" or not settings.full_modules["hybrid_retrieval"]:
        return lexical[:limit], None
    text = "\n".join(
        [
            str(task.get("goal", "")),
            *[str(item) for item in task.get("task_types", [])],
            *[str(item) for item in task.get("signals", [])],
        ]
    )
    return hybrid_scores(settings, text, lexical, limit)
