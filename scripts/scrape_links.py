from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from scrapling.fetchers import Fetcher


WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_DB = WORKSPACE / "data" / "db" / "agentic_workflow.db"
DEFAULT_RAW_DIR = WORKSPACE / "data" / "scraped" / "raw"

X_DOMAINS = {"x.com", "twitter.com", "mobile.twitter.com"}
SUCCESS_STATUSES = {"success", "inaccessible", "skipped"}
UNRESOLVED_STATUSES = {"retry_pending", "failed", "no_attempt"}
TRANSIENT_ERROR_FRAGMENTS = (
    "timed out",
    "timeout",
    "connection",
    "connection refused",
    "connection reset",
    "could not resolve",
    "dns",
    "network",
    "proxy",
    "ssl",
    "tls",
    "rate limit",
    "too many requests",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def clean_text(text: str, max_chars: int) -> str:
    lines = [line.strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    collapsed = "\n".join(line for line in lines if line)
    return collapsed[:max_chars]


def status_from_http(http_status: int | None, extracted_text: str, url: str) -> str:
    if http_status in {401, 403, 404, 410, 451}:
        return "inaccessible"
    if http_status is None:
        return "failed"
    if 200 <= http_status < 400:
        if domain(url) in X_DOMAINS and (
            len(extracted_text) < 80
            or "JavaScript is not available" in extracted_text
            or "Something went wrong" in extracted_text
        ):
            return "retry_pending"
        return "success"
    if 500 <= http_status < 600 or http_status in {408, 409, 425, 429}:
        return "retry_pending"
    return "failed"


def status_from_exception(exc: Exception) -> str:
    message = str(exc).lower()
    if any(fragment in message for fragment in TRANSIENT_ERROR_FRAGMENTS):
        return "retry_pending"
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return "retry_pending"
    return "failed"


def commit_with_retry(conn: sqlite3.Connection, attempts: int = 5, delay: float = 0.5) -> None:
    for attempt in range(1, attempts + 1):
        try:
            conn.commit()
            return
        except sqlite3.OperationalError:
            if attempt == attempts:
                raise
            time.sleep(delay * attempt)


def record_attempt_with_retry(
    conn: sqlite3.Connection,
    link_ids: list[int],
    attempted_at: str,
    status: str,
    http_status: int | None,
    final_url: str | None,
    title: str | None,
    extracted_text: str | None,
    metadata: dict[str, Any] | None,
    error_type: str | None,
    error_message: str | None,
    duration_ms: int,
    attempts: int = 5,
    delay: float = 1.0,
) -> None:
    for attempt in range(1, attempts + 1):
        try:
            record_attempt(
                conn,
                link_ids,
                attempted_at,
                status,
                http_status,
                final_url,
                title,
                extracted_text,
                metadata,
                error_type,
                error_message,
                duration_ms,
            )
            commit_with_retry(conn)
            return
        except sqlite3.OperationalError:
            try:
                conn.rollback()
            except sqlite3.Error:
                pass
            if attempt == attempts:
                raise
            time.sleep(delay * attempt)


def page_html(page: Any) -> str:
    html_content = getattr(page, "html_content", None)
    if isinstance(html_content, str) and html_content:
        return html_content
    text = getattr(page, "text", None)
    if isinstance(text, str) and text:
        return text
    body = getattr(page, "body", None)
    if isinstance(body, bytes):
        return body.decode("utf-8", errors="replace")
    if isinstance(body, str):
        return body
    return str(page)


def extract_metadata(html: str, page: Any, url: str, raw_path: Path | None) -> tuple[str | None, str, dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    if not title:
        try:
            title = page.css("title::text").get(default="").strip() or None
        except Exception:
            title = None

    meta: dict[str, Any] = {
        "domain": domain(url),
        "raw_html_path": str(raw_path) if raw_path else None,
        "headers": dict(getattr(page, "headers", {}) or {}),
    }
    for key, selector in {
        "description": 'meta[name="description"]',
        "og_title": 'meta[property="og:title"]',
        "og_description": 'meta[property="og:description"]',
        "og_url": 'meta[property="og:url"]',
        "twitter_title": 'meta[name="twitter:title"]',
        "twitter_description": 'meta[name="twitter:description"]',
    }.items():
        node = soup.select_one(selector)
        if node and node.get("content"):
            meta[key] = node["content"].strip()

    try:
        extracted_text = page.get_all_text()
    except Exception:
        extracted_text = soup.get_text("\n")
    return title, extracted_text, meta


def pending_groups(
    conn: sqlite3.Connection,
    priority: str,
    limit: int | None,
    retry_failed: bool,
) -> list[sqlite3.Row]:
    conn.create_function("domain", 1, domain)
    filters: list[str] = []
    params: list[Any] = []
    if priority == "non-x":
        filters.append("domain(normalized_url) NOT IN ('x.com', 'twitter.com', 'mobile.twitter.com')")
    elif priority == "x":
        filters.append("domain(normalized_url) IN ('x.com', 'twitter.com', 'mobile.twitter.com')")
    elif priority == "github":
        filters.append("domain(normalized_url) = 'github.com'")
    elif priority != "all":
        raise ValueError(f"Unknown priority: {priority}")

    if retry_failed:
        filters.append(
            """
            EXISTS (
              SELECT 1
              FROM scrape_attempts sa
              JOIN links l2 ON l2.id = sa.link_id
              WHERE l2.normalized_url = links.normalized_url
                AND sa.status IN ('failed', 'retry_pending')
            )
            """
        )
    else:
        filters.append(
            """
            NOT EXISTS (
              SELECT 1
              FROM scrape_attempts sa
              JOIN links l2 ON l2.id = sa.link_id
              WHERE l2.normalized_url = links.normalized_url
                AND sa.status IN ('success', 'inaccessible', 'skipped', 'retry_pending')
            )
            """
        )

    where_sql = " AND ".join(f"({item})" for item in filters)
    limit_sql = "LIMIT ?" if limit else ""
    if limit:
        params.append(limit)
    return list(
        conn.execute(
            f"""
            SELECT
              normalized_url,
              MIN(raw_url) AS raw_url,
              domain(normalized_url) AS domain,
              GROUP_CONCAT(id) AS link_ids,
              COUNT(*) AS link_count,
              MIN(id) AS first_link_id
            FROM links
            WHERE {where_sql}
            GROUP BY normalized_url
            ORDER BY
              CASE domain(normalized_url)
                WHEN 'github.com' THEN 0
                WHEN 'openai.com' THEN 1
                WHEN 'developers.openai.com' THEN 1
                WHEN 'cookbook.openai.com' THEN 1
                WHEN 'anthropic.com' THEN 2
                WHEN 'arxiv.org' THEN 3
                WHEN 'x.com' THEN 9
                ELSE 4
              END,
              first_link_id
            {limit_sql}
            """,
            params,
        )
    )


def raw_path_for_url(url: str, raw_dir: Path) -> Path:
    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return raw_dir / f"{url_hash}.html"


def raw_missing(path: Path) -> bool:
    try:
        return (not path.exists()) or path.stat().st_size == 0
    except OSError:
        return True


def latest_status_groups(
    conn: sqlite3.Connection,
    priority: str,
    limit: int | None,
    latest_statuses: list[str],
) -> list[sqlite3.Row]:
    conn.create_function("domain", 1, domain)
    filters: list[str] = []
    params: list[Any] = []
    if priority == "non-x":
        filters.append("domain(normalized_url) NOT IN ('x.com', 'twitter.com', 'mobile.twitter.com')")
    elif priority == "x":
        filters.append("domain(normalized_url) IN ('x.com', 'twitter.com', 'mobile.twitter.com')")
    elif priority == "github":
        filters.append("domain(normalized_url) = 'github.com'")
    elif priority != "all":
        raise ValueError(f"Unknown priority: {priority}")

    status_placeholders = ",".join("?" for _ in latest_statuses)
    filters.append(f"latest_status IN ({status_placeholders})")
    params.extend(latest_statuses)
    where_sql = " AND ".join(f"({item})" for item in filters)
    limit_sql = "LIMIT ?" if limit else ""
    if limit:
        params.append(limit)
    return list(
        conn.execute(
            f"""
            WITH latest AS (
              SELECT
                sa.*,
                ROW_NUMBER() OVER (
                  PARTITION BY sa.link_id
                  ORDER BY sa.attempted_at DESC, sa.id DESC
                ) AS rn
              FROM scrape_attempts sa
            ),
            eligible AS (
              SELECT
                links.id,
                links.raw_url,
                links.normalized_url,
                domain(links.normalized_url) AS domain,
                COALESCE(latest.status, 'no_attempt') AS latest_status
              FROM links
              LEFT JOIN latest
                ON latest.link_id = links.id
               AND latest.rn = 1
            )
            SELECT
              normalized_url,
              MIN(raw_url) AS raw_url,
              domain,
              GROUP_CONCAT(id) AS link_ids,
              COUNT(*) AS link_count,
              MIN(id) AS first_link_id
            FROM eligible
            WHERE {where_sql}
            GROUP BY normalized_url
            ORDER BY
              CASE domain
                WHEN 'github.com' THEN 0
                WHEN 'openai.com' THEN 1
                WHEN 'developers.openai.com' THEN 1
                WHEN 'cookbook.openai.com' THEN 1
                WHEN 'anthropic.com' THEN 2
                WHEN 'arxiv.org' THEN 3
                WHEN 'x.com' THEN 9
                ELSE 4
              END,
              first_link_id
            {limit_sql}
            """,
            params,
        )
    )


def attempt_counts(conn: sqlite3.Connection, link_ids: list[int]) -> dict[int, int]:
    if not link_ids:
        return {}
    placeholders = ",".join("?" for _ in link_ids)
    rows = conn.execute(
        f"""
        SELECT link_id, COUNT(*) AS count
        FROM scrape_attempts
        WHERE link_id IN ({placeholders})
        GROUP BY link_id
        """,
        link_ids,
    ).fetchall()
    return {int(row["link_id"]): int(row["count"]) for row in rows}


def artifact_paths(metadata: dict[str, Any] | None) -> list[str]:
    if not metadata:
        return []
    paths: list[str] = []
    for key in ("raw_html_path", "raw_json_path", "screenshot_path", "html_path", "text_path"):
        value = metadata.get(key)
        if isinstance(value, str) and value:
            paths.append(value)
    return paths


def append_attempt_log(path: Path | None, item: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def groups_missing_raw(
    conn: sqlite3.Connection,
    priority: str,
    limit: int | None,
    raw_dir: Path,
) -> list[sqlite3.Row]:
    conn.create_function("domain", 1, domain)
    filters: list[str] = []
    params: list[Any] = []
    if priority == "non-x":
        filters.append("domain(normalized_url) NOT IN ('x.com', 'twitter.com', 'mobile.twitter.com')")
    elif priority == "x":
        filters.append("domain(normalized_url) IN ('x.com', 'twitter.com', 'mobile.twitter.com')")
    elif priority == "github":
        filters.append("domain(normalized_url) = 'github.com'")
    elif priority != "all":
        raise ValueError(f"Unknown priority: {priority}")

    filters.append(
        """
        EXISTS (
          SELECT 1
          FROM scrape_attempts sa
          JOIN links l2 ON l2.id = sa.link_id
          WHERE l2.normalized_url = links.normalized_url
            AND sa.status IN ('success', 'inaccessible')
        )
        """
    )
    where_sql = " AND ".join(f"({item})" for item in filters)
    rows = list(
        conn.execute(
            f"""
            SELECT
              normalized_url,
              MIN(raw_url) AS raw_url,
              domain(normalized_url) AS domain,
              GROUP_CONCAT(id) AS link_ids,
              COUNT(*) AS link_count,
              MIN(id) AS first_link_id
            FROM links
            WHERE {where_sql}
            GROUP BY normalized_url
            ORDER BY first_link_id
            """,
            params,
        )
    )
    missing = [row for row in rows if raw_missing(raw_path_for_url(row["normalized_url"], raw_dir))]
    return missing[:limit] if limit else missing


def record_attempt(
    conn: sqlite3.Connection,
    link_ids: list[int],
    attempted_at: str,
    status: str,
    http_status: int | None,
    final_url: str | None,
    title: str | None,
    extracted_text: str | None,
    metadata: dict[str, Any] | None,
    error_type: str | None,
    error_message: str | None,
    duration_ms: int,
) -> None:
    payload = json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True)
    for link_id in link_ids:
        conn.execute(
            """
            INSERT INTO scrape_attempts(
              link_id, attempted_at, tool, status, http_status, final_url, title,
              extracted_text, metadata_json, error_type, error_message, duration_ms
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                link_id,
                attempted_at,
                "scrapling.Fetcher",
                status,
                http_status,
                final_url,
                title,
                extracted_text,
                payload,
                error_type,
                error_message,
                duration_ms,
            ),
        )


def scrape_one(url: str, raw_dir: Path, timeout: int, max_chars: int, save_raw: bool, fetch_retries: int) -> dict[str, Any]:
    started = time.perf_counter()
    raw_path: Path | None = None
    try:
        page = Fetcher.get(
            url,
            timeout=timeout,
            retries=fetch_retries,
            follow_redirects="safe",
            impersonate="chrome",
        )
        html = page_html(page)
        if save_raw:
            raw_dir.mkdir(parents=True, exist_ok=True)
            raw_path = raw_path_for_url(url, raw_dir)
            raw_path.write_text(html, encoding="utf-8", errors="replace")
        title, extracted_text, metadata = extract_metadata(html, page, url, raw_path)
        extracted_text = clean_text(extracted_text, max_chars)
        http_status = getattr(page, "status", None)
        final_url = str(getattr(page, "url", url))
        status = status_from_http(http_status, extracted_text, final_url)
        metadata.update(
            {
                "source_url": url,
                "text_length": len(extracted_text),
                "html_length": len(html),
                "fetch_retries": fetch_retries,
            }
        )
        return {
            "status": status,
            "http_status": http_status,
            "final_url": final_url,
            "title": title,
            "extracted_text": extracted_text if status == "success" else (extracted_text or None),
            "metadata": metadata,
            "error_type": None,
            "error_message": None,
            "duration_ms": int((time.perf_counter() - started) * 1000),
        }
    except Exception as exc:
        return {
            "status": status_from_exception(exc),
            "http_status": None,
            "final_url": None,
            "title": None,
            "extracted_text": None,
            "metadata": {"source_url": url, "domain": domain(url), "fetch_retries": fetch_retries},
            "error_type": type(exc).__name__,
            "error_message": str(exc)[:2000],
            "duration_ms": int((time.perf_counter() - started) * 1000),
        }


def run(args: argparse.Namespace) -> dict[str, int]:
    conn = sqlite3.connect(args.db, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = PERSIST")
    if args.refresh_raw:
        groups = groups_missing_raw(conn, args.priority, args.limit, args.raw_dir)
    elif args.latest_statuses:
        groups = latest_status_groups(conn, args.priority, args.limit, args.latest_statuses)
    else:
        groups = pending_groups(conn, args.priority, args.limit, args.retry_failed)
    stats = {"selected_url_count": len(groups), "success": 0, "retry_pending": 0, "inaccessible": 0, "failed": 0, "skipped": 0, "terminal_failed": 0}
    for index, row in enumerate(groups, start=1):
        url = row["normalized_url"]
        link_ids = [int(item) for item in str(row["link_ids"]).split(",") if item]
        previous_attempt_counts = attempt_counts(conn, link_ids)
        result = scrape_one(url, args.raw_dir, args.timeout, args.max_chars, args.save_raw, args.fetch_retries)
        if args.terminalize_unresolved and result["status"] in {"retry_pending", "failed"}:
            original_status = result["status"]
            metadata = dict(result.get("metadata") or {})
            metadata.update(
                {
                    "pre_terminal_status": original_status,
                    "terminalized_by": "scripts/scrape_links.py",
                    "terminalized_reason": "Bounded Goal 007 retry still did not capture content.",
                }
            )
            result["metadata"] = metadata
            result["status"] = args.terminal_status
            result["error_type"] = result["error_type"] or "TerminalizedUnresolvedScrape"
            result["error_message"] = (
                f"Terminalized after bounded retry; original status was {original_status}. "
                + (result["error_message"] or "")
            )[:2000]
        attempted_at = utc_now()
        record_attempt_with_retry(
            conn,
            link_ids,
            attempted_at,
            result["status"],
            result["http_status"],
            result["final_url"],
            result["title"],
            result["extracted_text"],
            result["metadata"],
            result["error_type"],
            result["error_message"],
            result["duration_ms"],
        )
        stats[result["status"]] = stats.get(result["status"], 0) + 1
        for link_id in link_ids:
            append_attempt_log(
                args.attempts_log,
                {
                    "timestamp": attempted_at,
                    "link_id": link_id,
                    "normalized_url": url,
                    "domain": row["domain"],
                    "tool": "scrapling.Fetcher",
                    "status": result["status"],
                    "http_status": result["http_status"],
                    "error_type": result["error_type"],
                    "error_message": result["error_message"],
                    "artifact_paths": artifact_paths(result.get("metadata")),
                    "retry_count": previous_attempt_counts.get(link_id, 0) + 1,
                    "duration_ms": result["duration_ms"],
                    "source_script": "scripts/scrape_links.py",
                },
            )
        print(
            json.dumps(
                {
                    "index": index,
                    "of": len(groups),
                    "status": result["status"],
                    "http_status": result["http_status"],
                    "domain": row["domain"],
                    "link_rows": len(link_ids),
                    "url": url,
                    "title": result["title"],
                    "duration_ms": result["duration_ms"],
                },
                ensure_ascii=True,
            )
        )
        if args.delay:
            time.sleep(args.delay)
    conn.close()
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape pending links with Scrapling and store attempts in SQLite.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--priority", choices=["all", "non-x", "x", "github"], default="non-x")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("--max-chars", type=int, default=200_000)
    parser.add_argument("--save-raw", action="store_true")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--refresh-raw", action="store_true")
    parser.add_argument("--latest-status", dest="latest_statuses", action="append", choices=sorted(UNRESOLVED_STATUSES | SUCCESS_STATUSES | {"auth_required", "unsupported", "terminal_failed"}))
    parser.add_argument("--attempts-log", type=Path)
    parser.add_argument("--fetch-retries", type=int, default=1)
    parser.add_argument("--terminalize-unresolved", action="store_true")
    parser.add_argument("--terminal-status", default="terminal_failed")
    args = parser.parse_args()
    stats = run(args)
    print("SUMMARY " + json.dumps(stats, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
