# CLI Reference

`experience` is the fallback local interface for setup, troubleshooting, explicit
processing, and research telemetry. Normal daily review is simpler in the Dashboard;
agent workflows should use MCP.

Run `experience COMMAND --help` for every option.

| Command | Audience | Purpose and safe example |
| --- | --- | --- |
| `status` | Owner / troubleshooting | Show software and store counts. `experience status --root .` |
| `lint` | Owner / CI | Validate JSONL parsing, hashes, lineage, and evidence. `experience lint --root .` |
| `dashboard` | Owner | Open the local review app. `experience dashboard --root .` |
| `import` | Troubleshooting | Import validated Event JSONL. `experience import trace.jsonl --root .` |
| `start-session` | Agent / telemetry | Start a session. `experience start-session demo SESSION-001 --goal "Validate the parser" --root .` |
| `end-session` | Agent / telemetry | End and normally consolidate a session. `experience end-session demo SESSION-001 --summary "Focused tests passed" --outcome success --root .` |
| `record-event` | Agent / telemetry | Append a neutral event. `experience record-event demo SESSION-001 decision agent --content "Use the existing fixture" --root .` |
| `process-session` | Owner / recovery | Consolidate an incomplete or selected session. `experience process-session --session-id SESSION-001 --root .` |
| `query` | Agent / owner | Retrieve grounded Experience. `experience query "How did we fix parser setup?" --project demo --root .` |
| `review-latest` | Owner | Print the latest session report. `experience review-latest --root .` |
| `list-inbox` | Owner / troubleshooting | List source files and processing state. `experience list-inbox --root .` |
| `process-inbox` | Owner | Extract supported files into Knowledge candidates. `experience process-inbox --project demo --root .` |
| `query-knowledge` | Agent / owner | Retrieve external Knowledge. `experience query-knowledge "What does the parser guide require?" --project demo --root .` |
| `query-memory` | Agent / owner | Retrieve separately labeled Knowledge and Experience. `experience query-memory "parser setup" --project demo --root .` |
| `record-retrieval-usage` | Agent / research | Record what was retrieved and used. `experience record-retrieval-usage demo SESSION-002 "parser setup" --retrieved-experience-id EXP-001 --used-experience-id EXP-001 --task-outcome success --root .` |

## Common Options

- `--root PATH` selects the Experience Brain store. The default is the current directory.
- `--project NAME` limits retrieval or assigns imported Knowledge to a project.
- `--limit N` limits retrieval results.
- provenance options on session and Inbox commands include `--agent`, `--model`,
  `--reasoning-effort`, `--experiment-id`, and `--run-id`.

Use a dedicated `--root` for experiments and pilots. Store roots must not overlap.

## Owner Commands

Most owners need only:

```powershell
experience status
experience dashboard
experience process-session
experience review-latest
experience lint
```

The Dashboard handles file upload, Inbox processing, Knowledge review, Experience
review, provenance inspection, and session inspection without requiring record IDs.

## Agent And MCP Equivalents

The CLI command names are not the MCP protocol. For example, `experience query` maps to
the `query_experience` MCP tool, and `experience process-inbox` maps to `process_inbox`.
See [MCP_SETUP.md](MCP_SETUP.md) for the canonical MCP surface.

## Import Safety

`experience import` accepts Event JSONL that validates against the current schema. It is
for controlled trace import, not arbitrary documents. External documents belong in the
Knowledge Inbox. Review imported content for secrets, personal or patient data,
benchmark leakage, and hidden reasoning before import.
