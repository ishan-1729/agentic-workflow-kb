# CLI Wake Bridge

## Purpose

Codex app automations are not the primary wake mechanism for this project. The required handoff is CLI-side and deterministic:

1. A bounded Codex CLI `/goal` runs in this workspace.
2. The goal writes its `learnings/goal-*.done` marker only after validation passes.
3. The Codex CLI `Stop` hook runs from `.codex/hooks.json`.
4. The hook detects the new done marker, calls `scripts/codex_app_notify.py`, and starts a turn in the orchestrator app thread.
5. The main orchestrator audits the goal, closes out the completed goal context, and continues the next eligible project task without waiting for a user prompt unless there is a precise blocker.

## Verified Codex Features

- `<codex-home>\.codex\config.toml` has `[features] goals = true` and `hooks = true`.
- `<workspace>\.codex\config.toml` also enables `goals` and `hooks` for the trusted project layer.
- The project hook was reviewed through CLI `/hooks`, trusted, and toggled active. `/hooks` reports `Stop` as 1 installed and 1 active.
- Official hooks docs say hooks load from project-local `.codex/hooks.json` in trusted projects, `Stop` hooks run at turn stop, and hook commands receive JSON on stdin.
- Official app-server docs say `codex app-server --listen stdio://` accepts JSON-RPC, supports `thread/resume`, and starts work with `turn/start`.
- The installed local CLI reports `hooks` as the active feature flag name. It warns that the older `codex_hooks` key is deprecated.

Primary docs:

- `https://developers.openai.com/codex/hooks`
- `https://developers.openai.com/codex/app-server`

## Local Files

- `.codex/hooks.json`: project-local Stop hook config.
- `scripts/codex_goal_stop_hook.py`: CLI Stop hook bridge.
- `scripts/codex_app_notify.py`: app-server JSON-RPC notifier.
- `data/orchestrator_bridge/config.json`: orchestrator thread id and model settings.
- `data/orchestrator_bridge/notified_goals.json`: de-duplication state.
- `data/orchestrator_bridge/notifications/<goal-id>.json`: notification success markers.
- `data/orchestrator_bridge/stop_hook.log`: hook audit log.
- `data/orchestrator_bridge/codex_app_notify.log`: app-server JSON-RPC log.

## De-Duplication Rule

Existing done markers are baselined before the bridge is enabled. The hook only notifies for a new or changed `learnings/goal-*.done` file.

If the state file is missing, the hook creates a baseline from current done files and does not notify retroactively. This prevents stale completed goals from spamming the orchestrator thread.

## Runner Coordination

`scripts/run_codex_goal.py` waits for `data/orchestrator_bridge/notifications/<goal-id>.json` after the goal done marker appears. This prevents the runner from sending `/quit` before the CLI `Stop` hook has a chance to fire.

Only if the marker does not appear before `--post-done-hook-wait` expires may the runner use its legacy direct notifier fallback, and only when `--notify-thread-id` or `CODEX_ORCHESTRATOR_THREAD_ID` is explicitly set. Normal operation should rely on the CLI Stop hook.

## Autonomous Continuation Contract

The hook notification is not just a completion alert. Its prompt tells the orchestrator to:

- Treat the completed CLI goal as closed.
- Audit the done/blocker marker and goal artifacts.
- Apply safe local integration fixes.
- Read `docs/handoff.md` and the latest checkpoint.
- Continue the next eligible project task without waiting for the user.
- Launch another bounded interactive CLI `/goal` only for genuinely long-running work.
- Stop only when the project is complete, a precise blocker needs user judgment, or safety rules prevent continuing.

## Safety Boundaries

- The hook only acts for sessions whose `cwd` is inside `<workspace>`.
- It only reads `learnings/goal-*.done` markers and bridge config/state.
- It does not touch WhatsApp exports.
- It does not use the user's personal browser or browser profile.
- It does not install or run GitHub projects.

## Test Commands

Compile bridge scripts:

```powershell
uv run --no-cache python -B -m py_compile scripts\codex_goal_stop_hook.py scripts\codex_app_notify.py scripts\run_codex_goal.py
```

Test app-server can resume this thread without starting a turn:

```powershell
uv run --no-cache python -B scripts\codex_app_notify.py --thread-id <thread-id> --resume-only
```

Dry-run hook detection:

```powershell
'{"hook_event_name":"Stop","cwd":"D:\\Projects\\agentic_workflow"}' | uv run --no-cache python -B scripts\codex_goal_stop_hook.py --dry-run
```

Verify the CLI sees the hook:

```text
/hooks
```

Expected: `Stop` shows `1` installed and `1` active. If a hook says it needs review, open `/hooks`, select `Stop`, trust the hook, and toggle it on.

Real Stop-hook smoke result on 2026-05-09: an interactive CLI prompt caused `scripts/codex_goal_stop_hook.py` to append `no new goal done marker` to `data/orchestrator_bridge/stop_hook.log`.

Actual app wake test on 2026-05-09: `scripts/codex_app_notify.py` successfully called `thread/resume` for thread `<thread-id>` and `turn/start` returned turn id `<thread-id>` with status `inProgress`.

## Review Pitfall

Codex will not run a newly discovered hook until it has been reviewed in `/hooks`. The startup warning looks like:

```text
1 hook needs review before it can run. Open /hooks to review it.
```

Do not treat this as a code failure. Open `/hooks`, review the command, trust it, and enable it. The hook command must stay scoped to this workspace.
