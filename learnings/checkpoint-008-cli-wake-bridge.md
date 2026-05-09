# Checkpoint 008: CLI Wake Bridge Repair

Date: 2026-05-09

## Problem

The previous wake mechanism used app-side polling automations. That was the wrong control plane for this project. The desired handoff is deterministic and CLI-side: a Codex CLI `/goal` completes, the CLI itself triggers a wake into this orchestrator thread, then the orchestrator audits and launches the next bounded goal.

## Fix

- Added `scripts/codex_goal_stop_hook.py`, a Codex CLI `Stop` hook that detects new `learnings/goal-*.done` markers.
- Added `.codex/hooks.json` with a project-local `Stop` hook command:
  - `uv run --no-cache python -B "<workspace>\scripts\codex_goal_stop_hook.py"`
- Added `.codex/config.toml` and enabled `hooks = true`.
- Updated `<codex-home>\.codex\config.toml` to use the local CLI's current feature flag: `[features] hooks = true`.
- Added exact-case workspace trust for `<workspace>`.
- Added bridge config/state under `data/orchestrator_bridge/`.
- Initialized notification baseline for Goals 000-005 so old done markers do not retroactively notify.
- Updated `scripts/run_codex_goal.py` so it waits for the CLI Stop-hook notification marker before sending `/quit`.

## Review Gate

The CLI loaded the project hook but initially refused to run it until reviewed:

```text
1 hook needs review before it can run. Open /hooks to review it.
```

Using `/hooks`, the Stop hook was reviewed, trusted, and toggled active. `/hooks` now reports Stop as 1 installed and 1 active.

## Verification

- `uv run --no-cache python -B -m py_compile scripts\codex_goal_stop_hook.py scripts\codex_app_notify.py scripts\run_codex_goal.py` passed.
- `codex features list` reports `goals` true and `hooks` true.
- `scripts/codex_app_notify.py --resume-only` successfully resumed thread `<thread-id>`.
- Hook dry-run detected a temporary new done marker without notifying.
- Real interactive CLI Stop-hook smoke appended `no new goal done marker` to `data/orchestrator_bridge/stop_hook.log`.
- Actual app-server wake test accepted `turn/start` and returned turn id `<thread-id>`.

## Important Pitfalls

- The installed CLI reports `codex_hooks` as deprecated; use `hooks = true`.
- Hook review and hook activation are separate. A trusted hook can still be inactive until toggled on.
- The PTY runner must not close the CLI immediately after a done file appears; it now waits for `data/orchestrator_bridge/notifications/<goal-id>.json`.
- App-side polling automations are not the normal wake path.
- Existing done markers must be baselined before enabling notifications to avoid stale wakes.

## Goal 005 Audit

Goal 005 completed and passed audit checks:

- Done marker exists: `learnings/goal-005-kb-candidate-review.done`.
- Checkpoint exists: `learnings/checkpoint-007-kb-candidate-review.md`.
- SQLite integrity check: ok.
- `kb_candidates`: 14.
- `decisions`: 1.
- Initial decision: implement a project-owned, Obsidian-compatible Markdown KB generated from SQLite, with FTS5 lexical search first and external GitHub projects deferred until promptfoo safety review.

Next phase can proceed to Goal 006 after this bridge repair.
