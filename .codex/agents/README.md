# Experience Brain Codex Agents

This repository defines two project-local Codex roles.

- `planner.toml`: read-only planning with `gpt-5.6-sol` and high reasoning.
- `implementer.toml`: approved-plan execution with `gpt-5.6-terra` and high reasoning.

Always route a planning phase to `planner` before implementation. Route an
approved plan to `implementer`, which may edit any file inside this repository,
including `.codex/`. Do not silently replace either pinned model. If the chosen
role is unavailable, stop and report the routing blocker.
