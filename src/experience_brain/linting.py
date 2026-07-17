from __future__ import annotations

from typing import Any

from .config import Settings
from .event_store import read_events
from .tokens import count_tokens
from .util import canonical_json, read_markdown, read_yaml, sha256_text
from .wiki import lint_wiki


def lint(settings: Settings) -> list[str]:
    if settings.condition == "c1":
        return lint_wiki(settings)
    if settings.condition != "c2":
        return []
    return _lint_lite(settings)


def _lint_lite(settings: Settings) -> list[str]:
    errors: list[str] = []
    events = read_events(settings.root)
    previous = ""
    event_ids: set[str] = set()
    hashes: set[str] = set()
    for event in events:
        event_ids.add(str(event.get("id")))
        if event.get("previous_hash", "") != previous:
            errors.append(f"event {event.get('id')} has invalid previous hash")
        expected = sha256_text(
            canonical_json({key: value for key, value in event.items() if key != "record_hash"})
        )
        if event.get("record_hash") != expected:
            errors.append(f"event {event.get('id')} has invalid record hash")
        previous = str(event.get("record_hash", ""))
        hashes.add(previous)
    episodes: dict[str, dict[str, Any]] = {}
    for path in (settings.root / "memory" / "episodes").glob("*.md"):
        metadata, _ = read_markdown(path)
        episodes[str(metadata.get("id"))] = metadata
        if not set(metadata.get("events", [])) <= event_ids:
            errors.append(f"episode {metadata.get('id')} references missing events")
        if not set(metadata.get("provenance", {}).get("event_hashes", [])) <= hashes:
            errors.append(f"episode {metadata.get('id')} has broken provenance")
    index = read_yaml(settings.root / "memory" / "skills" / "index.yaml", {"skills": {}})
    for skill_id, entry in index.get("skills", {}).items():
        path = settings.root / str(entry.get("path", ""))
        if not path.exists():
            errors.append(f"skill {skill_id} index path is missing")
            continue
        metadata, _ = read_markdown(path)
        evidence = metadata.get("evidence", {}).get("episode_ids", [])
        if not evidence or not set(evidence) <= set(episodes):
            errors.append(f"skill {skill_id} has broken episode evidence")
        if (
            metadata.get("status") == "verified"
            and len(evidence) < settings.minimum_successful_episodes
        ):
            errors.append(f"skill {skill_id} is verified with insufficient evidence")
    for path in (settings.root / "capsules").glob("*.md"):
        metadata, body = read_markdown(path)
        if count_tokens(settings, path.read_text(encoding="utf-8")) > int(
            metadata.get("budget_tokens", 0)
        ):
            errors.append(f"capsule {path.name} exceeds token budget")
        if not body.startswith("# Task contract"):
            errors.append(f"capsule {path.name} has no task contract")
    for path in (settings.root / "sources" / "converted").glob("*.yaml"):
        metadata = read_yaml(path, {})
        if metadata.get("trust") != "untrusted_external_content":
            errors.append(f"source sidecar {path.name} is not untrusted")
    return errors
