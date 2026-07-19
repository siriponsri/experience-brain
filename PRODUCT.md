# PRODUCT.md — Experience Brain

**Status:** Product direction after `v0.3.0-poc`  
**Product stage:** Research POC → Public Research Preview  
**Primary owner persona:** Low-code / non-developer researcher or professional using an Agent CLI  
**License:** Apache License 2.0 for the project unless the owner explicitly changes it

---

## 1. Product Definition

Experience Brain is an open-source, agent-agnostic system that gives AI agents a grounded cross-session experience lifecycle.

It separates:

```text
Knowledge
= what the Agent has read or received

Experience
= what the Agent has actually done and learned from observed outcomes

Rules
= what the Owner or active project explicitly requires

Working Context
= what matters in the current task
```

The core lifecycle is:

```text
Capture
→ Consolidate
→ Retrieve
→ Review / Update
```

The product is not simply chat history, user-profile memory, or a vector database wrapper.

---

## 2. Product Promise

> Help an AI agent carry forward grounded, reviewable experience across sessions while preserving evidence and provenance.

The product should make memory:

- useful;
- traceable;
- reviewable;
- project-aware;
- provider-agnostic;
- safe to inspect;
- usable by a low-code owner.

---

## 3. Target Users

### Primary

Researchers, analysts, pharmacists, scientists, and other domain experts who:

- use an AI coding/research agent repeatedly;
- work across many sessions;
- need continuity;
- care about evidence and provenance;
- are not full-time software developers.

### Secondary

Developers building agent workflows who need:

- an MCP-compatible experience layer;
- append-only provenance;
- explicit memory lifecycle semantics;
- auditable retrieval and usage telemetry.

---

## 4. Core Jobs To Be Done

### Job A — Remember grounded lessons

> When I return to a project later, help the Agent recover lessons from work it actually performed.

### Job B — Keep external reading separate

> When I upload papers or documents, store them as Knowledge rather than pretending the Agent personally validated them.

### Job C — Let me review important memory

> When uncertain or important Experience is created, let me review it without editing raw JSON.

### Job D — Show evidence

> When the system recalls something, let me inspect where it came from.

### Job E — Work across projects safely

> Reuse relevant external-project Experience without allowing it to override owner or active-project rules.

---

## 5. Product Surfaces

### 5.1 Agent / MCP Surface

Primary work path:

```text
Codex or another Agent
→ MCP
→ Experience Brain
```

Responsibilities:

- session lifecycle;
- event capture;
- consolidation;
- retrieval;
- retrieval-usage recording;
- task outcome feedback.

### 5.2 Dashboard Surface

Primary no-code review path:

```text
Owner
→ Local Dashboard
→ Review / Inbox / Knowledge / Experiences / Sessions
```

Responsibilities:

- system overview;
- Review Queue;
- file upload and processing;
- Knowledge review;
- Experience review;
- provenance inspection;
- session/event inspection.

### 5.3 Fallback CLI

The `experience` CLI is a reliable operational and troubleshooting interface.

Document every public command in `docs/CLI_REFERENCE.md`.

---

## 6. No-Code Positioning

Current truthful positioning:

> Experience Brain provides a **no-code daily review and knowledge-ingestion workflow** through a local dashboard, with a low-code installation and Agent/MCP setup.

Do not claim:

- one-click installation;
- cloud SaaS;
- multi-user support;
- zero-configuration deployment;

until these capabilities actually exist.

---

## 7. Public Research Repo Goal

The repository should allow a new technical reader to understand the project within five minutes.

The README should answer:

1. What problem does Experience Brain solve?
2. How is Experience different from Knowledge?
3. What is the lifecycle?
4. What can I run today?
5. How do I start the Dashboard?
6. How do I connect Codex through MCP?
7. What are the CLI commands?
8. What is validated?
9. What remains unproven?
10. How is the project licensed?

---

## 8. Recommended Repository Structure

Keep the core structure lean.

Add only documentation and public-facing assets that improve usability:

```text
experience-brain/
├── README.md
├── LICENSE
├── NOTICE.md                    # optional; only if useful/needed
├── CITATION.cff                 # recommended for research repo
├── CONTRIBUTING.md              # recommended
├── SECURITY.md                  # recommended
├── CHANGELOG.md                 # recommended
├── PRODUCT.md
├── DESIGN.md
├── docs/
│   ├── CLI_REFERENCE.md
│   ├── MCP_SETUP.md
│   ├── DASHBOARD_GUIDE.md
│   ├── THAIPHALEX_PILOT.md
│   └── assets/
├── src/
├── tests/
├── experiments/
└── benchmark-exp/
```

Do not create documentation files that duplicate one another without a clear owner.

---

## 9. README Blueprint

Recommended order:

### 1. Hero

- project name;
- concise tagline;
- project status badge;
- Python version;
- license;
- test status if CI exists.

### 2. One-sentence value proposition

Example:

> Experience Brain is an open-source, agent-agnostic memory layer that turns grounded agent episodes into reviewable cross-session Experience while keeping external Knowledge separate.

### 3. Architecture visual

Use an original SVG.

### 4. Knowledge vs Experience

A compact two-column explanation.

### 5. What works today

Be explicit.

### 6. Quick Start

Shortest validated local path.

### 7. Dashboard

Include actual screenshots.

### 8. MCP / Codex integration

Minimal working configuration.

### 9. CLI

Short table + link to full reference.

### 10. Research evaluation

Explain MemoryArena adapter status without performance claims.

### 11. ThaiPhaLex pilot

Describe as dogfooding / real-world pilot, not benchmark proof.

### 12. Limitations

Keep visible.

### 13. Roadmap

Short and honest.

### 14. Citation

Link to `CITATION.cff`.

### 15. License

Apache-2.0.

---

