# Legacy Baseline

The pre-reframe repository is preserved by Git history and the annotated tag
`pre-reframe-v0.1.0`.

- Original commit before owner instruction freeze: `d30f4a4a4179e64016d27b6c705558e1ba1530d9`
- Freeze commit and tag target: `dd2d3cf98d65b816f1ee79222d5ffc6e4e02d372`
- Tag: `pre-reframe-v0.1.0`
- Reframe branch: `reframe/v0.2.0`

The old active codebase implemented Experience Brain Lite with benchmark,
research-wiki, C0/C1/C2/C3 condition routing, capsules, source conversion,
hybrid retrieval gates, and benchmark analysis tooling.

Those files were removed from the active branch because the owner-approved
direction is now a lean Agent-CLI-first Experience Brain POC with two canonical
JSONL stores: `data/events.jsonl` and `data/experiences.jsonl`.

No large `legacy/` directory is kept in `main`; the verified tag is the archive.

