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

## C1 research-wiki condition

C1 is selected in `brain.yaml` with `condition: c1` and a run-specific `run_id`. Its
store is isolated at `wiki/runs/<run_id>/`; it never reads Lite events, episodes,
skills, retrieval results, or capsules. Configure the frozen Prompt 01/02 files under
`wiki.prompt_references`. C1 refuses to run when those repository-relative references
are absent, so the original prompt text is never invented or changed per run.

The C1 workflow uses explicit foreground commands:

```powershell
brain ingest source.md --kind source --metadata source.yaml
brain maintain --manifest maintenance.yaml
brain context --task task.yaml
brain leakage --task frozen-deployment-task.yaml
brain report
brain lint
brain reset --confirm-run-id <run-id>
```

Raw sources are immutable and content-hashed. Wiki pages and lessons are append-only
version files with source, maintenance-operation, and frozen-prompt provenance.
Maintenance manifests must report input/output tokens and wall time; the C1 report
includes those tokens as background wiki-maintenance cost. Context is packed in stable
wiki-index order under the same configured token budget and treats wiki material as
untrusted evidence rather than instructions.

## Benchmark harness

The verifier-first harness connects C0, C1, and C2 through isolated workspaces.
It requires an official external checkout lock, an exact runtime rate card, frozen
prompt files, and canonical task manifests before execution.

```powershell
brain benchmark preflight --manifest evaluations/manifests/smoke-v1.json
brain benchmark smoke --manifest evaluations/manifests/smoke-v1.json --run-id smoke-001
brain benchmark completeness --run-id smoke-001 --expected-attempts 6
brain benchmark estimate --smoke-run-id smoke-001 --pilot-manifest evaluations/manifests/pilot-v1.json
```

`brain benchmark run --stage pilot` additionally requires a `protocol-v1` tag and
an approval YAML whose manifest, runtime, and cost-estimate hashes all match. Local
checkouts, workspaces, run artifacts, and runtime configs are intentionally ignored
by Git to avoid retaining benchmark solutions or secrets.

## Verification

```powershell
.\.venv\Scripts\python -m pytest --cov=experience_brain --cov-fail-under=90
.\.venv\Scripts\ruff check .
.\.venv\Scripts\ruff format --check .
.\.venv\Scripts\mypy src tests
.\.venv\Scripts\brain lint
```
