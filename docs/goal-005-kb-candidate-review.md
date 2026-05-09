# Goal 005: Knowledge Base Candidate Review

## Start Interactive CLI

Run this in the terminal panel that will host the delegated Codex CLI agent:

```powershell
codex --disable fast_mode -C "<workspace>" -s workspace-write -m gpt-5.5 -c model_reasoning_effort="xhigh"
```

Then paste this into the Codex CLI composer:

```text
/goal Perform the Knowledge Base candidate extraction and deep review for this project without stopping until credible KB candidates are identified, compared, and a recommended KB approach is recorded, or until a precisely documented blocker requires orchestrator/user judgment. Read docs/README.md, docs/handoff.md, docs/operating-rules.md, docs/data-pipeline.md, docs/classification.md, docs/knowledge-base-review.md, docs/sqlite-schema.md, docs/scraping.md, docs/codex-goals.md, docs/import-state.md, learnings/checkpoint-004-x-oembed-parse.md, learnings/checkpoint-005-continuous-loop-repair.md, and learnings/checkpoint-006-broad-classification.md before acting. Use uv only for local Python work. Keep imports/ strictly read-only. Use SQLite as source of truth: messages classified as Knowledge_Base, plus related Memory, Graphs_Knowledge_Graphs, Search_Retrieval, and Methods_Workflows evidence where relevant. Use existing scraped/oEmbed content first, then use internet lookup for factual verification, current docs, reviews, limitations, and comparisons; cite source URLs in the checkpoint. Do not mutate WhatsApp. Do not scrape private/authenticated content. Do not install, clone, execute, or run GitHub projects. Do not use browser automation unless a public webpage cannot be read otherwise and the sandbox rules in docs/browser-sandbox.md are followed; prefer ordinary web/HTTP lookup. If a candidate is a GitHub project, treat it as untrusted and only record metadata/README evidence; promptfoo safety review is required later before any implementation or execution. Populate or update kb_candidates rows for credible KB candidates with candidate_name, candidate_type, summary, evidence, limitations, safety_notes, and review_status. Add a decisions row with a decision_key such as 'knowledge_base_approach_initial' and a clear recommended approach for this project. The likely output should be an implementation direction, not necessarily a full implementation yet. You own only kb_candidates and decisions rows in data/db/agentic_workflow.db, helper scripts under scripts/ if needed, docs/knowledge-base-review.md if needed, learnings/checkpoint-007-kb-candidate-review.md, learnings/goal-005-kb-candidate-review.heartbeat.json, and learnings/goal-005-kb-candidate-review.done. Keep durable logging: start/end time, commands, number of Knowledge_Base messages reviewed, candidate counts, source URLs checked, comparison criteria, recommendation, unresolved risks, and next implementation steps. Update learnings/goal-005-kb-candidate-review.heartbeat.json at the start, after each major phase, and before done/blocker. Validate with uv run --no-cache python -B scripts/db_status.py and SQLite queries showing kb_candidates count > 0 and a decision row exists for the initial KB approach, or write a blocker with exact reasons. At the very end, after validation passes or after documenting a blocker, write learnings/goal-005-kb-candidate-review.done with a one-paragraph completion/blocker summary beginning with GOAL_005_DONE or GOAL_005_BLOCKED. Stop when the KB candidate review and initial decision are complete or a blocker requires orchestrator/user judgment.
```

## Orchestrator Note

While this goal runs, the main orchestrator should not concurrently edit KB review scripts/docs or SQLite `kb_candidates`/`decisions` rows.
