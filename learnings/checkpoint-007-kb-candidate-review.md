# Checkpoint 007: Knowledge Base Candidate Review

Date: 2026-05-09

## Scope

- Goal: identify credible Knowledge Base candidates, compare them, write candidate/decision rows, and record an initial KB approach.
- Required docs and checkpoints were read before candidate extraction or DB writes.
- Raw `imports/` files remained read-only.
- WhatsApp was not opened or mutated.
- Browser automation was not used.
- No GitHub project was installed, cloned, executed, imported, or run.
- SQLite was used as source of truth for local evidence.

## Timing

- Started: 2026-05-09T11:40:47.915935+00:00
- Checkpoint generated: 2026-05-09T11:47:20.637758+00:00

## Commands Run

- `Get-Content -Raw <required docs/checkpoints>`
- `uv run --no-cache python -B scripts/db_status.py`
- `uv run --no-cache python -B -  # SQLite schema/category/evidence queries`
- `web search/open for public source verification`
- `uv run --no-cache python -B scripts/review_kb_candidates.py --apply`

## Local Evidence Reviewed

- Total messages in DB: 598
- Knowledge_Base messages reviewed: 67
- Related Memory / Graphs_Knowledge_Graphs / Search_Retrieval / Methods_Workflows messages scanned: 362
- SQLite integrity check before write: ok
- kb_candidates before write: 0
- decisions before write: 0
- kb_candidates inserted/updated in this pass: 14

## Public Sources Checked

- https://gist.github.com/karpathy?direction=desc&sort=updated
- https://obsidian.md/help/data-storage
- https://obsidian.md/help/links
- https://obsidian.md/help/plugins/backlinks
- https://obsidian.md/help/plugins/graph
- https://www.sqlite.org/fts5.html
- https://github.com/agenticnotetaking/arscontexta
- https://github.com/agno-agi/pal
- https://github.com/nashsu/llm_wiki
- https://github.com/AgriciDaniel/claude-obsidian
- https://github.com/topoteretes/cognee
- https://github.com/Lum1104/Understand-Anything
- https://github.com/cytostack/openwolf
- https://openwolf.com/
- https://github.com/kepano/obsidian-skills
- https://github.com/safishamsi/graphify
- https://github.com/cocoindex-io/cocoindex-code

## Comparison Criteria

- Factual alignment with WhatsApp/SQLite KB evidence
- Readable local Markdown and wiki-style backlinks
- Agent consumption/editing without a fragile app dependency
- SQLite provenance/importability from messages, links, and scrape rows
- Lexical search now and semantic/graph search later
- Graph/relationship support without making graph infra the primary source
- Low Windows operational risk
- Minimal untrusted install/execute surface before promptfoo review

## Candidate Comparison

| Candidate | Type | Score/40 | Status | Disposition |
| --- | --- | ---: | --- | --- |
| Project-owned Obsidian-compatible Markdown wiki backed by SQLite | recommended_architecture | 38 | recommended_primary | Recommended initial implementation direction. |
| Karpathy LLM Wiki pattern | method_pattern | 36 | recommended_pattern | Use as the core mental model for the KB. |
| Obsidian-compatible local Markdown vault | markdown_wiki_format | 35 | recommended_format | Use compatible Markdown/wikilinks, not an Obsidian dependency. |
| SQLite FTS5 lexical search layer | supporting_search_layer | 34 | recommended_component | Implement with the initial KB if FTS5 is available locally. |
| Ars Contexta | external_claude_code_plugin | 27 | deferred_promptfoo_required | Study as design inspiration after safety review; do not adopt initially. |
| Pal (Personal Agent that Learns) | external_personal_agent_kb | 25 | deferred_promptfoo_required | Use as architecture reference for raw/wiki/SQL separation, not as initial implementation. |
| LLM Wiki desktop app (nashsu/llm_wiki) | external_desktop_kb_app | 24 | deferred_promptfoo_required | Compare later; initial repo-native Markdown is simpler and safer. |
| claude-obsidian | external_obsidian_companion | 25 | deferred_promptfoo_required | Useful comparison target; do not run before safety review. |
| Cognee | external_graph_vector_memory_engine | 22 | deferred_later_graph_memory | Evaluate later for semantic/graph memory enrichment. |
| Understand Anything | external_graph_overlay | 23 | deferred_later_graph_overlay | Potential graph visualization layer after initial KB and safety review. |
| OpenWolf | external_code_agent_memory | 18 | not_initial_primary | Not a primary KB candidate; keep as a memory design reference. |
| Graphify | external_folder_to_graph_skill | 21 | deferred_later_graph_overlay | Potential later graph extractor, not initial KB foundation. |
| Obsidian Skills | external_agent_obsidian_interface | 20 | deferred_supporting_agent_interface | Possible later helper, not an initial dependency. |
| CocoIndex-style graph and semantic retrieval backend | external_retrieval_backend | 19 | deferred_later_semantic_search | Future search/backend comparison candidate. |

