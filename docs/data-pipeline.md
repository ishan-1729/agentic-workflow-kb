# Data Pipeline

## Inputs

Raw WhatsApp exports should be stored unchanged in:

```text
imports/whatsapp_raw/
```

Each file should be accompanied by a small manifest entry, either generated or written manually, recording:

- Source group name or alias
- Whether it is the primary group or another tagged group
- Export date
- Export method
- Any filters used

## Normalization

Normalize all messages into records containing:

- Source file
- Group alias
- Message timestamp if present
- Sender or group marker if present
- Raw message text
- Extracted tags
- Extracted URLs
- Import batch ID
- Raw content hash

## Level 1 Deduplication

Perform exact duplicate detection using canonical record content. The canonical form should include normalized message text and URLs, but must not collapse near-duplicates or same-link-different-commentary records.

Recommended fields:

- `exact_hash`
- `is_exact_duplicate`
- `duplicate_of_message_id`

## Link Extraction And Scraping

For each URL:

- Store URL exactly as found.
- Store normalized URL separately.
- Assign link ID.
- Scrape with Scrapling in batches.
- Store status: `pending`, `success`, `failed`, `retry_pending`, `inaccessible`, or `skipped`.
- Store extracted title, text, metadata, HTTP status, final URL, and error details.
- Store every scrape attempt, not only the latest result, so retry history remains auditable.
- Maintain batch-level logs with attempted URL counts, success/error counts, started/finished timestamps, commands, and notable failure reasons.

First pass should move forward even if links fail. Later passes should focus on unresolved links until no feasible retries remain.

## Classification

Classify each item based on WhatsApp text plus scraped linked content when available. Keep classification confidence and rationale.

Categories are not mutually exclusive unless a later schema requires primary/secondary labels.

## Knowledge Base Review

Deep-review all Knowledge Base items, compare candidates, decide the best implementation approach for this project, then implement and later revisit after scrape completion improves.
