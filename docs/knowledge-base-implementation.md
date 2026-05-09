# Knowledge Base Implementation

## Baseline

The initial Knowledge Base implementation is repo-owned and generated from SQLite by `scripts/build_kb.py`.

It does not install, import, run, or depend on external KB projects. Obsidian compatibility is a Markdown file format target, not a runtime dependency.

## Outputs

- `kb/index.md`: main vault entry point.
- `kb/decisions/knowledge-base-approach.md`: current KB decision and decision history.
- `kb/comparisons/candidate-comparison.md`: candidate comparison with promptfoo disposition.
- `kb/candidates/`: one page per KB candidate.
- `kb/topics/`: one page per broad classification category.
- `kb/sources/messages/`: one source page per imported WhatsApp message.
- `kb/indexes/backlinks.md`: generated wikilink backlink index.
- `kb/indexes/unresolved-scrape-gaps.md`: scrape gaps before the exhaustive retry goal.
- `kb/indexes/topic-cooccurrence-graph.md`: repo-owned topic co-occurrence graph generated from classification rows.
- `kb/comparisons/graph-memory-search-comparison.md`: Venn-style comparison of backlinks, topic graph, FTS5 search, and deferred graph/semantic backends.
- `kb/search.md`: local search usage.

## Commands

```powershell
uv run --no-cache python -B scripts\build_kb.py generate
uv run --no-cache python -B scripts\build_kb.py validate --json
uv run --no-cache python -B scripts\build_kb.py search "Obsidian" --limit 10
uv run --no-cache python -B scripts\build_kb.py intent-search "agent memory graph" --limit 10
uv run --no-cache python -B scripts\build_kb.py checkpoint
```

## SQLite Tables

The generator creates and maintains:

- `kb_pages`: generated page text and metadata.
- `kb_page_links`: extracted wikilinks and resolved target paths.
- `kb_pages_fts`: SQLite FTS5 lexical search index.

SQLite remains the source of truth. Markdown is regenerated output.

## Validation Rules

- Every generated Markdown page must have frontmatter.
- Synthesis/source pages must carry provenance through source message IDs, link IDs, candidate IDs, or decision IDs.
- Every `[[wikilink]]` must resolve.
- SQLite integrity check must pass.
- FTS row count must match generated page count.
- A sample search for `Obsidian` must return hits.

## Search And Graph Baseline

- SQLite FTS5 remains the regular keyword-search layer.
- Deterministic `intent-search` expands common project concepts and ranks generated KB pages locally without embeddings, vector stores, or external services.
- Topic co-occurrence graph pages are generated from classification rows and are analysis artifacts, not external graph databases.

## Deferred Work

- External vector, embedding, graph, or semantic retrieval backends remain blocked until a separate promptfoo-backed isolated execution review approves a concrete integration.