## Recommendation

Implement a project-owned, Obsidian-compatible Markdown wiki under `kb/`, generated from SQLite. Keep SQLite as source of truth for messages, links, scrape attempts, classifications, candidates, and decisions. Generate source-cited synthesis pages with stable YAML frontmatter, Obsidian-compatible `[[wikilinks]]`, backlinks/comparison pages, and a generated index. Add SQLite FTS5 lexical search first. Defer external GitHub projects, semantic retrieval, and graph overlays until the repo-native Markdown KB is working and a promptfoo-backed safety review approves any code execution.

## Candidate Notes

### Project-owned Obsidian-compatible Markdown wiki backed by SQLite

- Type: recommended_architecture
- Local anchor: message_id=17, link_id=14
- Summary: Use SQLite as source of truth and generate a local Markdown wiki under kb/ with stable frontmatter, message/link provenance, wikilinks/backlinks, comparison pages, and SQLite FTS5 lexical search.
- Limitations: Requires implementing page generation, backlink extraction, source citation discipline, and validation scripts. Semantic search and graph visualization remain later phases.
- Safety: Lowest-risk path because it uses this repo's SQLite DB and Markdown files instead of executing external projects.
- Status: recommended_primary

### Karpathy LLM Wiki pattern

- Type: method_pattern
- Local anchor: message_id=17, link_id=14
- Summary: A method where raw sources stay immutable while an LLM incrementally compiles persistent interlinked Markdown articles, indexes, and lint/health checks.
- Limitations: It is a pattern, not a complete product. The project still needs local schemas, generation rules, and review gates.
- Safety: Safe as an architectural pattern; no external code execution required.
- Status: recommended_pattern

### Obsidian-compatible local Markdown vault

- Type: markdown_wiki_format
- Local anchor: message_id=18, link_id=15
- Summary: Emit ordinary Markdown files that can be opened as an Obsidian vault while remaining editable by agents and other tools.
- Limitations: Obsidian-specific block links and some plugin metadata are less portable. The repo should keep core pages valid Markdown.
- Safety: No need to install Obsidian to generate or consume Markdown; treat Obsidian as an optional viewer.
- Status: recommended_format

### SQLite FTS5 lexical search layer

- Type: supporting_search_layer
- Local anchor: message_id=None, link_id=None
- Summary: Add an FTS5 index over generated KB pages and/or source evidence for fast local lexical search before semantic search is introduced.
- Limitations: Lexical search does not cover semantic equivalence; later embedding or graph search should be evaluated separately.
- Safety: Low-risk built-in SQLite extension path, subject to local SQLite FTS5 availability validation.
- Status: recommended_component

### Ars Contexta

- Type: external_claude_code_plugin
- Local anchor: message_id=51, link_id=46
- Summary: Claude Code plugin that generates individualized Markdown knowledge systems, hooks, navigation maps, and note templates.
- Limitations: Claude Code plugin orientation, hook surface, generated automation, and token-intensive setup are broader than this initial KB need.
- Safety: GitHub or external project code was not installed, cloned, executed, or imported. Treat as untrusted until a later promptfoo-backed safety and dependency review.
- Status: deferred_promptfoo_required

### Pal (Personal Agent that Learns)

- Type: external_personal_agent_kb
- Local anchor: message_id=22, link_id=19
- Summary: Personal agent that combines raw sources, a compiled wiki, SQL structured data, and a routing/learning loop.
- Limitations: Requires Docker/service setup and external integrations; too broad for the initial local KB generation phase.
- Safety: GitHub or external project code was not installed, cloned, executed, or imported. Treat as untrusted until a later promptfoo-backed safety and dependency review.
- Status: deferred_promptfoo_required

### LLM Wiki desktop app (nashsu/llm_wiki)

- Type: external_desktop_kb_app
- Local anchor: message_id=204, link_id=196
- Summary: Cross-platform desktop app that ingests documents into an organized interlinked LLM-maintained wiki with graph/search features.
- Limitations: External app with a larger dependency footprint, GPL-3.0 licensing, and UI workflows that may not map cleanly to this repo.
- Safety: GitHub or external project code was not installed, cloned, executed, or imported. Treat as untrusted until a later promptfoo-backed safety and dependency review.
- Status: deferred_promptfoo_required

### claude-obsidian

- Type: external_obsidian_companion
- Local anchor: message_id=166, link_id=159
- Summary: Claude plus Obsidian companion that implements a persistent compounding wiki vault based on the Karpathy LLM Wiki pattern.
- Limitations: Plugin-specific workflow and seeded-vault assumptions may be useful but are not necessary for this project's first KB pass.
- Safety: GitHub or external project code was not installed, cloned, executed, or imported. Treat as untrusted until a later promptfoo-backed safety and dependency review.
- Status: deferred_promptfoo_required

### Cognee

