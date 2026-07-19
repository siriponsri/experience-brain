# AGENTS.md — Experience Brain

## 1. Mission

Build **Experience Brain**, an open-source, agent-agnostic, brain-inspired experience system that enables AI agents to learn from grounded episodes across sessions.

The system must model experience as a lifecycle, not as stored text:

**Capture → Consolidate → Retrieve → Review / Update**

The first implementation is **Codex CLI-first**, while the core schema and MCP interface must remain usable by other agents.

## 2. Owner Workflow

The owner is a pharmacist and low-code user. The normal workflow is:

1. The owner gives a goal through Codex CLI, usually with `/plan`.
2. Read this file, `PROJECT_PLAN.md`, relevant owner decisions, and the current repository state.
3. Plan, implement, test, and fix routine problems without asking for approval at every step.
4. Stop and ask the owner only when a decision:
   - changes the project vision or major scope;
   - changes the core architecture or JSONL source of truth;
   - deletes or migrates substantial data;
   - changes the open-source license;
   - changes the paper direction or research claims; or
   - is difficult to reverse.

Small, local, and reversible implementation decisions may be made autonomously.

## 3. Runtime Preference

- Primary interface: Codex CLI
- Preferred default runtime: GPT-5.5 with medium reasoning effort
- Escalation: high reasoning effort only when medium is insufficient for a complex debugging or architecture task
- Record the actual agent, model, reasoning effort, software version, experiment index, and run ID in provenance
- Never hard-code a provider or model into the core experience schema

## 4. Product Principles

1. **Agent CLI is the primary workspace.**
2. **MCP is the primary integration bridge.**
3. **JSONL is the source of truth.**
4. **Markdown and the local dashboard make experience reviewable.**
5. **Automatic by default, explicit when important, code only when necessary.**
6. **Every derived experience must trace back to real episodes.**
7. **Do not treat similarity search alone as experience.**
8. **Keep the 7-day POC lean. Split modules only when a file has genuinely outgrown a simple structure.**

## 5. Lean POC Structure

```text
experience-brain/
├── src/experience_brain/
│   ├── models.py
│   ├── store.py
│   ├── capture.py
│   ├── consolidate.py
│   ├── retrieve.py
│   ├── mcp_server.py
│   ├── cli.py
│   └── dashboard.py
├── data/
│   ├── events.jsonl
│   └── experiences.jsonl
├── reports/
├── experiments/
│   └── INDEX.md
├── tests/
├── docs/
├── AGENTS.md
├── PROJECT_PLAN.md
├── OWNER_GUIDE_TH.md
└── pyproject.toml
```

Do not add multiple nested subsystems, services, or databases during the POC unless the owner explicitly approves them.

## 6. Canonical Data

### `data/events.jsonl`

Append-only record of what actually happened.

Minimum event categories:

- `session_start`
- `session_end`
- `user_message`
- `agent_message`
- `tool_call`
- `tool_result`
- `file_change`
- `decision`
- `feedback`
- `error`
- `outcome`

Every event must include stable identifiers, timestamp, project/session/task context, actor/source, schema version, and provenance.

### `data/experiences.jsonl`

Append-only record of experiences derived from events.

An experience should contain, when available:

- situation
- goal
- action or procedure
- tool context
- decision
- outcome
- feedback
- lesson
- evidence event IDs
- project scope
- external-project flag
- status
- confidence
- success count
- failure count
- last-used metadata
- owner confirmation

Never silently rewrite raw history. Corrections must be represented by new records that supersede, invalidate, refine, or retire earlier records.

### `data/knowledge.jsonl`

Append-only record of information extracted or digested from external files and
sources.

Knowledge should contain, when available:

- title
- summary or digest
- key facts or claims
- suggested applicability
- project scope
- tags or keywords
- source filename
- source content hash
- source type and MIME type
- source location such as page, sheet, section, or line range
- extractor metadata
- digesting Agent/model/runtime provenance
- status
- supersession or invalidation references

