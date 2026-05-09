from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_IMPORTS = WORKSPACE / "imports"
DEFAULT_DB = WORKSPACE / "data" / "db" / "agentic_workflow.db"
DEFAULT_INTERMEDIATE = WORKSPACE / "data" / "intermediate"

MESSAGE_START_RE = re.compile(
    r"^\ufeff?\u200e?\[?"
    r"(?P<date>\d{1,2}/\d{1,2}/\d{2,4}),\s+"
    r"(?P<time>\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APMapm]{2})?)"
    r"\]?\s+-\s+"
    r"(?P<body>.*)$"
)
URL_RE = re.compile(r"https?://[^\s<>\"]+")
ADD_TO_RE = re.compile(r"\badd\s+to\s+([^\n\r]+)", re.IGNORECASE)

SCOPE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("add_to_claude_code", re.compile(r"\badd\s+to\b.*\bclaude\s+code\b", re.IGNORECASE)),
    ("add_to_codex", re.compile(r"\badd\s+to\b.*\bcodex\b", re.IGNORECASE)),
    ("add_to_openclaw", re.compile(r"\badd\s+to\b.*\bopen\s*claw\b", re.IGNORECASE)),
    ("add_to_agentic_systems", re.compile(r"\badd\s+to\b.*\bagentic\s+systems?\b", re.IGNORECASE)),
    ("add_to_ai_agents", re.compile(r"\badd\s+to\b.*\bai\s+agents?\b", re.IGNORECASE)),
    ("add_to_prompt_engineering", re.compile(r"\badd\s+to\b.*\bprompt\s+engineering\b", re.IGNORECASE)),
    ("add_to_super_llm", re.compile(r"\badd\s+to\b.*\bsuper\s+llms?\b", re.IGNORECASE)),
    ("add_to_skills", re.compile(r"\badd\s+to\b.*\b(?:claude\s+)?skills?\b", re.IGNORECASE)),
    ("claude_code_tag", re.compile(r"\bclaude\s+code\b", re.IGNORECASE)),
    ("codex_tag", re.compile(r"\bcodex\b", re.IGNORECASE)),
    ("openclaw_tag", re.compile(r"\bopen\s*claw\b", re.IGNORECASE)),
    ("claude_skill_tag", re.compile(r"\bclaude\s+skills?\b", re.IGNORECASE)),
    ("agentic_systems_tag", re.compile(r"\bagentic\s+systems?\b", re.IGNORECASE)),
    ("verification_loop_tag", re.compile(r"\bverification\s+loops?\b", re.IGNORECASE)),
]


@dataclass
class ParsedMessage:
    source_file: Path
    source_group: str
    folder_role: str
    line_start: int
    line_end: int
    timestamp_raw: str | None
    timestamp_iso: str | None
    sender: str | None
    raw_text: str
    normalized_text: str
    scope_reason: str | None
    tags: list[str]
    urls: list[str]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFKC", text)
    return text.strip()


def exact_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def normalize_url(url: str) -> str:
    url = url.strip()
    while url and url[-1] in ".,;:!?)]}":
        url = url[:-1]
    return url


def split_sender(body: str) -> tuple[str | None, str]:
    if ": " not in body:
        return None, body
    sender, text = body.split(": ", 1)
    if len(sender) > 120 or "\n" in sender:
        return None, body
    return sender.strip() or None, text


def parse_timestamp(date_part: str, time_part: str) -> tuple[str, str | None]:
    raw = f"{date_part}, {time_part}"
    candidates = [
        "%m/%d/%y, %H:%M",
        "%m/%d/%y, %H:%M:%S",
        "%m/%d/%Y, %H:%M",
        "%m/%d/%Y, %H:%M:%S",
        "%m/%d/%y, %I:%M %p",
        "%m/%d/%y, %I:%M:%S %p",
        "%m/%d/%Y, %I:%M %p",
        "%m/%d/%Y, %I:%M:%S %p",
        "%d/%m/%y, %H:%M",
        "%d/%m/%y, %H:%M:%S",
        "%d/%m/%Y, %H:%M",
        "%d/%m/%Y, %H:%M:%S",
        "%d/%m/%y, %I:%M %p",
        "%d/%m/%y, %I:%M:%S %p",
        "%d/%m/%Y, %I:%M %p",
        "%d/%m/%Y, %I:%M:%S %p",
    ]
    normalized_raw = re.sub(r"\s+", " ", raw.upper())
    for fmt in candidates:
        try:
            parsed = datetime.strptime(normalized_raw, fmt)
            return raw, parsed.isoformat(timespec="minutes")
        except ValueError:
            continue
    return raw, None


