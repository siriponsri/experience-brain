# EXP-03 - Live Codex MCP Integration

## Purpose

Verify the real end-to-end Experience Brain workflow:

```text
Codex CLI session -> Experience Brain MCP -> events.jsonl -> consolidation
-> experiences.jsonl -> Markdown review -> later retrieval -> usage trace
```

## Software Version

`v0.2.1`

## Parent Experiment

`EXP-02 - Lean Agent-CLI-first reframe`

## Exact Change

- Audited MCP placeholders: previous server exposed only `process_session`,
  `query_experience`, and `review_latest`.
- Added MCP tools for `start_session`, `end_session`, `record_event`,
  `record_retrieval_usage`, and `record_outcome_feedback`.
- Added append-only retrieval usage records and last-used Experience updates.
- Added project-aware retrieval filtering so unrelated zero-overlap tasks do not
  receive prior Experience as primary context.
- Added Codex MCP wiring documentation.
- Added isolated live Codex example fixture and integration test.

## Expected Benefit

A later Codex session can retrieve a grounded Experience from prior first-party
events, see its evidence IDs, record whether it was used, and avoid unrelated
Experience as primary context.

## Risks

- The sandbox did not allow direct edits to the tracked `.codex/` directory, so
  Codex MCP wiring is documented and validated by command/config override rather
  than committed into `.codex/config.toml`.
- The live workflow is simulated through MCP tool calls in-process; an actual
  interactive Codex TUI session still needs owner-side smoke testing.
- Retrieval remains lexical plus authority/project/confidence scoring; no vector
  database or benchmark claim is introduced.

## Evidence Sources

- `tests/test_live_codex_mcp_integration.py`
- `tests/fixtures/live_codex_example/`
- `docs/CODEX_MCP.md`
- `reports/latest.md` generated during isolated test roots

## Summary of Results

Final development result: the live-style MCP workflow passed the focused
integration test and the full local validation suite. The flow covered an
initial grounded calculator task, a related later session with retrieval usage,
an unrelated docs task with no primary retrieval, and an external-project
retrieval-label check.

Owner live validation continued in EXP-03.1. The existing proposed Experience
`EXP-327D87ACD4` appeared in the persistent Dashboard Review Queue even though
the newest Markdown report had no candidates. The dashboard Confirm action
appended an owner-authored revision, preserved the original candidate and
evidence references, and made the confirmed revision retrievable in a later
related query. An unrelated clinical query returned no primary Experience.

## Limitations

This is a development integration experiment only. It does not begin or imply a
publication benchmark.

## Decision

Keep for POC live workflow. Do not treat as benchmark readiness.
