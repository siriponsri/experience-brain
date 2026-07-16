# Experience Brain Lite

Deterministic, provenance-preserving procedural memory for the Lite phase. The canonical store is append-only JSONL events plus Markdown/YAML episodes and skills. It does not use vector search, knowledge graphs, background agents, multimodal memory, or external LLM calls.

## Quick start (Windows PowerShell)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock
.\.venv\Scripts\python -m pip install -e . --no-deps
.\.venv\Scripts\brain ingest tests\fixtures\synthetic\events.jsonl --kind events
.\.venv\Scripts\brain consolidate
.\.venv\Scripts\brain retrieve --task tests\fixtures\synthetic\task.yaml
.\.venv\Scripts\brain capsule --task tests\fixtures\synthetic\task.yaml --budget 1000
.\.venv\Scripts\brain report
.\.venv\Scripts\brain lint
```

## Quick start (macOS/Linux)

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install -e . --no-deps
.venv/bin/brain ingest tests/fixtures/synthetic/events.jsonl --kind events
.venv/bin/brain consolidate
.venv/bin/brain retrieve --task tests/fixtures/synthetic/task.yaml
.venv/bin/brain capsule --task tests/fixtures/synthetic/task.yaml --budget 1000
.venv/bin/brain report
.venv/bin/brain lint
```

## Safety and lifecycle

- Events are append-only and linked by SHA-256 hashes.
- Episodes and skills retain event/verifier provenance.
- A skill becomes `verified` only after two independent successful episodes.
- Converted external Markdown is always untrusted data and cannot supply a skill candidate.
- Capsules contain only verified procedures and never exceed their configured token budget.

## Verification

```powershell
.\.venv\Scripts\python -m pytest --cov=experience_brain --cov-fail-under=90
.\.venv\Scripts\ruff check .
.\.venv\Scripts\ruff format --check .
.\.venv\Scripts\mypy src tests
.\.venv\Scripts\brain lint
```
