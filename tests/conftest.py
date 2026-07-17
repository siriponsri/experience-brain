from __future__ import annotations

from pathlib import Path

import pytest

from experience_brain.store import ensure_store


@pytest.fixture()
def brain_root(tmp_path: Path) -> Path:
    ensure_store(tmp_path)
    return tmp_path
