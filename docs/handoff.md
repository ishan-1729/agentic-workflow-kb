# Handoff

## Project State

Local WhatsApp group exports have been imported into SQLite. Exhaustive linked-content retry is complete: latest scrape statuses have zero `retry_pending`, zero `failed`, and zero `no_attempt` rows; X/Twitter coverage is 479 parsed oEmbed rows and 2 terminal inaccessible rows. Broad classification has been rerun after Goal 007 against the fuller scrape corpus. Initial Knowledge Base candidate review and promptfoo-backed static KB safety review are complete. The repo-owned Markdown KB has been regenerated with source provenance, wikilinks/backlinks, validation, graph/comparison enrichment, SQLite FTS5 lexical search, and deterministic intent search. Final acceptance audit passed in `learnings/final-acceptance-audit.json`. The deterministic CLI-side wake bridge is installed, trusted, active, smoke-tested, and prompts the app-side orchestrator to continue the next eligible project task after auditing a completed CLI goal.

## Immediate Next Work

No immediate required implementation remains for the repo-owned KB baseline. Preserve raw exports unchanged. Do not install, clone, execute, import, or run external GitHub projects. Future work is optional/explicitly gated: external vector or embedding backends, external graph databases/overlays, external GitHub project execution, and credentialed browser/profile scraping all require separate promptfoo-backed safety review and user/orchestrator approval. The external-backend safety inventory is scaffolded in `docs/external-backend-safety-gate.md` and `scripts/external_backend_safety_matrix.py`; it opens SQLite read-only and writes ignored local reports under `data/safety_reviews/`.

## Planned Local Folders

- `imports/whatsapp_raw/`: untouched user-provided exports.
- `imports/Primary/`: actual primary group export folder currently provided by user.
- `imports/Secondary_1/`, `imports/Secondary_2/`: actual secondary export folders currently provided by user.
- `data/intermediate/`: normalized JSONL/CSV and exact-dedup outputs.
- `data/scraped/`: raw scrape artifacts and per-link logs.
- `data/db/`: SQLite database files.
- `kb/`: implemented wiki-style knowledge base.
- `scripts/`: import, deduplication, scraping, categorization, review, and search scripts.
- `learnings/`: checkpoint notes, pitfalls, decisions, and recovery state.

## Coordination With Codex CLI

The Codex CLI feature `goals` is enabled. Use `/goal` only for durable long-running work with one objective, checkpoints, validation commands/artifacts, and a verifiable stopping condition. Do not use `/goal` for short audits, doc corrections, deterministic local integration edits, or small validation passes that the orchestrator can complete directly.

Long-running delegated work must use an interactive CLI `/goal`, not `codex exec`.

Read `docs/codex-goals.md` before starting any delegated long task.

The project should run as an orchestrated loop until completion:

1. Main orchestrator handles short audits, doc corrections, deterministic implementation, and validation directly.
2. When a phase is genuinely long-running, main orchestrator launches one bounded CLI `/goal`.
3. CLI goal writes heartbeat/status files, checkpoint, and done/blocker marker.
4. The Codex CLI `Stop` hook bridge in `docs/cli-wake-bridge.md` detects the new done marker and starts a turn in this orchestrator app thread. App-side polling automations are not the normal wake mechanism.
5. Main orchestrator audits the result, fixes small integration issues if needed, updates docs/learnings, and decides whether the next phase is self-work or another bounded CLI `/goal`.
6. Repeat until the Knowledge Base, graph/comparison enrichment, and search functionality are complete.

Do not treat a completed goal as the end of the project unless the final project acceptance criteria are complete.

The main orchestrator remains responsible for integration, safety checks, database consistency, and final decisions.

## Known Blockers

- promptfoo setup for Goal 006 succeeded in a documented local/Codex-memories setup, but external projects still require separate isolated execution gates before any install/run/adoption.
- Python work should use `uv`; `uv 0.8.16` is available.
- Scrapling static fetching works after adding explicit dependencies: `curl-cffi`, `playwright`, and `browserforge`.
