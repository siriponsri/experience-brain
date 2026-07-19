# HANDOFF.md — Experience Brain

**Repository:** https://github.com/siriponsri/experience-brain  
**Owner:** Siripon  
**Owner profile:** Pharmacist, low-code / low-dev user  
**Primary interface:** Codex CLI in VS Code Terminal  
**Primary development model preference:** GPT-5.5, medium reasoning by default; high only for difficult architecture/debugging  
**License:** Apache License 2.0  
**Handoff date:** 2026-07-18

---

## 1. Purpose of This Handoff

This file summarizes the owner decisions, architecture, implementation progress, live validation, and research plan established in the previous session.

The next session should continue from the **local repository state**, not assume that the GitHub `main` branch contains the latest work.

At the time of handoff:

- GitHub remote `main` still appears to be behind the local reframe work.
- The local branch used for the reframe is `reframe/v0.2.0`.
- Do **not** reset local work to remote `main`.
- Do **not** push, merge, retag, or rewrite history without explicit owner approval.

The next session must first inspect:

```powershell
git branch --show-current
git status
git log --oneline --decorate -15
git tag --list
```

Then read the canonical project documents before making changes.

---

## 2. Canonical Project Documents

Read completely:

- `AGENTS.md`
- `PROJECT_PLAN.md`
- `OWNER_GUIDE_TH.md`
- `experiments/INDEX.md`
- `README.md`
- this `HANDOFF.md`

Also inspect the latest experiment records under:

- `experiments/EXP-03*`
- `benchmark-exp/memoryarena/`

Treat `AGENTS.md` and `PROJECT_PLAN.md` as authoritative unless a later explicit owner decision in this handoff supersedes them.

---

## 3. Core Vision

The project is **Experience Brain**.

The goal is to build an open-source, agent-agnostic system that allows AI agents to accumulate grounded experience across sessions and later prove its value with existing benchmark datasets.

The long-term sequence is:

```text
Build the system
→ Validate the system end to end
→ Test on existing benchmark datasets
→ Perform controlled experiments and ablations
→ Write paper / arXiv
→ Later real-world pilots: LabLoop and ThaiPhaLex
```

The project is **not** merely:

- chatbot memory
- user-profile memory
- a vector database wrapper
- a research wiki
- a chat-history RAG system
- hidden chain-of-thought storage
- a framework tied to one model/provider
- an autonomous self-improving AGI system

Preferred paper framing:

1. **System contribution** — open-source Experience Brain architecture
2. **Method contribution** — grounded brain-inspired experience lifecycle
3. **Empirical contribution** — benchmark evidence and ablations

Use cautious language such as:

> A brain-inspired experience lifecycle that enables AI agents to learn from grounded episodes across sessions.

Do not claim that the system reproduces the human brain.

---

## 4. Current Mental Model

The system now has distinct information sources.

### 4.1 Working Context

What matters in the current task/session.

### 4.2 Rules / Preferences

What the owner or active project explicitly requires.

Authority order:

1. Owner
2. Active project rule
3. Feedback from real outcomes
4. Repeatedly successful Experience

### 4.3 Experience Memory

**What the Agent has actually done and learned through grounded action and outcomes.**

Canonical store:

```text
data/experiences.jsonl
```

Every Experience must trace back to real Events.

### 4.4 Knowledge Memory

**What the Agent has read or received from external sources.**

Canonical store:

```text
data/knowledge.jsonl
```

Critical semantic rule:

```text
External source says X
→ Knowledge

Agent performs X and observes an outcome
→ Experience
```

Never convert a statement from a paper or uploaded document into an Experience as if the Agent had personally tested it.

---

## 5. Canonical Data Stores

The original two-store design was intentionally extended to three append-only stores.

```text
data/events.jsonl
data/experiences.jsonl
data/knowledge.jsonl
```

Meaning:

- `events.jsonl` = what actually happened
- `experiences.jsonl` = what was learned from grounded Agent episodes/outcomes
- `knowledge.jsonl` = what was extracted/digested from external information

Principles:

- append-only
- provenance-preserving
- stable IDs
- supersession/invalidation rather than destructive rewriting
- no vector database yet
- no knowledge graph yet

---

