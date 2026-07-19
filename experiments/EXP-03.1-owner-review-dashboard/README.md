# EXP-03.1 - Owner Review Dashboard

## Purpose

Make the Streamlit dashboard the primary low-code interface for reviewing and
managing candidate Experiences without changing the JSONL, MCP, provenance, or
append-only architecture.

## Software Version

`v0.2.2`

## Parent Experiment

`EXP-03 - Live Codex MCP Integration`

## Exact Change

- Replaced raw dashboard tables with Overview, persistent Review Queue,
  Experiences, and Sessions / Events views.
- Added Confirm, Edit and Confirm, Reject / Invalidate, and Retire actions.
- Represented every owner action as a new Experience record linked through
  `supersedes` or `invalidates`.
- Separated unresolved Experience status from the newest Markdown report.
- Added explicit `retrieval_result`, `usage`, and `task_outcome` fields to new
  retrieval usage Event metadata while retaining the prior `outcome` input.

## Expected Benefit

The owner can complete the Experience review lifecycle visually and confirmed
lessons become available to the next agent session without direct JSONL edits.

## Risks

- Streamlit remains a local, single-owner process and has no concurrent-writer
  coordination beyond the current append-only store behavior.
- Retrieval remains lexical and can match a shared domain word; validation must
  use genuinely unrelated wording when checking the no-match path.
- Historical retrieval usage Events do not gain the new explicit metadata;
  backward compatibility preserves them as recorded.

## Evidence Sources

- `tests/test_dashboard.py`
- `tests/test_live_codex_mcp_integration.py`
- `data/experiences.jsonl`
- Dashboard live-validation run `RUN-20260718122242684951`

## Summary of Results

The existing proposed Experience `EXP-327D87ACD4` appeared automatically in
Review Queue. Clicking Confirm in the rendered dashboard appended confirmed
revision `EXP-327D87ACD4-REV-20260718122242684951-A7152DA6`, retained the
original record and evidence IDs, recorded owner/dashboard provenance, and
cleared the queue. A later related benchmark-isolation query retrieved the
confirmed revision as primary context. The unrelated query `warfarin bleeding
INR adherence` returned no Experience.

No MemoryArena real inference was started.

## Limitations

This is owner workflow and development validation, not benchmark performance
evidence or a research claim.

## Decision

Keep as the default low-code owner review workflow for the POC.
