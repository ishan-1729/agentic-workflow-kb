---
title: "Topic Co-occurrence Graph"
page_type: "graph_index"
generated_by: "scripts/build_kb.py"
generator_version: "baseline-kb-v1"
generated_at: "2026-05-09T23:31:23+00:00"
source_message_ids: [1, 2, 3, 4, 5]
source_link_ids: []
candidate_ids: []
decision_ids: []
tags: ["graph", "index", "topics"]
---
# Topic Co-occurrence Graph

This repo-owned graph view is generated from SQLite classification rows. It is an analysis artifact, not an external graph database.

## Graph Model

- Node: broad topic category.
- Edge: one message classified into both topics.
- Edge weight: count of messages sharing both topics.

## Topic Nodes

| Topic | Messages |
| --- | ---: |
| [[Topic: Search Retrieval]] | 3 |
| [[Topic: Knowledge Base]] | 2 |
| [[Topic: Graphs Knowledge Graphs]] | 1 |
| [[Topic: Memory]] | 1 |
| [[Topic: Methods Workflows]] | 1 |
| [[Topic: Safety Verification]] | 1 |
| [[Topic: Verification Evals]] | 1 |

## Strongest Edges

| Topic A | Topic B | Shared Messages |
| --- | --- | ---: |
| [[Topic: Knowledge Base]] | [[Topic: Search Retrieval]] | 2 |
| [[Topic: Methods Workflows]] | [[Topic: Verification Evals]] | 1 |
| [[Topic: Graphs Knowledge Graphs]] | [[Topic: Safety Verification]] | 1 |
| [[Topic: Memory]] | [[Topic: Search Retrieval]] | 1 |

## Adjacency List

- [[Topic: Graphs Knowledge Graphs]]: [[Topic: Safety Verification]] (1)
- [[Topic: Knowledge Base]]: [[Topic: Search Retrieval]] (2)
- [[Topic: Memory]]: [[Topic: Search Retrieval]] (1)
- [[Topic: Methods Workflows]]: [[Topic: Verification Evals]] (1)
- [[Topic: Safety Verification]]: [[Topic: Graphs Knowledge Graphs]] (1)
- [[Topic: Search Retrieval]]: [[Topic: Knowledge Base]] (2), [[Topic: Memory]] (1)
- [[Topic: Verification Evals]]: [[Topic: Methods Workflows]] (1)
