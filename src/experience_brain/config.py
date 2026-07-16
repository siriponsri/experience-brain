from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .util import read_yaml


@dataclass(frozen=True)
class Settings:
    root: Path
    tokenizer_encoding: str
    default_budget_tokens: int
    minimum_successful_episodes: int
    minimum_verifier_score: float


def load_settings(root: Path) -> Settings:
    data = read_yaml(root / "brain.yaml", {})
    verification = data.get("verification", {})
    return Settings(
        root=root,
        tokenizer_encoding=str(data.get("tokenizer_encoding", "cl100k_base")),
        default_budget_tokens=int(data.get("default_budget_tokens", 2000)),
        minimum_successful_episodes=int(verification.get("minimum_successful_episodes", 2)),
        minimum_verifier_score=float(verification.get("minimum_verifier_score", 1.0)),
    )
