# EXP-04 Protocol Draft

## Scope

This protocol prepares a MemoryArena integration and a 5-task engineering smoke
study for `formal_reasoning_math`. It must be reviewed and frozen before any
full benchmark execution.

## Official Benchmark Behavior

At MemoryArena commit `6cd9de14b71915e39ac742a20dc33785e14b6aab`, the formal
reasoning runner:

- loads `ZexueHe/memoryarena` with config `formal_reasoning_math` and split
  `test`;
- iterates dataset rows in dataset order;
- builds each task group from `questions`, `answers`, and `backgrounds`;
- wraps each subtask prompt with memory via `MemoryClient.wrap_user_prompt`;
- evaluates each subtask with the formal reasoning environment;
- stores action/observation memory after each subtask;
- defaults `judge_result_in_memory` to `false`.

Do not modify official questions, answers, backgrounds, ordering, evaluator
logic, scoring logic, or retry behavior.

## Frozen Smoke Selection

Dataset revision:
`da1a37c8b19280e18627ca01cf368195a5e1d92e`

Subset: `formal_reasoning_math`

Selected task group IDs, in order: `0, 1, 2, 3, 4`

The same IDs and order must be used for `C0`, `C1`, and `C2`.

## Conditions

`C0 - No Persistent Memory`

- No Experience Brain store is used as persistent memory.
- The prompt receives only the current MemoryArena-allowed prompt content and an
  empty memory context.

`C1 - Raw Episode Memory`

- Store prior action/observation chunks as append-only Events.
- Do not consolidate Events into Experiences.
- Retrieve raw Events with deterministic lexical overlap.

`C2 - Full Experience Brain`

- Capture prior chunks as Events.
- Consolidate each chunk into a traceable automated Experience.
- Retrieve Experiences before later subtasks.
- Record retrieval usage traces.
- No human owner intervention after a benchmark run begins.

## Fairness Controls

Hold constant across conditions wherever technically possible:

- base model and model version;
- reasoning configuration;
- task group IDs and ordering;
- official environment and tools;
- prompt template except memory-context content;
- retry, token, and time limits;
- evaluator and scoring method.

Any unavoidable differences must be recorded in the environment manifest and
run result.

## Leakage Controls

Never store these in Experience Brain memory:

- gold answers;
- `ground_truth`;
- evaluator-only feedback;
- `judge_result`;
- `is_correct`;
- correctness reward values;
- benchmark solution labels that reveal the answer.

Use separate stores per condition and task group. Do not share memory between
`C0`, `C1`, and `C2`, and do not share memory across task groups unless the
official protocol explicitly requires it.

## Metrics

Collect only metrics available from logs or stores.

Primary:

- subtask accuracy;
- complete task-group success rate.

Supporting:

- performance by subtask position;
- errors;
- retries;
- tool failures;
- wall-clock time;
- input tokens;
- output tokens;
- total tokens;
- tokens per successful subtask.

Experience Brain diagnostics:

- number of Events captured;
- number of Experiences consolidated;
- retrieval count;
- retrieval utilization;
- provenance completeness;
- stale or irrelevant retrieval count where measurable;
- harmful retrieval cases where measurable.

## Execution Gate

Before real inference:

1. Owner reviews and freezes this protocol.
2. Official MemoryArena environment server is installed and starts cleanly.
3. Memory server or direct adapter shim is wired.
4. Model credentials and base URLs are available.
5. Dry-run tests pass.
6. Dataset and environment manifests are regenerated.

The 5-task smoke study is engineering validation only and must not be used to
select a winning method or support a performance claim.
