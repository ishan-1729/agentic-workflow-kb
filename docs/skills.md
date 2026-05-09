# Required Skills And Capabilities

## Local Data Engineering

- Parse WhatsApp exported text or archive formats.
- Normalize message records while preserving source provenance.
- Extract URLs and message tags.
- Deduplicate exact records in a deterministic way.
- Design and maintain SQLite tables, indexes, and import logs.
- Use `uv` for Python environments, scripts, and dependency installs.

## Web Extraction

- Use Scrapling in batches.
- Respect timeouts and retry budgets.
- Store scrape status, errors, timestamps, extracted text, and raw snapshots where useful.
- Handle Twitter/X links as a likely special case.

## Classification And Review

- Categorize items into broad categories such as:
  - Tools
  - Skills
  - Methods/Workflows
  - Memory
  - Knowledge Base
  - Graphs
  - Prompts
  - Verification Loops
  - Evaluation/Safety
  - Agent Orchestration
  - IDE/CLI Setup
  - MCP/Plugins
- Use internet verification for unfamiliar tools or concepts.
- Compare Knowledge Base candidates by features, limitations, expert evidence, maintenance state, project fit, extensibility, and safety.

## Knowledge Base Implementation

- Create wiki-style Markdown pages with consistent front matter.
- Generate backlinks and related-note indexes.
- Include comparison pages, decision records, and provenance links to source database item IDs.
- Add lexical search.
- Add semantic search.
- Add graph or knowledge-graph views if warranted by the reviewed material.
- Add Venn-style comparison artifacts where useful.

## Safety Evaluation

- Use promptfoo or equivalent test harnesses before running downloaded GitHub projects.
- Review repository metadata, install scripts, dependencies, permissions, network behavior, and maintainer signals.
- Prefer isolated test environments for unknown code.
