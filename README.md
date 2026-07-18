# Experience Brain

Experience Brain is a lean, open-source, agent-agnostic experience system for AI agents.
It models experience as a grounded lifecycle:

```text
Capture -> Consolidate -> Retrieve -> Review / Update
```

The first implementation is Codex CLI-first. The core schema and MCP interface are
kept neutral so other agent CLIs can connect later.

## Canonical Stores

Experience Brain uses two append-only JSONL files as the source of truth:

```text
data/events.jsonl
data/experiences.jsonl
```

Events record what happened. Experiences are derived records that must cite real
event IDs as evidence. Raw history is not silently rewritten; corrections are new
records that supersede, invalidate, refine, or retire earlier records.

## Owner Workflow

The primary workflow is through an Agent CLI connected to the MCP server:

```text
Codex or another Agent CLI -> MCP -> Experience Brain
```

Primary owner commands are:

```text
process session
query experience: <question>
review latest
```

The fallback Python CLI is named `experience`:

```powershell
python -m pip install -e .[dev]
experience status
experience process-session
experience query "How did we fix this before?"
experience review-latest
experience lint
```

## MCP Server

The MCP server name is `experience-brain`.

```powershell
experience-brain-mcp
```

EXP-03 MCP tools:

- `start_session`
- `end_session`
- `record_event`
- `process_session`
- `query_experience`
- `review_latest`
- `record_retrieval_usage`
- `record_outcome_feedback`

Codex CLI can be wired to the local MCP server with:

```powershell
codex mcp add experience-brain -- python -m experience_brain.mcp_server --root .
```

Or add this server stanza to a local Codex config:

```toml
[mcp_servers.experience-brain]
command = "python"
args = ["-m", "experience_brain.mcp_server", "--root", "."]
cwd = "."
```

Use GPT-5.5 with medium reasoning for normal POC work. Escalate reasoning only
for complex debugging or architecture blockers, then record the escalation in
provenance.

## Dashboard

The local single-owner dashboard uses Streamlit:

```powershell
experience dashboard
```

It displays events, experiences, the latest Markdown review report, and lint status.

## Development

```powershell
python -m pip install -e .[dev]
python -m pytest
ruff check .
ruff format --check .
mypy src tests
experience --help
```

## Scope

This POC intentionally does not include a benchmark harness, vector database,
knowledge graph, cloud deployment, REST API, autonomous background agent, or
multi-user service. Benchmark and paper work are deferred until the POC lifecycle
works end to end.

## License

Apache License 2.0.
