from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_yaml(path: Path, default: Any) -> Any:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return default
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return default if loaded is None else loaded


def write_yaml(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def render_markdown(front_matter: dict[str, Any], body: str = "") -> str:
    metadata = yaml.safe_dump(front_matter, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{metadata}\n---\n\n{body.rstrip()}\n"


def read_markdown(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path} has no YAML front matter")
    _, metadata, body = text.split("---\n", 2)
    parsed = yaml.safe_load(metadata)
    if not isinstance(parsed, dict):
        raise ValueError(f"{path} front matter is not a mapping")
    return parsed, body.lstrip("\n")


def word_set(value: str) -> set[str]:
    return {word.casefold() for word in re.findall(r"[^\W_]+", value, flags=re.UNICODE)}


def slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    return result or "skill"
