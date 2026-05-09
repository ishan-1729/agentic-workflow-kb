# Checkpoint 018: Synthetic KB Example

Date: 2026-05-10

## Scope

- Decided to publish generated KB example pages only when they are built from synthetic fixture data.
- Regenerated the synthetic fixture DB with repo-relative source paths.
- Generated `examples/synthetic-kb/` from the synthetic fixture and validated it.

## Commands Run

- `uv run --no-cache python -B scripts\create_synthetic_fixture.py`
- `uv run --no-cache python -B scripts\build_kb.py --db data\fixtures\synthetic\agentic_workflow.db --kb-dir examples\synthetic-kb generate`
- `uv run --no-cache python -B scripts\build_kb.py --db data\fixtures\synthetic\agentic_workflow.db --kb-dir examples\synthetic-kb validate --json`
- `rg -n "<local workspace path>|<local user home>|<thread-id pattern>" examples fixtures scripts\create_synthetic_fixture.py README.md`

## Validation Results

- Generated pages: 25
- SQLite integrity: ok
- Missing frontmatter: 0
- Missing provenance: 0
- Unresolved wikilinks: 0
- FTS rows: 25
- Keyword search sample hits: 5
- Intent search sample hits: 5
- Local path/thread-id scan: no matches in committed example/fixture docs.

## Safety Confirmation

The checked-in generated example KB is synthetic. It does not include private WhatsApp messages, private scraped content, private SQLite data, local hook state, credentials, personal browser state, or generated pages from the private KB.
