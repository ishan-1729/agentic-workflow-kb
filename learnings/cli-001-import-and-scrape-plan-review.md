# CLI-001 Import And Scrape Plan Review

## Sources Reviewed

- `docs/README.md`
- `docs/import-state.md`
- `docs/data-pipeline.md`
- `data/intermediate/import_summary.json`
- Read-only SQLite inspection of `data/db/agentic_workflow.db`

`/goal` was requested if available, but no callable `/goal` interface is exposed in this secondary agent context. I treated the prompt as the bounded goal.

## Observed Import State

- Import batch: `1`, imported at `2026-05-09T02:46:29+00:00`.
- Raw text files: 3; standalone attachment/unsupported file: 1.
- Raw message counts:
  - Primary WhatsApp export: 298
  - Secondary_1 export: 472
  - Secondary_2 export: 1533
- In-scope messages: 598.
- Level 1 exact duplicates: 9.
- Level 1 unique messages: 589.
- Links: 588 total, 575 distinct normalized URLs.
- DB tables currently have no scrape attempts, classifications, KB candidates, or decisions.
- Links by domain:
  - `x.com`: 481 links, 471 distinct URLs
  - `github.com`: 77 links, 74 distinct URLs
  - `arxiv.org`: 5
  - YouTube/`youtu.be`: 5
  - `reddit.com`: 3
  - OpenAI domains: 4 across `openai.com`, `cookbook.openai.com`, `developers.openai.com`
  - Other singletons: Anthropic, Claude, Cursor, DSPy, Substack, Martin Fowler, etc.

## Import Scope And Filtering Review

The high-level scope is internally consistent with the docs: the primary group is treated as fully in scope, while secondary groups are filtered by agentic/Codex/Claude/OpenClaw-style tags. The SQLite counts match `import_summary.json`: 598 in-scope messages, 589 unique after exact deduplication, and 588 extracted links.

The main assumption to keep explicit is that all primary messages are useful enough to preserve, including WhatsApp system messages. The DB currently includes primary system rows such as end-to-end-encryption notice, group creation, and membership changes. This is acceptable for provenance preservation, but classification and KB review should either mark these as non-content or exclude them from candidate generation.

The secondary filtering strategy is reasonable for a first pass, but it is intentionally conservative. Secondary_1 contributes only 38 of 472 raw messages and Secondary_2 contributes 262 of 1533 raw messages. That prevents broad scope creep, but it can miss relevant untagged follow-up messages, replies, quoted context, or messages adjacent to a tagged link.

The filter list includes `add_to_codex`, but SQLite tag counts did not show any `add_to_codex` hits; `codex_tag` appears only 9 times. Codex-specific material may therefore be mostly coming from the primary full export, not from explicit secondary labels. Before treating the secondary import as complete, run an audit for near-match variants such as `Add to Codex CLI`, `Codex`, `OpenAI Codex`, casing differences, punctuation differences, and messages adjacent to matching tags.

Exact deduplication only removed 9 messages and left 13 repeated normalized URLs. That matches the documented "level 1" dedup policy and is the right conservative choice. Do not collapse same-link-different-commentary records before classification; instead dedupe scrape work at the normalized URL layer while preserving all message-link provenance.

## Scrape Batching Priorities

Start with a small pilot batch before running all 588 links. Recommended pilot: 10 `github.com`, 10 `x.com`, 5 official/vendor docs, 3 papers/videos/blogs, and 2 known duplicate URLs. This validates Scrapling extraction, status writing, retry behavior, duplicate URL handling, and metadata quality without burning time on 481 X links.

Batch priority 1: non-X, high-signal, easier-to-scrape sources. Scrape the 107 non-X links first, deduped to 104 distinct normalized URLs. Within that, lead with GitHub repos and official docs because they are likely to drive KB implementation choices and project safety review. For GitHub, store README/title/description/stars/license/default branch if available, but do not install or run projects. For official docs and blogs, capture title, body text, canonical URL, publish date if available, and final URL.

Batch priority 2: GitHub safety/relevance pass. The 77 GitHub links are concentrated in the primary export and contain many candidate tools. Scrape metadata and README content first, then classify into likely categories such as KB/wiki, memory/context, skills, orchestration, evaluation/safety, prompt engineering, agent frameworks, and unrelated. Defer any execution, cloning beyond metadata needs, or dependency installation until after promptfoo-style safety/evaluation checks.

Batch priority 3: X/Twitter links in controlled chunks. With 481 X links, avoid treating them as a single blocking scrape. Process in batches of 25 to 50 distinct URLs, record status per URL, and expect a significant inaccessible/login/rate-limit fraction. Use final URL, tweet ID, author, timestamp, text, media/card URLs, quoted/reposted URL, and error details when available. If Scrapling cannot extract tweet text reliably, mark as `retry_pending` or `inaccessible` rather than inventing summaries from WhatsApp context.

Batch priority 4: X links with external cards or duplicates. Prioritize X posts that expose external article/GitHub/arXiv/video cards because they can unlock content even if tweet text is limited. Also scrape duplicate X URLs once at URL level, then fan out the result to every message-link provenance record.

Batch priority 5: remaining long tail and retries. Run arXiv, YouTube, Reddit, Substack, and singleton domains after the first non-X pass or in parallel-friendly small groups. Then retry unresolved links by failure type: transient network/timeouts first, anti-bot/login-required second, deleted/private third. Stop only when each unresolved link has a documented status and error reason.

## Risks And Pitfalls

- X/Twitter accessibility is the largest operational risk. Login walls, rate limits, deleted tweets, protected accounts, anti-bot responses, and JavaScript-rendered content can produce empty or misleading scrape output.
- X post IDs in `x.com/i/status/...` form may need canonicalization to regular status URLs for tooling, but raw URLs must remain unchanged.
- The current DB has zero scrape attempts, so downstream classification would be premature if it relies on linked-content evidence.
- Secondary filtering can create false negatives by excluding untagged replies, adjacent context, and label variants not covered by the pattern list.
- Primary full import can create false positives because system messages and casual/administrative chatter are preserved as in-scope.
- Domain-level deduplication is not enough. Repeated normalized URLs should share scrape results, but message-specific commentary must remain attached for classification.
- Some URLs have query strings or fragments that may be meaningful (`github.com/...#claude-code`, YouTube comment links, arXiv `?s=08`). Preserve raw and normalized forms and avoid over-normalizing before scrape.
- GitHub links are tempting to evaluate by popularity or README claims alone. The project docs require safety verification and promptfoo-based checks before implementation or execution.
- Attachment handling is not complete content handling. The primary PDF is tracked as an attachment/unsupported file, so any knowledge inside it is currently outside the message/link scrape path unless a separate PDF extraction pass is planned.
- Scrape status vocabulary should be applied consistently: use `failed` for errors worth retrying, `retry_pending` for scheduled retries, `inaccessible` for durable access barriers, and `skipped` only for deliberate policy/priority decisions.

## Blockers

No blocker for the next scrape-planning step. The only limitation in this review is that `/goal` was not available as a callable interface in this secondary agent context.

DONE: Report written at `learnings/cli-001-import-and-scrape-plan-review.md`; no blockers.