## 10. CLI Documentation Requirement

The public CLI reference must document at least the currently exposed commands:

```text
experience status
experience lint
experience dashboard
experience import
experience start-session
experience end-session
experience record-event
experience process-session
experience query
experience review-latest
experience list-inbox
experience process-inbox
experience query-knowledge
experience query-memory
experience record-retrieval-usage
```

For each command include:

- purpose;
- common syntax;
- one safe example;
- when a normal owner should use it;
- whether it is primarily for Agent/MCP, owner workflow, research telemetry, or troubleshooting.

Do not document commands that do not exist.

---

## 11. ThaiPhaLex IS1 Pilot

The first real-world dogfooding target may be ThaiPhaLex IS1.

This is a **pilot**, not controlled benchmark evidence.

### Pilot goals

Validate:

- cross-session continuity;
- memory relevance;
- retrieval usefulness;
- harmful / irrelevant retrievals;
- review burden;
- knowledge ingestion in a real research workflow;
- separation between external Knowledge and grounded Experience;
- operational reliability.

### Isolation

Use an isolated store for the ThaiPhaLex pilot.

Do not mix:

- Experience Brain development store;
- ThaiPhaLex pilot store;
- MemoryArena C0/C1/C2 stores.

### Suggested experiment

```text
EXP-05 — ThaiPhaLex Cross-Session Research Workflow Pilot
```

Suggested metrics:

- number of sessions;
- events captured;
- Experiences proposed;
- Experiences confirmed;
- Knowledge items;
- retrievals;
- retrieved Experiences actually used;
- useful retrievals;
- irrelevant retrievals;
- harmful retrievals;
- owner review burden;
- failures;
- latency where practical.

Optional owner usefulness score:

```text
0 = harmful
1 = irrelevant
2 = somewhat useful
3 = useful
4 = very useful
```

Do not claim task-performance improvement from uncontrolled pilot observations.

---

## 12. Controlled Benchmark Strategy

After dogfooding and critical blocker fixes:

```text
C0 — No Persistent Memory
C1 — Raw Episode Memory
C2 — Full Experience Brain
```

Hold constant where practical:

- model;
- reasoning configuration;
- task order;
- tools;
- retry policy;
- evaluator;
- limits.

Primary research outcome:

- task success / benchmark score.

Supporting:

- retries;
- errors;
- tool failures;
- time;
- tokens;
- retrieval usage;
- harmful retrievals.

No benchmark-performance claim should appear in README until real controlled evidence exists.

---

## 13. Product Roadmap

### Milestone A — `v0.3.0-poc`

Status: frozen technical POC.

Includes:

- append-only Events;
- Experience lifecycle;
- MCP;
- Dashboard;
- Review Queue;
- Knowledge Inbox;
- unified Knowledge + Experience retrieval;
- MemoryArena dry adapter.

### Milestone B — Public Research Preview

Goals:

- professional README;
- design system;
- improved Dashboard;
- complete CLI reference;
- MCP setup guide;
- screenshots;
- original architecture visuals;
- contribution / security / citation metadata;
- no-code workflow clarity.

### Milestone C — ThaiPhaLex Dogfooding

Goals:

- real multi-session use;
- failure-mode discovery;
- critical fixes only.

### Milestone D — Controlled Benchmark

Goals:

- MemoryArena C0/C1/C2;
- protocol freeze;
- statistical analysis;
- ablations.

### Milestone E — Paper

Goals:

- system contribution;
- method contribution;
- benchmark evidence;
- real-world pilot evidence where appropriate.

---

## 14. Licensing and Asset Protection

The project is currently Apache License 2.0.

### Repository rules

- Keep a root `LICENSE` file.
- State the license clearly in README.
- Add copyright notice where desired.
- Do not remove existing attribution or license notices.
- Add `NOTICE.md` if the project begins distributing material that requires notices.
- Add `THIRD_PARTY_NOTICES.md` if third-party code/assets with attribution requirements are bundled.
- Verify licenses before incorporating templates, icons, screenshots, fonts, or illustrations.
- Prefer original repository-created SVG/Mermaid assets.
- Do not commit externally sourced design-reference images without confirmed redistribution rights.

### Branding

Open-source licensing of code does not automatically define trademark policy.

If the project later needs brand-name/logo protection, handle that separately from the software license and obtain appropriate legal advice.

This document is a product policy, not legal advice.

---

## 15. Security and Privacy Position

Public documentation must emphasize:

- local-first POC;
- no intentional secret storage;
- no `.env` commit;
- redaction before storage;
- patient / sensitive personal data protections;
- benchmark leakage controls;
- no hidden chain-of-thought storage.

Add a `SECURITY.md` describing responsible reporting and safe handling expectations.

---

## 16. Professionalization Sprint Acceptance Criteria

The sprint is complete when:

- `v0.3.0-poc` remains immutable;
- work occurs on a new branch;
- README is rewritten for an international audience;
- architecture visuals are original and committed with clear provenance;
- Dashboard is redesigned without breaking current workflows;
- screenshots come from the actual running application;
- CLI reference matches actual commands;
- MCP setup is independently understandable;
- no-code workflow is explicitly documented;
- LICENSE remains present;
- third-party assets are reviewed for licensing;
- all tests, lint, formatting, typing, and store-integrity checks pass;
- no benchmark-performance claim is introduced;
- no new core feature is added unless required to preserve an existing workflow;
- no tag, merge, or push occurs without owner approval.

---

## 17. Decision Principle

During this sprint:

> Improve presentation, usability, documentation, and operator clarity — not the memory algorithm.

Any proposed change to:

- retrieval algorithm;
- Experience semantics;
- canonical stores;
- benchmark conditions;
- MCP contract;

must be treated as a separate architecture/research decision rather than hidden inside UI polish.
