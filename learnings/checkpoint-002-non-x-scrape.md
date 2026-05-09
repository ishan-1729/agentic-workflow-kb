# Checkpoint 002: Non-X First-Pass Scrape

## Date

2026-05-09

## Scope

- Goal: first-pass scrape for all currently pending non-X/Twitter normalized URLs.
- Raw imports under `imports/` remained read-only.
- X/Twitter scrape scope was not run.
- No GitHub project was installed or executed.

## Start And End

- Start: 2026-05-09T08:42+05:30, after reading the required docs and latest checkpoint.
- First scrape attempt: 2026-05-09T08:45:35+05:30.
- Final validation: 2026-05-09T09:00+05:30.

## Commands Run

The interactive goal runner holds the default uv cache, so validation and scrape commands were run with `UV_NO_CACHE=1` or `uv run --no-cache`. `PYTHONDONTWRITEBYTECODE=1` was used after a denied `.pyc` replacement. Proxy variables were removed for scrape commands because inherited `HTTP_PROXY`, `HTTPS_PROXY`, and `ALL_PROXY` pointed at `http://127.0.0.1:9`.

```powershell
uv run --no-cache python scripts/db_status.py
uv run --no-cache python scripts/scrape_links.py --priority non-x --save-raw
uv run --no-cache python -B scripts/scrape_links.py --priority non-x --save-raw
uv run python scripts/scrape_links.py --priority non-x --save-raw
uv run python scripts/scrape_links.py --priority non-x --save-raw --refresh-raw
uv run python scripts/db_status.py
uv run python -  # final SQLite validation query
```

Final no-op pending check:

```text
SUMMARY {"failed": 0, "inaccessible": 0, "retry_pending": 0, "selected_url_count": 0, "skipped": 0, "success": 0}
```

## Initial Selection

- Non-X distinct normalized URLs: 104.
- Non-X link rows: 107.
- Initial non-X scrape attempts: 0.
- Initial pending non-X normalized URLs under scraper semantics: 104.

Top selected domains:

- `github.com`: 77 link rows, 74 normalized URLs.
- `arxiv.org`: 5 link rows, 5 normalized URLs.
- `youtu.be`: 4 link rows, 4 normalized URLs.
- `reddit.com`: 3 link rows, 3 normalized URLs.
- `openai.com`: 2 link rows, 2 normalized URLs.

## Batch Results

Failed/retried setup batches:

- First full scrape selected 104 URL groups and fetched the first GitHub page, then SQLite raised `OperationalError: disk I/O error` during commit. The hot rollback journal recovered to 0 committed scrape attempts.
- Second retry selected 104 URL groups, committed no durable rows after recovery, and hit `OperationalError: disk I/O error` during a later insert.
- Third retry selected 104 URL groups and committed 3 success attempts, then failed while printing a GitHub title containing a Unicode star to cp1252 stdout.

Completed first-pass batch:

- Command: `uv run python scripts/scrape_links.py --priority non-x --save-raw`.
- Selected URL groups: 101, because 3 were already committed by the previous retry.
- Link rows affected in this batch: 104.
- URL-group summary from the command: 98 success, 2 inaccessible, 1 retry_pending, 0 failed, 0 skipped.
- After this batch, all 107 non-X link rows had at least one recorded scrape_attempt row.

Raw repair batch:

- Command: `uv run python scripts/scrape_links.py --priority non-x --save-raw --refresh-raw`.
- Reason: the original `page_html()` function selected Scrapling `.text`, which was empty for these responses, leaving 103 zero-byte raw files even though DB extracted text was present.
- Selected URL groups: 103 completed non-X URLs with zero-byte raw artifacts.
- Link rows affected: 106.
- URL-group summary: 101 success, 2 inaccessible, 0 retry_pending, 0 failed, 0 skipped.
- Raw HTML files after repair: 103.
- Zero-byte raw HTML files after repair: 0.
- Raw HTML total bytes: 44,125,015.
- Raw HTML size range: 16,643 to 1,835,716 bytes.

