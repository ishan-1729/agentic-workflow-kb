# Agentic Workflow Knowledge Base Project

This folder is the local working area for exporting, deduplicating, scraping, classifying, reviewing, and implementing a knowledge base from WhatsApp group material about agentic optimizations, setups, and workflows.

## Current Goal

Build a factual, searchable, wiki-style knowledge base for this project from:

- The entire primary WhatsApp group containing agentic optimizations and setups/workflows.
- Messages from other WhatsApp groups that are tagged with labels such as `Add to Claude Code`, `Add to Codex`, `Claude Code`, or similar variants.
- External content linked from those messages, especially Twitter/X links.

## Critical Constraints

- WhatsApp must be treated as read-only. Do not delete, edit, react to, forward, mark up, or post anything in WhatsApp.
- Export only to local files in this workspace.
- Preserve every WhatsApp entry in the local database, even when linked content cannot be scraped during a pass.
- Do exact duplicate removal first only as "level 1" deduplication.
- Use Scrapling for systematic linked-content extraction in batches.
- Use SQLite as the source of truth for exported messages, links, scraped content, categories, review evidence, and knowledge-base decisions.
- Verify unfamiliar claims, tools, and project safety before finalizing analysis.
- Do not blindly install or run code from GitHub projects. Use promptfoo-based safety/evaluation checks before implementation or execution.
- Document major checkpoints, learnings, pitfalls, and handoff state in `learnings/`.
- Long-running delegated work must use Codex CLI `/goal` plus the CLI-side `Stop` hook wake bridge in `docs/cli-wake-bridge.md`.

## High-Level Phases

1. Export WhatsApp material locally.
2. Normalize and exact-deduplicate the local export.
3. Extract links from all retained messages.
4. Scrape linked content in batches with Scrapling.
5. Store all raw and processed data in SQLite.
6. Categorize items into broad agentic workflow categories.
7. Deep-review Knowledge Base candidates and choose the best fit for this project.
8. Implement the chosen wiki-style knowledge base with backlinks, formatting, comparison pages, and search.
9. Retry unresolved link extraction until all feasible links are scraped or documented as inaccessible.
10. Re-run Knowledge Base analysis after complete scraping and update the implementation if necessary.
11. Enrich the knowledge base with graph/knowledge-graph comparisons and Venn-style comparison artifacts.
12. Add regular keyword search and intent-based semantic search.

## Resume Instructions

If context is lost, first read:

1. `docs/handoff.md`
2. `docs/operating-rules.md`
3. `docs/cli-wake-bridge.md`
4. `docs/data-pipeline.md`
5. Latest file in `learnings/`

Then inspect the SQLite database and local export folders before continuing.
