"""PI-gated Full module lifecycle and module-pilot preflight."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .benchmark.core import load_manifest
from .config import FULL_MODULES
from .util import canonical_json, read_yaml, sha256_text, write_yaml

MODULE_ORDER = FULL_MODULES


def _hash_file(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _decision_directory(root: Path) -> Path:
    return root / "evaluations" / "module-decisions"


def _decision_hash(value: dict[str, Any]) -> str:
    return sha256_text(
        canonical_json({key: item for key, item in value.items() if key != "decision_hash"})
    )


def _decision_files(root: Path, module: str) -> list[Path]:
    return sorted(_decision_directory(root).glob(f"{module}-v*.yaml"))


def latest_decision(root: Path, module: str) -> dict[str, Any] | None:
    if module not in MODULE_ORDER:
        raise ValueError(f"unknown Full module: {module}")
    files = _decision_files(root, module)
    if not files:
        return None
    value = read_yaml(files[-1], {})
    if not isinstance(value, dict) or value.get("module") != module:
        raise ValueError(f"invalid decision artifact for {module}")
    if value.get("decision") not in {"keep", "remove"}:
        raise ValueError(f"invalid decision value for {module}")
    if value.get("decision_hash") != _decision_hash(value):
        raise ValueError(f"decision hash mismatch for {module}")
    return value


def check_gate(root: Path, next_module: str) -> dict[str, Any]:
    if next_module not in MODULE_ORDER:
        raise ValueError(f"unknown Full module: {next_module}")
    position = MODULE_ORDER.index(next_module)
    required = MODULE_ORDER[:position]
    decisions = {module: latest_decision(root, module) for module in required}
    missing = [module for module, value in decisions.items() if value is None]
    if missing:
        raise ValueError(f"PI decision required before {next_module}: {', '.join(missing)}")
    return {
        "next_module": next_module,
        "status": "open",
        "previous_decisions": {
            module: str(value["decision"])
            for module, value in decisions.items()
            if value is not None
        },
    }


def record_decision(
    root: Path, module: str, decision: str, evidence: Path, approved_by: str
) -> Path:
    if module not in MODULE_ORDER:
        raise ValueError(f"unknown Full module: {module}")
    if decision not in {"keep", "remove"}:
        raise ValueError("decision must be keep or remove")
    if not approved_by.strip():
        raise ValueError("approved_by must be a non-empty role identifier")
    check_gate(root, module)
    evidence = evidence.resolve()
    if not evidence.is_dir():
        raise ValueError("evidence must be an analysis directory")
    required = ("analysis_provenance.json", "gain_cost_memo.md")
    absent = [name for name in required if not (evidence / name).is_file()]
    if absent:
        raise ValueError(f"evidence is incomplete: {', '.join(absent)}")
    version = len(_decision_files(root, module)) + 1
    prior = latest_decision(root, module)
    artifact: dict[str, Any] = {
        "schema_version": 1,
        "module": module,
        "version": version,
        "decision": decision,
        "approved_by": approved_by,
        "approved_at": datetime.now(UTC).isoformat(),
        "evidence": {
            "directory": str(evidence),
            "analysis_provenance_sha256": _hash_file(evidence / "analysis_provenance.json"),
            "gain_cost_memo_sha256": _hash_file(evidence / "gain_cost_memo.md"),
        },
        "supersedes": prior.get("decision_hash") if prior else None,
    }
    artifact["decision_hash"] = _decision_hash(artifact)
    path = _decision_directory(root) / f"{module}-v{version}.yaml"
    if path.exists():
        raise ValueError(f"decision artifact is immutable: {path.name}")
    write_yaml(path, artifact)
    return path


def module_pilot_preflight(
    root: Path, module: str, manifest_path: Path, ablation_config: Path
) -> dict[str, Any]:
    """Validate a frozen module-pilot request before a future C3 run runner."""
    check_gate(root, module)
    manifest, manifest_hash = load_manifest(manifest_path)
    final = root / "evaluations" / "manifests" / "final-v1.json"
    if manifest_path.resolve() == final.resolve():
        raise ValueError("module pilots must not use final-v1.json")
    if final.is_file() and _hash_file(manifest_path) == _hash_file(final):
        raise ValueError("module pilot manifest matches frozen final manifest")
    config = read_yaml(ablation_config, {})
    if not isinstance(config, dict):
        raise ValueError("ablation config must be a mapping")
    arms = config.get("arms")
    if not isinstance(arms, list) or not all(isinstance(arm, dict) for arm in arms):
        raise ValueError("ablation config must define arms")
    names = {str(arm.get("name", "")) for arm in arms}
    if "lite" not in names or "candidate" not in names:
        raise ValueError("ablation arms must include lite and candidate")
    if int(config.get("runs_per_arm", 0)) < 3:
        raise ValueError("module pilot requires at least three runs per arm")
    if config.get("module") != module:
        raise ValueError("ablation config module does not match requested module")
    return {
        "module": module,
        "manifest_id": manifest.get("manifest_id"),
        "manifest_hash": manifest_hash,
        "ablation_config_sha256": _hash_file(ablation_config),
        "status": "preflight_passed_execution_blocked_without_official_runs",
    }


def write_gain_cost_memo(analysis_dir: Path, module: str) -> Path:
    """Create a decision-ready memo from an analysis bundle without inventing results."""
    if module not in MODULE_ORDER:
        raise ValueError(f"unknown Full module: {module}")
    report_path = analysis_dir / "validation_report.json"
    provenance_path = analysis_dir / "analysis_provenance.json"
    if not report_path.is_file() or not provenance_path.is_file():
        raise ValueError(
            "analysis bundle requires validation_report.json and analysis_provenance.json"
        )
    report = read_yaml(report_path, {})
    if not isinstance(report, dict):
        raise ValueError("validation report must be a mapping")
    bootstrap = read_yaml(analysis_dir / "bootstrap_ci.json", {})
    if not isinstance(bootstrap, dict):
        bootstrap = {}
    status = "blocked_missing_data" if int(report.get("rows", 0)) == 0 else "review_required"
    document = "\n".join(
        [
            "# Gain/Cost Memo",
            "",
            f"Module: `{module}`",
            f"Status: **{status.upper()}**",
            f"Validation: `{report.get('status', 'unknown')}`",
            f"Rows: {report.get('rows', 0)}; paired units: {report.get('pairs', 0)}.",
            f"Token reduction CI: {bootstrap.get('token_reduction_ci', 'unknown')}",
            f"Success CI: {bootstrap.get('success_pp_ci', 'unknown')}",
            "",
            "Incremental foreground/background token, latency, index-build, query, and storage "
            "costs remain unknown until complete verifier-backed official module-pilot "
            "outcomes exist.",
            "",
            "PI must record keep or remove only after reviewing the frozen analysis bundle.",
        ]
    )
    path = analysis_dir / "gain_cost_memo.md"
    path.write_text(document + "\n", encoding="utf-8")
    return path