## Final Validation

`uv run python scripts/db_status.py`:

```text
scrape_attempts: 213
links: 588
messages: 598
```

Final SQLite validation query:

```text
quick_check ok
non_x_distinct_urls 104
non_x_link_rows 107
all_non_x_scrape_attempt_rows 213
x_scrape_attempt_rows 0
non_x_link_rows_without_attempt 0
remaining_pending_non_x_normalized_urls 0
```

Latest status counts by non-X link row:

```text
success: 104 link rows, 101 normalized URLs
inaccessible: 2 link rows, 2 normalized URLs
retry_pending: 1 link row, 1 normalized URL
```

All non-X scrape_attempt rows:

```text
success: 208
inaccessible: 4
retry_pending: 1
```

The larger attempt count is expected because the raw repair pass re-fetched completed URLs and recorded those attempts rather than silently overwriting raw artifacts.

## Representative Successes

- `https://github.com/Yeachan-Heo/oh-my-claudecode` -> 200, GitHub repository title captured.
- `https://github.com/Yeachan-Heo/oh-my-codex` -> 200, GitHub repository title captured.
- `https://github.com/instructkr/claw-code` -> 200, redirected/final GitHub title captured.
- `https://openai.com/index/harness-engineering/` -> 200, OpenAI article title captured.
- `https://github.com/HKUDS/DeepTutor` -> 200, GitHub repository title captured for both linked rows.

## Representative Errors And Reasons

- `https://github.com/TheRealSeanDonahoe/agents-md`: `inaccessible`, HTTP 404, title `Page not found - GitHub`.
- `https://github.com/mattpocock/skills/tree/main/grill-me`: `inaccessible`, HTTP 404, title `File not found - GitHub`.
- `https://youtu.be/srqWFT_TUec`: `retry_pending`, `DNSError`, message: `Failed to perform, curl: (6) Could not resolve host: www.youtube.com`.

## Fixes Made

Modified `scripts/scrape_links.py` only.

- Added transient exception classification so network/DNS/proxy/timeouts record `retry_pending` instead of staying indefinitely pending as `failed`.
- Added whole-transaction write retries for SQLite scrape_attempt inserts and commits.
- Set SQLite `busy_timeout` and `journal_mode = PERSIST` to avoid repeated rollback-journal deletion failures in this Windows sandbox.
- Escaped terminal JSON output with `ensure_ascii=True` so non-ASCII page titles do not fail on cp1252 stdout.
- Fixed raw HTML persistence to prefer Scrapling `html_content` and non-empty response body over empty `.text`.
- Added `--refresh-raw` to re-fetch completed URLs with missing or zero-byte raw artifacts while recording the repair attempts in SQLite.

## Remaining Notes

- One non-X URL remains `retry_pending`: `https://youtu.be/srqWFT_TUec`, because `www.youtube.com` failed DNS resolution during this pass. It has a recorded scrape_attempt status, so it is no longer pending under the project scraper semantics.
- Two GitHub URLs are durable 404s and are marked `inaccessible`.
- `data/db/agentic_workflow.db-journal` remains as the expected persistent SQLite journal sidecar after switching to `journal_mode = PERSIST`.
- A failed `py_compile` attempt left `scripts/__pycache__/scrape_links.cpython-313.pyc.2498783455504`; repeated deletion attempts failed with Windows `Access is denied`. Later commands used `PYTHONDONTWRITEBYTECODE=1`.

## Next Actions

- Later retry the single `retry_pending` YouTube URL when DNS/network conditions are stable, or use a YouTube-specific extractor if static Scrapling continues to fail.
- Treat the two GitHub 404s as inaccessible unless source messages reveal corrected URLs.
- X/Twitter scraping remains untouched and should be handled under a separate goal.
