from __future__ import annotations

import re
from pathlib import Path

from .models import Actor, Event, EventType, Provenance, Redaction
from .store import append_event

SECRET_PATTERNS = (
    (re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*['\"]?[^'\"\s]+"), "secret"),
    (re.compile(r"sk-[A-Za-z0-9_-]{12,}"), "api_key"),
    (re.compile(r"(?i)BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY"), "private_key"),
    (re.compile(r"(?i)patient\s*(id|name|dob)\s*[:=]\s*[^,\n]+"), "patient_data"),
    (re.compile(r"(?i)(chain[- ]of[- ]thought|hidden reasoning)\s*[:=].+"), "hidden_reasoning"),
)


def redact_text(text: str) -> tuple[str, list[Redaction]]:
    redactions: list[Redaction] = []
    result = text
    for pattern, reason in SECRET_PATTERNS:
        if pattern.search(result):
            result = pattern.sub("[REDACTED]", result)
            redactions.append(Redaction(field_path="content", reason=reason))
    return result, redactions


def capture_event(root: Path, event: Event) -> Event:
    content, redactions = redact_text(event.content)
    provenance = event.provenance.model_copy(
        update={"redactions": [*event.provenance.redactions, *redactions]}
    )
    sanitized = event.model_copy(update={"content": content, "provenance": provenance})
    append_event(root, sanitized)
    return sanitized


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
