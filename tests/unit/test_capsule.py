from __future__ import annotations

from pathlib import Path

import pytest

from experience_brain.capsule import build_capsule
from experience_brain.config import load_settings


def test_capsule_rejects_oversized_mandatory_contract(brain_root: Path) -> None:
    task = brain_root / "large.yaml"
    task.write_text("id: large\ngoal: " + "word " * 2000 + "\nconstraints: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="exceed"):
        build_capsule(load_settings(brain_root), task, 10)
    assert list((brain_root / "capsules").glob("*.md")) == []
