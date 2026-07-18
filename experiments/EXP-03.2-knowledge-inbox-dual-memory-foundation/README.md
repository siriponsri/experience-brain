# EXP-03.2 - Knowledge Inbox and Dual-Memory Foundation

## Purpose

Extend Experience Brain from an Experience-only POC into a dual-memory system:

```text
Knowledge = what the Agent has read
Experience = what the Agent has done
Rules = what the Owner or active project requires
Working Context = what matters now
```

## Software Version

`v0.2.3`

## Parent Experiment

`EXP-03.1 - Owner Review Dashboard`

## Exact Change

- Added append-only `data/knowledge.jsonl` as the third canonical store.
- Added `Knowledge` schema with source filename, content hash, source type,
  source location, extractor metadata, status, provenance, and append-only
  review lineage.
- Added top-level `inbox/` for owner-managed file drop workflows.
- Added extractor registry for `.md`, `.txt`, `.json`, `.jsonl`, `.yaml`,
  `.yml`, `.csv`, common source-code text files, text-based `.pdf`, `.docx`,
  and `.xlsx`.
- Added explicit unsupported, needs-extractor, duplicate, and error statuses.
- Added Dashboard Inbox and Knowledge views.
- Added CLI and MCP workflows for `process inbox`, Knowledge query, and
  separated Knowledge/Experience unified retrieval.

## Expected Benefit

The owner can add external source material without editing JSONL, and an Agent
can retrieve source-provenanced Knowledge separately from grounded Experience.

## Risks

- Retrieval remains lexical and is an interim POC implementation.
- The built-in digest is heuristic and provider-agnostic; Agents can provide
  better semantic digests through MCP without hard-coding a provider.
- PDF support is text-extraction only. Scanned/image-only files are not OCRed.
- Office extractors depend on local Python packages declared in `pyproject.toml`.

## Evidence Sources

- `tests/test_knowledge_inbox.py`
- `tests/test_dashboard.py`
- `tests/test_live_codex_mcp_integration.py`
- `src/experience_brain/knowledge.py`
- `data/knowledge.jsonl`

## Summary of Results

Validation passed. The isolated Knowledge Inbox smoke test covered Markdown/TXT,
JSON, XLSX, duplicate content, and an unsupported binary file. Supported files
created append-only Knowledge records with source hashes, extractor metadata,
redaction provenance, and source filenames. Reprocessing unchanged files returned
duplicate status without silently appending duplicate Knowledge.

Knowledge retrieval returned source-provenanced Knowledge. Experience retrieval
continued to return grounded Experience with evidence Event IDs. Unified retrieval
returned clearly separated Knowledge and Experience sections. An unrelated query
did not retrieve the test Knowledge as primary context.

Dashboard startup, Dashboard owner views, MCP startup, MCP `process_inbox`,
pytest, Ruff, mypy, and `experience lint` passed.

No MemoryArena real inference was started.

## Limitations

This experiment creates the Knowledge Inbox and dual-memory foundation only. It
does not make a benchmark performance claim and does not change the broader
MemoryArena research protocol.

## Decision

Keep as the POC dual-memory foundation. Do not begin real MemoryArena inference
until the benchmark protocol is reviewed and frozen.