## 6. Primary Experience Lifecycle

```text
Capture
→ Consolidate
→ Retrieve
→ Review / Update
```

### Capture

Capture Agent/session events through MCP or middleware.

### Consolidate

Hybrid session processing:

- normal session end may consolidate automatically
- `process session` handles incomplete/old/manual reprocessing
- candidate Experience is generated from grounded events
- uncertain/important candidates enter Review Queue

### Retrieve

Retrieval must clearly distinguish:

```text
Relevant Knowledge
Relevant Experience
```

### Review / Update

The owner must not edit JSONL manually.

The owner workflow is through:

- Dashboard
- Agent CLI / MCP
- Markdown reports

---

## 7. Low-Code Owner Workflow

Main Agent commands:

```text
process session
query experience: <question>
review latest
process inbox
```

Secondary workflows:

```text
status
lint experience
dashboard
compare EXP-XX with EXP-YY
```

Preferred principle:

> Agent CLI is the primary workspace.  
> MCP is the execution bridge.  
> JSONL is the source of truth.  
> Dashboard and Markdown make the system reviewable.

The owner should not need to:

- edit JSONL
- remember Experience IDs
- manually change status fields
- write Python for normal use

---

## 8. Dashboard State

EXP-03.1 implemented a working low-code Review Dashboard.

Completed features reported:

- persistent Review Queue
- Overview
- Experiences
- Sessions / Events
- append-only Confirm
- Edit and Confirm
- Reject / Invalidate
- Retire
- explicit retrieval result / usage / task outcome semantics

The previously proposed isolation Experience:

```text
EXP-327D87ACD4
```

was confirmed through the Dashboard as revision:

```text
EXP-327D87ACD4-REV-20260718122242684951-A7152DA6
```

Validation reported:

- related query retrieved the confirmed revision
- unrelated clinical query returned no match
- provenance/hash integrity remained valid

Known limitation:

- retrieval remains lexical and may match on shared terms even when intent differs

---

## 9. Live MCP Validation

EXP-03 implemented the live MCP workflow.

Known local commits reported:

```text
0601b02  feat: add live MCP session workflow
56137ac  docs: record exp-03 mcp integration
```

MCP tools include workflows for:

- start session
- end session
- record events
- process session
- query Experience
- latest review
- retrieval usage
- outcome feedback

A live three-session owner validation was performed.

### Session 1

Session:

```text
EB-20260718-BENCH-ISO-01
```

Recorded decision:

> Keep benchmark-specific code in `benchmark-exp/memoryarena/adapter` and `benchmark-exp/memoryarena/scripts`, with condition-scoped stores under `benchmark-exp/memoryarena/runs/EXP-04/stores/<condition>/<task_group>`, while keeping `src/experience_brain` generic and letting the adapter own leakage scanning and benchmark glue.

Result:

- Events recorded
- Experience candidate created
- status initially `proposed`

### Session 2

The proposed Experience was not returned because retrieval only allowed active/confirmed/refined records.

This was correct behavior under Reviewable Automation.

### Dashboard review

The owner then confirmed the Experience through EXP-03.1.

A later related query successfully retrieved the confirmed Experience.

### Negative control

An unrelated query did not retrieve the benchmark-isolation Experience as primary context.

Conclusion:

> Basic live cross-session MCP + reviewed Experience retrieval is functioning.

---

## 10. Knowledge Inbox / Dual-Memory State

EXP-03.2 was completed.

Reported local commit:

```text
2e1f3d8  EXP-03.2 — Knowledge Inbox & Dual-Memory Foundation
```

Software status reported:

```text
Experience Brain v0.2.3
events=9
experiences=2
knowledge=0
```

The zero Knowledge count is expected if the owner has not yet processed real files in the main store.

### Inbox

Top-level:

```text
inbox/
```

Low-code flow:

```text
Drop file into inbox/
→ process inbox
→ extract
→ redact
→ classify/digest
→ Knowledge record
→ provenance retained
→ retrieve later
```

Dashboard also supports Inbox + Knowledge views.

### Supported file types

Reported support:

- `.md`
- `.txt`
- `.json`
- `.jsonl`
- `.yaml`
- `.yml`
- `.csv`
- common text source-code files
- text-based `.pdf`
- `.docx`
- `.xlsx`

