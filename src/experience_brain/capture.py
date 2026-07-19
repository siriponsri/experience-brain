from __future__ import annotations

import re
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal, cast

from .models import Actor, Event, EventType, Provenance, Redaction
from .store import append_event

SECRET_PATTERNS = (
    (re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*['\"]?[^'\"\s]+"), "secret"),
    (re.compile(r"sk-[A-Za-z0-9_-]{12,}"), "api_key"),
    (re.compile(r"(?i)BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY"), "private_key"),
    (re.compile(r"(?i)patient\s*(id|name|dob)\s*[:=]\s*[^,\n]+"), "patient_data"),
    (re.compile(r"(?i)(chain[- ]of[- ]thought|hidden reasoning)\s*[:=].+"), "hidden_reasoning"),
    (re.compile(r"(?i)benchmark\s+solution\s*[:=].+"), "benchmark_leakage"),
)


def redact_text(text: str, *, field_path: str = "content") -> tuple[str, list[Redaction]]:
    redactions: list[Redaction] = []
    result = text
    for pattern, reason in SECRET_PATTERNS:
        if pattern.search(result):
            result = pattern.sub("[REDACTED]", result)
            redactions.append(Redaction(field_path=field_path, reason=reason))
    return result, redactions


def redact_value(value: Any, *, field_path: str) -> tuple[Any, list[Redaction]]:
    if isinstance(value, str):
        return redact_text(value, field_path=field_path)
    if isinstance(value, list):
        redactions: list[Redaction] = []
        sanitized: list[Any] = []
        for index, item in enumerate(value):
            clean_item, item_redactions = redact_value(item, field_path=f"{field_path}.{index}")
            sanitized.append(clean_item)
            redactions.extend(item_redactions)
        return sanitized, redactions
    if isinstance(value, dict):
        redactions = []
        sanitized_dict: dict[str, Any] = {}
        for key, item in value.items():
            clean_item, item_redactions = redact_value(item, field_path=f"{field_path}.{key}")
            sanitized_dict[str(key)] = clean_item
            redactions.extend(item_redactions)
        return sanitized_dict, redactions
    return value, []


def make_event_id(prefix: str, *, project: str, session_id: str, content: str = "") -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    digest = sha256(f"{prefix}:{project}:{session_id}:{content}:{timestamp}".encode()).hexdigest()
    return f"{prefix}-{timestamp}-{digest[:8]}".upper()


def capture_event(root: Path, event: Event) -> Event:
    content, redactions = redact_text(event.content)
    metadata, metadata_redactions = redact_value(event.metadata, field_path="metadata")
    extra, extra_redactions = redact_value(event.provenance.extra, field_path="provenance.extra")
    provenance = event.provenance.model_copy(
        update={
            "redactions": [
                *event.provenance.redactions,
                *redactions,
                *metadata_redactions,
                *extra_redactions,
            ],
            "extra": extra,
        }
    )
    sanitized = event.model_copy(
        update={"content": content, "metadata": metadata, "provenance": provenance}
    )
    append_event(root, sanitized)
    return sanitized


def record_event(
    root: Path,
    *,
    project: str,
    session_id: str,
    event_type: EventType,
    actor: Actor,
    content: str = "",
    event_id: str | None = None,
    task_id: str | None = None,
    source: str = "mcp",
    tool_name: str | None = None,
    error_signature: str | None = None,
    outcome: str | None = None,
    metadata: dict[str, Any] | None = None,
    provenance: Provenance | None = None,
) -> Event:
    event = Event(
        id=event_id
        or make_event_id("EVT", project=project, session_id=session_id, content=content),
        type=event_type,
        actor=actor,
        source=source,
        project=project,
        session_id=session_id,
        task_id=task_id,
        content=content,
        tool_name=tool_name,
        error_signature=error_signature,
        outcome=cast(Literal["success", "failure", "unknown"] | None, outcome),
        metadata=metadata or {},
        provenance=provenance or Provenance(),
    )
    return capture_event(root, event)


def start_session(
    root: Path,
    *,
    project: str,
    session_id: str,
    goal: str = "",
    task_id: str | None = None,
    provenance: Provenance | None = None,
    metadata: dict[str, Any] | None = None,
) -> Event:
    return record_event(
        root,
        event_id=f"EVT-{session_id}-START",
        event_type=EventType.session_start,
        actor=Actor.agent,
        project=project,
        session_id=session_id,
        task_id=task_id,
        content=goal,
        metadata=metadata,
        provenance=provenance,
    )


def end_session(
    root: Path,
    *,
    project: str,
    session_id: str,
    summary: str = "",
    outcome: str | None = None,
    task_id: str | None = None,
    provenance: Provenance | None = None,
    metadata: dict[str, Any] | None = None,
) -> Event:
    return record_event(
        root,
        event_id=f"EVT-{session_id}-END",
        event_type=EventType.session_end,
        actor=Actor.agent,
        project=project,
        session_id=session_id,
        task_id=task_id,
        content=summary,
        outcome=outcome,
        metadata=metadata,
        provenance=provenance,
    )


def capture_message(
    root: Path,
    *,
    event_id: str,
    project: str,
    session_id: str,
    content: str,
    actor: Actor = Actor.agent,
    task_id: str | None = None,
    provenance: Provenance | None = None,
) -> Event:
    event = Event(
        id=event_id,
        type=EventType.agent_message if actor == Actor.agent else EventType.user_message,
        actor=actor,
        project=project,
        session_id=session_id,
        task_id=task_id,
        content=content,
        provenance=provenance or Provenance(),
    )
    return capture_event(root, event)
