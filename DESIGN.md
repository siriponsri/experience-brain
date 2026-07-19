# DESIGN.md — Experience Brain

**Status:** Proposed post-`v0.3.0-poc` design system  
**Purpose:** Define the visual language, dashboard UX, documentation visuals, and public-facing design rules for Experience Brain.  
**Scope:** Public research repo + local single-owner dashboard.  
**Non-goal:** This document does not change the core memory architecture, canonical JSONL stores, MCP contract, or benchmark protocol.

---

## 1. Design Intent

Experience Brain should feel like a serious open-source research tool, not a generic AI dashboard.

The interface should communicate:

- grounded evidence;
- provenance and traceability;
- calm review rather than noisy monitoring;
- clear separation between **Knowledge** and **Experience**;
- low cognitive load for a non-developer owner;
- research credibility without pretending benchmark improvement has already been proven.

The visual direction is inspired by modern analytical dashboards with:

- a restrained dark top bar;
- a soft neutral canvas;
- white cards with generous whitespace;
- rounded corners used consistently;
- sparse accent colors;
- strong information hierarchy;
- lightweight charts and health indicators;
- minimal decoration.

The supplied dashboard reference image is **visual inspiration only**. Do not copy, redistribute, or commit that image unless its reuse license is explicitly verified.

---

## 2. Product Personality

Experience Brain should feel:

**Calm · Evidence-led · Research-grade · Trustworthy · Local-first · Human-reviewable**

Avoid:

- neon “AI” gradients;
- glowing robot/brain clichés;
- excessive glassmorphism;
- dense enterprise admin panels;
- large walls of JSON by default;
- decorative animations that distract from review;
- claims such as “self-improving intelligence” or “human-like brain”.

Preferred wording:

> A brain-inspired experience lifecycle that enables AI agents to learn from grounded episodes across sessions.

---

## 3. Visual System

### 3.1 Recommended Palette

Use CSS variables so the theme can later be changed centrally.

```css
:root {
  --bg-canvas: #F4F6FB;
  --bg-surface: #FFFFFF;
  --bg-header: #20232D;

  --text-primary: #171A21;
  --text-secondary: #667085;
  --text-muted: #98A2B3;
  --text-on-dark: #F8FAFC;

  --border-subtle: #E7EAF0;

  --accent-primary: #716FE5;
  --accent-primary-soft: #EEEDFF;

  --accent-warm: #F4B86A;
  --accent-warm-soft: #FFF3E2;

  --success: #3F8F78;
  --success-soft: #E8F5F0;

  --warning: #C9872F;
  --warning-soft: #FFF4DE;

  --danger: #C85B63;
  --danger-soft: #FCEBEC;

  --info: #4D7FC7;
  --info-soft: #EAF1FB;
}
```

### 3.2 Color Use Rules

- Use `accent-primary` for navigation state, primary action, and selected items.
- Use `accent-warm` sparingly for highlights or “attention needed”.
- Use semantic colors only for actual state:
  - green = healthy / confirmed / active;
  - amber = proposed / pending;
  - red = invalid / failed / integrity issue;
  - blue = informational.
- Do not encode status by color alone. Always include a text label or icon.
- Limit each screen to one dominant accent and one supporting accent.

### 3.3 Typography

Preferred stack:

```css
font-family:
  Inter,
  ui-sans-serif,
  system-ui,
  -apple-system,
  BlinkMacSystemFont,
  "Segoe UI",
  sans-serif;
```

Optional display font for hero headings only:

- Manrope
- Geist
- Inter

Do not require proprietary fonts.

Suggested scale:

- Page title: 28–32 px / 700
- Section title: 20–24 px / 650–700
- Card title: 14–16 px / 600
- Body: 14–16 px / 400
- Metadata: 12–13 px / 400–500

---

## 4. Layout System

### 4.1 Global Layout

Desktop target:

```text
┌───────────────────────────────────────────────────────────────┐
│ Experience Brain     Search / status      Health    Owner     │
├───────────────────────────────────────────────────────────────┤
│ Page title + concise purpose                                  │
│ Optional tab / navigation row                                 │
│                                                               │
│ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│ │ KPI / Card │ │ KPI / Card │ │ KPI / Card │ │ KPI / Card │   │
│ └────────────┘ └────────────┘ └────────────┘ └────────────┘   │
│                                                               │
│ ┌───────────────────────┐ ┌───────────────────────────────┐   │
│ │ Primary work surface  │ │ Secondary evidence / status   │   │
│ └───────────────────────┘ └───────────────────────────────┘   │
└───────────────────────────────────────────────────────────────┘
```

### 4.2 Grid

- 12-column conceptual grid.
- 24 px desktop page gutter minimum.
- 16–24 px gap between cards.
- Avoid more than 3 major visual columns on a normal desktop screen.
- Use full-width content for review queues, long evidence, and provenance.
- Cards should not all have equal visual weight.

### 4.3 Cards

Default card:

- white surface;
- 1 px subtle border or very soft shadow;
- 14–18 px radius;
- 16–24 px internal padding;
- no heavy gradients;
- no thick colored borders except compact status indicators.

---

## 5. Dashboard Information Architecture

The current tab model should be retained conceptually:

1. **Overview**
2. **Review Queue**
3. **Inbox**
4. **Knowledge**
5. **Experiences**
6. **Sessions / Events**

A future navigation redesign may present these as a top navigation row or compact sidebar, but the information architecture should remain stable.

---

## 6. Overview Page

### 6.1 Goal

Answer these questions in under 10 seconds:

- Is the store healthy?
- Is anything waiting for my review?
- How much grounded memory exists?
- What happened recently?
- Is the system ready for normal use?

### 6.2 Recommended Components

Top summary cards:

- Active / Confirmed Experiences
- Knowledge Records
- Pending Reviews
- Sessions
- Store Integrity
- Current Software Version

Primary panels:

**Memory Health**
- store integrity;
- unresolved review count;
- invalidated / retired records;
- last successful lint.

**Recent Activity**
- latest sessions;
- newly proposed Experiences;
- newly processed Knowledge;
- recent invalidations.

**Retrieval Activity**
- match / no-match;
- retrieved / used;
- successful task outcomes when available.

Do not present benchmark-performance charts before real benchmark evidence exists.

---

## 7. Review Queue

This is the highest-priority human-review screen.

Each Experience review card should show, in this order:

1. lesson / concise candidate statement;
2. status;
3. project;
4. source session;
5. confidence;
6. evidence count;
7. situation;
8. goal;
9. evidence preview;
10. actions.

Primary actions:

- Confirm
- Edit & Confirm

Secondary destructive actions:

- Reject / Invalidate
- Retire when applicable

Destructive actions should use confirmation UI where practical.

Never require the owner to edit JSONL manually.

---

## 8. Inbox

### 8.1 Goal

Make document ingestion understandable to a no-code user.

Preferred flow:

```text
Upload files
→ Inspect queue
→ Process Inbox
→ See result per file
→ Open resulting Knowledge
```

Each file row should display:

- filename;
- detected type;
- processing status;
- duplicate indicator;
- Knowledge ID when created;
- clear error message when processing fails.

Supported / unsupported states must be explicit.

Do not silently fail.

---

## 9. Knowledge

Knowledge is:

> What the Agent has read or received from an external source.

Each Knowledge card should show:

- concise digest;
- key facts / claims;
- suggested applicability;
- project;
- source filename;
- source type;
- provenance;
- content hash;
- status.

Actions:

- Confirm
- Invalidate
- Retire

Never visually imply that external Knowledge is a grounded Experience.

Use a distinct icon or label for Knowledge across the entire product.

---

## 10. Experiences

Experience is:

> What the Agent has actually done and learned through grounded action and observed outcomes.

Each Experience should show:

- lesson;
- situation;
- goal;
- project;
- confidence;
- owner-confirmed state;
- internal vs External Project Experience;
- evidence events;
- provenance and lineage;
- current lifecycle status.

Experience and Knowledge must remain visually and semantically distinct.

Suggested labels:

- `Knowledge`
- `Grounded Experience`
- `Project Rule`
- `Working Context`

---

## 11. Sessions / Events

Default view should be human-readable.

Show:

- session;
- timeline;
- event type;
- timestamp;
- actor;
- tool;
- outcome.

Raw JSON should be inside an expander, not the default presentation.

---

## 12. Search / Ask Memory

Not required for the initial professionalization sprint.

If added later, it should be a thin UI over the existing retrieval APIs and must render two explicit sections:

```text
Relevant Knowledge
Relevant Experience
```

Do not merge both into an unlabeled answer.

---

## 13. No-Code UX Requirements

A normal owner should be able to:

- launch the dashboard with one documented command;
- upload a supported file;
- process the inbox;
- inspect Knowledge;
- review Experience;
- confirm / edit / invalidate / retire records;
- inspect provenance;
- understand system health;

without:

- editing JSONL;
- writing Python;
- knowing record IDs in advance;
- using Git for daily operation.

Current product classification:

> **Low-code setup, no-code daily review and knowledge-ingestion workflow.**

Do not claim “zero-install no-code product” until a one-click installer or hosted deployment exists.

---

## 14. Accessibility

Minimum requirements:

- WCAG-aware contrast for text and controls;
- no status conveyed by color alone;
- visible keyboard focus;
- clear button labels;
- tooltips for provenance and technical terms;
- responsive layout down to tablet width where practical;
- avoid tiny chart labels;
- avoid hover-only essential information.

---

## 15. Documentation Visuals

Prefer self-created assets with clear provenance:

```text
docs/assets/
├── architecture.svg
├── knowledge-vs-experience.svg
├── cross-session-lifecycle.svg
├── dashboard-overview.png
├── dashboard-review-queue.png
└── benchmark-conditions.svg
```

Recommended visuals:

1. System architecture
2. Knowledge vs Experience
3. Cross-session lifecycle
4. Actual dashboard screenshot
5. Research evaluation design: C0 / C1 / C2

### Asset Policy

- Prefer original SVG, Mermaid, or diagrams generated specifically for this repository.
- Do not download random illustrations, icons, or dashboard templates without a verified license.
- Keep attribution where a license requires it.
- Record third-party assets in `THIRD_PARTY_NOTICES.md` when applicable.
- Never commit the supplied design-reference screenshot unless the owner confirms its redistribution rights.

---

## 16. README Visual Style

README should feel research-professional, not marketing-heavy.

Recommended top section:

```text
# Experience Brain

Grounded cross-session experience memory for AI agents.

[Badges]

One-sentence problem statement.

[Architecture SVG]

Knowledge is what the Agent has read.
Experience is what the Agent has done.

[Quick Start]
```

Avoid exaggerated badges, unverified benchmark scores, fake user counts, and unsupported performance claims.

---

## 17. Dashboard Redesign Acceptance Criteria

The redesign is complete when:

- all current dashboard functions still work;
- automated tests remain green;
- all tabs remain accessible;
- Knowledge and Experience are visually distinct;
- the Overview answers system-health questions quickly;
- no-code owner workflows require no JSONL editing;
- provenance remains accessible but not visually dominant;
- the UI remains local-first and single-owner for this release;
- no benchmark claim is added;
- no core memory architecture is changed;
- screenshots in README are generated from the actual running dashboard;
- the final UI is clearly inspired by modern analytics dashboards but is not a copied template.

---

## 18. Versioning Guidance

The `v0.3.0-poc` tag is a frozen technical milestone.

Professionalization and dashboard redesign should happen **after** that tag on a new branch and should produce a new patch/minor development version only after review.

Suggested branch:

```text
product/v0.3.1-public-preview
```

Do not move or rewrite the `v0.3.0-poc` tag.
