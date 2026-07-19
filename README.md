# Experience Brain

<p align="center">
  <img src="docs/assets/experience-brain-logo.svg" alt="Experience Brain" width="680">
</p>

<p align="center">
  <img alt="Status: public research preview" src="https://img.shields.io/badge/status-public_research_preview-716FE5">
  <img alt="Python 3.11" src="https://img.shields.io/badge/python-3.11-4D7FC7">
  <img alt="License: Apache 2.0" src="https://img.shields.io/badge/license-Apache--2.0-3F8F78">
</p>

**Grounded cross-session experience for AI agents.**

Experience Brain is an open-source, agent-agnostic memory layer that turns grounded
agent episodes into reviewable cross-session Experience while keeping external
Knowledge separate. It is Codex CLI-first, connects through MCP, and uses append-only
JSONL so every derived lesson remains traceable to real events and outcomes.

> Project status: the local POC lifecycle is implemented and validated. The MemoryArena
> integration is dry-validation only; no controlled benchmark result or performance
> improvement claim exists yet.

## Architecture

![Experience Brain architecture](docs/assets/architecture.svg)

The canonical source of truth is intentionally small:

```text
data/events.jsonl       what happened
data/experiences.jsonl  lessons grounded in events and outcomes
data/knowledge.jsonl    digests of external sources
```

Records are append-only. A correction creates a new record that supersedes,
invalidates, refines, or retires the earlier record; raw history is not silently
rewritten.

## Knowledge Is Not Experience

![Knowledge and Experience remain distinct](docs/assets/knowledge-vs-experience.svg)

| Memory class | Meaning | Required grounding |
| --- | --- | --- |
| **Knowledge** | What the agent has read or received from an external source | Source filename, content hash, location, extractor metadata, and provenance |
| **Grounded Experience** | What the agent has actually done and learned from an observed outcome | Real evidence Event IDs, action, outcome, confidence, provenance, and lifecycle status |

External Knowledge never becomes Experience automatically. It may inform a later
action, but only a grounded episode with an observed outcome can support Experience.

## Experience Lifecycle

![Cross-session Experience Brain lifecycle](docs/assets/cross-session-lifecycle.svg)

```text
Capture -> Consolidate -> Retrieve -> Review / Update
```

Experience is retrieved before a task, around important errors or decisions, and before
final output. Retrieval considers project, situation, tool context, error signature,
outcome, evidence, authority, recency, and source project; it is not treated as keyword
similarity alone.

## What Works Today

- append-only Events, Experiences, and Knowledge with hash-chain integrity checks;
- redaction of secrets, sensitive personal or patient data, leakage-prone content, and
  hidden reasoning before storage;
- session capture, consolidation, Markdown review reports, and evidence-backed review;
- project-aware Experience retrieval and separate Knowledge retrieval;
- Knowledge Inbox for supported text, PDF, DOCX, and XLSX sources;
- Codex-compatible stdio MCP server and fallback Python CLI;
- local single-owner Streamlit Dashboard for review and ingestion;
- isolated MemoryArena adapter and C0/C1/C2 protocol dry validation.

## Install

Requirements: Git, Python `3.11`, and a local terminal. Windows PowerShell is the
primary validated environment.

### Windows PowerShell

```powershell
git clone https://github.com/siriponsri/experience-brain.git
cd experience-brain
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
experience status
experience lint
```

`experience status` should print the software version and JSONL record counts.
`experience lint` should finish with `lint passed`.

### macOS Or Linux

```bash
git clone https://github.com/siriponsri/experience-brain.git
cd experience-brain
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
experience status
experience lint
```

The Python core is cross-platform, while the current owner workflow is validated
Windows-first.

## Dashboard

The Dashboard is a local, single-owner interface with six work areas: Overview, Review
Queue, Inbox, Knowledge, Experiences, and Sessions / Events.

![Dashboard overview](docs/assets/dashboard-overview.png)

![Knowledge review in the Dashboard](docs/assets/dashboard-knowledge.png)

See the [Dashboard guide](docs/DASHBOARD_GUIDE.md) for setup, daily review, provenance
inspection, and failure handling.

## Codex And MCP

With the virtual environment active, register the local stdio server from the
repository root:

```powershell
codex mcp add experience-brain -- python -m experience_brain.mcp_server --root .
codex mcp list
```

Restart Codex after registration. `codex mcp list` should show `experience-brain` as
enabled. Start Codex from this repository so that `--root .` continues to point to the
intended local store.

The MCP server is the primary agent integration bridge. It exposes neutral session,
capture, consolidation, retrieval, Knowledge Inbox, and telemetry tools without
hard-coding a provider or model into the core schema.

See [MCP setup](docs/MCP_SETUP.md) for configuration, isolated stores, the full tool
surface, and troubleshooting.

## CLI

The `experience` CLI is a fallback operational and troubleshooting interface.

| Command | Purpose |
| --- | --- |
| `experience status` | Show software and canonical-store counts |
| `experience dashboard` | Open the local review Dashboard |
| `experience process-session` | Consolidate an incomplete or selected session |
| `experience query` | Retrieve grounded Experience |
| `experience process-inbox` | Extract supported files into Knowledge candidates |
| `experience query-knowledge` | Retrieve external Knowledge |
| `experience query-memory` | Return clearly separated Knowledge and Experience |
| `experience review-latest` | Print the latest Markdown session report |
| `experience lint` | Validate stores, evidence, and hash chains |

