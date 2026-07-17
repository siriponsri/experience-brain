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
| EXP-01 | Pre-reframe baseline | v0.1.0 | planned freeze | Existing Lite repository before owner-led reframe | To be frozen at tag `pre-reframe-v0.1.0` | Baseline only | Tag and document before restructuring |
| EXP-02 | Lean Agent-CLI-first reframe | v0.2.0 target | planned | Two JSONL stores, MCP-first workflow, Markdown review, local dashboard | No result yet | Unknown | Implement after baseline tag is verified |

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
