# EXP-04 - MemoryArena Benchmark Integration and Smoke Study

## Purpose

Integrate Experience Brain as an experimental memory backend for the official
MemoryArena benchmark framework and prepare a reproducible smoke-study pipeline.

## Software Version

`v0.2.1`

## Parent Experiment

`EXP-03 - Live Codex MCP Integration`

## Exact Change

- Added `benchmark-exp/memoryarena/` research structure.
- Audited official MemoryArena code, dataset, setup docs, and formal reasoning
  runner.
- Identified the memory abstraction as `add_chunk(chunk)` and
  `wrap_user_prompt(question)`.
- Added C0, C1, and C2 condition configs.
- Added an Experience Brain adapter implementing C1 raw Events and C2
  automated Experience lifecycle behavior.
- Added deterministic run IDs and frozen 5-task `formal_reasoning_math` smoke
  subset.
- Added dataset and environment manifests.
- Added leakage and store-isolation checks.
- Added dry-run result serialization and tests.

## Expected Benefit

The project can run controlled MemoryArena smoke validation once official
services and model credentials are available, while preserving benchmark
questions, gold answers, task order, and evaluation rules.

## Risks

- Real MemoryArena inference was not run: no local model credentials/base URL,
  MemoryArena memory server, or MemoryArena environment server were available.
- The inspected MemoryArena repository commit has no root license file.
- The adapter is validated by local dry runs and tests, not by official
  environment execution.
- Dry-run outputs are engineering diagnostics only and must not be interpreted
  as benchmark performance.

## Evidence Sources

- `benchmark-exp/memoryarena/README.md`
- `benchmark-exp/memoryarena/PROTOCOL.md`
- `benchmark-exp/memoryarena/configs/smoke_formal_reasoning_math_5.json`
- `benchmark-exp/memoryarena/manifests/dataset_manifest.json`
- `benchmark-exp/memoryarena/manifests/environment_manifest.json`
- `tests/test_memoryarena_adapter.py`

## Summary of Results

Adapter dry-run validation passed for all three conditions:

- `C0`: no persistent memory.
- `C1`: raw episode Events without Experience consolidation.
- `C2`: Events, automated Experiences, Experience retrieval, and retrieval
  usage traces.

No real benchmark inference was run.

## Limitations

This experiment establishes an integration pipeline and smoke harness. It does
not compare benchmark accuracy and does not support any claim that Experience
Brain improves MemoryArena performance.

## Decision

Keep as the MemoryArena research integration baseline. Freeze the protocol with
the owner before running official inference.
