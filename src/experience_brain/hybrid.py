"""Feature-gated, rebuildable hybrid retrieval for the Full profile."""

from __future__ import annotations

import json
import math
import subprocess
import time
from pathlib import Path
from typing import Any

from .config import Settings
from .util import canonical_json, read_markdown, read_yaml, sha256_text, write_yaml

INDEX_VERSION = 1


class GpuApprovalRequired(ValueError):
    """The configured embedder needs an Owner-approved GPU runtime."""


def _hash_file(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _index_path(settings: Settings) -> Path:
    return settings.root / ".indexes" / "hybrid" / "index.json"


def _embedder(settings: Settings) -> dict[str, Any]:
    hybrid = settings.full.get("hybrid", {})
    if not isinstance(hybrid, dict):
        raise ValueError("full.hybrid must be a mapping")
    embedder = hybrid.get("embedder", {})
    if not isinstance(embedder, dict):
        raise ValueError("full.hybrid.embedder must be a mapping")
    command = embedder.get("command")
    if (
        not isinstance(command, list)
        or not command
        or not all(isinstance(item, str) for item in command)
    ):
        raise ValueError("full.hybrid.embedder.command must be a non-empty string list")
    fingerprint = embedder.get("fingerprint")
    dimensions = embedder.get("dimensions")
    if not isinstance(fingerprint, str) or not fingerprint:
        raise ValueError("full.hybrid.embedder.fingerprint is required")
    if not isinstance(dimensions, int) or dimensions <= 0:
        raise ValueError("full.hybrid.embedder.dimensions must be positive")
    if not isinstance(embedder.get("requires_gpu", False), bool):
        raise ValueError("full.hybrid.embedder.requires_gpu must be a boolean")
    return embedder


def _gpu_request(settings: Settings, embedder: dict[str, Any]) -> Path:
    request = {
        "schema_version": 1,
        "status": "owner_decision_required",
        "module": "hybrid_retrieval",
        "runtime_fingerprint": embedder["fingerprint"],
        "command": embedder["command"],
        "cuda": embedder.get("cuda", "unspecified"),
        "minimum_vram_gb": embedder.get("minimum_vram_gb", "unspecified"),
        "storage_gb": embedder.get("storage_gb", "unspecified"),
        "estimated_runtime_minutes": embedder.get("estimated_runtime_minutes", "unspecified"),
        "estimated_cost": embedder.get("estimated_cost", "unspecified"),
        "artifact_transfer": "BENCHMARK_HOME only; no benchmark content in repository",
    }
    path = settings.root / "evaluations" / "gpu-requests" / "hybrid-retrieval.yaml"
    write_yaml(path, request)
    return path


def _ensure_runtime(settings: Settings) -> dict[str, Any]:
    if settings.profile != "full" or not settings.full_modules["hybrid_retrieval"]:
        raise ValueError("hybrid retrieval is not enabled")
    embedder = _embedder(settings)
    if embedder.get("requires_gpu", False):
        request = _gpu_request(settings, embedder)
        raise GpuApprovalRequired(f"GPU approval required; owner spec written to {request}")
    return embedder


def _embed(settings: Settings, text: str, purpose: str) -> tuple[list[float], dict[str, Any]]:
    embedder = _ensure_runtime(settings)
    started = time.monotonic()
    try:
        result = subprocess.run(
            list(embedder["command"]),
            input=canonical_json({"text": text, "purpose": purpose}) + "\n",
            capture_output=True,
            check=False,
            encoding="utf-8",
            timeout=int(embedder.get("timeout_seconds", 60)),
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"embedder unavailable: {error}") from error
    if result.returncode != 0:
        raise ValueError(f"embedder unavailable: exit {result.returncode}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ValueError("embedder stdout must be a JSON object") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("embedding"), list):
        raise ValueError("embedder result needs embedding")
    vector = payload["embedding"]
    if len(vector) != int(embedder["dimensions"]) or not all(
        isinstance(value, (int, float)) and math.isfinite(float(value)) for value in vector
    ):
        raise ValueError("embedder returned invalid dimensions or values")
    telemetry = {
        "latency_seconds": round(time.monotonic() - started, 6),
        "input_tokens": _non_negative(payload.get("input_tokens", 0), "embedder input_tokens"),
        "output_tokens": _non_negative(payload.get("output_tokens", 0), "embedder output_tokens"),
        "runtime_fingerprint": embedder["fingerprint"],
    }
    return [float(value) for value in vector], telemetry


def _non_negative(value: object, label: str) -> int:
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _verified_skills(root: Path) -> list[dict[str, Any]]:
    index = read_yaml(root / "memory" / "skills" / "index.yaml", {"skills": {}})
    if not isinstance(index, dict) or not isinstance(index.get("skills", {}), dict):
        raise ValueError("skills index must be a mapping")
    result: list[dict[str, Any]] = []
    for skill_id, entry in sorted(index["skills"].items()):
        if not isinstance(entry, dict) or entry.get("status") != "verified":
            continue
        path = root / str(entry.get("path", ""))
        if not path.is_file():
            raise ValueError(f"verified skill {skill_id} has no canonical file")
        metadata, body = read_markdown(path)
        result.append(
            {
                "id": str(skill_id),
                "path": str(entry["path"]),
                "source_sha256": _hash_file(path),
                "text": canonical_json(metadata) + "\n" + body,
            }
        )
    return result


def rebuild_hybrid_index(settings: Settings) -> dict[str, Any]:
    """Build the generated dense index exclusively from verified skill files."""
    embedder = _ensure_runtime(settings)
    sources = _verified_skills(settings.root)
    rows: list[dict[str, Any]] = []
    build_latency = 0.0
    input_tokens = 0
    output_tokens = 0
    for source in sources:
        vector, telemetry = _embed(settings, source["text"], "index")
        rows.append(
            {key: source[key] for key in ("id", "path", "source_sha256")} | {"embedding": vector}
        )
        build_latency += float(telemetry["latency_seconds"])
        input_tokens += int(telemetry["input_tokens"])
        output_tokens += int(telemetry["output_tokens"])
    payload = {
        "schema_version": INDEX_VERSION,
        "module": "hybrid_retrieval",
        "embedder_fingerprint": embedder["fingerprint"],
        "dimensions": embedder["dimensions"],
        "sources": rows,
        "source_set_sha256": sha256_text(canonical_json(rows)),
    }
    payload["index_sha256"] = sha256_text(canonical_json(payload))
    path = _index_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(payload) + "\n", encoding="utf-8")
    return payload | {
        "path": str(path),
        "storage_bytes": path.stat().st_size,
        "build": {
            "latency_seconds": round(build_latency, 6),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    }


def load_hybrid_index(settings: Settings) -> dict[str, Any]:
    embedder = _ensure_runtime(settings)
    path = _index_path(settings)
    if not path.is_file():
        raise ValueError(
            "hybrid index is missing; run brain index rebuild --module hybrid_retrieval"
        )
    try:
        index = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("hybrid index is invalid JSON") from error
    if not isinstance(index, dict) or index.get("module") != "hybrid_retrieval":
        raise ValueError("hybrid index has invalid schema")
    if index.get("embedder_fingerprint") != embedder["fingerprint"]:
        raise ValueError("hybrid index runtime fingerprint mismatch")
    if index.get("dimensions") != embedder["dimensions"]:
        raise ValueError("hybrid index dimensions mismatch")
    expected_hash = sha256_text(
        canonical_json({key: value for key, value in index.items() if key != "index_sha256"})
    )
    if index.get("index_sha256") != expected_hash:
        raise ValueError("hybrid index integrity hash mismatch")
    current = {(row["id"], row["source_sha256"]) for row in _verified_skills(settings.root)}
    indexed = {
        (str(row.get("id")), str(row.get("source_sha256")))
        for row in index.get("sources", [])
        if isinstance(row, dict)
    }
    if current != indexed:
        raise ValueError("hybrid index is stale; rebuild from canonical skills")
    return index


def verify_hybrid_index(settings: Settings) -> dict[str, Any]:
    index = load_hybrid_index(settings)
    path = _index_path(settings)
    return {
        "module": "hybrid_retrieval",
        "index_sha256": index["index_sha256"],
        "sources": len(index["sources"]),
        "storage_bytes": path.stat().st_size,
        "status": "valid",
    }


def _cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    denominator = math.sqrt(sum(a * a for a in left) * sum(b * b for b in right))
    return numerator / denominator if denominator else 0.0


def hybrid_scores(
    settings: Settings, task_text: str, lexical: list[dict[str, Any]], limit: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index = load_hybrid_index(settings)
    query, telemetry = _embed(settings, task_text, "query")
    dense = {
        str(row["id"]): _cosine(query, [float(value) for value in row["embedding"]])
        for row in index["sources"]
    }
    lexical_rank = {str(item["id"]): number for number, item in enumerate(lexical, start=1)}
    dense_rank = {
        skill_id: number
        for number, (skill_id, _) in enumerate(
            sorted(dense.items(), key=lambda item: (-item[1], item[0])), start=1
        )
    }
    combined: list[dict[str, Any]] = []
    for item in lexical:
        skill_id = str(item["id"])
        score = 1 / (60 + lexical_rank[skill_id]) + 1 / (60 + dense_rank[skill_id])
        combined.append(
            dict(item)
            | {
                "score": round(score, 8),
                "lexical_score": item["score"],
                "dense_score": round(dense[skill_id], 8),
                "retrieval_policy_version": "full-hybrid-rrf-v1",
            }
        )
    combined.sort(key=lambda item: (-float(item["score"]), str(item["id"])))
    return combined[:limit], telemetry | {
        "index_sha256": index["index_sha256"],
        "index_storage_bytes": _index_path(settings).stat().st_size,
        "policy": "full-hybrid-rrf-v1",
    }
