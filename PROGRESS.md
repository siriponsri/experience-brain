# Project Progress

Last updated: 2026-07-17

## Repository State

- Current branch: `main`
- Local implementation commit: `8673840 feat: add reproducible benchmark and full-module gates`
- Local branch is ahead of `origin/main`; push is blocked because the Windows
  Git HTTPS credential provider returned `SEC_E_NO_CREDENTIALS`.
- No raw benchmark outcomes, official run registry, `pilot-v1.json`, or
  `final-v1.json` are present. Do not infer benchmark results from fixtures.
- `starter-kit/BENCHMARK_PROTOCOL.md` and `starter-kit/EXPERIMENT_PLAN.md`
  remain unchanged.

## Completed

- Lite core: append-only events, verifier-backed episode/skill consolidation,
  lexical retrieval, bounded capsules, Wiki baseline controls, linting, and
  reports.
- Benchmark harness: frozen manifest/lock/runtime preflight, smoke/pilot
  controls, retry/completeness checks, provenance-preserving outcomes, and
  cost estimation.
- Reproducible analysis: explicit frozen registry/config, artifact and runtime
  validation, paired effects, deterministic bootstrap, failure taxonomy,
  figures/tables, and fail-closed decision memo.
- Full foundation: `profile: full`, C3 alias, feature flags, local ignored
  `.indexes/`, immutable PI decision artifacts, and sequential module gates.
- Full module 1: hybrid retrieval uses the existing lexical candidates plus a
  runtime-provided embedding command and deterministic reciprocal-rank fusion.
  It records runtime/index fingerprints, source hashes, query/build telemetry,
  and fails closed on stale/corrupt indexes, unavailable embedder, or runtime
  mismatch.
- GPU-required hybrid runtimes do not execute. They write an Owner decision
  spec under `evaluations/gpu-requests/` and stop.

## Full Module Gate

Order is fixed in `src/experience_brain/full.py`:

1. `hybrid_retrieval`
2. `consolidation_pruning`
3. `proactive_intervention`
4. `temporal_kg`
5. `multimodal`

Only Hybrid is implemented. The next module must not be implemented or enabled
until a valid, immutable PI `keep` or `remove` decision exists for Hybrid.
`remove` keeps the code available for reproducibility but leaves it disabled in
the cumulative Full profile.

## Commands

Configure a C3 store with `profile: full`, `condition: c3`,
`full.modules.hybrid_retrieval: true`, and a runtime-provided embedder command,
fingerprint, and dimensions. Do not pin an embedding model in repository
configuration.

```powershell
brain index rebuild --module hybrid_retrieval --root <brain-root>
brain index verify --module hybrid_retrieval --root <brain-root>
brain benchmark run-module --module hybrid_retrieval --manifest <pilot-manifest> --ablation-config <ablation.yaml> --root <repo-root>
brain benchmark analyze-module --module hybrid_retrieval --registry <registry.yaml> --config <analysis.yaml> --output <output-dir> --root <repo-root>
brain full decision --module hybrid_retrieval --decision keep --evidence <analysis-dir> --approved-by <pi-role> --root <repo-root>
brain full gate --next-module consolidation_pruning --root <repo-root>
```

`run-module` is intentionally preflight-only until official C3 execution is
added. The current benchmark runner still expands only C0/C1/C2. It must be
extended with a frozen C2-versus-C3 module-pilot runner before collecting the
Hybrid ablation. `analyze-module` remains fail-closed and produces a
`blocked_missing_data` gain/cost memo when raw official outcomes are absent.

## Required Before Hybrid PI Decision

- Create and freeze the official `evaluations/manifests/pilot-v1.json`; it
  must not overlap with a future `final-v1.json`.
- Add a frozen ablation config with `lite` and `candidate` arms and at least
  three randomized runs per arm.
- Extend the benchmark runner for isolated C2 and C3 stores while preserving
  existing C0/C1/C2 behavior and final-manifest immutability.
- Run complete paired pilots using one unchanged runtime/endpoint fingerprint.
- Generate the analysis bundle and gain/cost memo from verifier artifacts.
- Record the PI decision with evidence hashes. Only then open the next module.

## Validation

- Last full test run: `42 passed`.
- Last coverage run: `90%` total coverage.
- Ruff and MyPy passed.
- `git diff --check` passed.

## Push Blocker

Git remote is `https://github.com/siriponsri/experience-brain.git`. Authenticate
GitHub for this Windows session, then run:

```powershell
git push origin main
```

Do not rewrite history or force-push. After credentials are available, commit
this handoff file and push both local commits.
