# Scraping

## Tooling

Linked-content extraction uses Scrapling through `scripts/scrape_links.py`.

The local environment is managed with `uv`. Scrapling `0.4.7` required explicit runtime dependencies in this environment:

- `curl-cffi`
- `playwright`
- `browserforge`

Static Scrapling fetching works without installing browser binaries. Playwright-managed Chromium is installed for explicitly approved sandboxed browser fallback use.

Browser isolation rule: never use the user's personal browser, existing browser profile, browser cookies, saved sessions, or any logged-in account context for scraping or viewing linked content. If a browser is ever explicitly approved, use only a Playwright-managed Chromium install with a fresh project-local profile such as `data/browser_sandbox/<run-id>/`, no imported storage state, no CDP connection to an existing browser, no `real_chrome`, and no reuse of Chrome/Edge/Brave/Firefox user data directories.

## Current Strategy

The scraper deduplicates network fetches by `normalized_url`, then writes a `scrape_attempts` row for every `links` row that shares that URL. This preserves message provenance while avoiding repeated fetches.

X/Twitter scraping is unauthenticated by default. Do not use credentials, browser profile cookies, session exports, bearer tokens, paid APIs, or any authenticated account context unless the user explicitly approves a separate method. If public unauthenticated scraping is blocked, record the exact status/error as `retry_pending` or `inaccessible` with the reason instead of bypassing access controls.

For X/Twitter, a recorded scrape attempt is not enough for downstream classification or Knowledge Base analysis. At least 50% of X/Twitter link rows must have actual parsed content before moving to DB-driven categorization/review work. "Parsed content" means post/embed text, author/date metadata, extracted outbound URLs/cards, or equivalent factual content captured from an approved source. HTTP 200 JavaScript shell pages, login walls, empty text, and generic retry records do not count toward this threshold.

Current approved unauthenticated X/Twitter strategy:

1. Prefer X's official oEmbed endpoint for individual public post URLs because it requires no authentication and can return fallback HTML containing post text and author/date markup.
2. Extract post IDs from `x.com/.../status/<id>` and `twitter.com/.../status/<id>` URLs, normalize mobile/share variants, and skip non-post URLs unless a specific approved endpoint exists.
3. Parse oEmbed JSON/HTML into structured text, author, author URL, post date when present, and embedded outbound links.
4. If oEmbed fails to produce enough parsed content, use only the approved sandboxed Playwright-managed Chromium fallback. This fallback must be no-login, no-credential, no-cookie, no-existing-profile, and project-local. It may view public X URLs in a fresh sandbox, capture HTML/screenshot evidence, and parse visible public content if available.
5. Store each attempt with method metadata such as `x_oembed` or `x_sandbox_browser` and validate parsed coverage by link row and normalized URL.
6. Do not use any other X extraction route unless the user explicitly changes this rule. This excludes public front ends, authenticated API access, paid providers, session cookies, bearer tokens, browser profiles, CDP to an existing browser, `real_chrome`, CAPTCHA bypasses, and any account-backed method.
7. If oEmbed plus the sandboxed browser fallback cannot reach the 50% parsed-content threshold, pause for orchestrator/user judgment.

The implemented oEmbed command stores parsed post content in `scrape_attempts` with `tool = 'x_oembed'`, writes raw oEmbed JSON/HTML under `data/scraped/raw/x_oembed/`, and maintains goal logs under `learnings/goal-003-x-oembed-parse/`.

Every important scrape process must leave an audit trail in two places:

- SQLite `scrape_attempts`: one row per linked WhatsApp record, including status, HTTP status, final URL, title, extracted text, metadata, error type, error message, and duration.
- Checkpoint/log files in `learnings/`: batch-level summary of commands run, start/end time, attempted URLs, successes, failures, inaccessible links, retry-pending links, representative errors, and next actions.

Do not rely only on terminal output. If a process is long-running or delegated through `/goal`, it must write a durable checkpoint file.

Recommended order:

1. Pilot batch across non-X links.
2. Non-X links, prioritizing GitHub and official docs.
3. GitHub metadata/relevance review.
4. X/Twitter links in small chunks.
5. Retry unresolved links by failure type.

## Commands

```powershell
uv run python scripts/scrape_links.py --priority non-x --limit 20 --save-raw
uv run python scripts/scrape_links.py --priority non-x --save-raw
uv run python scripts/scrape_links.py --priority x --limit 25 --save-raw
uv run python scripts/scrape_links.py --priority all --retry-failed --limit 50 --save-raw
uv run --no-cache python -B scripts/x_oembed_parse.py --save-raw --timeout 15 --delay 0.1 --heartbeat-interval 25
```

After a batch, write a checkpoint in `learnings/` and include status counts from SQLite.

## Status Meanings

- `success`: content was fetched and extracted.
- `retry_pending`: content may need dynamic scraping, login context, rate-limit handling, or another attempt.
- `inaccessible`: durable access barrier such as 401, 403, 404, 410, or 451.
- `failed`: unexpected error or status that needs inspection.
- `skipped`: deliberate policy or priority skip.

## Minimum Batch Log Fields

Each scrape checkpoint should include:

- Batch name and date.
- Command(s) run.
- Scope, such as `non-x`, `x`, `github`, or `retry-failed`.
- Number of normalized URLs selected.
- Number of link rows affected.
- Counts by status.
- Top domains processed.
- Representative successes.
- Representative failures with error type and error message.
- Retry plan for `retry_pending` and `failed` records.
- Any code or dependency changes made during the batch.