The [CLI reference](docs/CLI_REFERENCE.md) documents all public commands, options, safe
examples, and intended audiences.

## Step-By-Step Usage

Experience Brain uses MCP for agent activity and the Dashboard for owner review. After
the one-time installation and MCP registration above, use this workflow.

### 1. Start A Grounded Session

Open Codex in the repository and give it a concrete project name, session ID, and goal:

```text
Use the Experience Brain MCP server for this task. Start session SESSION-001 for
project demo with the goal "Fix and verify the parser tests". Record externally visible
decisions, tool activity, errors, file changes, feedback, and outcomes. Do not record
hidden chain-of-thought.
```

Codex should call `start_session`. A `session_start` Event is appended to
`data/events.jsonl`; the raw history is not rewritten later.

### 2. Retrieve Relevant Experience Before Work

Ask in natural language:

```text
query experience: How have we fixed parser test failures in this project before?
```

Codex should call `query_experience` with the current project. A first session may
correctly return no match. In later sessions, inspect the evidence and project label
before applying a retrieved lesson.

### 3. Perform The Task And Capture Outcomes

Continue the task normally in Codex. Ask it to record only externally visible facts,
such as a command result, error signature, selected approach, owner feedback, or test
outcome. Secrets, personal or patient data, benchmark leakage, and hidden reasoning are
redacted before storage.

### 4. End And Consolidate The Session

When the work is complete, state the observed result:

```text
Record that the parser tests passed, end Experience Brain session SESSION-001 with a
successful outcome, and consolidate the session.
```

Codex should call `end_session` with consolidation enabled. This creates candidate
Experience in `data/experiences.jsonl` when the evidence is sufficient and writes a
Markdown report under `reports/`.

If a session ended abnormally or was not consolidated, use:

```text
process session
```

### 5. Review The Result

Ask Codex:

```text
review latest
```

For visual review, open the local Dashboard:

```powershell
experience dashboard
```

Open **Review Queue**, inspect the evidence and provenance, then confirm, edit,
supersede, invalidate, or retire the candidate as appropriate. Daily review does not
require editing JSONL, writing Python, using Git, or knowing record IDs in advance.

### 6. Add External Knowledge When Needed

In the Dashboard, open **Inbox**, upload a supported text, PDF, DOCX, or XLSX file, and
select **Process Inbox**. Review the result under **Knowledge**. Imported material stays
Knowledge; it does not become Experience until an agent performs a grounded action and
observes an outcome.

The CLI equivalent is:

```powershell
experience process-inbox --project demo
experience query-knowledge "What does the parser guide require?" --project demo
```

### 7. Reuse Experience In The Next Session

Start a new session with a new ID, query relevant Experience before acting, and ask
Codex to record whether the retrieved item was actually used and whether the task
succeeded. This closes the Capture -> Consolidate -> Retrieve -> Review / Update loop
with traceable outcome evidence.

### Fallback CLI Walkthrough

The fallback CLI can exercise the lifecycle without MCP:

```powershell
experience start-session demo SESSION-CLI-001 --goal "Verify the parser"
experience query "How did we verify the parser before?" --project demo
experience record-event demo SESSION-CLI-001 decision agent --content "Use the focused parser test"
experience record-event demo SESSION-CLI-001 outcome agent --content "Focused parser tests passed" --outcome success
experience end-session demo SESSION-CLI-001 --summary "Parser verified" --outcome success
experience review-latest
experience lint
```

Use a unique session ID for each run. This is not a one-click installer or cloud
service; MCP remains the primary agent integration path.

## Research Evaluation

The planned controlled comparison is:

![Planned MemoryArena conditions](docs/assets/benchmark-conditions.svg)

The adapter, manifests, isolation rules, and smoke protocol have been dry-validated.
No real benchmark inference has been run. Experience Brain therefore makes **no claim
of benchmark improvement**. See [`benchmark-exp/memoryarena/`](benchmark-exp/memoryarena/)
and [EXP-04](experiments/EXP-04-memoryarena-benchmark-integration/README.md).

## Limitations

- retrieval is currently lexical and intentionally has no embeddings or vector database;
- built-in Knowledge digestion is heuristic and provider-agnostic;
- PDFs must contain extractable text; OCR is not implemented;
- the Dashboard is local and single-owner, with no authentication or cloud deployment;
- there is no REST API, knowledge graph, autonomous background agent, or multi-user service;
- benchmark performance remains unmeasured.

## Roadmap

1. **Public Research Preview** - repository, Dashboard UX, documentation, and asset quality.
2. **Isolated dogfooding** - operational validation and failure-mode discovery.
3. **Controlled benchmark** - MemoryArena C0/C1/C2 runs and ablations.
4. **Research paper** - claims only after controlled evidence is available.

See [PRODUCT.md](PRODUCT.md), [PROJECT_PLAN.md](PROJECT_PLAN.md), and the
[experiment index](experiments/INDEX.md) for the current product and research direction.

## Contributing And Security

Contributions are welcome within the current architecture and evidence requirements.
Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a change. Report vulnerabilities
privately as described in [SECURITY.md](SECURITY.md); do not include secrets, patient
data, or benchmark solutions in a public issue.

## Citation

Use the repository metadata in [CITATION.cff](CITATION.cff). Until a paper or DOI exists,
cite the software repository and the exact version or commit used.

## License

Copyright 2026 Experience Brain contributors.

Licensed under the [Apache License 2.0](LICENSE). The repository does not currently
define a separate trademark policy.
