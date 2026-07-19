from __future__ import annotations

from pathlib import Path


def condition_store_root(base_dir: Path, condition: str, task_group_id: str) -> Path:
    safe_task_group = task_group_id.replace("/", "_").replace("\\", "_")
    return base_dir / "stores" / condition / safe_task_group


def validate_store_isolation(paths: list[Path]) -> None:
    resolved = [path.resolve() for path in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError("memory store roots must be unique")
    for index, current in enumerate(resolved):
        for other in resolved[index + 1 :]:
            if current in other.parents or other in current.parents:
                raise ValueError("memory store roots must not be nested")


def scan_store_for_forbidden_terms(root: Path, forbidden_terms: list[str]) -> list[str]:
    findings: list[str] = []
    lowered_terms = [term.casefold() for term in forbidden_terms]
    for relative in ("data/events.jsonl", "data/experiences.jsonl"):
        path = root / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8").casefold()
        for term in lowered_terms:
            if term in text:
                findings.append(f"{relative}: {term}")
    return findings