Unsupported/scanned/encrypted/non-text files must produce explicit statuses such as:

- `unsupported`
- `needs_extractor`
- `error`

No silent failure.

### EXP-03.2 validation

Reported:

- `python -m pytest` → 22 passed
- Ruff check passed
- Ruff format check passed
- strict mypy passed
- `experience lint` passed
- Dashboard health passed
- MCP tool listing passed
- `process_inbox` passed
- `query_memory` passed
- isolated Inbox smoke passed for:
  - Markdown/TXT
  - JSON
  - XLSX
  - duplicate
  - unsupported binary
- existing EXP-03/EXP-03.1 regression coverage passed

Known limitations:

- lexical retrieval is interim
- built-in Knowledge digest is heuristic/provider-agnostic
- PDF is text-only
- no OCR/multimodal extraction

---

## 11. Data Safety / Redaction

Before storage, redact or block:

- API keys
- tokens
- passwords
- credentials
- `.env` contents
- PII
- patient data
- sensitive personal data
- benchmark gold answers / leakage-prone evaluator information
- hidden chain-of-thought

External documents are Knowledge, not automatically trusted Experience.

---

## 12. Repository Reframe History

The owner authorized a breaking reframe.

Pre-reframe freeze:

```text
pre-reframe-v0.1.0
```

Freeze commit:

```text
dd2d3cf98d65b816f1ee79222d5ffc6e4e02d372
```

Local reframe branch:

```text
reframe/v0.2.0
```

Known local commits reported during the session:

```text
dd2d3cf98d65b816f1ee79222d5ffc6e4e02d372  docs: freeze owner reframe instructions
f2e5d67  remove obsolete environment report
2be0a93  add lean Experience Brain foundation
0601b02  feat: add live MCP session workflow
56137ac  docs: record exp-03 mcp integration
f5ff072d4fb66af67687778a43117b0bd923fc7f  MemoryArena adapter implementation
b6fb7e0  EXP-04 records
2e1f3d8  EXP-03.2 Knowledge Inbox & Dual-Memory Foundation
```

The exact commit ID for EXP-03.1 was not captured in the conversation; inspect local `git log`.

Important:

- GitHub remote currently may not contain these later local commits.
- Do not assume remote `main` is authoritative.
- Do not reset/rebase away local work.
- Do not push until the owner explicitly approves.

---

## 13. MemoryArena Research Track

Location:

```text
benchmark-exp/memoryarena/
```

Principle:

```text
src/experience_brain/
= product/core system

benchmark-exp/memoryarena/
= research harness / evaluation integration
```

### EXP-04

EXP-04 — MemoryArena Benchmark Integration and Smoke Study

Official sources used:

- Project: https://memoryarena.github.io/
- Code: https://github.com/ZexueHe/MemoryArena
- Dataset: https://huggingface.co/datasets/ZexueHe/memoryarena
- Paper reference used during setup: https://huggingface.co/papers/2602.16313

Pinned during setup:

```text
MemoryArena commit:
6cd9de14b71915e39ac742a20dc33785e14b6aab

Dataset revision:
da1a37c8b19280e18627ca01cf368195a5e1d92e

Deterministic smoke task IDs:
0, 1, 2, 3, 4
```

Implemented:

- adapter
- configs
- manifests
- protocol draft
- citation note
- dry-run script
- result serialization

Integrated MemoryArena memory shape:

```text
add_chunk(chunk)
wrap_user_prompt(question)
```

Dry validation passed for C0/C1/C2.

No real benchmark inference has been run yet.

---

## 14. Planned Benchmark Conditions

### C0 — No Persistent Memory

No persistent cross-session memory.

### C1 — Raw Episode Memory

Persist prior grounded action/observation/feedback/outcome episodes.

No Experience Brain consolidation into generalized Experience.

### C2 — Full Experience Brain

Use:

```text
Capture
→ Consolidate
→ Retrieve
→ Review / Update logic
```

For automated benchmark runs, no human review can occur after the run begins.

A deterministic **Benchmark Automation Mode** may therefore be needed for C2.

It must:

