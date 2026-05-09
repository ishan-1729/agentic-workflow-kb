from __future__ import annotations

import argparse
import sqlite3
from urllib.parse import urlparse
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_DB = WORKSPACE / "data" / "db" / "agentic_workflow.db"


def scalar(conn: sqlite3.Connection, sql: str) -> int:
    return int(conn.execute(sql).fetchone()[0])


def domain(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    return host[4:] if host.startswith("www.") else host


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a concise SQLite project status.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    conn.create_function("domain", 1, domain)
    print(f"Database: {args.db}")
    for table in [
        "import_batches",
        "source_files",
        "messages",
        "message_tags",
        "links",
        "attachments",
        "scrape_attempts",
        "classifications",
        "kb_candidates",
    ]:
        print(f"{table}: {scalar(conn, f'SELECT COUNT(*) FROM {table}')}")

    print("\nMessages by group:")
    for row in conn.execute("SELECT source_group, COUNT(*) AS count FROM messages GROUP BY source_group ORDER BY count DESC"):
        print(f"  {row['source_group']}: {row['count']}")

    print("\nLevel 1 duplicates:")
    for row in conn.execute("SELECT is_exact_duplicate, COUNT(*) AS count FROM messages GROUP BY is_exact_duplicate ORDER BY is_exact_duplicate"):
        label = "duplicate" if row["is_exact_duplicate"] else "unique"
        print(f"  {label}: {row['count']}")

    print("\nTop link domains:")
    for row in conn.execute(
        """
        SELECT domain(normalized_url) AS rough_domain, COUNT(*) AS count
        FROM links
        GROUP BY rough_domain
        ORDER BY count DESC
        LIMIT 15
        """
    ):
        print(f"  {row['rough_domain']}: {row['count']}")

    conn.close()


if __name__ == "__main__":
    main()
