"""Fail-closed, verifier-first analysis for frozen benchmark cohorts.

The analysis input is intentionally a *registry*, never a directory scan.  A
registry names every run that belongs to a planned comparison; the companion
configuration freezes hashes, runtime expectations, and bootstrap settings.
This makes it impossible for this module to silently select a convenient run.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import struct
import zlib
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any

from ..util import canonical_json, read_yaml, sha256_text
from .core import CONDITIONS, benchmark_home

ANALYSIS_VERSION = "analysis-v2"
_TOKEN_FIELDS = (
    "foreground_input_tokens",
    "foreground_output_tokens",
    "foreground_cache_tokens",
    "maintenance_input_tokens",
    "maintenance_output_tokens",
    "retrieval_tokens",
    "consolidation_tokens",
    "judge_tokens",
    "background_tokens",
)


def _json_lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(value) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical_json(row) + "\n" for row in rows), encoding="utf-8")


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row}) or ["status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in fields})


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return canonical_json(value)
    return "" if value is None else value


def _write_markdown_table(path: Path, rows: list[dict[str, Any]], title: str) -> None:
    fields = sorted({key for row in rows for key in row})
    lines = [f"# {title}", ""]
    if not fields:
        lines.append("No rows.")
    else:
        lines += ["| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
        for row in rows:
            lines.append(
                "| "
                + " | ".join(str(_csv_value(row.get(key))).replace("|", "\\|") for key in fields)
                + " |"
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _contract(path: Path) -> dict[str, Any]:
    """Read either legacy single-file contract or v2 analysis config."""
    value = read_yaml(path, {})
    if not isinstance(value, dict):
        raise ValueError("analysis config must be a mapping")
    required = ("analysis_id", "stage", "bootstrap", "decision")
    missing = [key for key in required if key not in value]
    if missing:
        raise ValueError(f"analysis config missing: {missing}")
    if value["stage"] not in {"pilot", "main-lite"}:
        raise ValueError("analysis stage must be pilot or main-lite")
    if not isinstance(value["bootstrap"], dict) or not isinstance(value["decision"], dict):
        raise ValueError("analysis bootstrap and decision must be mappings")
    if "runs" in value and (not isinstance(value["runs"], list) or not value["runs"]):
        raise ValueError("analysis contract must enumerate runs")
    return value


def _registry(path: Path, config: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    value = read_yaml(path, {})
    if isinstance(value, list):
        value = {"runs": value}
    if not isinstance(value, dict):
        raise ValueError("frozen run registry must be a mapping")
    runs = value.get("runs", config.get("runs"))
    if not isinstance(runs, list) or not runs:
        raise ValueError("frozen run registry must enumerate runs")
    return value, runs


def _artifact_ok(root: Path, ref: object) -> bool:
    if not isinstance(ref, dict) or not isinstance(ref.get("relative_path"), str):
        return False
    try:
        home = benchmark_home(root)
    except ValueError:
        return False
    path = (home / str(ref["relative_path"])).resolve()
    return (
        path.is_file()
        and path.is_relative_to(home)
        and _hash_file(path) == ref.get("sha256")
        and ("size" not in ref or path.stat().st_size == ref.get("size"))
    )


def _artifact_details(root: Path, ref: object, kind: str) -> tuple[bool, dict[str, Any]]:
    if not isinstance(ref, dict):
        return False, {"kind": kind, "relative_path": None, "status": "missing"}
    details = {
        "kind": kind,
        "relative_path": ref.get("relative_path"),
        "sha256": ref.get("sha256"),
        "size": ref.get("size"),
    }
    return _artifact_ok(root, ref), details | {
        "status": "valid" if _artifact_ok(root, ref) else "invalid"
    }


def _taxonomy(outcome: dict[str, Any]) -> tuple[str, str]:
    """Classify verifier and harness signatures without agent self-report."""
    failure = outcome.get("infrastructure_failure")
    if isinstance(failure, dict):
        category = str(failure.get("category", "unknown")).casefold()
        if "verifier" in category:
            return "infrastructure", "verifier"
        if any(word in category for word in ("agent", "model", "service")):
            return "infrastructure", "model_or_service"
        if any(word in category for word in ("docker", "container")):
            return "infrastructure", "docker_or_container"
        if any(word in category for word in ("worker", "harness")):
            return "infrastructure", "worker_or_harness"
        if any(word in category for word in ("artifact", "telemetry")):
            return "infrastructure", "artifact_or_telemetry"
        if "memory" in category:
            return "infrastructure", "memory_protocol"
        return "infrastructure", category
    signature = str(outcome.get("failure_signature") or "").casefold()
    stop = str(outcome.get("stop_reason") or "").casefold()
    text = f"{signature} {stop}".strip()
    if outcome.get("contamination") or outcome.get("leakage"):
        return "contamination", "leakage_or_solution_marker"
    if not text:
        return "task", "passed" if outcome.get("success") is True else "unknown_unclassified"
    if "depend" in text or "build" in text or "compile" in text:
        return "task", "dependency_or_build"
    if "timeout" in text or "budget" in text or "token" in text:
        return "task", "time_or_token_stop"
    if "tool" in text:
        return "task", "tool_misuse"
    if "state" in text or "output" in text:
        return "task", "wrong_state_or_output"
    if "assert" in text or "test" in text or "verif" in text:
        return "task", "verifier_requirement_unmet"
    if "retriev" in text:
        return "task", "retrieval_omission"
    return "task", "unknown_unclassified"


def _total_tokens(outcome: dict[str, Any]) -> int:
    """Compute known total, rejecting an absent mandatory foreground component."""
    for field in (
        "foreground_input_tokens",
        "foreground_output_tokens",
        "foreground_cache_tokens",
    ):
        value = outcome.get(field)
        if value is None and field == "foreground_cache_tokens":
            continue
        if not isinstance(value, int) or value < 0:
            raise ValueError("missing or negative token field")
    foreground = sum(int(outcome.get(field, 0) or 0) for field in _TOKEN_FIELDS[:3])
    breakdown = outcome.get("token_breakdown")
    background = outcome.get("background_tokens")
    if background is not None:
        if not isinstance(background, int) or background < 0:
            raise ValueError("missing or negative token field")
        # Harness background tokens are aggregate; breakdown entries must not
        # be added a second time.
        return foreground + background
    detailed = 0
    available = False
    aliases = {
        "maintenance_input_tokens": "maintenance_input",
        "maintenance_output_tokens": "maintenance_output",
    }
    for field in _TOKEN_FIELDS[3:-1]:
        value = outcome.get(field)
        if value is None and isinstance(breakdown, dict):
            value = breakdown.get(aliases.get(field, field))
        if value is None:
            continue
        if not isinstance(value, int) or value < 0:
            raise ValueError("missing or negative token field")
        available = True
        detailed += value
    if not available:
        raise ValueError("missing or negative token field")
    return foreground + detailed


def _token_status(outcome: dict[str, Any]) -> str:
    optional = _TOKEN_FIELDS[2:]
    if any(outcome.get(field) is not None for field in optional):
        return "complete"
    breakdown = outcome.get("token_breakdown")
    return "complete" if isinstance(breakdown, dict) and breakdown else "lower_bound"


def _is_deployment(outcome: dict[str, Any]) -> bool:
    if outcome.get("benchmark") != "skillevolbench":
        return False
    selector = outcome.get("selector", {})
    role = selector.get("role") if isinstance(selector, dict) else None
    return outcome.get("split") == "deployment" or role in {"T4", "T5", "T6"}


def _percentile(values: list[float]) -> list[float] | None:
    if not values:
        return None
    ordered = sorted(values)
    return [ordered[int(0.025 * (len(ordered) - 1))], ordered[int(0.975 * (len(ordered) - 1))]]


def _iqr(values: list[float]) -> list[float] | None:
    if not values:
        return None
    ordered = sorted(values)
    return [ordered[len(ordered) // 4], ordered[(3 * len(ordered)) // 4]]


def _bootstrap(pairs: list[dict[str, Any]], repetitions: int, seed: int) -> dict[str, Any]:
    if not pairs:
        return {
            "replicates": 0,
            "success_pp_ci": None,
            "token_reduction_ci": None,
            "zero_success_replicates": 0,
        }
    blocks: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pair in pairs:
        blocks[str(pair["block_id"])].append(pair)
    names = sorted(blocks)
    rng = random.Random(seed)
    success_effects: list[float] = []
    token_reductions: list[float] = []
    repeated_differences: list[float] = []
    missing_tokens = 0
    for _ in range(repetitions):
        sampled: list[dict[str, Any]] = []
        for _ in names:
            family = blocks[rng.choice(names)]
            sampled.extend(rng.choice(family) for _ in family)
        c0_success, c2_success = (
            sum(x["c0_success"] for x in sampled),
            sum(x["c2_success"] for x in sampled),
        )
        success_effects.append(100 * (c2_success - c0_success) / len(sampled))
        c0_fail = sum(x.get("c0_repeated_failure", 0) for x in sampled)
        c2_fail = sum(x.get("c2_repeated_failure", 0) for x in sampled)
        repeated_differences.append(100 * (c2_fail - c0_fail) / len(sampled))
        c0_tokens, c2_tokens = (
            sum(x["c0_tokens"] for x in sampled),
            sum(x["c2_tokens"] for x in sampled),
        )
        if c0_success == 0 or c2_success == 0:
            missing_tokens += 1
        else:
            token_reductions.append(
                100 * (c0_tokens / c0_success - c2_tokens / c2_success) / (c0_tokens / c0_success)
            )
    return {
        "replicates": repetitions,
        "seed": seed,
        "success_pp_ci": _percentile(success_effects),
        "token_reduction_ci": _percentile(token_reductions),
        "repeated_failure_pp_ci": _percentile(repeated_differences),
        "success_pp_median": median(success_effects),
        "success_pp_iqr": _iqr(success_effects),
        "token_reduction_median": median(token_reductions) if token_reductions else None,
        "token_reduction_iqr": _iqr(token_reductions),
        "computed_token_replicates": len(token_reductions),
        "zero_success_replicates": missing_tokens,
        "missing_token_replicate_fraction": missing_tokens / repetitions,
    }


def _descriptor(root: Path, run_id: str) -> dict[str, Any]:
    path = root / "evaluations" / "runs" / run_id / "run.json"
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"_invalid": True}
    return value if isinstance(value, dict) else {"_invalid": True}


def _expected(config: dict[str, Any], key: str) -> Any:
    frozen = config.get("frozen_inputs", {})
    return frozen.get(key, config.get(key)) if isinstance(frozen, dict) else config.get(key)


def _validate_row(
    row: dict[str, Any],
    config: dict[str, Any],
    run_id: str,
    errors: list[str],
    deviations: list[dict[str, Any]],
    artifact_rows: list[dict[str, Any]],
    root: Path,
) -> None:
    attempt = str(row.get("attempt_id", "unknown"))
    for key, expected in (
        ("manifest_hash", _expected(config, "manifest_hash")),
        ("benchmark_lock_hash", _expected(config, "lock_hash")),
        ("config_hash", _expected(config, "runtime_hash")),
    ):
        if expected and row.get(key) != expected:
            message = f"{run_id}/{attempt}: {key} mismatch"
            errors.append(message)
            deviations.append(
                {
                    "run_id": run_id,
                    "attempt_id": attempt,
                    "type": "hash_mismatch",
                    "detail": message,
                    "preregistered": True,
                }
            )
    verifier = row.get("verifier")
    ref = verifier.get("raw_stdout") if isinstance(verifier, dict) else None
    if ref is None and isinstance(verifier, dict):
        ref = verifier.get("raw_stdout_path")
    ok, details = _artifact_details(root, ref, "verifier")
    details |= {"run_id": run_id, "attempt_id": attempt}
    artifact_rows.append(details)
    if not ok:
        errors.append(f"{run_id}/{attempt}: missing or corrupt verifier artifact")
    # Agent/infrastructure artifacts are checked when the harness supplied refs.
    for key in ("agent", "infrastructure"):
        ref = row.get("artifacts", {}).get(key) if isinstance(row.get("artifacts"), dict) else None
        if ref is not None:
            ok, details = _artifact_details(root, ref, key)
            artifact_rows.append(details | {"run_id": run_id, "attempt_id": attempt})
            if not ok:
                errors.append(f"{run_id}/{attempt}: missing or corrupt {key} artifact")
    if row.get("attempt_status") != "infrastructure_failure" and not isinstance(
        row.get("success"), bool
    ):
        errors.append(f"{run_id}/{attempt}: verifier-only success is unavailable")
    if row.get("attempt_status") == "infrastructure_failure" and row.get("success") is not None:
        errors.append(f"{run_id}/{attempt}: infrastructure failure has task success")
    try:
        _total_tokens(row)
    except ValueError as error:
        errors.append(f"{run_id}/{attempt}: {error}")
    if (
        not isinstance(row.get("wall_seconds", 0), (int, float))
        or float(row.get("wall_seconds", 0)) < 0
    ):
        errors.append(f"{run_id}/{attempt}: invalid latency")
    strict = int(config.get("schema_version", 1)) >= 2 or "frozen_inputs" in config
    if strict and (
        not isinstance(row.get("budget", {}), dict)
        or row.get("stop_reason") is not None
        and not row.get("budget")
    ):
        errors.append(f"{run_id}/{attempt}: missing budget/stop provenance")


def _effect_rows(pairs: list[dict[str, Any]], bootstrap: dict[str, Any]) -> list[dict[str, Any]]:
    if not pairs:
        return []
    c0_success = sum(x["c0_success"] for x in pairs)
    c2_success = sum(x["c2_success"] for x in pairs)
    c0_tps = sum(x["c0_tokens"] for x in pairs) / c0_success if c0_success else None
    c2_tps = sum(x["c2_tokens"] for x in pairs) / c2_success if c2_success else None
    reduction = 100 * (c0_tps - c2_tps) / c0_tps if c0_tps and c2_tps is not None else None
    rows = [
        {
            "comparison": "C2-C0",
            "metric": "deployment_success_pp",
            "point_estimate": 100 * (c2_success - c0_success) / len(pairs),
            "ci_95": bootstrap.get("success_pp_ci"),
        },
        {
            "comparison": "C2-C0",
            "metric": "tokens_per_success_reduction_percent",
            "point_estimate": reduction,
            "ci_95": bootstrap.get("token_reduction_ci"),
        },
        {
            "comparison": "C2-C0",
            "metric": "repeated_failure_pp",
            "point_estimate": 100
            * (sum(x["c2_repeated_failure"] - x["c0_repeated_failure"] for x in pairs))
            / len(pairs),
            "ci_95": bootstrap.get("repeated_failure_pp_ci"),
        },
    ]
    for condition in ("c1",):
        if all(f"{condition}_success" in pair for pair in pairs):
            rows.append(
                {
                    "comparison": "C1-C0",
                    "metric": "deployment_success_pp",
                    "point_estimate": 100
                    * sum(x[f"{condition}_success"] - x["c0_success"] for x in pairs)
                    / len(pairs),
                    "ci_95": None,
                }
            )
    return rows


def _mde(pairs: list[dict[str, Any]]) -> dict[str, Any]:
    differences = [100 * (x["c2_success"] - x["c0_success"]) for x in pairs]
    if len(differences) < 2:
        return {"observed_paired_variance": None, "mde_95_percent_pp": None}
    mean = sum(differences) / len(differences)
    variance = sum((x - mean) ** 2 for x in differences) / (len(differences) - 1)
    return {
        "observed_paired_variance": variance,
        "mde_95_percent_pp": 1.96 * math.sqrt(variance / len(differences)),
    }


def _svg(path: Path, title: str, rows: list[dict[str, Any]], provenance: str) -> None:
    labels = [str(r.get("condition", r.get("metric", "row"))) for r in rows] or ["no data"]
    values = [float(r.get("total_tokens", r.get("point_estimate", 0)) or 0) for r in rows] or [0]
    maximum = max(max(values), 1.0)
    bars: list[str] = []
    for i, (label, value) in enumerate(zip(labels, values)):
        x = 30 + i * 80
        height = int(120 * value / maximum)
        bars.append(
            f'<rect x="{x}" y="{170 - height}" width="45" height="{height}" fill="#377eb8"/>'
        )
        bars.append(f'<text x="{x}" y="190" font-size="10">{label}</text>')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="220">'
        f"<metadata>{provenance}</metadata>"
        f'<text x="20" y="25" font-size="16">{title}</text>' + "".join(bars) + "</svg>\n",
        encoding="utf-8",
    )


def _png(path: Path, color: tuple[int, int, int]) -> None:
    """Write a deterministic minimal provenance companion raster (1x1 PNG)."""
    raw = b"\x00" + bytes(color)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    data = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(data)


def _figures(
    output: Path,
    normalized: Path,
    effects: list[dict[str, Any]],
    taxonomy: list[dict[str, Any]],
    provenance: str,
) -> None:
    rows = _json_lines(normalized)
    by_condition: dict[str, dict[str, Any]] = {}
    for condition in CONDITIONS:
        group = [x for x in rows if x.get("condition") == condition]
        by_condition[condition] = {
            "condition": condition,
            "total_tokens": sum(int(x.get("total_tokens", 0)) for x in group),
            "foreground_tokens": sum(
                int(x.get("foreground_input_tokens", 0)) + int(x.get("foreground_output_tokens", 0))
                for x in group
            ),
            "background_tokens": sum(int(x.get("background_tokens", 0)) for x in group),
        }
    charts = {
        "paired_effects": ("Paired effects (95% CI in table)", effects),
        "tokens_by_condition": (
            "Foreground and background token totals",
            list(by_condition.values()),
        ),
        "failure_taxonomy": ("Failure taxonomy distribution", taxonomy),
        "per_run_outcomes": ("Per-run paired outcomes", rows),
    }
    for name, (title, data) in charts.items():
        _svg(output / "figures" / f"{name}.svg", title, data, provenance)
        _png(output / "figures" / f"{name}.png", (55, 126, 184))


def _decision(
    stage: str,
    rows: list[dict[str, Any]],
    errors: list[str],
    pairs: list[dict[str, Any]],
    bootstrap: dict[str, Any],
    threshold: float,
) -> str:
    if not rows:
        return "blocked_missing_data"
    if stage == "pilot":
        return "redesign"
    if errors or not pairs:
        return "redesign"
    token_ci = bootstrap.get("token_reduction_ci")
    success_ci = bootstrap.get("success_pp_ci")
    repeat_ci = bootstrap.get("repeated_failure_pp_ci")
    if bootstrap.get("missing_token_replicate_fraction", 1) > 0.05:
        return "redesign"
    non_inferior = bool(success_ci and float(success_ci[0]) >= -2.0)
    token_go = bool(token_ci and float(token_ci[0]) >= threshold)
    repeated_point = (
        100 * sum(x["c0_repeated_failure"] - x["c2_repeated_failure"] for x in pairs) / len(pairs)
    )
    repeated_go = bool(repeat_ci and repeated_point >= 15 and float(repeat_ci[1]) < 0)
    if non_inferior and (token_go or repeated_go):
        return "go"
    if not non_inferior:
        return "stop"
    return "redesign"


def analyze(
    root: Path, contract_path: Path, output: Path, registry_path: Path | None = None
) -> Path:
    """Validate all frozen registry entries and produce a reproducible bundle."""
    config = _contract(contract_path)
    registry, registry_runs = _registry(registry_path or contract_path, config)
    output.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    deviations: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    seen_runs: set[str] = set()
    stage_runs: Counter[str] = Counter()
    for item in registry_runs:
        if not isinstance(item, dict) or not isinstance(item.get("run_id"), str):
            errors.append("registry contains invalid run entry")
            continue
        run_id = str(item["run_id"])
        if run_id in seen_runs:
            errors.append(f"duplicate preregistered run: {run_id}")
            continue
        seen_runs.add(run_id)
        descriptor = _descriptor(root, run_id)
        if descriptor.get("_invalid"):
            errors.append(f"invalid run descriptor: {run_id}")
        if descriptor and descriptor.get("stage") != config["stage"]:
            errors.append(f"{run_id}: run stage does not match frozen analysis stage")
        path = root / "evaluations" / "runs" / run_id / "outcomes.jsonl"
        if not path.is_file():
            errors.append(f"missing preregistered run: {run_id}")
            continue
        source_hash = _hash_file(path)
        attempts: set[str] = set()
        for outcome in _json_lines(path):
            attempt = str(outcome.get("attempt_id", ""))
            if not attempt or attempt in attempts:
                errors.append(f"{run_id}: duplicate or missing attempt id")
                continue
            attempts.add(attempt)
            _validate_row(outcome, config, run_id, errors, deviations, artifacts, root)
            try:
                total = _total_tokens(outcome)
            except ValueError:
                total = 0
            category, label = _taxonomy(outcome)
            enriched = dict(outcome) | {
                "block_id": str(item.get("block_id", run_id)),
                "source_run_id": run_id,
                "source_sha256": source_hash,
                "total_tokens": total,
                "token_accounting": _token_status(outcome),
                "failure_class": category,
                "failure_taxon": label,
                "taxonomy_mapping_version": "v1",
                "failure_reason": str(
                    outcome.get("failure_signature") or outcome.get("stop_reason") or ""
                ),
            }
            rows.append(enriched)
            stage_runs[str(outcome.get("condition"))] += 1
    # Runtime/endpoint mismatch is a confirmatory-analysis stopping deviation.
    fingerprints = sorted(
        {
            canonical_json(
                {
                    key: row.get(key)
                    for key in (
                        "model",
                        "reasoning",
                        "config_hash",
                        "endpoint_fingerprint",
                        "tools",
                    )
                }
            )
            for row in rows
        }
    )
    if len(fingerprints) > 1:
        errors.append("runtime/endpoint fingerprint differs across frozen runs")
        deviations.append(
            {
                "run_id": "*",
                "attempt_id": "*",
                "type": "runtime_endpoint_mismatch",
                "detail": "confirmatory analysis stopped",
                "preregistered": True,
            }
        )
    if config["stage"] == "main-lite":
        run_conditions = Counter(
            str(item.get("condition", item.get("run_id", "").split("-", 1)[0]))
            for item in registry_runs
        )
        for condition in CONDITIONS:
            if run_conditions[condition] < 3:
                errors.append(
                    f"main-lite requires at least three preregistered runs for {condition}"
                )
    # one accepted primary terminal attempt per block/task/condition
    cells: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if _is_deployment(row) and row.get("attempt_status") != "infrastructure_failure":
            cells[
                (str(row["block_id"]), str(row.get("task_id")), str(row.get("condition")))
            ].append(row)
    pairs: list[dict[str, Any]] = []
    keys = {(block, task) for block, task, _ in cells}
    for block, task in sorted(keys):
        cell: dict[str, dict[str, Any]] = {}
        for condition in CONDITIONS:
            values = cells.get((block, task, condition), [])
            if len(values) != 1:
                errors.append(f"unmatched or duplicate condition cell: {block}/{task}/{condition}")
            elif values:
                cell[condition] = values[0]
        if not all(condition in cell for condition in CONDITIONS):
            continue
        pairs.append(
            {
                "block_id": block,
                "task_id": task,
                **{
                    f"{condition}_success": int(cell[condition].get("success") is True)
                    for condition in CONDITIONS
                },
                **{
                    f"{condition}_tokens": int(cell[condition]["total_tokens"])
                    for condition in CONDITIONS
                },
                **{
                    f"{condition}_repeated_failure": int(
                        cell[condition].get("success") is False
                        and cell[condition]["failure_class"] == "task"
                    )
                    for condition in CONDITIONS
                },
            }
        )
    repetitions = int(config["bootstrap"].get("replicates", 10000))
    bootstrap = _bootstrap(pairs, repetitions, int(config["bootstrap"].get("seed", 0)))
    effects = _effect_rows(pairs, bootstrap)
    sensitivity = _mde(pairs)
    threshold = float(config["decision"].get("token_reduction_percent", 10))
    decision = _decision(config["stage"], rows, errors, pairs, bootstrap, threshold)
    validation = {
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "rows": len(rows),
        "pairs": len(pairs),
        "stage": config["stage"],
        "analysis_version": ANALYSIS_VERSION,
        "analysis_config_hash": _hash_file(contract_path),
        "registry_hash": _hash_file(registry_path or contract_path),
        "completeness_fraction": 0
        if not registry_runs
        else (len(seen_runs) - sum("missing preregistered run" in e for e in errors))
        / len(registry_runs),
        "runtime_fingerprint_count": len(fingerprints),
        "artifact_count": len(artifacts),
        "run_conditions": dict(
            sorted(Counter(str(x.get("condition", "unknown")) for x in registry_runs).items())
        ),
    }
    _write_jsonl(output / "normalized_metrics.jsonl", rows)
    _write(output / "validation_report.json", validation)
    _write(output / "bootstrap_ci.json", bootstrap | sensitivity)
    _write(output / "paired_effects.json", {"pairs": pairs, "effects": effects})
    _write_csv(output / "paired_effects.csv", effects)
    taxonomy_counts = Counter((row["failure_class"], row["failure_taxon"]) for row in rows)
    taxonomy = [
        {"class": key[0], "taxon": key[1], "count": count}
        for key, count in sorted(taxonomy_counts.items())
    ]
    _write(output / "failure_taxonomy.json", taxonomy)
    _write_csv(output / "failure_taxonomy.csv", taxonomy)
    _write_csv(output / "protocol_deviations.csv", deviations)
    _write_csv(
        output / "tables" / "validation_completeness.csv",
        [{key: value for key, value in validation.items() if key != "errors"}],
    )
    _write_csv(
        output / "tables" / "endpoint_runtime_fingerprint.csv",
        [{"fingerprint": x} for x in fingerprints],
    )
    _write_csv(
        output / "tables" / "tokens_by_condition.csv",
        [
            {
                "condition": c,
                "foreground_tokens": sum(
                    int(x.get("foreground_input_tokens", 0))
                    + int(x.get("foreground_output_tokens", 0))
                    for x in rows
                    if x.get("condition") == c
                ),
                "background_tokens": sum(
                    int(x.get("background_tokens", 0)) for x in rows if x.get("condition") == c
                ),
                "total_tokens": sum(
                    int(x.get("total_tokens", 0)) for x in rows if x.get("condition") == c
                ),
            }
            for c in CONDITIONS
        ],
    )
    _write_markdown_table(
        output / "tables" / "validation_completeness.md",
        [{key: value for key, value in validation.items() if key != "errors"}],
        "Validation and completeness",
    )
    _write_markdown_table(
        output / "tables" / "endpoint_runtime_fingerprint.md",
        [{"fingerprint": x} for x in fingerprints],
        "Endpoint/runtime fingerprints",
    )
    _write_markdown_table(output / "tables" / "paired_effects.md", effects, "Paired effects")
    (output / "validation_report.md").write_text(
        "# Validation report\n\n"
        + "\n".join(f"- {error}" for error in errors or ["passed"])
        + "\n",
        encoding="utf-8",
    )
    provenance = sha256_text(
        canonical_json(
            {
                "source": validation["analysis_config_hash"],
                "registry": validation["registry_hash"],
                "normalized": _hash_file(output / "normalized_metrics.jsonl"),
                "command": "brain benchmark analyze",
            }
        )
    )
    _figures(output, output / "normalized_metrics.jsonl", effects, taxonomy, provenance)
    memo = "# Decision memo\n\n"
    memo += f"Decision: **{decision.upper()}**\n\n"
    memo += f"Validation status: {validation['status']}. Stage: `{config['stage']}`.\n\n"
    memo += (
        f"C2 token threshold: {threshold:.1f}%; bootstrap CI: "
        f"{bootstrap.get('token_reduction_ci')}. Success CI: "
        f"{bootstrap.get('success_pp_ci')}.\n\n"
    )
    memo += (
        "Pilot estimates are diagnostic only; a main-lite decision requires "
        "valid, complete frozen main-lite inputs.\n"
    )
    (output / "DECISION_MEMO.md").write_text(memo, encoding="utf-8")
    (output / "decision_memo.md").write_text(memo, encoding="utf-8")
    _write(
        output / "analysis_provenance.json",
        {
            "analysis_version": ANALYSIS_VERSION,
            "analysis_config_sha256": validation["analysis_config_hash"],
            "registry_sha256": validation["registry_hash"],
            "normalized_metrics_sha256": _hash_file(output / "normalized_metrics.jsonl"),
            "generation_command": (
                "brain benchmark analyze --registry ... --config ... --output ..."
            ),
            "figure_provenance": provenance,
            "bootstrap": bootstrap,
            "artifacts": artifacts,
        },
    )
    return output


def validate_analysis(root: Path, config_path: Path, registry_path: Path, output: Path) -> Path:
    """Run validation and write the same fail-closed bundle without selection."""
    return analyze(root, config_path, output, registry_path)


def decision_from_analysis(directory: Path) -> str:
    """Return the memo decision only when the analysis bundle validated."""
    report = json.loads((directory / "validation_report.json").read_text(encoding="utf-8"))
    memo = (directory / "decision_memo.md").read_text(encoding="utf-8")
    if report.get("status") != "passed" or report.get("stage") != "main-lite":
        raise ValueError("decision is blocked: validation failed or input is pilot-only")
    for result in ("go", "redesign", "stop"):
        if f"**{result.upper()}**" in memo:
            return result
    raise ValueError("decision memo has no valid decision")