- remain isolated from normal owner Reviewable Automation
- activate only benchmark-eligible candidates according to frozen deterministic rules
- preserve provenance
- avoid gold/evaluator leakage
- be identical across all C2 runs
- be documented before full inference

---

## 15. Benchmark Fairness Requirements

Hold constant across C0/C1/C2 where possible:

- base model
- model version
- reasoning configuration
- task order
- tool access
- prompt outside memory-specific additions
- retries
- token limits
- time limits
- evaluator
- scoring

Primary variable:

```text
memory condition
```

Use isolated stores for:

```text
condition × task group
```

Never share memory between C0/C1/C2.

Do not contaminate unrelated task groups unless official protocol explicitly requires it.

Gold answers/evaluator-only information must never enter reusable Knowledge or Experience.

---

## 16. Initial Benchmark Scope

Start with MemoryArena:

```text
formal_reasoning_math
```

First real inference should remain a deterministic 5-task engineering smoke:

```text
Task IDs: 0,1,2,3,4
Conditions: C0,C1,C2
```

This smoke is for pipeline validation only.

Do not:

- tune C2 to these five tasks
- select a winning method from smoke
- make publication claims

After smoke passes:

1. review/freeze `PROTOCOL.md`
2. run full formal reasoning subset under frozen protocol
3. perform statistical analysis
4. add ablations
5. consider a second benchmark later

---

## 17. OpenRouter Plan

The owner intends to use VS Code Terminal and may use OpenRouter with a small/low-cost model for early real inference.

OpenRouter is intended for the **MemoryArena model provider**, not as a replacement for Experience Brain MCP.

Conceptual separation:

```text
Codex CLI
→ MCP
→ Experience Brain


MemoryArena
→ OpenRouter
→ selected small model
```

Before real inference:

1. add OpenRouter provider preflight
2. keep credentials in environment variables only
3. verify endpoint connectivity
4. verify model availability
5. use the same model for C0/C1/C2
6. record exact model/provider/runtime in manifest
7. verify required MemoryArena servers/environment

Do not hard-code API keys.

Do not commit `.env`.

---

## 18. Research Metrics

Primary:

- subtask accuracy
- complete task-group success rate

Supporting:

- performance by subtask position
- errors
- retries
- tool failures
- wall-clock time
- input tokens
- output tokens
- total tokens
- tokens per successful subtask

Experience Brain diagnostics:

- Events captured
- Experiences consolidated
- Knowledge retrieved where applicable
- retrieval count
- retrieval utilization
- provenance completeness
- irrelevant/stale retrievals
- harmful retrieval cases

---

## 19. Current Development Status

```text
Repo reframe / lean core                  DONE
Append-only Events                        DONE
Experience consolidation                  DONE
Reviewed Experience lifecycle             DONE
MCP foundation                            DONE
Live MCP cross-session validation         BASIC PASS
Dashboard Review Queue                    DONE
Knowledge Inbox foundation                DONE
Dual Knowledge + Experience retrieval     DONE
MemoryArena adapter                       DRY VALIDATED
MemoryArena C0/C1/C2 real inference       NOT STARTED
OpenRouter real provider test             NOT STARTED
Benchmark protocol freeze                 NOT DONE
Full benchmark experiment                 NOT STARTED
Paper                                     NOT STARTED
```

The project has reached the point where **feature expansion should stop** unless a blocker is discovered.

The next mode should be:

```text
Build
→ Integration validation
→ Freeze POC
→ Evaluate
```

---

## 20. Recommended Next Session Sequence

### Step 1 — Orient to the actual local state

Run:

```powershell
git branch --show-current
git status
git log --oneline --decorate -15
git tag --list

experience status
experience lint
```

Read:

```text
AGENTS.md
PROJECT_PLAN.md
OWNER_GUIDE_TH.md
HANDOFF.md
experiments/INDEX.md
benchmark-exp/memoryarena/PROTOCOL.md
```

### Step 2 — Perform one real owner Knowledge Inbox smoke

Before benchmark work, verify the new feature with a real user-facing flow.

Recommended:

1. owner places one harmless real Markdown/TXT/PDF/DOCX file into `inbox/`
2. run `process inbox` through Agent/MCP or Dashboard
3. verify `data/knowledge.jsonl` gains a Knowledge record
4. verify provenance
5. query the Knowledge in a new Agent session
6. run unified retrieval and verify Knowledge and Experience are separated
7. verify no Experience is falsely created from the external document

