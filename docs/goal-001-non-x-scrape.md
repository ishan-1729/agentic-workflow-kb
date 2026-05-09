# Goal 001: First-Pass Non-X Scrape

## Start Interactive CLI

Run this in the terminal panel that will host the delegated Codex CLI agent:

```powershell
codex --disable fast_mode -C "<workspace>" -s workspace-write -m gpt-5.5 -c model_reasoning_effort="xhigh"
```

Then paste this into the Codex CLI composer:

```text
/goal Complete the first-pass scrape for all non-X/Twitter links in this project without stopping until every currently pending non-X normalized URL has a recorded scrape_attempt status in SQLite. Read docs/README.md, docs/handoff.md, docs/operating-rules.md, docs/data-pipeline.md, docs/scraping.md, docs/codex-goals.md, docs/import-state.md, and the latest learnings checkpoint before acting. Use uv only. Keep imports/ strictly read-only. Use the existing script: uv run python scripts/scrape_links.py --priority non-x --save-raw. If a batch fails, inspect the error, make minimal fixes only inside scripts/scrape_links.py or docs/scraping.md if truly necessary, then retry. Do not scrape X/Twitter links in this goal. Do not install or run GitHub projects. Do not alter WhatsApp raw exports. You own only data/db/agentic_workflow.db scrape_attempt rows, data/scraped/raw/, docs/scraping.md if needed, scripts/scrape_links.py if needed, learnings/checkpoint-002-non-x-scrape.md, and learnings/goal-001-non-x-scrape.done. Keep durable logging: SQLite scrape_attempt rows for every link row and a checkpoint file listing commands, start/end time, selected URL counts, link rows affected, status counts, representative successes, representative errors with reasons, fixes, and next retry/actions. Validate with uv run python scripts/db_status.py and a SQLite query showing remaining pending non-X normalized URLs equals 0, or document exact blockers if not achievable. At the very end, after validation passes or after documenting a blocker, write learnings/goal-001-non-x-scrape.done with a one-paragraph completion/blocker summary beginning with GOAL_001_DONE or GOAL_001_BLOCKED. Stop when validation passes or a blocker requires orchestrator/user judgment.
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

While this goal runs, the main orchestrator should not concurrently run non-X scraping or edit `scripts/scrape_links.py`, `docs/scraping.md`, or `data/db/agentic_workflow.db`.
