---
title: "Decision: Knowledge Base Approach"
page_type: "decision"
generated_by: "scripts/build_kb.py"
generator_version: "baseline-kb-v1"
generated_at: "2026-05-09T23:31:23+00:00"
source_message_ids: []
source_link_ids: []
candidate_ids: [1, 2, 3, 4]
decision_ids: [1]
tags: ["decision", "knowledge-base"]
---
# Decision: Knowledge Base Approach

Primary implementation: [[Candidate: Project-owned Obsidian-compatible Markdown wiki backed by SQLite]].

## Decision

Use the project-owned SQLite-backed Markdown KB baseline for the synthetic fixture.

## Rationale

The fixture is designed to validate local generation, provenance, wikilinks, FTS search, and intent search without private data.

## Related Pages

- [[Candidate Comparison]]
- [[Candidate: Karpathy LLM Wiki pattern]]
- [[Candidate: Obsidian-compatible local Markdown vault]]
- [[Candidate: SQLite FTS5 lexical search layer]]
- [[Search Guide]]

## Decision History

| ID | Key | Decided At | Supersedes |
| ---: | --- | --- | ---: |
| 1 | `synthetic_fixture_kb_approach` | 2026-05-09T23:31:17+00:00 |  |
