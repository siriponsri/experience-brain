# Security Policy

## Supported Version

Security fixes target the current public research preview. Earlier POC tags are frozen
research artifacts and may not receive fixes.

## Reporting A Vulnerability

Use GitHub's private vulnerability reporting for this repository when available. Do not
open a public issue containing exploit details, credentials, private data, patient data,
benchmark solutions, or a copy of a sensitive store.

Include the affected version or commit, operating system, reproduction steps using
synthetic data, impact, and any proposed mitigation. Maintainers will acknowledge and
triage the report before public disclosure.

## Local-First Boundary

The Dashboard is a local single-owner application with no authentication. Do not expose
it directly to an untrusted network. MCP is a local stdio integration in the reference
setup, not a hosted security boundary.

## Sensitive Data

Experience Brain attempts to redact secrets, sensitive personal and patient data,
benchmark leakage, and hidden reasoning before storage. Redaction is defense in depth,
not a guarantee. Review sources before ingestion and use synthetic data in reports,
tests, and vulnerability reproductions.

Never commit `.env` files, credentials, production traces, patient records, or private
pilot stores. If a secret is committed, revoke it first; removing it from the latest
commit is not sufficient remediation.