- Type: external_graph_vector_memory_engine
- Local anchor: message_id=205, link_id=197
- Summary: Open-source knowledge/memory engine combining graph and vector retrieval for agent memory.
- Limitations: Graph/vector database stack is heavier than needed for a first local Markdown KB and may introduce service/configuration risk.
- Safety: GitHub or external project code was not installed, cloned, executed, or imported. Treat as untrusted until a later promptfoo-backed safety and dependency review.
- Status: deferred_later_graph_memory

### Understand Anything

- Type: external_graph_overlay
- Local anchor: message_id=229, link_id=220
- Summary: Graph overlay that can analyze code, docs, or a Karpathy-pattern LLM wiki into an explorable/searchable knowledge graph.
- Limitations: Best suited after KB Markdown exists; it is not the source-of-truth layer itself.
- Safety: GitHub or external project code was not installed, cloned, executed, or imported. Treat as untrusted until a later promptfoo-backed safety and dependency review.
- Status: deferred_later_graph_overlay

### OpenWolf

- Type: external_code_agent_memory
- Local anchor: message_id=240, link_id=231
- Summary: Claude Code middleware that creates project intelligence, learning memory, and token-aware file maps.
- Limitations: Optimized for coding-agent file reading and hooks, not for a WhatsApp-derived public knowledge base.
- Safety: GitHub or external project code was not installed, cloned, executed, or imported. Treat as untrusted until a later promptfoo-backed safety and dependency review.
- Status: not_initial_primary

### Graphify

- Type: external_folder_to_graph_skill
- Local anchor: message_id=153, link_id=146
- Summary: AI coding assistant skill that turns folders of code, docs, schemas, and other assets into a queryable knowledge graph.
- Limitations: Graph generation should come after source-backed Markdown pages exist; first pass should not depend on graph tooling.
- Safety: GitHub or external project code was not installed, cloned, executed, or imported. Treat as untrusted until a later promptfoo-backed safety and dependency review.
- Status: deferred_later_graph_overlay

### Obsidian Skills

- Type: external_agent_obsidian_interface
- Local anchor: message_id=249, link_id=240
- Summary: Agent skills for working with Obsidian concepts such as Markdown, Bases, JSON Canvas, and CLI operations.
- Limitations: Useful only if Obsidian operational integration becomes necessary; the initial repo can generate Markdown directly.
- Safety: GitHub or external project code was not installed, cloned, executed, or imported. Treat as untrusted until a later promptfoo-backed safety and dependency review.
- Status: deferred_supporting_agent_interface

### CocoIndex-style graph and semantic retrieval backend

- Type: external_retrieval_backend
- Local anchor: message_id=260, link_id=250
- Summary: Retrieval/indexing approach that can build graph and semantic stores from local files or object storage.
- Limitations: Likely requires extra services or indexes; unnecessary before lexical search and source-backed Markdown are working.
- Safety: GitHub or external project code was not installed, cloned, executed, or imported. Treat as untrusted until a later promptfoo-backed safety and dependency review.
- Status: deferred_later_semantic_search


## Unresolved Risks

- External GitHub projects may contain unsafe install scripts, telemetry, credentials handling, broad hooks, or dependency risks. They require promptfoo-backed safety review before execution.
- Current X/Twitter oEmbed coverage is sufficient for this review but not complete; unresolved X rows may reveal more candidates later.
- Generated Markdown needs strict source citation rules so assistant synthesis remains separate from source content.
- FTS5 availability should be validated before relying on it for search.
- Semantic search and graph visualization should be introduced only after lexical search and page generation are reliable.

## Next Implementation Steps

1. Define `kb/` folder layout: `sources/`, `topics/`, `tools/`, `comparisons/`, `decisions/`, and `indexes/`.
2. Write a deterministic KB page generator from SQLite that preserves message/link provenance and source URLs.
3. Add backlink extraction and a generated relationship index from `[[wikilinks]]`.
4. Add SQLite FTS5 search over generated pages and selected source evidence.
5. Add validation that every generated synthesis page has source references and no orphaned links.
6. Run promptfoo safety review before considering any external GitHub project or plugin.

## Validation

Final validation passed.

Commands run:

- `uv run --no-cache python -B scripts/db_status.py`
- `uv run --no-cache python -B -  # SQLite candidate/decision validation query`
- `uv run --no-cache python -B -  # SQLite FTS5 availability smoke test`

Results:

```json
{
  "validated_at": "2026-05-09T11:48:13.772862+00:00",
  "db_status_kb_candidates": 14,
  "integrity_check": "ok",
  "kb_candidates_count": 14,
  "initial_decision_count": 1,
  "latest_initial_decision": {
    "id": 1,
    "decision_key": "knowledge_base_approach_initial",
    "decided_at": "2026-05-09T11:47:20.637758+00:00"
  },
  "recommended_candidate_count": 4,
  "fts5_available": true
}
```
