from __future__ import annotations

import re
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

from experience_brain import __version__
from experience_brain.models import SCHEMA_VERSION

MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REPO_ROOT = Path(__file__).resolve().parents[1]


def test_public_versions_are_consistent() -> None:
    payload = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert payload["project"]["version"] == "0.3.1"
    assert __version__ == "0.3.1"
    assert SCHEMA_VERSION == "v0.3.1"


def test_public_markdown_local_links_exist() -> None:
    documents = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "CONTRIBUTING.md",
        REPO_ROOT / "SECURITY.md",
        REPO_ROOT / "CHANGELOG.md",
        *sorted((REPO_ROOT / "docs").glob("*.md")),
    ]
    missing: list[str] = []
    for document in documents:
        text = document.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(text):
            target = match.group(1).strip().strip("<>").split("#", maxsplit=1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (document.parent / target).resolve()
            if not resolved.exists():
                missing.append(f"{document.relative_to(REPO_ROOT)} -> {target}")
    assert missing == []


def test_original_svg_assets_are_self_contained() -> None:
    expected = {
        "architecture.svg",
        "benchmark-conditions.svg",
        "cross-session-lifecycle.svg",
        "experience-brain-logo.svg",
        "knowledge-vs-experience.svg",
    }
    assets = REPO_ROOT / "docs" / "assets"
    assert expected.issubset({path.name for path in assets.glob("*.svg")})
    for name in expected:
        root = ET.parse(assets / name).getroot()
        assert root.tag.endswith("svg")
        assert any(child.tag.endswith("title") for child in root)
        assert any(child.tag.endswith("desc") for child in root)
        text = (assets / name).read_text(encoding="utf-8")
        assert "http://www.w3.org/2000/svg" in text
        assert "href=" not in text


def test_citation_metadata_has_required_public_fields() -> None:
    citation = (REPO_ROOT / "CITATION.cff").read_text(encoding="utf-8")
    for field in (
        "cff-version: 1.2.0",
        'title: "Experience Brain"',
        'repository-code: "https://github.com/siriponsri/experience-brain"',
        "license: Apache-2.0",
        "version: 0.3.1",
    ):
        assert field in citation
