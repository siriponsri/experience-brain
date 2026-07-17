# COST_ESTIMATE

Status: BLOCKED — no approved runtime rate card or smoke outcomes exist yet.

Generate the final estimate only from a completed local smoke run:

```powershell
brain benchmark estimate --smoke-run-id <run-id> --pilot-manifest evaluations/manifests/pilot-v1.json
```

The generated estimate will include base, expected (+10% infrastructure reserve),
and hard worst-case (one retry per attempt) token and currency totals. A full pilot
remains blocked until `evaluations/approvals/pilot-cost-v1.yaml` has matching hashes.
