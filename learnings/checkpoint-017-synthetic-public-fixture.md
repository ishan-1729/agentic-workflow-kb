# Checkpoint 017: Synthetic Public Fixture

Date: 2026-05-10

## Scope

- Added a synthetic WhatsApp-style fixture that is safe for the public repository.
- Added `scripts/create_synthetic_fixture.py` to build a small SQLite DB under ignored `data/fixtures/synthetic/`.
- Exercised KB generation, validation, keyword search, intent search, and external-backend safety matrix reporting against the synthetic DB.

## Files Added

- `fixtures/README.md`
- `fixtures/synthetic/imports/Primary/WhatsApp Chat with Synthetic Agentic Workflow Lab.txt`
- `scripts/create_synthetic_fixture.py`

## Generator Fix

The fixture exposed a validation edge case in `scripts/build_kb.py`: when all links were successful, `indexes/unresolved-scrape-gaps.md` had no provenance IDs even though it summarized link status counts. The generator now records all link IDs as provenance for that page.

## Commands Run

- `uv run --no-cache python -B scripts\create_synthetic_fixture.py`
- `uv run --no-cache python -B scripts\build_kb.py --db data\fixtures\synthetic\agentic_workflow.db --kb-dir data\fixtures\synthetic\kb generate`
- `uv run --no-cache python -B scripts\build_kb.py --db data\fixtures\synthetic\agentic_workflow.db --kb-dir data\fixtures\synthetic\kb validate --json`
- `uv run --no-cache python -B scripts\build_kb.py --db data\fixtures\synthetic\agentic_workflow.db --kb-dir data\fixtures\synthetic\kb search "Obsidian" --json`
- `uv run --no-cache python -B scripts\build_kb.py --db data\fixtures\synthetic\agentic_workflow.db --kb-dir data\fixtures\synthetic\kb intent-search "agent memory graph" --json`
- `uv run --no-cache python -B scripts\external_backend_safety_matrix.py --db data\fixtures\synthetic\agentic_workflow.db --print-markdown`
- `uv run --no-cache python -B -c "<compile all scripts>"`

## Validation Results

- Synthetic messages: 5
- Level 1 duplicates: 1
- Links: 5
- Scrape attempts: 5 success rows
- Classifications: 10
- KB candidates: 5
- KB safety reviews: 5
- Generated KB pages: 25
- SQLite integrity: ok
- Missing frontmatter: 0
- Missing provenance: 0
- Unresolved wikilinks: 0
- FTS rows: 25
- Keyword search sample hits: 5
- Intent search sample hits: 5

## Safety Confirmation

The fixture is synthetic and does not include private WhatsApp messages, private URLs, credentials, local SQLite data, scrape artifacts, or generated private KB pages.
