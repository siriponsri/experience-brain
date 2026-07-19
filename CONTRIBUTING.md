# Contributing

Experience Brain welcomes focused contributions that preserve its grounded,
append-only experience lifecycle.

## Before Opening A Change

Read `AGENTS.md`, `PROJECT_PLAN.md`, `PRODUCT.md`, and the relevant experiment record.
Open an issue before proposing a change that alters the core architecture, canonical
JSONL stores, schema semantics, license, research protocol, or major project scope.

The current preview intentionally excludes vector databases, embeddings, knowledge
graphs, REST APIs, cloud deployment, multi-user authentication, autonomous background
agents, and unrelated framework adapters.

## Development Setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Required Checks

```powershell
python -m pytest
ruff check .
ruff format --check .
mypy src tests
experience lint --root .
git diff --check
```

MemoryArena work must remain isolated under `benchmark-exp/memoryarena/`; do not run
real benchmark inference unless the experiment explicitly authorizes it.

## Change Requirements

- Keep every derived Experience traceable to real Event IDs and observed outcomes.
- Keep external Knowledge semantically distinct from Experience.
- Preserve append-only correction, invalidation, supersession, and retirement.
- Add tests proportional to the behavioral risk.
- Do not add secrets, patient data, benchmark solutions, hidden reasoning, or generated
  artifacts unrelated to the change.
- Document public CLI or MCP changes and update the changelog.
- Use original or correctly licensed assets and record required attribution.

## Pull Requests

Keep commits focused and describe what changed, how it was tested, and any risk to the
research baseline. Do not claim benchmark improvement without controlled evidence.

By contributing, you agree that your contribution is licensed under Apache License 2.0.
