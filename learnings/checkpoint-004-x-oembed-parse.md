# Checkpoint 004: X oEmbed Parsed-Content Pass

## Date

2026-05-09

## Scope

- Goal: parse enough X/Twitter linked rows to reach at least 50% real parsed content.
- Required docs and prior checkpoints were read before acting.
- Raw imports under `imports/` remained read-only.
- WhatsApp was not opened or mutated.
- No GitHub project was installed or run.
- No X credentials, cookies, bearer tokens, paid APIs, public front ends, internal GraphQL endpoints, personal browser profile, CDP connection, `real_chrome`, CAPTCHA bypass, or account context were used.
- Browser fallback was not used because official unauthenticated oEmbed reached the threshold.

## Code And Storage Changes

- Added `scripts/x_oembed_parse.py`.
- Updated `docs/scraping.md` with the new oEmbed command.
- No SQLite schema change was needed.
- Parsed content is stored in existing `scrape_attempts` rows with `tool = 'x_oembed'`, `status = 'success'`, non-empty `extracted_text`, and `metadata_json.parsed_content = true`.
- Raw oEmbed artifacts are stored under `data/scraped/raw/x_oembed/`.
- Durable goal logs are stored under `learnings/goal-003-x-oembed-parse/`.

## Commands Run

```powershell
uv run --no-cache python -B scripts/db_status.py
uv run --no-cache python -B scripts/x_oembed_parse.py --help
uv run --no-cache python -B scripts/x_oembed_parse.py --save-raw --limit-post-groups 5 --timeout 15 --delay 0.1 --heartbeat-interval 5
uv run --no-cache python -B scripts/x_oembed_parse.py --save-raw --timeout 15 --delay 0.1 --heartbeat-interval 25
uv run --no-cache python -B scripts/db_status.py
uv run --no-cache python -B -  # final SQLite parsed-content validation query
```

## Initial Counts

- Total X/Twitter link rows: 481.
- Required threshold: `ceiling(0.50 * 481) = 241`.
- Parsed X/Twitter link rows before this pass: 0.
- Latest X/Twitter status before this pass: 481 `retry_pending` rows from the earlier static Scrapling JavaScript-shell pass.

## Batch Results

Pilot oEmbed batch:

- Command: `uv run --no-cache python -B scripts/x_oembed_parse.py --save-raw --limit-post-groups 5 --timeout 15 --delay 0.1 --heartbeat-interval 5`.
- Attempted post groups: 5.
- Success post groups: 5.
- Parsed link rows added: 6.
- Finding: `https://publish.x.com/oembed` accepted `https://x.com/i/status/<id>` URLs and returned usable fallback HTML.

Threshold oEmbed batch:

- Command: `uv run --no-cache python -B scripts/x_oembed_parse.py --save-raw --timeout 15 --delay 0.1 --heartbeat-interval 25`.
- Started with 6 parsed rows.
- Attempted post groups: 226.
- Success post groups: 226.
- Parsed link rows added: 235.
- Stopped immediately when parsed X/Twitter link rows reached 241.

Combined oEmbed result:

- Parsed X/Twitter link rows: 241.
- Parsed X/Twitter normalized URLs: 232.
- Parsed post groups/artifact pairs: 231.
- oEmbed failures during this goal: 0.
- Browser fallback: not used.

## Artifacts And Logs

- Raw oEmbed JSON files: 231.
- Raw oEmbed HTML files: 231.
- Attempt log: `learnings/goal-003-x-oembed-parse/oembed_attempts.jsonl`.
- Summary log: `learnings/goal-003-x-oembed-parse/summary.json`.
- Heartbeat: `learnings/goal-003-x-oembed-parse.heartbeat.json`.
- Browser sandbox directory: null, because no browser fallback was needed.

## Final Validation

`uv run --no-cache python -B scripts/db_status.py`:

```text
scrape_attempts: 935
links: 588
messages: 598
```

Final SQLite validation query:

```json
{
  "parsed_x_link_rows": 241,
  "parsed_x_normalized_urls": 232,
  "passes": true,
  "threshold_ceiling_50_percent": 241,
  "total_x_link_rows": 481,
  "x_attempt_status_counts": {
    "scrapling.Fetcher:retry_pending": 481,
    "x_oembed:success": 241
  }
}
```

Latest X/Twitter link-row status after this goal:

```json
{
  "retry_pending": 240,
  "success": 241
}
```

## Representative Parsed Samples

- Link 1, `https://x.com/i/status/2037182739695493399`: author `Cline`, date `March 26, 2026`, text begins `Introducing Cline Kanban: A standalone app for CLI-agnostic multi-agent orchestration...`, outbound media link `https://t.co/4HjvwSu4Mo`.
- Link 2, `https://x.com/i/status/2038660653410320556`: author `Alvaro Cintas`, date `March 30, 2026`, text begins `This is the most complete Claude Code setup that exists right now...`, outbound media link `https://t.co/FhcoewKY3c`.
- Link 3, `https://x.com/i/status/2038663014098899416`: author `Claude`, date `March 30, 2026`, text begins `Computer use is now in Claude Code...`, outbound media link `https://t.co/s2FDQaDmr1`.

## Remaining Notes

- The project stopping condition was met exactly, so the pass did not continue through the remaining 240 X/Twitter rows.
- The remaining rows still have the previous latest `retry_pending` status and can be handled by a later goal if fuller X coverage is needed.
- Because oEmbed reached the threshold, the approved Playwright-managed Chromium fallback was unnecessary and was not started.
