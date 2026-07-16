from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .util import read_yaml, sha256_text, write_yaml


def ingest_source(root: Path, source_path: Path, metadata_path: Path) -> str:
    metadata = read_yaml(metadata_path, {})
    if not isinstance(metadata, dict):
        raise ValueError("source metadata must be a YAML mapping")
    text = source_path.read_text(encoding="utf-8")
    content_hash = sha256_text(text)
    source_id = str(metadata.get("source_id") or f"src_{content_hash[:12]}")
    destination = root / "sources" / "converted" / f"{source_id}.md"
    sidecar = destination.with_suffix(".yaml")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.read_text(encoding="utf-8") != text:
        raise ValueError(f"source id {source_id} already refers to different content")
    if not destination.exists():
        shutil.copyfile(source_path, destination)
    sidecar_data: dict[str, Any] = dict(metadata)
    sidecar_data.update(
        {
            "source_id": source_id,
            "converted_path": destination.relative_to(root).as_posix(),
            "converted_sha256": content_hash,
            "trust": "untrusted_external_content",
            "review_status": str(metadata.get("review_status", "pending")),
        }
    )
    write_yaml(sidecar, sidecar_data)
    return source_id
