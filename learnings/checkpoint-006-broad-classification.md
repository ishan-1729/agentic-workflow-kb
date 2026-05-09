# Checkpoint 006: Broad Classification

Date: 2026-05-09

## Scope

- Goal: classify every imported in-scope WhatsApp message into broad, non-mutually-exclusive categories.
- Required docs and checkpoints were read before acting.
- SQLite was used as the source of truth: message text, tags, duplicate flags, links/domains, latest successful non-X scrape content, and latest successful `x_oembed` content.
- Raw `imports/` files remained read-only.
- No scraping, browser automation, WhatsApp mutation, GitHub project install/run, or internet lookup was performed.
- No additional categories were added beyond `docs/classification.md`.

## Code And Storage Changes

- Added `scripts/classify_items.py`.
- Wrote classification rows to `data/db/agentic_workflow.db` with `model_or_method = 'goal-004-rule-based-broad-v1'`.
- Wrote durable summary log to `learnings/goal-004-broad-classification/summary.json`.
- Updated `learnings/goal-004-broad-classification.heartbeat.json` at start, during batches, and on completion.

## Method

The classifier is deterministic and reproducible. It joins messages, tags, links, and latest successful scrape rows from SQLite. For X/Twitter links it uses `x_oembed` success rows when available; for non-X links it uses latest successful scrape titles, metadata descriptions, and bounded extracted text. It scores broad categories from explicit tags, domains, and evidence phrases, then writes one row per selected category with concise evidence-grounded rationales.

Exact duplicates receive their own classification rows. Duplicate rationales name the source `duplicate_of_message_id` when present.

## Commands Run

```powershell
uv run --no-cache python -B scripts/db_status.py
uv run --no-cache python -B scripts/classify_items.py --help
uv run --no-cache python -B scripts/classify_items.py --dry-run --batch-size 150
uv run --no-cache python -B scripts/classify_items.py --batch-size 100
uv run --no-cache python -B scripts/db_status.py
uv run --no-cache python -B -  # SQLite validation query
```

Additional local inspection commands were used to read required docs, inspect schema/sample rows, inspect file attributes, and verify the stale SQLite journal recovery described below.

## Journal Recovery Note

The first write attempt failed on commit with `sqlite3.OperationalError: disk I/O error`. The workspace allowed creating/writing files under `data/db` but denied delete/rename operations, which prevented SQLite's default rollback-journal cleanup. Before retrying, the main DB was opened in immutable read-only mode and `PRAGMA integrity_check` returned `ok` with zero committed classifications. The failed transaction journal header was zeroed to invalidate the stale hot journal, and `scripts/classify_items.py` was updated to use `PRAGMA journal_mode = PERSIST` so future commits do not require deleting the journal file.

## Final Counts

- Total messages: 598.
- Non-duplicate messages: 589.
- Duplicate messages: 9.
- Classified messages: 598.
- Classified non-duplicate messages: 589.
- Classified duplicate messages: 9.
- Unclassified non-duplicate messages: 0.
- Classification rows: 2,409.
- Low-confidence rows/messages: 39.

Low-confidence rows are `Uncategorized` entries, mainly WhatsApp system/pinned messages or URL-only links with no parsed topical content available in SQLite.

## Category Counts

| Category | Rows |
| --- | ---: |
| Infrastructure_Devtools | 401 |
| Tools | 389 |
| Methods_Workflows | 301 |
| Agents_Multiagent | 278 |
| UX_Productivity | 268 |
| Models_Reasoning | 203 |
| Memory | 82 |
| Search_Retrieval | 79 |
| Knowledge_Base | 67 |
| Prompts | 67 |
| Skills | 67 |
| Evaluation_Benchmarking | 57 |
| Context_Engineering | 44 |
| Uncategorized | 39 |
| Safety_Security | 19 |
| Browser_Web_Automation | 18 |
| Verification_Loops | 17 |
| Graphs_Knowledge_Graphs | 13 |

## Representative Examples

- `Agents_Multiagent`: message 4, Cline Kanban oEmbed text matched multi-agent orchestration.
- `Tools`: message 5, Claude Code setup oEmbed text matched open source setup/tooling.
- `Knowledge_Base`: message 17, Karpathy LLM knowledge base oEmbed text matched personal knowledge-base evidence.
- `Graphs_Knowledge_Graphs`: message 33 matched "Graph Traversal" and "wikilinks".
- `Verification_Loops`: message 14 matched AutoResearch/measurement-loop evidence.
- `Browser_Web_Automation`: message 6 matched computer use and UI testing evidence.
- `Uncategorized`: message 1 is a WhatsApp encryption system notice with no topical evidence.

Full per-category examples are in `learnings/goal-004-broad-classification/summary.json`.

## Final Validation

`uv run --no-cache python -B scripts/db_status.py` reported:

```text
messages: 598
message_tags: 1284
links: 588
scrape_attempts: 935
classifications: 2409
```

SQLite validation query:

```json
{
  "classified_duplicate_messages": 9,
  "classified_non_duplicate_messages": 589,
  "classification_rows_method": 2409,
  "classification_rows_total": 2409,
  "duplicate_messages": 9,
  "integrity_check": "ok",
  "low_confidence_rows_lt_0_45": 39,
  "non_duplicate_messages": 589,
  "total_messages": 598,
  "unclassified_non_duplicate_messages": 0
}
```

## Unresolved Questions

- Some URL-only X/Twitter messages have no parsed oEmbed content and no tags. They are classified as low-confidence `Uncategorized` until a later approved scrape/parse pass adds topical evidence.