def source_role(path: Path, imports_dir: Path) -> tuple[str, str]:
    relative = path.relative_to(imports_dir)
    group = relative.parts[0] if len(relative.parts) > 1 else path.stem
    role = "primary" if group.lower() == "primary" else "secondary"
    return group, role


def extract_urls(text: str) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for match in URL_RE.finditer(text):
        url = normalize_url(match.group(0))
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def extract_tags(text: str) -> list[str]:
    tags: list[str] = []
    seen: set[str] = set()
    for match in ADD_TO_RE.finditer(text):
        raw = match.group(1).strip(" .;:")
        for part in re.split(r"[,/|]", raw):
            tag = normalize_text(part).strip(" .;:")
            if tag and tag.lower() not in seen:
                seen.add(tag.lower())
                tags.append(tag)
    for label, pattern in SCOPE_PATTERNS:
        if pattern.search(text) and label not in seen:
            seen.add(label)
            tags.append(label)
    return tags


def scope_reason(text: str, role: str) -> str | None:
    if role == "primary":
        return "primary_full_export"
    matches = [label for label, pattern in SCOPE_PATTERNS if pattern.search(text)]
    return ";".join(matches) if matches else None


def parse_whatsapp_txt(path: Path, imports_dir: Path) -> tuple[list[ParsedMessage], int]:
    source_group, folder_role = source_role(path, imports_dir)
    messages: list[ParsedMessage] = []
    total_messages = 0
    current: dict[str, object] | None = None

    def flush() -> None:
        nonlocal current, total_messages
        if not current:
            return
        total_messages += 1
        raw_text = normalize_text(str(current["raw_text"]))
        reason = scope_reason(raw_text, folder_role)
        if reason:
            messages.append(
                ParsedMessage(
                    source_file=path,
                    source_group=source_group,
                    folder_role=folder_role,
                    line_start=int(current["line_start"]),
                    line_end=int(current["line_end"]),
                    timestamp_raw=current["timestamp_raw"],  # type: ignore[arg-type]
                    timestamp_iso=current["timestamp_iso"],  # type: ignore[arg-type]
                    sender=current["sender"],  # type: ignore[arg-type]
                    raw_text=raw_text,
                    normalized_text=normalize_text(raw_text),
                    scope_reason=reason,
                    tags=extract_tags(raw_text),
                    urls=extract_urls(raw_text),
                )
            )
        current = None

    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.rstrip("\r\n")
            match = MESSAGE_START_RE.match(line)
            if match:
                flush()
                timestamp_raw, timestamp_iso = parse_timestamp(match.group("date"), match.group("time"))
                sender, body = split_sender(match.group("body"))
                current = {
                    "line_start": line_number,
                    "line_end": line_number,
                    "timestamp_raw": timestamp_raw,
                    "timestamp_iso": timestamp_iso,
                    "sender": sender,
                    "raw_text": body,
                }
            elif current:
                current["raw_text"] = f"{current['raw_text']}\n{line}"
                current["line_end"] = line_number
            elif line.strip():
                current = {
                    "line_start": line_number,
                    "line_end": line_number,
                    "timestamp_raw": None,
                    "timestamp_iso": None,
                    "sender": None,
                    "raw_text": line,
                }
        flush()
    return messages, total_messages


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS import_batches (
  id INTEGER PRIMARY KEY,
  source_name TEXT NOT NULL,
  source_type TEXT NOT NULL,
  export_path TEXT NOT NULL,
  imported_at TEXT NOT NULL,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS source_files (
  id INTEGER PRIMARY KEY,
  import_batch_id INTEGER NOT NULL REFERENCES import_batches(id),
  source_group TEXT NOT NULL,
  folder_role TEXT NOT NULL,
  path TEXT NOT NULL,
  extension TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  bytes INTEGER NOT NULL,
  modified_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY,
  import_batch_id INTEGER NOT NULL REFERENCES import_batches(id),
  source_file_id INTEGER NOT NULL REFERENCES source_files(id),
  source_group TEXT NOT NULL,
  folder_role TEXT NOT NULL,
  source_file TEXT NOT NULL,
  line_start INTEGER,
  line_end INTEGER,
  message_timestamp TEXT,
  timestamp_iso TEXT,
  sender TEXT,
  raw_text TEXT NOT NULL,
  normalized_text TEXT NOT NULL,
  exact_hash TEXT NOT NULL,
  is_exact_duplicate INTEGER NOT NULL DEFAULT 0,
  duplicate_of_message_id INTEGER REFERENCES messages(id),
  scope_reason TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS message_tags (
  id INTEGER PRIMARY KEY,
  message_id INTEGER NOT NULL REFERENCES messages(id),
  tag TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS links (
  id INTEGER PRIMARY KEY,
  message_id INTEGER NOT NULL REFERENCES messages(id),
  raw_url TEXT NOT NULL,
  normalized_url TEXT NOT NULL,
  url_hash TEXT NOT NULL,
  first_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attachments (
  id INTEGER PRIMARY KEY,
  source_file_id INTEGER NOT NULL REFERENCES source_files(id),
  attachment_type TEXT NOT NULL,
  path TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  bytes INTEGER NOT NULL,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS scrape_attempts (
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

CREATE TABLE IF NOT EXISTS classifications (
  id INTEGER PRIMARY KEY,
  message_id INTEGER NOT NULL REFERENCES messages(id),
  category TEXT NOT NULL,
  confidence REAL,
  rationale TEXT,
  classified_at TEXT NOT NULL,
  model_or_method TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS kb_candidates (
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

CREATE TABLE IF NOT EXISTS decisions (
  id INTEGER PRIMARY KEY,
  decision_key TEXT NOT NULL,
  decision_value TEXT NOT NULL,
  rationale TEXT NOT NULL,
  decided_at TEXT NOT NULL,
  supersedes_decision_id INTEGER REFERENCES decisions(id)
);

CREATE TABLE IF NOT EXISTS import_stats (
  id INTEGER PRIMARY KEY,
  import_batch_id INTEGER NOT NULL REFERENCES import_batches(id),
  metric TEXT NOT NULL,
  value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_exact_hash ON messages(exact_hash);
CREATE INDEX IF NOT EXISTS idx_messages_scope ON messages(scope_reason);
CREATE INDEX IF NOT EXISTS idx_links_url_hash ON links(url_hash);
CREATE INDEX IF NOT EXISTS idx_scrape_attempts_link ON scrape_attempts(link_id);
"""


def reset_database(conn: sqlite3.Connection) -> None:
    tables = [
        "import_stats",
        "decisions",
        "kb_candidates",
        "classifications",
        "scrape_attempts",
        "attachments",
        "links",
        "message_tags",
        "messages",
        "source_files",
        "import_batches",
    ]
    conn.execute("PRAGMA foreign_keys = OFF")
    for table in tables:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")


def iter_import_files(imports_dir: Path) -> Iterable[Path]:
    for path in sorted(imports_dir.rglob("*")):
        if path.is_file():
            yield path


def write_jsonl(path: Path, rows: Iterable[dict[str, object]]) -> int:
    count = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def run_ingest(imports_dir: Path, db_path: Path, intermediate_dir: Path, rebuild: bool) -> dict[str, object]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    intermediate_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    if rebuild:
        reset_database(conn)
    conn.executescript(SCHEMA)
    conn.execute("PRAGMA foreign_keys = ON")

    imported_at = utc_now()
    cursor = conn.execute(
        "INSERT INTO import_batches(source_name, source_type, export_path, imported_at, notes) VALUES (?, ?, ?, ?, ?)",
        ("whatsapp_groups", "whatsapp_export", str(imports_dir), imported_at, "Primary full export; secondary groups filtered by agentic/Codex/Claude/OpenClaw tag patterns."),
    )
    batch_id = int(cursor.lastrowid)

    source_file_ids: dict[Path, int] = {}
    parsed_messages: list[ParsedMessage] = []
    total_raw_messages_by_file: dict[str, int] = {}
    unsupported_files = 0
    attachment_files = 0

    for path in iter_import_files(imports_dir):
        source_group, folder_role = source_role(path, imports_dir)
        stat = path.stat()
        source_cursor = conn.execute(
            """
            INSERT INTO source_files(import_batch_id, source_group, folder_role, path, extension, sha256, bytes, modified_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch_id,
                source_group,
                folder_role,
                str(path),
                path.suffix.lower(),
                file_sha256(path),
                stat.st_size,
                datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            ),
        )
        source_file_id = int(source_cursor.lastrowid)
        source_file_ids[path] = source_file_id

        if path.suffix.lower() == ".txt":
            messages, total_messages = parse_whatsapp_txt(path, imports_dir)
            parsed_messages.extend(messages)
            total_raw_messages_by_file[str(path)] = total_messages
        else:
            attachment_files += 1
            conn.execute(
                """
                INSERT INTO attachments(source_file_id, attachment_type, path, sha256, bytes, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (source_file_id, "standalone_import_file", str(path), file_sha256(path), stat.st_size, "Non-text file present in WhatsApp import folder."),
            )
            unsupported_files += 1

    first_by_hash: dict[str, int] = {}
    message_rows: list[dict[str, object]] = []
    link_rows: list[dict[str, object]] = []
    duplicate_count = 0

    for message in parsed_messages:
        msg_hash = exact_hash(message.normalized_text)
        duplicate_of = first_by_hash.get(msg_hash)
        is_duplicate = duplicate_of is not None
        cursor = conn.execute(
            """
            INSERT INTO messages(
              import_batch_id, source_file_id, source_group, folder_role, source_file,
              line_start, line_end, message_timestamp, timestamp_iso, sender,
              raw_text, normalized_text, exact_hash, is_exact_duplicate,
              duplicate_of_message_id, scope_reason, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch_id,
                source_file_ids[message.source_file],
                message.source_group,
                message.folder_role,
                str(message.source_file),
                message.line_start,
                message.line_end,
                message.timestamp_raw,
                message.timestamp_iso,
                message.sender,
                message.raw_text,
                message.normalized_text,
                msg_hash,
                1 if is_duplicate else 0,
                duplicate_of,
                message.scope_reason,
                imported_at,
            ),
        )
        message_id = int(cursor.lastrowid)
        if not is_duplicate:
            first_by_hash[msg_hash] = message_id
        else:
            duplicate_count += 1

        for tag in message.tags:
            conn.execute("INSERT INTO message_tags(message_id, tag) VALUES (?, ?)", (message_id, tag))

        for url in message.urls:
            normalized = normalize_url(url)
            url_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            link_cursor = conn.execute(
                """
                INSERT INTO links(message_id, raw_url, normalized_url, url_hash, first_seen_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (message_id, url, normalized, url_hash, imported_at),
            )
            link_id = int(link_cursor.lastrowid)
            link_rows.append(
                {
                    "id": link_id,
                    "message_id": message_id,
                    "source_group": message.source_group,
                    "raw_url": url,
                    "normalized_url": normalized,
                    "url_hash": url_hash,
                }
            )

        message_rows.append(
            {
                "id": message_id,
                "source_group": message.source_group,
                "folder_role": message.folder_role,
                "source_file": str(message.source_file),
                "line_start": message.line_start,
                "line_end": message.line_end,
                "message_timestamp": message.timestamp_raw,
                "timestamp_iso": message.timestamp_iso,
                "sender": message.sender,
                "raw_text": message.raw_text,
                "normalized_text": message.normalized_text,
                "exact_hash": msg_hash,
                "is_exact_duplicate": is_duplicate,
                "duplicate_of_message_id": duplicate_of,
                "scope_reason": message.scope_reason,
                "tags": message.tags,
                "urls": message.urls,
            }
        )

    unique_rows = [row for row in message_rows if not row["is_exact_duplicate"]]
    write_jsonl(intermediate_dir / "messages_in_scope_all.jsonl", message_rows)
    write_jsonl(intermediate_dir / "messages_level1_dedup.jsonl", unique_rows)
    write_jsonl(intermediate_dir / "links_all.jsonl", link_rows)
    write_csv(
        intermediate_dir / "links_all.csv",
        link_rows,
        ["id", "message_id", "source_group", "raw_url", "normalized_url", "url_hash"],
    )

    stats: dict[str, object] = {
        "import_batch_id": batch_id,
        "imported_at": imported_at,
        "imports_dir": str(imports_dir),
        "db_path": str(db_path),
        "source_file_count": len(source_file_ids),
        "text_source_file_count": sum(1 for path in source_file_ids if path.suffix.lower() == ".txt"),
        "attachment_or_unsupported_file_count": unsupported_files,
        "standalone_attachment_file_count": attachment_files,
        "raw_message_counts_by_file": total_raw_messages_by_file,
        "in_scope_message_count": len(message_rows),
        "level1_duplicate_count": duplicate_count,
        "level1_unique_message_count": len(unique_rows),
        "link_count": len(link_rows),
        "secondary_filter_patterns": [label for label, _ in SCOPE_PATTERNS],
    }
    for metric, value in stats.items():
        conn.execute(
            "INSERT INTO import_stats(import_batch_id, metric, value) VALUES (?, ?, ?)",
            (batch_id, metric, json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value),
        )
    conn.commit()
    conn.close()

    summary_path = intermediate_dir / "import_summary.json"
    summary_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Import WhatsApp group exports into local SQLite.")
    parser.add_argument("--imports-dir", type=Path, default=DEFAULT_IMPORTS)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--intermediate-dir", type=Path, default=DEFAULT_INTERMEDIATE)
    parser.add_argument("--rebuild", action="store_true", help="Drop and recreate local derived database tables.")
    args = parser.parse_args()

    stats = run_ingest(args.imports_dir.resolve(), args.db.resolve(), args.intermediate_dir.resolve(), args.rebuild)
    print(json.dumps(stats, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

