# PROJECT_PLAN.md — Experience Brain

## 1. Project Goal

Create a lean, open-source, agent-agnostic **Experience Brain** that allows AI agents to accumulate, retrieve, review, and update grounded experience across sessions.

The first milestone is a production-oriented local POC that can be built in approximately seven focused days.

The first paper will later combine:

- a system contribution;
- a method contribution based on a brain-inspired experience lifecycle; and
- empirical evidence from existing benchmark datasets.

The 7-day POC itself does **not** claim benchmark improvement.

## 2. Owner Vision

The final system should:

- give AI agents usable experience rather than simple conversation memory;
- capture all episodes, tools, decisions, feedback, outcomes, successes, and failures;
- convert selected episodes into grounded experience;
- improve future task performance after later benchmark validation;
- work with agent CLIs and other agent frameworks, not only a standalone CLI;
- remain open source under Apache License 2.0;
- support reproducible research and a future arXiv paper; and
- remain understandable and operable by a low-code owner.

## 3. Reframe Strategy

The existing repository is the starting point.

Before implementation:

1. freeze the current repository state with tag `pre-reframe-v0.1.0`;
2. keep Git history;
3. remove obsolete benchmark and research-wiki structures from `main`;
4. retain useful append-only event, provenance, consolidation, retrieval, and test concepts;
5. restructure into the lean layout defined in `AGENTS.md`;
6. add `docs/LEGACY.md` pointing to the frozen tag.

Breaking restructuring is allowed because the new vision takes priority over backward compatibility.

## 4. POC Scope

### Must have

- append-only `events.jsonl`
- append-only `experiences.jsonl`
- stable Pydantic schemas
- MCP server
- Codex CLI-first reference workflow
- automatic event capture through MCP or middleware
- hybrid session processing
- candidate experience consolidation
- cross-session retrieval
- provenance from experience back to events
- review queue
- Markdown review report
- single-owner local Streamlit dashboard
- fallback Python CLI
- generic JSONL trace importer
- software, experiment, and run tracking
- tests and linting
- English open-source documentation
- Thai low-code owner guide
- Windows-first setup with cross-platform Python core

### Deferred

- REST API
- vector database
- knowledge graph
- cloud deployment
- multi-user authentication and permissions
- background agents
- multiple complete framework adapters
- advanced forgetting algorithms
- self-modifying prompts
- full benchmark harness

## 5. Lean Architecture

```text
Codex CLI or another Agent
            ↓
       MCP Server
            ↓
Capture → Consolidate → Retrieve → Review / Update
            ↓
 events.jsonl + experiences.jsonl
            ↓
Markdown Reports + Local Dashboard
```

The MCP and schema must use neutral event names so another agent can connect without modifying the core.

## 6. Session Processing

Use a hybrid model:

1. During a session, capture events continuously.
2. At a normal session end, consolidate automatically.
3. Create candidate experiences and a Markdown review report.
4. Put uncertain or important candidates into the review queue.
5. Use `process session` for old, incomplete, failed, or manually reprocessed sessions.
6. Use `review latest` to inspect the latest result.

## 7. Seven-Day Build Plan

### Day 0 — Preserve and Prepare

- tag `pre-reframe-v0.1.0`
- record the current commit
- create `docs/LEGACY.md`
- create a restructuring checklist
- do not begin destructive changes until the tag is verified

### Day 1 — Lean Foundation

- remove obsolete main-branch structure
- create the lean package layout
- define schemas for events and experiences
- implement append-only JSONL storage
- add schema and storage tests

**Exit:** events and experiences can be written, read, validated, and traced.

### Day 2 — Capture and Redaction

- implement capture API
- implement secret, PII, patient-data, benchmark-leakage, and hidden-reasoning redaction
- define neutral event categories
- add generic JSONL importer
- test duplicate, malformed, and redacted records

**Exit:** grounded session events can enter `events.jsonl` safely.

### Day 3 — Consolidation and Reports

- group events into episodes
- create candidate experiences
- preserve evidence event IDs
- apply status and confidence rules
- generate Markdown review reports
- add owner-confirmation and supersession behavior

**Exit:** a completed session produces reviewable candidate experience.

### Day 4 — Retrieval

- implement project-aware and situation-aware retrieval
- distinguish internal and External Project Experience
- implement authority order
- create pre-task briefing and final consistency-check outputs
- track when an experience was retrieved and used

**Exit:** a new session can receive relevant, traceable prior experience.

### Day 5 — MCP and Agent CLI Workflow

- expose minimal MCP tools
- implement the three primary owner workflows:
  - `process session`
  - `query experience: ...`
  - `review latest`
- document Codex CLI-first usage
- retain a fallback Python CLI for setup, lint, import, and troubleshooting

**Exit:** the owner can use the lifecycle from an Agent CLI without editing source code.

### Day 6 — Dashboard and Experiment Tracking

- create one local Streamlit dashboard
- provide views for sessions, events, experiences, review, and experiments
- support confirm, edit, supersede, invalidate, and retire actions
- initialize `experiments/INDEX.md`
- track software version, `EXP-XX`, and `RUN-XXX`

**Exit:** the owner can inspect and manage experience locally.

### Day 7 — Integration and Release Readiness

- implement Windows-first setup script
- verify cross-platform Python behavior where practical
- run tests, lint, type checks, and a complete local workflow
- create an example project and sample trace
- finalize README and Thai owner guide
- produce a POC limitations and next-phase note
- prepare a clean release candidate

**Exit:** clone → setup → use through Agent CLI → review → retrieve works end to end.

## 8. Definition of Done

The POC is done when this path works:

```text
Agent CLI performs real work
→ MCP records events
→ events.jsonl stores grounded episodes
→ consolidation creates candidate experience
→ experiences.jsonl stores traceable experience
→ owner reviews through Markdown or dashboard
→ a later session retrieves relevant experience
→ the system shows which evidence was used and why
```

Additionally:

- the owner does not need to edit source code for routine use;
- all experience traces back to real events;
- the core remains provider- and agent-agnostic;
- unsafe data is redacted before storage;
- version and experiment history are auditable;
- tests cover the critical path; and
- no unsupported benchmark claim is made.

## 9. Post-POC Research Roadmap

### Phase 2 — Existing Benchmarks and Paper

Use existing benchmark datasets before real-world pilots.

Primary research outcome:

- task success or benchmark score improvement

Supporting outcomes:

- reduced task time
- reduced error rate
- fewer retries or failed tool calls
- lower token use, especially tokens per successful task

Minimum comparison:

- Agent without Experience
- Agent with Experience

Potential ablations:

- raw episodes only
- structured experience
- structured experience plus outcome feedback
- full lifecycle

Paper framing:

- **System:** open-source Experience Brain architecture
- **Method:** grounded brain-inspired experience lifecycle
- **Evidence:** benchmark and ablation results

### Phase 3 — Real-World Pilots

Only after the benchmark and paper phase:

- LabLoop
- ThaiPhaLex

These are real-world external validations, not the first benchmark.

## 10. License and Naming

- License: Apache License 2.0
- Project and paper: Experience Brain
- Repository: `experience-brain`
- Python package: `experience_brain`
- CLI command: `experience`
- MCP server: `experience-brain`
