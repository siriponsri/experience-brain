# Codex MCP Wiring

Experience Brain exposes a stdio MCP server named `experience-brain`.

Install the package first:

```powershell
python -m pip install -e .[dev]
```

Then add the server to Codex CLI:

```powershell
codex mcp add experience-brain -- python -m experience_brain.mcp_server --root .
```

Equivalent local config stanza:

```toml
[mcp_servers.experience-brain]
command = "python"
args = ["-m", "experience_brain.mcp_server", "--root", "."]
cwd = "."
```

Minimum tools:

- `start_session`
- `end_session`
- `record_event`
- `process_session`
- `query_experience`
- `review_latest`
- `record_retrieval_usage`
- `record_outcome_feedback`

Knowledge Inbox tools added in EXP-03.2:

- `list_inbox_files`
- `inspect_inbox_file`
- `extract_inbox_file`
- `process_inbox`
- `save_knowledge_digest`
- `query_knowledge`
- `query_memory`

Use `process_inbox` for the owner command `process inbox`. It discovers files in
`inbox/`, extracts supported text, applies redaction, records source provenance,
deduplicates by SHA-256 content hash, and appends Knowledge records to
`data/knowledge.jsonl`. `query_memory` returns separated `knowledge` and
`experience` sections; do not merge the two into one undifferentiated memory list.

Default runtime for EXP-03 is GPT-5.5 with medium reasoning effort. Record
agent, model, reasoning effort, software version, experiment ID, and run ID in
event provenance.
