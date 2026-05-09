# Checkpoint 003: X/Twitter First-Pass Scrape

## Date

2026-05-09

## Scope

- Goal: first-pass scrape for all currently pending X/Twitter normalized URLs.
- Raw imports under `imports/` remained read-only.
- Only unauthenticated public scraping was used.
- No credentials, cookies, browser profiles, bearer tokens, paid APIs, or authenticated account context were used.
- WhatsApp was not opened or mutated.
- No GitHub project was installed or run.

## Start And End

- Required docs/checkpoints were read before acting.
- Scrape attempt window in SQLite: 2026-05-09T09:04:48+05:30 to 2026-05-09T09:14:18+05:30.
- Final validation: 2026-05-09T09:16:17+05:30.

## Commands Run

The required first-pass command was run with bytecode disabled and proxy variables removed from the process environment:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; Remove-Item Env:HTTP_PROXY -ErrorAction SilentlyContinue; Remove-Item Env:HTTPS_PROXY -ErrorAction SilentlyContinue; Remove-Item Env:ALL_PROXY -ErrorAction SilentlyContinue; Remove-Item Env:http_proxy -ErrorAction SilentlyContinue; Remove-Item Env:https_proxy -ErrorAction SilentlyContinue; Remove-Item Env:all_proxy -ErrorAction SilentlyContinue; uv run --no-cache python -B scripts/scrape_links.py --priority x --save-raw
```

Validation commands:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; uv run --no-cache python -B scripts/db_status.py
$env:PYTHONDONTWRITEBYTECODE='1'; @'<sqlite validation script>'@ | uv run --no-cache python -B -
```

The first validation query initially failed only while formatting `Asia/Kolkata` via `zoneinfo` because local `tzdata` was unavailable. It was rerun with an explicit `+05:30` offset and succeeded. That failed formatting-only query did not mutate the database.

## Initial Selection And Rows Affected

- X/Twitter distinct normalized URLs selected by the scraper: 471.
- X/Twitter link rows affected: 481.
- X/Twitter link rows without any scrape attempt after the run: 0.
- Remaining pending X/Twitter normalized URLs under first-pass scraper semantics: 0.
- Non-X scrape attempt rows after the run: 213, unchanged from Checkpoint 002.

## Batch Results

Command summary from SQLite after the run:

```text
links_total: 588
scrape_attempts_total: 694
x_distinct_normalized_urls: 471
x_link_rows: 481
x_scrape_attempt_rows: 481
remaining_pending_x_normalized_urls_first_pass: 0
non_x_distinct_normalized_urls: 104
non_x_link_rows: 107
non_x_scrape_attempt_rows: 213
```

Latest status counts by X/Twitter link row:

```text
retry_pending: 481 link rows, 471 normalized URLs
```

All X/Twitter scrape attempt rows:

```text
retry_pending: 481 attempt rows, 471 normalized URLs
```

## Raw Artifacts

- Expected X/Twitter raw files by distinct normalized URL: 471.
- Existing X/Twitter raw files: 471.
- Zero-byte X/Twitter raw files: 0.
- Total X/Twitter raw bytes: 128,256,680.
- Raw HTML size range: 266,380 to 302,648 bytes.

## Representative Successes

None. All public unauthenticated X/Twitter fetches returned HTTP 200 shell pages that did not expose tweet content to the static extractor, so they were recorded as `retry_pending`.

## Representative Errors And Reasons

Representative rows had:

- `status`: `retry_pending`
- `http_status`: 200
- `title`: NULL
- `error_type`: NULL
- `error_message`: NULL
- `text_length`: 493
- `html_length`: roughly 270,000 to 281,000 bytes in the sampled rows
- Reason: the extracted text begins with `JavaScript is not available. We've detected that JavaScript is disabled in this browser...`, indicating the unauthenticated static fetch received X's JavaScript shell rather than tweet content.

Representative normalized URLs:

- `https://x.com/i/status/2037182739695493399`
- `https://x.com/i/status/2038660653410320556`
- `https://x.com/i/status/2038663014098899416`
- `https://x.com/i/status/2038694680549077059`
- `https://x.com/i/status/2038894956459290963`

## Validation

`uv run --no-cache python -B scripts/db_status.py`:

```text
scrape_attempts: 694
links: 588
messages: 598
```

SQLite validation query:

```text
remaining_pending_x_normalized_urls_first_pass: 0
x_link_rows_without_attempt: 0
x_scrape_attempt_rows: 481
non_x_scrape_attempt_rows: 213
```

## Fixes Made

No code or documentation fixes were needed. `scripts/scrape_links.py` and `docs/scraping.md` were left unchanged.

## Next Actions

- Treat the 481 X/Twitter linked rows as first-pass recorded and no longer pending under scraper semantics.
- Later retry these `retry_pending` rows only with a separately approved public unauthenticated strategy. Do not use credentials, cookies, bearer tokens, account context, or paid APIs.
- Continue downstream classification/KB work with X/Twitter linked content marked unavailable pending a future public retry path.
