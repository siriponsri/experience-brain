from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import pydantic
import typer

import experience_brain


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def build_environment_manifest(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "experience_brain": {
            "software_version": f"v{experience_brain.__version__}",
            "git_commit": _git_commit(),
        },
        "memoryarena": {
            "git_commit": config["upstream"]["memoryarena_commit"],
            "project_url": "https://github.com/ZexueHe/MemoryArena",
        },
        "python_version": sys.version.split()[0],
        "dependency_versions": {
            "pydantic": pydantic.__version__,
            "typer": typer.__version__,
            "mcp": "installed; package does not expose __version__",
        },
        "operating_system": platform.platform(),
        "model": config["model"]["name"],
        "model_version": config["model"].get("version"),
        "reasoning_configuration": config["model"]["reasoning_effort"],
        "experiment_id": config["experiment_id"],
        "run_ids": config["run_ids"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    Path(args.output).write_text(
        json.dumps(build_environment_manifest(config), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
