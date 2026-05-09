# SQLite Schema Draft

The schema should preserve raw provenance, exact deduplication state, scrape attempts, classifications, and knowledge-base decisions.

## Core Tables

```sql
CREATE TABLE import_batches (
  id INTEGER PRIMARY KEY,
  source_name TEXT NOT NULL,
  source_type TEXT NOT NULL,
  export_path TEXT NOT NULL,
  imported_at TEXT NOT NULL,
  notes TEXT
);

CREATE TABLE messages (
  id INTEGER PRIMARY KEY,
  import_batch_id INTEGER NOT NULL REFERENCES import_batches(id),
  source_group TEXT NOT NULL,
  source_file TEXT NOT NULL,
  message_timestamp TEXT,
  sender TEXT,
  raw_text TEXT NOT NULL,
  normalized_text TEXT NOT NULL,
  exact_hash TEXT NOT NULL,
  is_exact_duplicate INTEGER NOT NULL DEFAULT 0,
  duplicate_of_message_id INTEGER REFERENCES messages(id),
  created_at TEXT NOT NULL
);

CREATE TABLE message_tags (
  id INTEGER PRIMARY KEY,
  message_id INTEGER NOT NULL REFERENCES messages(id),
  tag TEXT NOT NULL
);

CREATE TABLE links (
  id INTEGER PRIMARY KEY,
  message_id INTEGER NOT NULL REFERENCES messages(id),
  raw_url TEXT NOT NULL,
  normalized_url TEXT NOT NULL,
  url_hash TEXT NOT NULL,
  first_seen_at TEXT NOT NULL
);

CREATE TABLE scrape_attempts (
  id INTEGER PRIMARY KEY,
  link_id INTEGER NOT NULL REFERENCES links(id),
  attempted_at TEXT NOT NULL,
  tool TEXT NOT NULL,
  status TEXT NOT NULL,
  http_status INTEGER,
  final_url TEXT,
  title TEXT,
  extracted_text TEXT,
  metadata_json TEXT,
  error_type TEXT,
  error_message TEXT,
  duration_ms INTEGER
);

CREATE TABLE classifications (
  id INTEGER PRIMARY KEY,
  message_id INTEGER NOT NULL REFERENCES messages(id),
  category TEXT NOT NULL,
  confidence REAL,
  rationale TEXT,
  classified_at TEXT NOT NULL,
  model_or_method TEXT NOT NULL
);

CREATE TABLE kb_candidates (
  id INTEGER PRIMARY KEY,
  message_id INTEGER REFERENCES messages(id),
  link_id INTEGER REFERENCES links(id),
  candidate_name TEXT NOT NULL,
  candidate_type TEXT,
  summary TEXT,
  evidence TEXT,
  limitations TEXT,
  safety_notes TEXT,
  review_status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE decisions (
  id INTEGER PRIMARY KEY,
  decision_key TEXT NOT NULL,
  decision_value TEXT NOT NULL,
  rationale TEXT NOT NULL,
  decided_at TEXT NOT NULL,
  supersedes_decision_id INTEGER REFERENCES decisions(id)
);
```

## Search Tables

Use SQLite FTS5 for lexical search where available.

Semantic search can use a vector index if a local package is chosen, or store embeddings in SQLite with an external nearest-neighbor implementation.
