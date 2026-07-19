# Dashboard Guide

The Streamlit Dashboard is Experience Brain's local, single-owner review interface. It
supports a no-code daily review and Knowledge-ingestion workflow after one-time setup.

## Start

```powershell
.\.venv\Scripts\Activate.ps1
experience dashboard --root .
```

The browser UI is local. This preview has no login, cloud deployment, or multi-user
access control; do not expose it to an untrusted network.

## Daily Workflow

1. Open **Overview** and confirm Store Integrity is healthy.
2. Upload supported files in **Inbox**, then select **Process Inbox**.
3. Inspect the result for every file; use Retry only after correcting a failure.
4. Review digests and source provenance in **Knowledge**.
5. Confirm or edit candidates in **Review Queue**.
6. Inspect grounded lessons and evidence in **Experiences**.
7. Use **Sessions / Events** when the origin of a decision or outcome needs review.

No step requires JSONL editing, Python code, Git, or advance knowledge of record IDs.

## Views

### Overview

Shows the software version, store health, active or confirmed Experience, current
Knowledge, pending reviews, sessions, latest session, latest experiment, and recent
activity derived from local records. It does not display fabricated usage or benchmark
metrics.

### Review Queue

Shows unresolved candidate Experience with situation, goal, confidence, source session,
and evidence. Available actions are Confirm, Edit and Confirm, and Reject / Invalidate.
Every action appends a lineage record; it never overwrites the candidate.

### Inbox

Uploads files into the selected store's `inbox/` directory and processes supported
formats. Duplicate content is detected by SHA-256 hash. Unsupported or unreadable files
remain visible with an explicit status and error.

### Knowledge

Shows external-source digests, claims, applicability, source type, hash, extractor, and
provenance. Knowledge can be confirmed, invalidated, or retired. These actions do not
create Experience.

### Experiences

Shows grounded lessons with evidence Events, project scope, confidence, owner state,
lineage, and internal versus External Project Experience. Active or confirmed items may
be retired without deleting history.

### Sessions / Events

Shows a human-readable event timeline. Raw Event JSON and the latest Markdown review
report stay inside expanders.

## Supported Inbox Sources

The current extractors support Markdown, plain text, JSON/JSONL, YAML, CSV, common source
code and configuration text, text-based PDF, DOCX, and XLSX. Scanned/image-only PDF,
encrypted documents, images, audio, and video are not OCRed or transcribed.

## Safety

- Review sources before upload; converted content is untrusted evidence.
- Do not upload real patient data, credentials, `.env` files, benchmark solutions, or
  hidden chain-of-thought.
- Inspect redaction provenance when sensitive patterns may have appeared.
- If Store Integrity fails, stop review actions and run `experience lint --root PATH`.
- Never repair a JSONL file by hand. Represent corrections through review actions.

## Isolated Projects

Launch the same Dashboard against a separate root for pilots or experiments:

```powershell
experience dashboard --root "C:\ResearchStores\thaiphalex-is1"
```

The header and Overview identify the active store. Confirm the root before uploading or
reviewing data.
