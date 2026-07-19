# MemoryArena Benchmark Integration

EXP-04 integrates Experience Brain as an experimental memory backend for the
official MemoryArena benchmark framework without vendoring or modifying the
official benchmark code.

Official sources inspected:

- Project: https://memoryarena.github.io/
- Code: https://github.com/ZexueHe/MemoryArena
- Dataset: https://huggingface.co/datasets/ZexueHe/memoryarena
- Paper: https://huggingface.co/papers/2602.16313

Pinned revisions:

- MemoryArena code commit: `6cd9de14b71915e39ac742a20dc33785e14b6aab`
- Hugging Face dataset revision:
  `da1a37c8b19280e18627ca01cf368195a5e1d92e`
- Dataset license: CC-BY-4.0 on the Hugging Face dataset page.
- Code license: no root license file found in the inspected code commit.

The official memory interface is `add_chunk(chunk)` plus
`wrap_user_prompt(question)`, exposed either directly by memory-system classes
or through the MemoryArena memory server endpoints.

## Conditions

- `C0`: no persistent memory. Returns an empty `<memory_context>`.
- `C1`: raw episode memory. Stores prior MemoryArena chunks as Events only.
- `C2`: full Experience Brain. Stores Events, creates automated traceable
  Experiences, retrieves Experiences, and records retrieval usage.

All conditions use isolated stores. Gold answers, evaluator-only values,
`ground_truth`, judge feedback, and correctness rewards are blocked from
Experience Brain memory.

## Smoke Subset

Frozen subset: `formal_reasoning_math`

Selected task group IDs: `0, 1, 2, 3, 4`

Paper names observed at the pinned dataset revision:

- `2503.19064`
- `2510.16976`
- `2312.05134_part_2`
- `2408.12186`
- `2410.01101`

## Dry Run

The dry run validates adapter behavior and serialization without model calls,
official environment servers, or benchmark scoring:

```powershell
$out = Join-Path $env:TEMP ("experience-brain-exp04-dry-" + [guid]::NewGuid().ToString("N"))
python benchmark-exp/memoryarena/scripts/run_smoke.py --dry-run --output $out
```

Real MemoryArena inference requires the official environment setup, model
credentials, and owner-approved protocol freeze.
