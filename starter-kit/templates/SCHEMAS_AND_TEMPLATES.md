# Schemas and Templates

## Episode

```yaml
id: ep_...
run_id: ...
task_id: ...
goal: ...
started_at: ...
ended_at: ...
outcome:
  success: false
  verifier_score: 0
events:
  - event_...
decisions:
  - summary: ...
    evidence_event_ids: [...]
failure_signature: ...
cost:
  input_tokens: 0
  output_tokens: 0
  wall_seconds: 0
trust: first_party_execution
```

## Skill

```yaml
id: skill_...
version: 1
status: candidate
scope: project
activation:
  task_types: []
  signals: []
preconditions: []
procedure: []
termination: []
failure_modes: []
evidence:
  episode_ids: []
  verifier_results: []
confidence: 0.0
created_at: ...
updated_at: ...
supersedes: null
```

## Capsule

```yaml
id: capsule_...
task_id: ...
profile: lite
budget_tokens: 2000
estimated_tokens: 0
retrieval_policy_version: ...
items:
  - memory_id: ...
    type: skill
    score: 0.0
    tokens: 0
    evidence_ids: []
omitted_items: 0
```

## Protocol deviation

```yaml
id: deviation_...
run_ids: []
detected_at: ...
description: ...
cause: ...
condition_blinded: true
decision: include|exclude|rerun|report_only
rationale: ...
approved_by: ...
```

## Literature note

```yaml
paper_id: P001
citation_checked: false
screening_decision: pending
memory_unit: ...
write_update_forget: ...
retrieval_intervention: ...
provenance_verification: ...
benchmarks: []
models: []
token_cost_reported: unknown
main_findings: []
limitations: []
relation_to_our_work: ...
quotable_claims_with_page: []
```

