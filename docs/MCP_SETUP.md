# MCP Setup

Experience Brain exposes a local stdio MCP server named `experience-brain`. MCP is the
primary integration bridge for Codex and other compatible agents; the Python CLI is a
fallback interface.

## Install

From the repository root with Python 3.11:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Confirm the server entry point is available:

```powershell
experience-brain-mcp --help
```

## Register With Codex

```powershell
codex mcp add experience-brain -- python -m experience_brain.mcp_server --root .
codex mcp list
```

Equivalent Codex configuration:

```toml
[mcp_servers.experience-brain]
command = "python"
args = ["-m", "experience_brain.mcp_server", "--root", "."]
cwd = "."
```

Restart Codex after changing MCP configuration. Keep `cwd` and `--root` pointed at the
same intended store unless there is a deliberate reason to separate them.

## Tool Surface

| Tool | Role |
| --- | --- |
| `start_session` | Start a traceable session |
| `end_session` | End a session and optionally consolidate it |
| `record_event` | Capture a neutral typed event |
| `process_session` | Consolidate a selected or incomplete session |
| `query_experience` | Retrieve grounded Experience |
| `review_latest` | Read the latest Markdown consolidation report |
| `record_retrieval_usage` | Record match, use, stage, and task outcome |
| `record_outcome_feedback` | Record owner feedback tied to observed work |
| `list_inbox_files` | List Inbox files and processing status |
| `inspect_inbox_file` | Inspect a file before extraction |
| `extract_inbox_file` | Extract supported source content |
| `process_inbox` | Extract, redact, deduplicate, and append Knowledge |
| `save_knowledge_digest` | Save an agent-produced Knowledge digest with provenance |
| `query_knowledge` | Retrieve external Knowledge |
| `query_memory` | Retrieve separately labeled Knowledge and Experience |

`query_memory` does not merge the two memory classes. Consumers must preserve the
`knowledge` and `experience` sections and their different evidence requirements.

## Provenance

Pass the actual agent, model, reasoning effort, software version, experiment ID, and run
ID whenever they are available. The core schema does not require one provider or model.
Do not put hidden chain-of-thought in event content or provenance.

## Isolated Store

For an experiment or external project, point MCP at a dedicated root outside the
development repository:

```powershell
codex mcp add thaiphalex-experience-brain -- `
  python -m experience_brain.mcp_server `
  --root "C:\ResearchStores\thaiphalex-is1"
```

The root will contain its own `data/`, `inbox/`, and `reports/`. Never point a pilot at
the development store or a MemoryArena condition store.

## Troubleshooting

```powershell
experience status --root .
experience lint --root .
python -m experience_brain.mcp_server --root .
```

- If Codex cannot see tools, restart it and run `codex mcp list`.
- If the wrong data appears, inspect the configured `cwd` and `--root`.
- If store integrity fails, stop writes and run `experience lint`; do not edit JSONL.
- If a source file fails, inspect the Inbox status in the Dashboard and use Retry only
  after correcting the source or extractor condition.

## Trust Boundary

MCP input and imported files are untrusted until validated and redacted. External
Knowledge cannot become active Experience without grounded first-party episode evidence
or explicit owner confirmation.
