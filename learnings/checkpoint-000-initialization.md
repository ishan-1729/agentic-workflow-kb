# Checkpoint 000: Initialization

## Date

2026-05-09

## Completed

- Created persistent documentation scaffold in `docs/`.
- Created `learnings/` checkpoint area.
- Captured read-only WhatsApp policy, SQLite-first data model, Scrapling scraping requirement, promptfoo safety gate, and Codex CLI delegation rules.
- Confirmed `uv 0.8.16` is available and recorded that Python work should use `uv`.
- Corrected the source model from WhatsApp channels to WhatsApp groups.
- Verified official Codex `/goal` docs: goal mode must be set inside the interactive CLI TUI with `/goal <objective>` after `features.goals` is enabled. `codex exec` does not set a durable goal.

## Current Workspace State

- WhatsApp group exports are present under `imports/`.
- SQLite database exists at `data/db/agentic_workflow.db`.
- Import and scraping scripts exist under `scripts/`.
- The project folder is not currently a Git repository.

## Next Step

Use a real interactive Codex CLI `/goal` for any further long-running delegated work, then continue scraping and classification.

## Pitfalls

- `/goal` cannot be set via `codex exec`; use the interactive CLI composer.
- Twitter/X links may require retries or special handling.
- GitHub projects must not be installed or run until reviewed and evaluated.
