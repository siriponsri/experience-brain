from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .util import canonical_json, read_yaml, sha256_text

CONDITION_ALIASES = {
    "c0": "c0",
    "no_memory": "c0",
    "c1": "c1",
    "wiki": "c1",
    "c2": "c2",
    "lite": "c2",
    "c3": "c3",
    "full": "c3",
}

FULL_MODULES = (
    "hybrid_retrieval",
    "consolidation_pruning",
    "proactive_intervention",
    "temporal_kg",
    "multimodal",
)


@dataclass(frozen=True)
class Settings:
    root: Path
    condition: str
    run_id: str
    tokenizer_encoding: str
    default_budget_tokens: int
    minimum_successful_episodes: int
    minimum_verifier_score: float
    wiki_prompt_references: tuple[Path, ...]
    fairness: dict[str, Any]
    profile: str
    full_modules: dict[str, bool]
    full: dict[str, Any]

    @property
    def fairness_fingerprint(self) -> str:
        return sha256_text(canonical_json(self.fairness))


def _condition(value: object) -> str:
    normalized = str(value).strip().casefold()
    if normalized not in CONDITION_ALIASES:
        raise ValueError(f"unsupported condition {value!r}")
    return CONDITION_ALIASES[normalized]


def _run_id(value: object) -> str:
    candidate = str(value).strip()
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    if not candidate or any(character not in allowed for character in candidate):
        raise ValueError("run_id may contain only letters, digits, dot, underscore, and hyphen")
    return candidate


def load_settings(root: Path) -> Settings:
    data = read_yaml(root / "brain.yaml", {})
    verification = data.get("verification", {})
    wiki = data.get("wiki", {})
    references = wiki.get("prompt_references", [])
    if not isinstance(references, list):
        raise ValueError("wiki.prompt_references must be a list")
    fairness = data.get("fairness", {})
    if not isinstance(fairness, dict):
        raise ValueError("fairness must be a mapping")
    profile = str(data.get("profile", "lite")).strip().casefold()
    if profile not in {"lite", "full"}:
        raise ValueError("profile must be lite or full")
    full = data.get("full", {})
    if not isinstance(full, dict):
        raise ValueError("full must be a mapping")
    modules = full.get("modules", {})
    if not isinstance(modules, dict):
        raise ValueError("full.modules must be a mapping")
    full_modules: dict[str, bool] = {}
    for name in FULL_MODULES:
        value = modules.get(name, False)
        if not isinstance(value, bool):
            raise ValueError(f"full.modules.{name} must be a boolean")
        full_modules[name] = value
    condition = _condition(data.get("condition", data.get("profile", "c2")))
    if profile == "lite" and any(full_modules.values()):
        raise ValueError("Lite profile cannot enable Full modules")
    if profile == "full" and condition != "c3":
        raise ValueError("Full profile requires condition C3")
    return Settings(
        root=root,
        condition=condition,
        run_id=_run_id(data.get("run_id", "local")),
        tokenizer_encoding=str(data.get("tokenizer_encoding", "cl100k_base")),
        default_budget_tokens=int(data.get("default_budget_tokens", 2000)),
        minimum_successful_episodes=int(verification.get("minimum_successful_episodes", 2)),
        minimum_verifier_score=float(verification.get("minimum_verifier_score", 1.0)),
        wiki_prompt_references=tuple(Path(str(item)) for item in references),
        fairness={str(key): value for key, value in fairness.items()},
        profile=profile,
        full_modules=full_modules,
        full=full,
    )
