---
title: "Candidate: SQLite FTS5 lexical search layer"
page_type: "candidate"
generated_by: "scripts/build_kb.py"
generator_version: "baseline-kb-v1"
generated_at: "2026-05-09T23:31:23+00:00"
source_message_ids: [4]
source_link_ids: [4]
candidate_ids: [4]
decision_ids: []
tags: ["candidate", "knowledge-base"]
---
# Candidate: SQLite FTS5 lexical search layer

- Type: `supporting_search_layer`
- Review status: `recommended_component`
- Source message: [[Message 000004]]
- Promptfoo disposition: `fixture_recommended`
- Risk: `low`
- Fit: `high`

## Summary

Use SQLite FTS5 for local lexical search over generated KB pages.

## Limitations

Lexical matching is not semantic embedding search.

## Safety Notes

Uses local SQLite features only.

## Promptfoo Review

Synthetic fixture review only; no external project code exists or runs.

## Local Evidence

- No structured local evidence JSON was recorded.

## External Sources Checked

- fixtures/synthetic/imports/Primary/WhatsApp Chat with Synthetic Agentic Workflow Lab.txt

## Related

- [[Candidate Comparison]]
- [[Decision: Knowledge Base Approach]]
