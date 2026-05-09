# Operating Rules

## WhatsApp Handling

1. Read only.
2. Export only to local files.
3. Never write, delete, react, forward, pin, archive, or otherwise mutate WhatsApp data.
4. Preserve raw exports unchanged in `imports/whatsapp_raw/`.
5. Process copies into normalized intermediate files and SQLite.

## Data Integrity

1. Every imported WhatsApp entry gets a stable local ID.
2. Every link gets its own record linked back to the message record.
3. Exact duplicates are tracked, not silently forgotten.
4. First-pass scrape failures must be stored with error reason and retry status.
5. Missing linked content is represented as `NA` or NULL while retaining the parent WhatsApp message.
6. Major transforms must be reproducible by scripts.
7. Important long-running processes must produce durable logs. At minimum, log what was attempted, what succeeded, what failed, the exact error or reason, timestamps, counts, command used, and next retry/action status.

## Analysis Integrity

1. Separate source content from assistant interpretation.
2. Keep provenance for claims and comparisons.
3. Verify unknown tools or claims on the internet before final category or recommendation decisions.
4. Do not overfit to one viral post or one review.
5. Re-run Knowledge Base comparison after scrape completeness improves.

## Implementation Safety

1. No blind GitHub installs.
2. Check project safety with promptfoo-backed evaluations before implementation.
3. Prefer local, inspectable, low-risk implementations over heavy dependency stacks unless evidence supports them.
4. Avoid credentials in files, logs, screenshots, or database rows.
5. Keep generated outputs inside this workspace.
6. Use `uv` for Python environment and dependency management.
7. Never use the user's personal browser, existing browser profile, cookies, saved sessions, or logged-in account context for scraping/viewing. Any browser automation must use an explicitly approved Playwright-managed Chromium sandbox with a fresh project-local profile.

## Delegation Rules

1. Delegate long-running, bounded, non-overlapping batches to Codex CLI.
2. Use GPT-5.5 extra high reasoning and avoid fast mode.
3. Ask CLI tasks to report completion, changed files, unresolved failures, and next recommended action.
4. The main orchestrator integrates results and checks consistency.
5. Delegated goals must write checkpoint logs in `learnings/` and must not rely only on terminal scrollback.
