# Goal 004: Broad Multi-Label Classification

## Start Interactive CLI

Run this in the terminal panel that will host the delegated Codex CLI agent:

```powershell
codex --disable fast_mode -C "<workspace>" -s workspace-write -m gpt-5.5 -c model_reasoning_effort="xhigh"
```

Then paste this into the Codex CLI composer:

```text
/goal Classify every imported in-scope WhatsApp message into broad, non-mutually-exclusive categories without stopping until every non-duplicate message has at least one classification row in SQLite, or until a precisely documented blocker requires orchestrator/user judgment. Read docs/README.md, docs/handoff.md, docs/operating-rules.md, docs/data-pipeline.md, docs/classification.md, docs/sqlite-schema.md, docs/scraping.md, docs/browser-sandbox.md, docs/codex-goals.md, docs/import-state.md, learnings/checkpoint-004-x-oembed-parse.md, and learnings/checkpoint-005-continuous-loop-repair.md before acting. Use uv only. Keep imports/ strictly read-only. Do not scrape new links in this goal, do not mutate WhatsApp, do not install or run GitHub projects, and do not use browser automation. Use the existing SQLite DB as source of truth: WhatsApp message text, tags, duplicate flags, links/domains, latest successful non-X scrape content where available, and latest successful x_oembed content where available. Implement a reproducible classification script if needed, preferably scripts/classify_items.py, that writes rows into the existing classifications table with message_id, category, confidence, rationale, classified_at, and model_or_method. Use the category set in docs/classification.md, but add a small number of additional broad categories only if the data clearly requires them and document why. Categories are multi-label; each message can have several categories. Preserve all rows; exact duplicates may either receive their own classification or an explicit duplicate-linked classification, but every non-duplicate message must have at least one useful category. Keep rationales concise and evidence-grounded. If internet lookup is needed for unclear taxonomy concepts, use it sparingly and cite findings in the checkpoint. You own only scripts/classify_items.py if needed, data/db/agentic_workflow.db classification rows, docs/classification.md if needed, learnings/checkpoint-006-broad-classification.md, learnings/goal-004-broad-classification.heartbeat.json, and learnings/goal-004-broad-classification.done. Keep durable logging: start/end time, commands, total messages, unique/non-duplicate messages, classified counts, duplicate handling, category counts, low-confidence counts, representative category examples, and unresolved questions. Update learnings/goal-004-broad-classification.heartbeat.json at the start, after each major batch, and before done/blocker. Validate with uv run --no-cache python -B scripts/db_status.py and SQLite queries proving every non-duplicate message has at least one classification row and reporting category counts. At the very end, after validation passes or after documenting a blocker, write learnings/goal-004-broad-classification.done with a one-paragraph completion/blocker summary beginning with GOAL_004_DONE or GOAL_004_BLOCKED. Stop when validation passes or a blocker requires orchestrator/user judgment.
```

## Orchestrator Note

While this goal runs, the main orchestrator should not concurrently edit classification scripts, docs/classification.md, or SQLite classification rows.
