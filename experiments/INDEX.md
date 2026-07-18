# Experiment Index

This file tracks **experimental approaches**, not software releases.

- Software version: `v0.x.y`
- Experiment index: `EXP-XX`
- Run ID: `RUN-XXX`

Each experiment must state what changed, why it changed, what evidence exists, and whether it is better or worse than the previous best.

## Status Vocabulary

- `planned`
- `active`
- `completed`
- `best-so-far`
- `superseded`
- `rejected`

## Experiment Registry

| Experiment | Title | Software | Status | Change from previous | Evidence / finding | Better or worse? | Next action |
|---|---|---:|---|---|---|---|---|
| EXP-01 | Pre-reframe baseline | v0.1.0 | completed | Existing Lite repository before owner-led reframe | Frozen at annotated tag `pre-reframe-v0.1.0` targeting `dd2d3cf98d65b816f1ee79222d5ffc6e4e02d372` | Baseline only | Use tag for historical reference only |
| EXP-02 | Lean Agent-CLI-first reframe | v0.2.0 target | completed | Two JSONL stores, MCP-first workflow, Markdown review, local dashboard | Lean foundation present on branch `reframe/v0.2.0`; EXP-03 starts live MCP workflow validation | Better foundation for POC, not benchmark evidence | Use as baseline for live Codex MCP integration |
| EXP-03 | Live Codex MCP Integration | v0.2.1 | completed | Adds real session/event MCP capture, retrieval usage tracing, Codex wiring docs, and live-style fixture sessions | 10 pytest tests pass; Ruff, mypy, install, CLI, lint, MCP startup, and Codex MCP listing pass | Better for POC live workflow; not benchmark evidence | Owner smoke-test from an interactive Codex CLI session |
| EXP-04 | MemoryArena Benchmark Integration and Smoke Study | v0.2.1 | completed | Adds MemoryArena adapter, frozen 5-task smoke config, manifests, protocol draft, leakage/isolation checks, and dry-run harness | Adapter tests and dry-run validation pass for C0/C1/C2; real benchmark inference blocked by missing services/credentials | Better research pipeline readiness; not benchmark performance evidence | Owner review and freeze `benchmark-exp/memoryarena/PROTOCOL.md` |

Do not mark an experiment `best-so-far` without recorded evidence.

## Standard Experiment Record

Create one folder per experiment only when implementation or evaluation begins:

```text
experiments/
├── INDEX.md
├── EXP-01-pre-reframe-baseline/
└── EXP-02-lean-agent-cli-reframe/
```

Minimum files:

```text
README.md
config.yaml
results.json
```

### `README.md` must contain

- hypothesis or purpose
- software version
- parent or baseline experiment
- exact change
- expected benefit
- risks
- evidence sources
- summary of results
- limitations
- decision: keep, refine, supersede, or reject

### `config.yaml` must contain

```yaml
experiment_id: EXP-XX
software_version: v0.x.y
commit: <git-sha>
agent:
  interface: codex_cli
  model: <actual-model>
  reasoning_effort: <actual-effort>
data:
  events_path: data/events.jsonl
  experiences_path: data/experiences.jsonl
```

### `results.json` must contain

```json
{
  "experiment_id": "EXP-XX",
  "software_version": "v0.x.y",
  "runs": [
    {
      "run_id": "RUN-001",
      "commit": "<git-sha>",
      "started_at": "<timestamp>",
      "ended_at": "<timestamp>",
      "result": "pending",
      "notes": ""
    }
  ]
}
```

## Comparison Rule

When comparing experiments, report:

1. what changed;
2. which software version and commit were used;
3. which runs are being compared;
4. what improved;
5. what regressed;
6. whether the result is repeatable;
7. whether the approach becomes the new default.

During the 7-day POC, internal evidence may include:

- capture completeness
- schema validity
- provenance completeness
- retrieval relevance
- stale or duplicate experience rate
- latency
- token overhead
- owner review score
- regression-test results

These are development diagnostics, not publication claims.

## Future Benchmark Phase

After the POC, add experiments that compare:

- Agent without Experience
- raw episodes only
- structured Experience
- structured Experience plus outcome feedback
- full Experience lifecycle

Primary publication outcome:

- task success or benchmark score

Supporting outcomes:

- task time
- error rate
- failed tool calls and retries
- tokens per successful task
