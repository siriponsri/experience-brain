from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import Settings
from .retrieval import retrieve_for_settings
from .tokens import count_tokens
from .util import read_yaml, render_markdown

__all__ = ["build_capsule", "count_tokens"]


def _render(
    task: dict[str, Any],
    budget: int,
    selected: list[dict[str, Any]],
    omitted: int,
    estimate: int,
    profile: str = "lite",
    retrieval_telemetry: dict[str, Any] | None = None,
) -> str:
    items = [
        {
            "memory_id": item["id"],
            "type": "skill",
            "score": item["score"],
            "evidence_ids": item["skill"]["evidence"]["episode_ids"],
        }
        for item in selected
    ]
    metadata = {
        "id": f"capsule_{task.get('id', 'task')}_{budget}",
        "task_id": task.get("id", "task"),
        "profile": profile,
        "budget_tokens": budget,
        "estimated_tokens": estimate,
        "retrieval_policy_version": (
            retrieval_telemetry.get("policy", "full-hybrid-rrf-v1")
            if retrieval_telemetry
            else "lite-lexical-v1"
        ),
        "items": items,
        "omitted_items": omitted,
    }
    if retrieval_telemetry is not None:
        metadata["retrieval_telemetry"] = retrieval_telemetry
    lines = ["# Task contract", str(task.get("goal", "")), "", "## Safety constraints"]
    lines.extend(f"- {item}" for item in task.get("constraints", []))
    lines.append("\n## Verified procedures")
    for item in selected:
        skill = item["skill"]
        lines.append(f"### {skill['id']}")
        lines.extend(f"- {step}" for step in skill.get("procedure", []))
        lines.append("Evidence: " + ", ".join(skill["evidence"]["episode_ids"]))
    return render_markdown(metadata, "\n".join(lines))


def build_capsule(settings: Settings, task_path: Path, budget: int) -> Path:
    if budget <= 0:
        raise ValueError("budget must be positive")
    task = read_yaml(task_path, {})
    if not isinstance(task, dict):
        raise ValueError("task must be a YAML mapping")
    candidates, retrieval_telemetry = retrieve_for_settings(settings, task_path, limit=100)
    selected: list[dict[str, Any]] = []
    mandatory = _render(
        task,
        budget,
        [],
        len(candidates),
        0,
        settings.profile,
        retrieval_telemetry,
    )
    if count_tokens(settings, mandatory) > budget:
        raise ValueError("task contract and safety constraints exceed capsule budget")
    for candidate in candidates:
        candidate_rendered = _render(
            task,
            budget,
            [*selected, candidate],
            len(candidates) - len(selected) - 1,
            0,
            settings.profile,
            retrieval_telemetry,
        )
        if count_tokens(settings, candidate_rendered) <= budget:
            selected.append(candidate)
    rendered = _render(
        task,
        budget,
        selected,
        len(candidates) - len(selected),
        0,
        settings.profile,
        retrieval_telemetry,
    )
    for _ in range(5):
        estimate = count_tokens(settings, rendered)
        updated = _render(
            task,
            budget,
            selected,
            len(candidates) - len(selected),
            estimate,
            settings.profile,
            retrieval_telemetry,
        )
        if updated == rendered:
            break
        rendered = updated
    if count_tokens(settings, rendered) > budget:
        raise ValueError("capsule exceeds token budget")
    identifier = str(task.get("id", "task"))
    destination = settings.root / "capsules" / f"capsule_{identifier}_{budget}.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")
    return destination
