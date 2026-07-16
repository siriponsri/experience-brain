from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def brain_root(tmp_path: Path) -> Path:
    for relative in [
        "events",
        "memory/episodes",
        "memory/skills",
        "memory",
        "sources/converted",
        "capsules",
        "reports",
    ]:
        (tmp_path / relative).mkdir(parents=True, exist_ok=True)
    (tmp_path / "brain.yaml").write_text(
        "tokenizer_encoding: cl100k_base\n"
        "verification:\n"
        "  minimum_successful_episodes: 2\n"
        "  minimum_verifier_score: 1.0\n",
        encoding="utf-8",
    )
    (tmp_path / "events" / "events.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "memory" / "skills" / "index.yaml").write_text("skills: {}\n", encoding="utf-8")
    (tmp_path / "memory" / "review_queue.yaml").write_text("items: []\n", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def fixtures() -> Path:
    return Path(__file__).parent / "fixtures" / "synthetic"
