# Persistent Memory

## User Intent

The user wants a very careful local knowledge-base project built from WhatsApp group posts and linked external content. Precision, provenance, and repeatability matter more than speed.

## Non-Negotiable Rules

- WhatsApp is read-only.
- Export to local only.
- Keep every WhatsApp entry in SQLite, even if linked content is missing.
- Run exact duplicate removal before deeper analysis.
- Use Scrapling for link extraction/scraping batches.
- Do not make first-pass scrape failures blockers.
- Return later to retry failed or incomplete scrapes until all feasible content is captured.
- Use internet verification for unclear or unfamiliar concepts before finalizing classification and comparisons.
- Verify GitHub projects with promptfoo before trusting, installing, or implementing them.
- Write project learnings and pitfalls in `learnings/` between major checkpoints.

## Terms And Interpretations

- "Level 1 dedup" means exact duplicate removal only. Do not merge near-duplicates, paraphrases, or repeated links with changed commentary during this phase.
- "Knowledge Base section" refers to items categorized as knowledge-base systems, patterns, implementations, or methods, including "Karpathy style" personal or project knowledge-base approaches.
- "Wiki-style backlinks" means bidirectional note references, pages that link to related pages, and generated backlink indexes where practical.
- "Regular search" means lexical keyword search.
- "Intent based/semantic search" means embedding or vector-based retrieval over note and item content.

## Current Assumptions To Verify

- WhatsApp group exports should be obtained through the official per-chat/group export flow where possible.
- Most Twitter/X content may require special scraping handling due to rate limits, login walls, JavaScript rendering, or deleted/private posts.
- The knowledge base implementation may be plain Markdown plus SQLite-backed generated indexes unless a reviewed project clearly outperforms it for this workspace.
