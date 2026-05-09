# Goal 002: First-Pass X/Twitter Scrape

## Start Interactive CLI

Run this in the terminal panel that will host the delegated Codex CLI agent:

```powershell
codex --disable fast_mode -C "<workspace>" -s workspace-write -m gpt-5.5 -c model_reasoning_effort="xhigh"
```

Then paste this into the Codex CLI composer:

```text
/goal Complete the first-pass scrape for all X/Twitter links in this project without stopping until every currently pending X/Twitter normalized URL has a recorded scrape_attempt status in SQLite, or until a precisely documented blocker requires orchestrator/user judgment. Read docs/README.md, docs/handoff.md, docs/operating-rules.md, docs/data-pipeline.md, docs/scraping.md, docs/codex-goals.md, docs/import-state.md, learnings/checkpoint-001-import-and-goal-delegation.md, and learnings/checkpoint-002-non-x-scrape.md before acting. Use uv only. Keep imports/ strictly read-only. Use unauthenticated public scraping only: do not use credentials, cookies, browser profiles, bearer tokens, paid APIs, or authenticated account context. Do not write to WhatsApp, do not open WhatsApp for mutation, and do not install or run GitHub projects. Use the existing script first: set PYTHONDONTWRITEBYTECODE=1 and clear HTTP_PROXY, HTTPS_PROXY, ALL_PROXY, http_proxy, https_proxy, and all_proxy, then run uv run --no-cache python -B scripts/scrape_links.py --priority x --save-raw. If a batch fails, inspect the error, make minimal fixes only inside scripts/scrape_links.py or docs/scraping.md if truly necessary, then retry. If X/Twitter blocks unauthenticated extraction, record the exact status/error as retry_pending or inaccessible rather than trying to bypass with credentials. You own only data/db/agentic_workflow.db scrape_attempt rows for X/Twitter link rows, data/scraped/raw/ X/Twitter artifacts, docs/scraping.md if needed, scripts/scrape_links.py if needed, learnings/checkpoint-003-x-first-pass.md, and learnings/goal-002-x-first-pass.done. Keep durable logging: SQLite scrape_attempt rows for every X/Twitter link row and a checkpoint file listing commands, start/end time, selected URL counts, link rows affected, status counts, raw artifact counts, representative successes, representative errors with reasons, fixes, credential policy confirmation, and next retry/actions. Validate with uv run --no-cache python -B scripts/db_status.py and a SQLite query showing 0 remaining pending X/Twitter normalized URLs under first-pass semantics, plus confirming non-X scrape_attempt counts were not reduced. At the very end, after validation passes or after documenting a blocker, write learnings/goal-002-x-first-pass.done with a one-paragraph completion/blocker summary beginning with GOAL_002_DONE or GOAL_002_BLOCKED. Stop when validation passes or a blocker requires orchestrator/user judgment.
```

## Check Goal State

Inside the same interactive CLI session:

```text
/goal
```

Use these only when needed:

```text
/goal pause
/goal resume
/goal clear
```

## Orchestrator Note

While this goal runs, the main orchestrator should not concurrently run X/Twitter scraping or edit `scripts/scrape_links.py`, `docs/scraping.md`, or `data/db/agentic_workflow.db`.
