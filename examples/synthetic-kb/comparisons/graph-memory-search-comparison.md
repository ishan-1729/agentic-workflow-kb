---
title: "Graph, Memory, And Search Comparison"
page_type: "comparison"
generated_by: "scripts/build_kb.py"
generator_version: "baseline-kb-v1"
generated_at: "2026-05-09T23:31:23+00:00"
source_message_ids: [1, 3, 4]
source_link_ids: [1, 3, 4]
candidate_ids: [1, 2, 3, 4, 5]
decision_ids: []
tags: ["comparison", "graph", "memory", "search"]
---
# Graph, Memory, And Search Comparison

This comparison separates repo-owned artifacts that are already safe to generate from deferred external graph, memory, and semantic systems.

## Venn-Style Capability Map

| Capability | Markdown Wikilinks And Backlinks | Topic Co-occurrence Graph | SQLite FTS5 Lexical Search | Deferred Semantic Or Graph Backend |
| --- | --- | --- | --- | --- |
| Local-first source control | Yes | Yes | Yes | Depends on later safety review |
| Human-readable knowledge base | Yes | Partial | Search results only | Depends on backend |
| Relationship navigation | Yes, explicit wikilinks | Yes, inferred topic edges | No | Usually yes |
| Fast keyword search | No | No | Yes | Usually yes |
| Semantic equivalence search | No | No | No | Possible later |
| Agent-safe baseline | Yes | Yes | Yes | Not approved as runtime dependency |
| Current implementation status | Implemented | Implemented as generated page | Implemented | Deferred |

## Current Project Choice

- Keep SQLite as the source of truth.
- Keep Markdown pages, wikilinks, backlinks, FTS5 search, and topic graph pages as repo-owned generated artifacts.
- Treat external graph/vector/memory projects as comparison targets until a separate promptfoo-backed execution review approves a concrete integration.

## Relevant Candidates

| Candidate | Type | Review Status | Role In This Comparison |
| --- | --- | --- | --- |
| [[Candidate: Project-owned Obsidian-compatible Markdown wiki backed by SQLite]] | `recommended_architecture` | `recommended_primary` | current baseline |
| [[Candidate: Karpathy LLM Wiki pattern]] | `method_pattern` | `recommended_pattern` | current baseline |
| [[Candidate: Obsidian-compatible local Markdown vault]] | `markdown_wiki_format` | `recommended_format` | current baseline |
| [[Candidate: SQLite FTS5 lexical search layer]] | `supporting_search_layer` | `recommended_component` | current baseline |
| [[Candidate: Synthetic Graph Overlay Backend]] | `external_graph_overlay` | `deferred_later_graph_overlay` | deferred comparison target |

## Related Generated Pages

- [[Candidate Comparison]]
- [[Topic Co-occurrence Graph]]
- [[Search Guide]]
- [[Backlink Index]]