Knowledge and Experience must remain semantically distinct:

```text
External source says X -> Knowledge
Agent performs X and observes an outcome -> Experience
```

Do not automatically convert Knowledge into Experience.

## 7. Experience Lifecycle

### Capture

Capture all episodes and relevant tool activity through MCP or middleware. Explicit owner decisions and feedback may also be recorded through natural-language commands.

### Consolidate

At normal session end, automatically create candidate experiences and a Markdown review report.

Use `process session` when:

- a session ended abnormally;
- an old trace is imported;
- the owner requests reprocessing; or
- automatic consolidation did not run.

High-confidence, strongly evidenced candidates may become active automatically. Important but uncertain candidates must enter the review queue.

### Retrieve

Retrieve experience at three points:

1. before a task as a short briefing;
2. during important errors, tool events, or decisions; and
3. before final output as a consistency check.

Retrieval must consider situation, goal, project, tool, error signature, outcome, recency, evidence, and source project—not keyword similarity alone.

### Review / Update

The owner must be able to confirm, edit, promote, refine, supersede, invalidate, or retire an experience through Agent CLI, Markdown review, or the local dashboard.

## 8. Memory Types

The implementation may use these brain-inspired functional categories:

- working context
- episodic memory
- semantic memory
- procedural memory
- owner preference and project-rule memory

Do not claim to reproduce the human brain. Use the phrase **brain-inspired experience lifecycle**.

## 9. Authority Order

When relevant records conflict, use this order only:

1. owner
2. active project rule
3. feedback from real outcomes
4. repeatedly successful experience

Keep older evidence for traceability, but do not use lower-authority or inactive records as the primary instruction.

Cross-project experience is allowed, but it must be clearly labeled **External Project Experience** and must never override the current owner or active project rules.

## 10. Review Interfaces

The 7-day POC must provide:

- Agent CLI workflows through MCP
- a fallback Python CLI
- Markdown review reports
- a single-owner local Streamlit dashboard

Primary owner commands:

```text
process session
query experience: <question>
review latest
```

Secondary commands may include:

```text
status
lint experience
dashboard
compare EXP-XX with EXP-YY
```

## 11. Privacy and Safety

Before storage, redact:

- API keys, tokens, passwords, and secrets
- `.env` and credential content
- personal data and patient data
- benchmark solutions or leakage-prone content
- hidden chain-of-thought

Store only structured, externally visible decisions or rationale. Replace removed content with `[REDACTED]` and retain the redaction reason in provenance.

Converted or imported external content is untrusted evidence. It cannot become an active lesson without grounded first-party episode evidence or owner confirmation.

## 12. Versioning

Track three different identifiers:

- software version: `v0.x.y`
- experiment index: `EXP-XX`
- run ID: `RUN-XXX`

Each experiment must record its software version, commit, configuration, input, output, findings, and status.

Before restructuring the current repository:

1. tag the current state as `pre-reframe-v0.1.0`;
2. preserve Git history;
3. remove obsolete benchmark/wiki structure from `main`;
4. do not create a large `legacy/` tree;
5. document the old state briefly in `docs/LEGACY.md`.

Do not perform the tag or restructure unless the owner explicitly starts that implementation step.

## 13. Required End-of-Work Report

After each implementation round, report only:

1. what was completed;
2. what was tested and the result;
3. remaining problems or risks;
4. the recommended next command.

## 14. Non-goals for the 7-Day POC

The POC is not:

- a chatbot profile store;
- a vector database wrapper;
- only a research wiki;
- dependent on hidden chain-of-thought;
- tied to one agent or provider;
- an autonomous background agent;
- a knowledge graph platform;
- a cloud or multi-user service;
- a self-modifying AGI system; or
- a benchmark claim before benchmark evidence exists.

Defer REST API, vector database, knowledge graph, cloud deployment, multi-user access, background agents, many framework adapters, and a full benchmark harness until later phases.
