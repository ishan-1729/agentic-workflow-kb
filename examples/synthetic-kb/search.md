---
title: "Search Guide"
page_type: "search_guide"
generated_by: "scripts/build_kb.py"
generator_version: "baseline-kb-v1"
generated_at: "2026-05-09T23:31:23+00:00"
source_message_ids: []
source_link_ids: []
candidate_ids: []
decision_ids: [1]
tags: ["search"]
---
# Search Guide

Keyword search is backed by SQLite FTS5 over generated KB pages. Intent search is a repo-owned deterministic baseline that expands common project concepts before ranking generated KB pages; it does not use embeddings or an external vector backend.

## Commands

```powershell
uv run --no-cache python -B scripts\build_kb.py search "Obsidian" --limit 10
uv run --no-cache python -B scripts\build_kb.py search "knowledge base" --json
uv run --no-cache python -B scripts\build_kb.py intent-search "agent memory graph" --limit 10
uv run --no-cache python -B scripts\build_kb.py intent-search "safe browser automation" --json
uv run --no-cache python -B scripts\build_kb.py validate
```

## Notes

- FTS5 is the reliable lexical baseline.
- Intent search is deterministic query expansion plus local page scoring; it is useful for semantic-ish exploration without new dependencies.
- Any external vector, graph, or embedding backend still needs a separate safety review before execution.

## Related

- [[Decision: Knowledge Base Approach]]
- [[Candidate: SQLite FTS5 lexical search layer]]
- [[Topic Co-occurrence Graph]]
- [[Graph, Memory, And Search Comparison]]
- [[Unresolved Scrape Gaps]]
