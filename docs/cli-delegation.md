# Codex CLI Delegation

## Available CLI

The Codex CLI is installed and the `goals` feature is enabled.

Known working non-goal smoke-test shape:

```powershell
codex exec -C "<workspace>" --skip-git-repo-check --ephemeral -s read-only "Reply with exactly: CLI_READY"
```

## Preferred Delegation Pattern

Use interactive Codex CLI `/goal` for long-running, bounded work such as:

- Designing or validating SQLite schema variants.
- Running batch scraping passes.
- Reviewing Knowledge Base candidate sets.
- Retrying unresolved scrape failures.
- Generating search/index implementation drafts.

Each delegated task should:

- State exact file ownership.
- Avoid editing files owned by the main orchestrator at the same time.
- Ask for a final completion report.
- Include unresolved blockers and logs.
- Avoid fast mode.
- Use GPT-5.5 and extra high reasoning when available.
- Set a real `/goal` inside the interactive CLI TUI. Do not rely on `codex exec` for goal mode.

## Interactive Goal Startup

```powershell
codex --disable fast_mode `
  -C "<workspace>" `
  -s workspace-write `
  -m gpt-5.5 `
  -c model_reasoning_effort="xhigh"
```

Then type the project-specific slash command in the CLI composer:

```text
/goal <bounded task with objective, stopping condition, validation loop, progress log, and file ownership>
```

If Windows CLI behavior is unstable, try the same task from WSL after verifying paths and environment. Keep outputs in this workspace.

`codex exec` can still be used for short non-interactive checks, but it does not set a durable goal.

## Do Not Delegate

- WhatsApp write-capable automation.
- Ambiguous data deletion.
- Running unverified GitHub code.
- Final Knowledge Base implementation decision without orchestrator review.
