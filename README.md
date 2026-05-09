# Agentic Workflow KB

Project-owned tooling for turning local WhatsApp exports and linked public content into a sourced, searchable Markdown knowledge base for agentic workflow research.

This public repository contains the reusable pipeline, orchestration docs, safety-review scaffolding, and checkpoint notes. It intentionally does not include the private WhatsApp exports, SQLite database, scraped artifacts, browser sandbox state, or generated corpus-derived KB pages.

## What Is Included

- `scripts/`: ingestion, scraping, classification, KB generation, search, safety review, and Codex goal orchestration helpers.
- `docs/`: operating rules, data pipeline notes, scraping/browser constraints, goal specs, and handoff guidance.
- `evals/`: promptfoo configuration used for static KB candidate safety review.
- `learnings/checkpoint-*.md`: curated checkpoint records from major implementation phases.

## What Is Excluded

- `imports/`: local WhatsApp exports and source files.
- `data/`: SQLite databases, scrape artifacts, browser sandbox output, and generated safety-review output.
- `kb/`: generated knowledge-base pages derived from private corpus content, except `kb/README.md`.
- `.codex/`, `.tools/`, `.venv/`, `.uv_cache/`: local execution state and caches.

## Local Use

Install dependencies with `uv`:

```powershell
uv sync
```

Run status checks against a local database:

```powershell
uv run --no-cache python -B scripts\db_status.py
```

Generate and validate the local KB after private inputs are present:

```powershell
uv run --no-cache python -B scripts\build_kb.py --validate
```

The repository treats SQLite as the local source of truth and keeps raw exports read-only.
