# Experience Brain

Experience Brain is a lean, open-source, agent-agnostic memory system for AI agents.
It keeps Knowledge and Experience separate inside a brain-inspired experience lifecycle:

```text
Capture -> Consolidate -> Retrieve -> Review / Update
```

The first implementation is Codex CLI-first. The core schema and MCP interface are
kept neutral so other agent CLIs can connect later.

## Canonical Stores

Experience Brain uses three append-only JSONL files as the source of truth:

```text
data/events.jsonl
data/experiences.jsonl
data/knowledge.jsonl
```

Events record what happened. Experiences are lessons derived from grounded Agent
actions and outcomes, and must cite real event IDs as evidence. Knowledge records
what the system has read or been told from external sources, and must preserve
source filename, content hash, extractor metadata, and provenance.

The core mental model is:

```text
Knowledge = what the Agent has read
Experience = what the Agent has done
Rules = what the Owner or active project requires
Working Context = what matters now
```

Raw history is not silently rewritten. Corrections are new records that supersede,
invalidate, refine, or retire earlier records.

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
experience process-inbox
experience query-knowledge "What did the uploaded guide say?"
experience query-memory "What do we know and what have we done about this?"
experience review-latest
experience lint
```

## Knowledge Inbox

The owner can place files in `inbox/` or upload them through the local dashboard:

```text
Drop file -> process inbox -> inspect Knowledge -> Agent can retrieve it later
```

Supported initial file types are `.md`, `.txt`, `.json`, `.jsonl`, `.yaml`,
`.yml`, `.csv`, common source-code text files, text-based `.pdf`, `.docx`, and
`.xlsx`. Re-uploading unchanged content is detected by SHA-256 content hash and
does not silently create duplicate Knowledge. Unsupported, unreadable, scanned,
encrypted, image-only, audio, or video files are recorded with explicit statuses
such as `unsupported`, `needs_extractor`, or `error`.

Knowledge never becomes Experience automatically. External source says X creates
Knowledge; only an Agent action plus observed outcome can create Experience.

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

EXP-03.2 Knowledge tools:

- `list_inbox_files`
- `inspect_inbox_file`
- `extract_inbox_file`
- `process_inbox`
- `save_knowledge_digest`
- `query_knowledge`
- `query_memory`

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

It is the primary low-code review interface. The Review Queue includes every
unresolved candidate in the append-only Experience log, even when the newest
session report has no candidates. The owner can inspect evidence and confirm,
edit and confirm, reject, or retire Experiences without editing JSONL or
remembering Experience IDs.

The dashboard also includes Inbox and Knowledge views. The owner can upload files,
process supported files, inspect duplicate or error status, confirm or invalidate
Knowledge records, and view source provenance without editing JSONL.

`review latest` remains a session-level report. It is not the pending review queue.

Retrieval usage records distinguish the retrieval result (`match` / `no_match`),
usage (`used` / `not_used` / `unavailable`), and task outcome
(`success` / `failure` / `unknown`).

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
