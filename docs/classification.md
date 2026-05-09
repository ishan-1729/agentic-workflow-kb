# Classification

## Objective

Classify every imported in-scope WhatsApp item into broad, non-mutually-exclusive categories using:

- WhatsApp message text.
- Message tags.
- Linked URL/domain.
- Latest successful scraped content when available.
- Latest successful `x_oembed` content for X/Twitter links when available.

## Initial Category Set

- `Tools`
- `Skills`
- `Methods_Workflows`
- `Memory`
- `Knowledge_Base`
- `Graphs_Knowledge_Graphs`
- `Prompts`
- `Verification_Loops`
- `Agents_Multiagent`
- `Context_Engineering`
- `Search_Retrieval`
- `Browser_Web_Automation`
- `Evaluation_Benchmarking`
- `Safety_Security`
- `Infrastructure_Devtools`
- `Models_Reasoning`
- `UX_Productivity`
- `Uncategorized`

Categories are multi-label. A message can belong to several categories. Store confidence and a concise rationale in SQLite.

## Requirements

- Do not discard exact duplicates; classify all message rows, but note duplicate status in rationale or metadata when useful.
- Preserve provenance by linking classifications to `message_id`.
- Keep durable logs under `learnings/`.
- Use `classifications.model_or_method` to identify the method, for example `goal-004-cli-gpt-5.5-xhigh-batch`.
- Do not install or run discovered GitHub projects during classification.
- Look up unclear category concepts on the internet only when needed for taxonomy precision; cite findings in the checkpoint rather than pasting long source text.
- Prefer broad useful buckets over clever micro-taxonomies in this pass.

## Validation

The categorization pass should finish with:

- `classifications` count greater than or equal to the unique in-scope message count, unless a blocker is documented.
- Every non-duplicate message has at least one classification.
- Every duplicate message either has its own classification or an explicit `Duplicate`/linked rationale.
- Status counts by category are written to a checkpoint.
