from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import Settings
from .event_store import read_events
from .util import (
    canonical_json,
    read_markdown,
    read_yaml,
    render_markdown,
    sha256_text,
    slug,
    write_yaml,
)


def _episode_id(events: list[dict[str, Any]]) -> str:
    joined = ":".join(str(event["record_hash"]) for event in events)
    return f"ep_{sha256_text(joined)[:12]}"


def _skill_fingerprint(candidate: dict[str, Any]) -> str:
    selected = {
        "key": candidate.get("key", ""),
        "activation": candidate.get("activation", {}),
        "preconditions": candidate.get("preconditions", []),
        "procedure": candidate.get("procedure", []),
        "termination": candidate.get("termination", []),
    }
    return sha256_text(canonical_json(selected))


def _episode_document(events: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
    verifier = next(event for event in reversed(events) if event["type"] == "verifier")
    event_ids = [str(event["id"]) for event in events]
    event_hashes = [str(event["record_hash"]) for event in events]
    attribution_events = [event for event in events if isinstance(event.get("attribution"), dict)]
    decisions = [event["attribution"] for event in attribution_events]
    metadata: dict[str, Any] = {
        "id": _episode_id(events),
        "run_id": events[0]["run_id"],
        "task_id": events[0]["task_id"],
        "goal": events[0].get("goal", events[0]["task_id"]),
        "started_at": events[0]["timestamp"],
        "ended_at": verifier["timestamp"],
        "outcome": {
            "success": verifier["verifier"]["success"],
            "verifier_score": verifier["verifier"]["score"],
        },
        "events": event_ids,
        "provenance": {"event_hashes": event_hashes, "verifier_event_id": verifier["id"]},
        "decisions": decisions,
        "failure_signature": verifier["verifier"].get("failure_signature"),
        "cost": {
            "input_tokens": sum(int(event["cost"].get("input_tokens", 0)) for event in events),
            "output_tokens": sum(int(event["cost"].get("output_tokens", 0)) for event in events),
            "wall_seconds": sum(float(event["cost"].get("wall_seconds", 0)) for event in events),
        },
        "trust": "first_party_execution",
    }
    return metadata, "Deterministically consolidated from append-only events."


def _write_episode(root: Path, metadata: dict[str, Any], body: str) -> bool:
    path = root / "memory" / "episodes" / f"{metadata['id']}.md"
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(metadata, body), encoding="utf-8")
    return True


def _load_episode_documents(root: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in sorted((root / "memory" / "episodes").glob("*.md")):
        metadata, _ = read_markdown(path)
        result.append(metadata)
    return result


def _write_skill(root: Path, skill: dict[str, Any]) -> bool:
    index_path = root / "memory" / "skills" / "index.yaml"
    index = read_yaml(index_path, {"skills": {}})
    skills = index.setdefault("skills", {})
    skill_id = str(skill["id"])
    existing = skills.get(skill_id)
    evidence = skill["evidence"]["episode_ids"]
    if (
        existing
        and existing.get("evidence_episode_ids") == evidence
        and existing.get("status") == skill["status"]
    ):
        return False
    version = int(existing.get("version", 0)) + 1 if existing else 1
    skill["version"] = version
    skill["supersedes"] = existing.get("path") if existing else None
    relative = f"memory/skills/{skill_id}_v{version}.md"
    path = root / relative
    path.write_text(
        render_markdown(skill, "Verified procedural memory requires provenance."), encoding="utf-8"
    )
    skills[skill_id] = {
        "path": relative,
        "version": version,
        "status": skill["status"],
        "evidence_episode_ids": evidence,
        "fingerprint": skill["fingerprint"],
    }
    write_yaml(index_path, index)
    return True


def consolidate(settings: Settings, run_id: str | None = None) -> tuple[int, int]:
    events = read_events(settings.root)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        if run_id is None or event["run_id"] == run_id:
            grouped[(str(event["run_id"]), str(event["task_id"]))].append(event)
    created_episodes = 0
    for attempt_events in grouped.values():
        if any(event["type"] == "verifier" for event in attempt_events):
            metadata, body = _episode_document(attempt_events)
            created_episodes += int(_write_episode(settings.root, metadata, body))

    episodes = {str(item["id"]): item for item in _load_episode_documents(settings.root)}
    candidates: dict[str, dict[str, Any]] = {}
    for event in events:
        candidate = event.get("skill_candidate")
        if not isinstance(candidate, dict) or event["trust"] != "first_party_execution":
            continue
        fingerprint = _skill_fingerprint(candidate)
        bucket = candidates.setdefault(fingerprint, {"candidate": candidate, "episode_ids": set()})
        episode = next((item for item in episodes.values() if event["id"] in item["events"]), None)
        if episode is not None:
            bucket["episode_ids"].add(str(episode["id"]))

    written_skills = 0
    review_items: list[dict[str, Any]] = []
    for fingerprint, bucket in candidates.items():
        candidate = bucket["candidate"]
        episode_ids = sorted(bucket["episode_ids"])
        successful = [
            episode_id
            for episode_id in episode_ids
            if bool(episodes[episode_id]["outcome"]["success"])
            and float(episodes[episode_id]["outcome"]["verifier_score"])
            >= settings.minimum_verifier_score
        ]
        skill_id = f"skill_{slug(str(candidate.get('key') or fingerprint[:12]))}"
        status = (
            "verified" if len(successful) >= settings.minimum_successful_episodes else "candidate"
        )
        if status == "candidate":
            review_items.append(
                {
                    "skill_id": skill_id,
                    "reason": "insufficient verified episode evidence",
                    "episode_ids": episode_ids,
                }
            )
        skill: dict[str, Any] = {
            "id": skill_id,
            "version": 0,
            "status": status,
            "scope": str(candidate.get("scope", "project")),
            "activation": candidate.get("activation", {"task_types": [], "signals": []}),
            "preconditions": candidate.get("preconditions", []),
            "procedure": candidate.get("procedure", []),
            "termination": candidate.get("termination", []),
            "failure_modes": candidate.get("failure_modes", []),
            "evidence": {
                "episode_ids": episode_ids,
                "verifier_results": [episodes[item]["outcome"]["success"] for item in episode_ids],
                "verifier_event_ids": [
                    episodes[item]["provenance"]["verifier_event_id"] for item in episode_ids
                ],
            },
            "confidence": round(len(successful) / max(len(episode_ids), 1), 2),
            "fingerprint": fingerprint,
            "supersedes": None,
        }
        written_skills += int(_write_skill(settings.root, skill))
    write_yaml(settings.root / "memory" / "review_queue.yaml", {"items": review_items})
    return created_episodes, written_skills
