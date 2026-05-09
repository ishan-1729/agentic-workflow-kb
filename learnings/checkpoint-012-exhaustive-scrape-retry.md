# Checkpoint 012: Exhaustive Scrape Retry

Date: 2026-05-09

## Scope

- Retried every latest unresolved scrape row in `data/db/agentic_workflow.db`.
- Used SQLite as the source of truth.
- Kept `imports/`, WhatsApp exports, and generated `kb/` pages read-only.
- Did not use Nitter, personal browser profiles, cookies, storage state, CDP, `real_chrome`, credentials, login, or external GitHub project install/run.

## Timing

- Start heartbeat: `2026-05-09T18:14:27Z`
- Final validation: `2026-05-09T18:24:24Z`

## Baseline

Baseline query file: `learnings/goal-007-exhaustive-scrape-retry/baseline_latest_status_counts.sql`

Baseline latest link-row status counts:

- `success`: 345
- `inaccessible`: 2
- `retry_pending`: 241

Baseline unresolved rows:

- `x.com`: 240 `retry_pending`
- `youtu.be`: 1 `retry_pending`

## Commands Run

- `uv run --no-cache python -B scripts/scrape_links.py --priority non-x --latest-status retry_pending --latest-status no_attempt --save-raw --fetch-retries 3 --timeout 30 --delay 1 --attempts-log learnings/goal-007-exhaustive-scrape-retry/attempts.jsonl --terminalize-unresolved --terminal-status terminal_failed`
- `uv run --no-cache python -B scripts/x_oembed_parse.py --save-raw --timeout 15 --delay 0.1 --heartbeat-interval 25 --no-stop-at-threshold --log-dir learnings/goal-007-exhaustive-scrape-retry --heartbeat-file learnings/goal-007-exhaustive-scrape-retry.heartbeat.json --goal-id goal-007-exhaustive-scrape-retry --attempts-log learnings/goal-007-exhaustive-scrape-retry/attempts.jsonl`
- Same oEmbed command rerun after fixing the script's `--no-stop-at-threshold` early-return guard.
- `uv run --no-cache python -B scripts/db_status.py`
- No-bytecode `compile()` check through `uv run --no-cache python -B -` for `scripts/scrape_links.py` and `scripts/x_oembed_parse.py`.

`py_compile` was attempted first but hit the known Windows locked `scripts/__pycache__` replacement error. The no-bytecode compile check passed and avoided writing `.pyc` files.

## Scripts Changed

- `scripts/scrape_links.py`
  - Added latest-status selection so Goal 007 retried only rows whose latest status was unresolved.
  - Added per-link goal attempts JSONL logging.
  - Added bounded fetch retry configuration and optional terminalization of unresolved outcomes.
- `scripts/x_oembed_parse.py`
  - Added Goal 007 attempts JSONL logging.
  - Made the heartbeat goal id configurable.
  - Fixed `--no-stop-at-threshold` so it continues processing remaining unparsed posts even after the old 50% parsed threshold is already met.
  - Records unsupported X URLs as `unsupported` instead of `skipped`; none were encountered in this run.

## Results

Non-X retry:

- Retried `https://youtu.be/srqWFT_TUec`.
- Result: `success`, HTTP 200, title `Claude Code + Obsidian = UNLIMITED Memory! Solves Claude's Memory Problem! - YouTube`.

X/Twitter oEmbed retry:

- Selected 238 remaining post groups covering 240 unparsed link rows.
- Attempted 238 post groups through official unauthenticated `https://publish.x.com/oembed`.
- Added parsed oEmbed success for 238 link rows.
- Added terminal `inaccessible` for 2 X/Twitter link rows.
- No X/Twitter `retry_pending`, `failed`, or `no_attempt` rows remain.

Attempt log:

- `learnings/goal-007-exhaustive-scrape-retry/attempts.jsonl`
- Rows: 241
- Counts: `scrapling.Fetcher:success` 1, `x_oembed:success` 238, `x_oembed:inaccessible` 2

## Final Counts

Final latest link-row status counts:

- `success`: 584
- `inaccessible`: 4

Count deltas from baseline:

- `success`: +239
- `inaccessible`: +2
- `retry_pending`: -241

Validation artifacts:

- `learnings/goal-007-exhaustive-scrape-retry/validation_counts.json`
- `learnings/goal-007-exhaustive-scrape-retry/db_status.stdout.log`
- `learnings/goal-007-exhaustive-scrape-retry/compile.stdout.log`

SQLite validation:

- `PRAGMA integrity_check`: `ok`
- Latest `retry_pending` rows: 0
- Latest `failed` rows: 0
- Latest `no_attempt` rows: 0
- X/Twitter coverage: 481 total, 479 `parsed_oembed`, 2 `terminal_inaccessible`

## Terminal Inaccessible Rows

- `https://github.com/TheRealSeanDonahoe/agents-md`: existing GitHub HTTP 404.
- `https://github.com/mattpocock/skills/tree/main/grill-me`: existing GitHub HTTP 404.
- `https://x.com/manasjsaloi/status/1987432698970059234?t=EtAYE1J7oSTiR2J5SWF9Gw&s=08`: official oEmbed returned HTTP 404/error page.
- `https://x.com/i/status/2024665932522766797`: official oEmbed returned HTTP 403, `Sorry, you are not authorized to see this status.`

There were no `terminal_failed` rows.

## Browser Sandbox

Sandboxed browser fallback was not used. After the official oEmbed pass, validation found zero latest `retry_pending`, `failed`, or `no_attempt` links, so there were no remaining unresolved links eligible for browser fallback.

No personal browser, browser profile, cookies, storage state, CDP connection, `real_chrome`, login, CAPTCHA bypass, or anti-bot bypass was used.

## Next Audit Steps

- Audit `validation_counts.json` and the four terminal inaccessible rows.
- Regenerate the generated KB pages after audit; this goal intentionally did not edit `kb/`.
- Re-run downstream KB analysis/classification only if the orchestrator decides the newly captured linked content changes decisions.
