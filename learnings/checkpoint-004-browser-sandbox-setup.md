# Checkpoint 004: Browser Sandbox Setup

Date: 2026-05-09

## What Changed

- Installed Playwright-managed Chromium with `uv run --no-cache python -B -m playwright install chromium`.
- Documented the browser isolation rule in `docs/browser-sandbox.md`, `docs/scraping.md`, `docs/operating-rules.md`, and `docs/codex-goals.md`.
- Updated `docs/goal-003-x-oembed-parse.md` so sandboxed Playwright Chromium is allowed only as a fallback after oEmbed fails to reach the 50% parsed-content threshold.
- Updated `scripts/run_codex_goal.py` to write `data/cli_goal_logs/<goal-id>.status.json` while the CLI goal is running and when it finishes.
- After Goal 003, patched the runner's final status writer so a completed goal is marked `process_alive: false` even if WinPTY keeps a stale alive flag after `/quit`; the raw PTY value is retained as `pty_reported_alive`.

## Verification

Ran a Playwright smoke test with a fresh project-local profile under `data/browser_sandbox/` and opened `https://example.com` headlessly. The page title was `Example Domain`, and a screenshot was saved under the sandbox directory.

## Safety Constraints

- Never use the user's personal browser.
- Never use an existing browser profile, cookies, saved sessions, storage state, CDP connection, `real_chrome`, account credentials, or CAPTCHA bypass.
- Browser fallback for X/Twitter may only view public URLs in a fresh Playwright-managed Chromium sandbox and may only count visible post content as parsed content.
