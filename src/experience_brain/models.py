from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "v0.2.1"


class EventType(StrEnum):
    session_start = "session_start"
    session_end = "session_end"
    user_message = "user_message"
    agent_message = "agent_message"
    tool_call = "tool_call"
    tool_result = "tool_result"
    file_change = "file_change"
    decision = "decision"
    feedback = "feedback"
    error = "error"
    outcome = "outcome"


class Actor(StrEnum):
    owner = "owner"
    agent = "agent"
    tool = "tool"
    system = "system"
    importer = "importer"


class Trust(StrEnum):
    first_party = "first_party"
    external_untrusted = "external_untrusted"
    owner_confirmed = "owner_confirmed"


class ExperienceStatus(StrEnum):
    proposed = "proposed"
    active = "active"
    confirmed = "confirmed"
    refined = "refined"
    superseded = "superseded"
    invalidated = "invalidated"
    retired = "retired"


class Authority(StrEnum):
    owner = "owner"
    project_rule = "project_rule"
    outcome_feedback = "outcome_feedback"
    repeated_success = "repeated_success"


class Redaction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_path: str
    reason: str


class Cost(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    wall_seconds: float = Field(default=0.0, ge=0)


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None
    software_version: str = SCHEMA_VERSION
    experiment_id: str | None = None
    run_id: str | None = None
    source: str = "experience-brain"
    redactions: list[Redaction] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    schema_version: str = SCHEMA_VERSION
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    type: EventType
    actor: Actor
    source: str = "agent_cli"
    project: str
    session_id: str
    task_id: str | None = None
    content: str = ""
    tool_name: str | None = None
    error_signature: str | None = None
    outcome: Literal["success", "failure", "unknown"] | None = None
    trust: Trust = Trust.first_party
    cost: Cost = Field(default_factory=Cost)
    provenance: Provenance = Field(default_factory=Provenance)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id", "project", "session_id")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be non-empty")
        return value


class Experience(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    schema_version: str = SCHEMA_VERSION
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = None
    project: str
    source_project: str
    external_project: bool = False
    status: ExperienceStatus = ExperienceStatus.proposed
    authority: Authority = Authority.outcome_feedback
    situation: str = ""
    goal: str = ""
    action: str = ""
    tool_context: str | None = None
    decision: str | None = None
    outcome: str | None = None
    feedback: str | None = None
    lesson: str
    evidence_event_ids: list[str]
    confidence: float = Field(default=0.5, ge=0, le=1)
    success_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
    last_used_at: datetime | None = None
    last_used_session_id: str | None = None
    owner_confirmed: bool = False
    supersedes: str | None = None
    invalidates: str | None = None
    provenance: Provenance = Field(default_factory=Provenance)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id", "project", "source_project", "lesson")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be non-empty")
        return value

    @model_validator(mode="after")
    def _needs_evidence(self) -> Experience:
        if not self.evidence_event_ids:
            raise ValueError("experience must cite at least one evidence event")
        return self


class StoredEvent(Event):
    payload_hash: str
    previous_hash: str
    record_hash: str
    ingested_at: datetime


class StoredExperience(Experience):
    payload_hash: str
    previous_hash: str
    record_hash: str
    ingested_at: datetime
