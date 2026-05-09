# Codex Goals

## Verified Documentation

Official Codex docs describe `/goal` as an experimental Codex CLI slash command for long-running work with a durable objective and a verifiable stopping condition.

Key verified points from OpenAI documentation:

- `/goal` is for tasks where Codex should keep working across turns toward a verifiable stopping condition.
- It is experimental and requires `features.goals`.
- Enable it via `/experimental` or by setting `goals = true` under `[features]` in `config.toml`.
- Set a goal inside an interactive CLI session with `/goal <objective>`.
- View the current goal with `/goal`.
- Control it with `/goal pause`, `/goal resume`, and `/goal clear`.
- A good goal names the objective, stopping condition, files/docs to read first, validation commands/artifacts, checkpoints, and progress logging.

Sources:

- `https://developers.openai.com/codex/use-cases/follow-goals`
- `https://developers.openai.com/codex/cli/slash-commands`

## Local Verification

Local CLI version:

```text
codex-cli 0.130.0-alpha.5
```

The feature is enabled:

```text
goals    experimental    true
```

`<codex-home>\.codex\config.toml` contains:

```toml
[features]
goals = true
```

The default model config currently includes:

```toml
model = "gpt-5.5"
model_reasoning_effort = "xhigh"
```

## Important Finding

`codex exec` does not set a durable goal. A smoke test with a `/goal ...` prompt returned the requested text as a normal prompt response. Slash-command goal setup must be done through an interactive Codex CLI TUI session, not through `codex exec`.

## Required Workflow For Delegated Long Work

Use this workflow only when the task is bigger than one normal orchestrator turn, has one durable objective, can make autonomous progress for an extended period, and has a concrete validation/stopping condition. Do not use `/goal` for short audits, documentation corrections, local glue edits, deterministic script implementation, or quick validation commands.

1. Start interactive Codex CLI in this workspace:

```powershell
codex --disable fast_mode -C "<workspace>" -s workspace-write -m gpt-5.5 -c model_reasoning_effort="xhigh"
```

2. In the Codex CLI composer, verify status:

```text
/status
```

3. Set the durable objective:

```text
/goal <precise objective, constraints, checkpoints, validation commands, and stopping condition>
```

4. During the run, inspect or manage goal state with:

```text
/goal
/goal pause
/goal resume
/goal clear
```

## Programmatic PTY Runner

The local script `scripts/run_codex_goal.py` can host an interactive Codex CLI in a Windows pseudo-terminal, send a `/goal` from a goal markdown file, and log output under `data/cli_goal_logs/`.

Example:

```powershell
uv run python scripts/run_codex_goal.py --goal-id goal-001-non-x-scrape --goal-md docs/goal-001-non-x-scrape.md --done-file learnings/goal-001-non-x-scrape.done
```

The goal must write its own done signal file at the end so the runner can close the CLI and the orchestrator can audit the result.

The runner also writes a status heartbeat JSON file under `data/cli_goal_logs/<goal-id>.status.json`. Use this file plus the goal's done marker for monitoring; terminal scrollback alone is not a reliable wake-up mechanism.

For this project, goal completion is not a stopping point for the main orchestrator. After a done/blocker marker appears, the orchestrator must audit the result, update docs/learnings if needed, and either launch the next bounded CLI `/goal` or document the exact blocker that prevents continuing.

Required deterministic handoff: use the project-local Codex CLI `Stop` hook bridge documented in `docs/cli-wake-bridge.md`. The CLI goal writes its done marker, the CLI `Stop` hook detects the new marker, and the hook starts a turn in the orchestrator app thread through `codex app-server`. Do not use app-side polling automations as the normal wake mechanism.

The PTY runner must give the CLI `Stop` hook time to fire before closing the CLI. `scripts/run_codex_goal.py` does this by waiting for `data/orchestrator_bridge/notifications/<goal-id>.json` after the done marker appears.

## Project-Specific Goal Requirements

Every goal for this project must include:

- Read `docs/README.md`, `docs/handoff.md`, `docs/operating-rules.md`, `docs/data-pipeline.md`, `docs/scraping.md`, and latest `learnings/` checkpoint first.
- Keep WhatsApp raw files read-only.
- Use `uv` for Python.
- Write progress logs to `learnings/`.
- For important long-running processes, log attempted items, successes, failures, error reasons, timestamps, commands, counts, and retry/action status.
- Do not install or run unverified GitHub projects.
- Do not edit files outside the assigned scope.
- Stop and report when the validation condition is reached or when a blocker needs orchestrator/user judgment.
- For any browser work, use only explicitly approved sandboxed Playwright-managed Chromium profiles under this workspace. Never use the user's personal browser, cookies, saved sessions, CDP connection, or `real_chrome`.

## Current Delegation Boundary

The baseline KB generator, Markdown emission, backlink validation, and FTS5 lexical search are orchestrator self-work because the KB approach has already been selected and safety-reviewed. The next appropriate CLI `/goal` is the exhaustive unresolved-link scrape retry after the baseline KB exists, because that phase is long-running, retry-heavy, and has a clear terminal-state validation condition for every link.
