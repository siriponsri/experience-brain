# ThaiPhaLex IS1 Pilot

## Status

**Prepared, not started.** This document defines a future operational dogfooding pilot.
It is not a controlled benchmark protocol and must not be cited as proof of performance
improvement.

Suggested experiment identifier:

```text
EXP-05 - ThaiPhaLex Cross-Session Research Workflow Pilot
```

## Purpose

Use Experience Brain during real ThaiPhaLex IS1 research work to observe cross-session
continuity, retrieval relevance, review burden, ingestion reliability, and failure
modes. The pilot should test whether the workflow is usable, not whether a model beats a
benchmark.

## Isolation

Create a dedicated store outside both repositories, for example:

```text
C:\ResearchStores\thaiphalex-is1\
  data\events.jsonl
  data\experiences.jsonl
  data\knowledge.jsonl
  inbox\
  reports\
```

The pilot root must never be:

- the Experience Brain development repository;
- the ThaiPhaLex source repository itself;
- any `benchmark-exp/memoryarena/runs/.../stores/` condition root; or
- a parent directory shared by another active store.

Register a distinct MCP name and root:

```powershell
codex mcp add thaiphalex-experience-brain -- `
  python -m experience_brain.mcp_server `
  --root "C:\ResearchStores\thaiphalex-is1"
```

Use the same root when opening the Dashboard:

```powershell
experience dashboard --root "C:\ResearchStores\thaiphalex-is1"
```

## Before The First Session

1. Record the Experience Brain software version and commit.
2. Create the `EXP-05` experiment record with an initial `RUN-XXX`.
3. Run `experience lint` against the empty isolated root.
4. Confirm the Codex MCP server points to the isolated root.
5. Define which ThaiPhaLex files may enter Knowledge and exclude secrets, patient or
   personal data, benchmark answers, and unpublished restricted material.
6. Capture a dry workflow session before beginning substantive research work.

## Workflow

1. Start a traceable ThaiPhaLex research session through MCP.
2. Retrieve relevant Knowledge and Experience before the task.
3. Record visible actions, decisions, tool results, errors, and outcomes.
4. End and consolidate the session.
5. Review proposed Experience in the Dashboard.
6. Record whether retrieved Experience was actually used and whether it helped.
7. Inspect provenance before confirming an important lesson.

External papers and project files create Knowledge. Only agent action with an observed
outcome can support Grounded Experience.

## Metrics

Record per run where practical:

- sessions and Events captured;
- Experiences proposed and confirmed;
- Knowledge items processed;
- retrieval count and retrieved Experience actually used;
- useful, irrelevant, and harmful retrievals;
- owner review burden, preferably minutes and records reviewed;
- operational failures;
- latency for retrieval and review actions where practical.

Optional owner usefulness score:

```text
0 harmful | 1 irrelevant | 2 somewhat useful | 3 useful | 4 very useful
```

Define the score before collection and retain negative observations. Do not convert this
ordinal score into a benchmark-performance claim.

## Stop Conditions

Pause the pilot if the store root is wrong, sensitive data is captured, provenance is
missing, Knowledge is represented as Experience, retrieval is repeatedly harmful, or
store integrity fails. Preserve append-only evidence and document the incident before
resuming.

## Reporting Boundary

An EXP-05 report may describe workflow observations, counts, failures, review burden,
and examples with safe provenance. It must state that the pilot is uncontrolled and
must not claim task-performance improvement, model superiority, clinical validity, or
benchmark evidence.