If this passes, treat EXP-03.2 as owner-live validated.

Do not add new features unless this smoke exposes a blocker.

### Step 3 — POC integration freeze

Review the full POC state.

Candidate freeze milestone:

```text
v0.3.0-poc
```

Before tagging:

- all tests pass
- lint passes
- Dashboard works
- MCP works
- Experience live retrieval works
- Knowledge Inbox live flow works
- docs reflect actual behavior
- no secrets/private test artifacts are committed

Do not tag or push without owner approval.

### Step 4 — Review and freeze MemoryArena protocol

Review:

```text
benchmark-exp/memoryarena/PROTOCOL.md
```

Freeze:

- C0/C1/C2
- task IDs
- store isolation
- automation mode
- model selection rule
- scoring
- metrics
- leakage controls
- run IDs
- seeds where relevant

### Step 5 — OpenRouter preflight

Verify:

- API connectivity
- selected model
- rate limits/errors handled
- secrets never logged
- exact model/provider recorded

Use one small model for the 5-task engineering smoke.

### Step 6 — MemoryArena real 5-task smoke

Run:

```text
formal_reasoning_math
IDs 0,1,2,3,4
C0/C1/C2
```

Use isolated stores.

Treat results as engineering validation.

Do not make publication claims.

### Step 7 — Only after smoke passes

Freeze the benchmark protocol and move to the controlled larger experiment.

---

## 21. Suggested First Prompt for the Next Codex Session

```text
/plan

Read AGENTS.md, PROJECT_PLAN.md, OWNER_GUIDE_TH.md, HANDOFF.md,
experiments/INDEX.md, and the current git history before doing any work.

This is a continuation session. Do not redesign the project.

First audit the actual local state and verify that EXP-03.2 Knowledge Inbox &
Dual-Memory Foundation is present and healthy.

Then perform the smallest owner-live Knowledge Inbox integration validation:
process one safe real source through the inbox, verify append-only Knowledge
creation and provenance, query it through MCP in a later session, and verify
unified retrieval clearly separates Relevant Knowledge from Relevant Experience.

Do not add vector DB, knowledge graph, OCR pipeline, REST API, cloud services,
or other new features.

If the owner-live Knowledge Inbox workflow passes, update the EXP-03.2 record
and recommend whether the POC is ready to freeze before real MemoryArena
inference.

Do not start the full MemoryArena experiment yet.
Do not push, merge, or rewrite history.

At completion report exactly:

1. Completed
2. Tests and results
3. Problems or risks
4. Recommended next command
```

---

## 22. Important Owner Preferences

- Explain technical matters in simple Thai when communicating with the owner.
- The owner is low-code.
- Prefer one clear next command over many options.
- Do not ask for confirmation for small/reversible implementation decisions.
- Stop for owner input only on major architecture, research protocol, data-loss, license, or difficult-to-reverse decisions.
- Do not expand scope unnecessarily.
- Preserve provenance and evidence.
- Never claim benchmark improvement without controlled evidence.
- Do not make the owner manually edit JSONL for routine workflows.
- Keep the path to paper in mind, but finish the system validation before optimizing for publication.

---

## 23. Required End-of-Work Report for Agents

After each implementation round, report:

1. **Completed**
2. **Tests and results**
3. **Problems or risks**
4. **Recommended next command**

---

## 24. Bottom Line

Experience Brain now reportedly contains:

```text
Agent episodes
→ Events
→ Experience Memory

External files
→ Inbox
→ Knowledge Memory

Owner review
→ Dashboard

Agent integration
→ MCP

Task context
→ Unified Retrieval
   ├── Relevant Knowledge
   └── Relevant Experience

Research evaluation
→ MemoryArena adapter
```

Immediate priority:

```text
Owner-live Knowledge Inbox validation
→ POC freeze
→ MemoryArena protocol freeze
→ OpenRouter preflight
→ 5-task C0/C1/C2 real smoke
→ larger controlled experiment
→ paper
```

**Do not add major new features before evaluation unless a blocker is discovered.**
