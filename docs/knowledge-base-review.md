# Knowledge Base Review

## Objective

Review the items classified as `Knowledge_Base` and decide the best knowledge-base approach for this project before implementation.

## Inputs

- SQLite `messages`, `links`, `scrape_attempts`, and `classifications`.
- Latest successful non-X scraped content.
- Latest successful `x_oembed` content.
- Public web sources for current project docs, reviews, limitations, and comparisons.

## Candidate Scope

Candidate systems may include, but are not limited to:

- Markdown/wiki systems with backlinks.
- Obsidian-style vaults.
- LLM-oriented knowledge bases inspired by Karpathy's "LLM Knowledge Bases" idea.
- Agent memory systems.
- Graph or knowledge-graph-backed systems.
- Retrieval/search-first systems.
- Existing open-source tools linked from WhatsApp/X/GitHub.

## Review Criteria

- Factual alignment with the project use case.
- Ability to support wiki-style backlinks and readable Markdown.
- Local-first data ownership.
- Ease of agent consumption and editing.
- Search support: lexical now, semantic later.
- Graph/relationship support.
- Importability from WhatsApp/link evidence.
- Low operational risk on Windows.
- Minimal unsafe dependency or install surface.
- Promptfoo safety gate needed before running any external project code.
- Clear limitations and failure modes.

## Safety

Do not install, clone, execute, or run GitHub projects during review. Treat linked projects as untrusted until a later promptfoo-backed safety pass.

Use internet lookup for factual verification and current documentation, but keep citations concise in the checkpoint.

## Output

The review should produce:

- Populated or updated `kb_candidates` rows for credible candidates.
- One or more `decisions` rows identifying the recommended approach and rationale.
- A checkpoint under `learnings/` with comparison tables, source links, caveats, and next implementation steps.
- A done/blocker marker.
