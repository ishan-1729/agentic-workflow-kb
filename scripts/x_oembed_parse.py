from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import sqlite3
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup


WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_DB = WORKSPACE / "data" / "db" / "agentic_workflow.db"
DEFAULT_RAW_DIR = WORKSPACE / "data" / "scraped" / "raw" / "x_oembed"
DEFAULT_LOG_DIR = WORKSPACE / "learnings" / "goal-003-x-oembed-parse"
DEFAULT_HEARTBEAT = WORKSPACE / "learnings" / "goal-003-x-oembed-parse.heartbeat.json"

OEMBED_ENDPOINT = "https://publish.x.com/oembed"
X_DOMAINS = {"x.com", "twitter.com", "mobile.twitter.com"}
PARSED_TOOLS = {"x_oembed", "x_sandbox_browser"}
STATUS_ID_RE = re.compile(r"^\d{5,}$")
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


@dataclass(frozen=True)
class LinkRecord:
    link_id: int
    raw_url: str
    normalized_url: str
    post_id: str | None
    candidate_urls: tuple[str, ...]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def local_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def clean_inline(text: str | None, max_chars: int = 20_000) -> str:
    if not text:
        return ""
    collapsed = re.sub(r"\s+", " ", html.unescape(text)).strip()
    return collapsed[:max_chars]


def clean_multiline(text: str | None, max_chars: int = 200_000) -> str:
    if not text:
        return ""
    normalized = html.unescape(text).replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"\s+", " ", line).strip() for line in normalized.split("\n")]
    collapsed = "\n".join(line for line in lines if line)
    return collapsed[:max_chars]


def strip_tracking_query(url: str) -> str:
    parsed = urlparse(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in {"ref_src", "s", "t"}
    ]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True), fragment=""))


def extract_post_ref(url: str) -> tuple[str | None, str | None]:
    parsed = urlparse(url)
    host = domain(url)
    if host not in X_DOMAINS:
        return None, None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 3 and parts[0] == "i" and parts[1] == "status" and STATUS_ID_RE.match(parts[2]):
        return parts[2], None
    if len(parts) >= 4 and parts[0] == "i" and parts[1] == "web" and parts[2] == "status" and STATUS_ID_RE.match(parts[3]):
        return parts[3], None
    if len(parts) >= 3 and parts[1] == "status" and STATUS_ID_RE.match(parts[2]):
        username = parts[0]
        if username and username.lower() not in {"i", "intent", "share"}:
            return parts[2], username
        return parts[2], None
    return None, None


def candidate_from_url(url: str) -> tuple[str | None, str | None]:
    post_id, username = extract_post_ref(url)
    if not post_id:
        return None, None
    if username:
        return post_id, f"https://x.com/{username}/status/{post_id}"
    return post_id, f"https://x.com/i/status/{post_id}"


def unique_ordered(items: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return tuple(result)


def link_record_from_row(row: sqlite3.Row) -> LinkRecord:
    candidates: list[str] = []
    post_ids: list[str] = []
    for url in (row["raw_url"], row["normalized_url"]):
        post_id, candidate = candidate_from_url(url)
        if post_id:
            post_ids.append(post_id)
        if candidate:
            candidates.append(candidate)
            if "/i/status/" not in candidate:
                candidates.append(candidate.replace("https://x.com/", "https://twitter.com/", 1))
    post_id = post_ids[0] if post_ids else None
    if post_id:
        candidates.append(f"https://x.com/i/status/{post_id}")
        candidates.append(f"https://twitter.com/i/status/{post_id}")
    return LinkRecord(
        link_id=int(row["id"]),
        raw_url=row["raw_url"],
        normalized_url=row["normalized_url"],
        post_id=post_id,
        candidate_urls=unique_ordered(candidates),
    )


def is_status_permalink(href: str, post_id: str) -> bool:
    found_id, _username = extract_post_ref(href)
    return found_id == post_id


def same_profile_url(href: str, author_url: str | None) -> bool:
    if not href or not author_url:
        return False
    href_parts = [part for part in urlparse(href).path.split("/") if part]
    author_parts = [part for part in urlparse(author_url).path.split("/") if part]
    if not href_parts or not author_parts:
        return False
    return domain(href) in X_DOMAINS and domain(author_url) in X_DOMAINS and href_parts[0].lower() == author_parts[0].lower()


def author_handle(author_url: str | None) -> str | None:
    if not author_url:
        return None
    parts = [part for part in urlparse(author_url).path.split("/") if part]
    return parts[0] if parts else None


def extract_cards(soup: BeautifulSoup) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for node in soup.find_all(True):
        attrs = getattr(node, "attrs", {}) or {}
        for attr in ("data-expanded-url", "data-card-url", "data-url"):
            value = attrs.get(attr)
            if not value:
                continue
            text = clean_inline(node.get_text(" ", strip=True), 500)
            key = (attr, str(value))
            if key in seen:
                continue
            seen.add(key)
            cards.append({"attribute": attr, "url": str(value), "text": text})
    return cards


def parse_oembed_payload(
    payload: dict[str, Any],
    post_id: str,
    requested_post_url: str,
    raw_json_path: Path | None,
    raw_html_path: Path | None,
) -> dict[str, Any]:
    embed_html = str(payload.get("html") or "")
    soup = BeautifulSoup(embed_html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    blockquote = soup.select_one("blockquote.twitter-tweet") or soup.find("blockquote") or soup
    paragraph = blockquote.find("p") if blockquote else None
    post_text = clean_multiline(paragraph.get_text(" ", strip=True) if paragraph else "", 80_000)

    author_name = clean_inline(str(payload.get("author_name") or ""), 1_000) or None
    author_url_value = clean_inline(str(payload.get("author_url") or ""), 2_000) or None
    post_date_text: str | None = None
    post_url: str | None = None
    all_links: list[dict[str, str | bool]] = []
    outbound_links: list[dict[str, str]] = []
    seen_outbound: set[tuple[str, str]] = set()

    for anchor in soup.find_all("a"):
        href = clean_inline(anchor.get("href"), 4_000)
        text = clean_inline(anchor.get_text(" ", strip=True), 2_000)
        if not href:
            continue
        href_clean = strip_tracking_query(href)
        is_permalink = is_status_permalink(href_clean, post_id)
        is_author = same_profile_url(href_clean, author_url_value) and not is_permalink
        if is_permalink:
            post_url = href_clean
            if text:
                post_date_text = text
        link_entry = {
            "href": href_clean,
            "text": text,
            "is_post_permalink": is_permalink,
            "is_author_profile": is_author,
        }
        all_links.append(link_entry)
        if not is_permalink and not is_author:
            key = (href_clean, text)
            if key not in seen_outbound:
                seen_outbound.add(key)
                outbound_links.append({"href": href_clean, "text": text})

    cards = extract_cards(soup)
    content_fields = []
    if post_text:
        content_fields.append("post_text")
    if author_name:
        content_fields.append("author_name")
    if author_url_value:
        content_fields.append("author_url")
    if post_date_text:
        content_fields.append("post_date")
    if outbound_links:
        content_fields.append("outbound_links")
    if cards:
        content_fields.append("cards")

    parsed_content = bool(content_fields)
    extracted_parts = [f"X/Twitter post: {post_id}"]
    if author_name or author_url_value:
        author_line = "Author: " + (author_name or "unknown")
        if author_url_value:
            author_line += f" ({author_url_value})"
        extracted_parts.append(author_line)
    if post_date_text:
        extracted_parts.append(f"Post date: {post_date_text}")
    if post_text:
        extracted_parts.append("Post text:\n" + post_text)
    if outbound_links:
        outbound_text = "\n".join(
            f"- {item['text']} -> {item['href']}" if item.get("text") else f"- {item['href']}"
            for item in outbound_links
        )
        extracted_parts.append("Outbound links:\n" + outbound_text)
    if cards:
        card_text = "\n".join(
            f"- {item['attribute']}: {item['url']}" for item in cards
        )
        extracted_parts.append("Cards:\n" + card_text)

    extracted_text = clean_multiline("\n\n".join(extracted_parts), 200_000)
    metadata = {
        "method": "x_oembed",
        "parsed_content": parsed_content,
        "post_id": post_id,
        "requested_post_url": requested_post_url,
        "post_url": post_url,
        "post_text": post_text,
        "author_name": author_name,
        "author_url": author_url_value,
        "author_handle": author_handle(author_url_value),
        "post_date": post_date_text,
        "outbound_links": outbound_links,
        "cards": cards,
        "all_links": all_links,
        "content_fields": content_fields,
        "raw_json_path": str(raw_json_path) if raw_json_path else None,
        "raw_html_path": str(raw_html_path) if raw_html_path else None,
        "oembed_type": payload.get("type"),
        "oembed_version": payload.get("version"),
        "provider_name": payload.get("provider_name"),
        "provider_url": payload.get("provider_url"),
        "cache_age": payload.get("cache_age"),
        "html_length": len(embed_html),
        "text_length": len(extracted_text),
    }
    return {
        "parsed_content": parsed_content,
        "title": f"X post {post_id}" + (f" by {author_name}" if author_name else ""),
        "extracted_text": extracted_text if parsed_content else None,
        "metadata": metadata,
    }


def status_from_exception(exc: Exception) -> str:
    message = str(exc).lower()
    if any(fragment in message for fragment in TRANSIENT_ERROR_FRAGMENTS):
        return "retry_pending"
    if isinstance(exc, (TimeoutError, ConnectionError, httpx.TimeoutException, httpx.NetworkError)):
        return "retry_pending"
    return "failed"


def status_from_http(http_status: int) -> str:
    if http_status in {401, 403, 404, 410, 451}:
        return "inaccessible"
    if 500 <= http_status < 600 or http_status in {408, 409, 425, 429}:
        return "retry_pending"
    return "failed"


def raw_paths_for_post(raw_dir: Path, post_id: str, requested_post_url: str) -> tuple[Path, Path]:
    digest = hashlib.sha256(requested_post_url.encode("utf-8")).hexdigest()[:16]
    stem = f"{post_id}_{digest}"
    return raw_dir / f"{stem}.json", raw_dir / f"{stem}.html"


def endpoint_url_for(requested_post_url: str) -> str:
    query = urlencode({"url": requested_post_url, "omit_script": "true", "dnt": "true"})
    return f"{OEMBED_ENDPOINT}?{query}"


def fetch_oembed_group(
    client: httpx.Client,
    post_id: str,
    requested_post_urls: tuple[str, ...],
    raw_dir: Path,
    save_raw: bool,
    max_chars: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    candidate_attempts: list[dict[str, Any]] = []
    raw_dir.mkdir(parents=True, exist_ok=True)

    for requested_post_url in requested_post_urls:
        attempt_started = time.perf_counter()
        endpoint_url = endpoint_url_for(requested_post_url)
        try:
            response = client.get(
                OEMBED_ENDPOINT,
                params={"url": requested_post_url, "omit_script": "true", "dnt": "true"},
            )
            http_status = response.status_code
            attempt_info: dict[str, Any] = {
                "requested_post_url": requested_post_url,
                "endpoint_url": endpoint_url,
                "http_status": http_status,
                "duration_ms": int((time.perf_counter() - attempt_started) * 1000),
            }
            if http_status == 200:
                try:
                    payload = response.json()
                except json.JSONDecodeError as exc:
                    attempt_info.update(
                        {
                            "candidate_status": "failed",
                            "error_type": type(exc).__name__,
                            "error_message": str(exc)[:1000],
                        }
                    )
                    candidate_attempts.append(attempt_info)
                    continue

                raw_json_path: Path | None = None
                raw_html_path: Path | None = None
                if save_raw:
                    raw_json_path, raw_html_path = raw_paths_for_post(raw_dir, post_id, requested_post_url)
                    raw_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
                    raw_html_path.write_text(str(payload.get("html") or ""), encoding="utf-8", errors="replace")

                parsed = parse_oembed_payload(payload, post_id, requested_post_url, raw_json_path, raw_html_path)
                attempt_info.update(
                    {
                        "candidate_status": "success" if parsed["parsed_content"] else "retry_pending",
                        "parsed_content": parsed["parsed_content"],
                        "raw_json_path": str(raw_json_path) if raw_json_path else None,
                        "raw_html_path": str(raw_html_path) if raw_html_path else None,
                    }
                )
                candidate_attempts.append(attempt_info)
                if parsed["parsed_content"]:
                    parsed["metadata"].update(
                        {
                            "source_endpoint": OEMBED_ENDPOINT,
                            "source_endpoint_url": endpoint_url,
                            "candidate_attempts": candidate_attempts,
                            "max_chars": max_chars,
                        }
                    )
                    parsed["extracted_text"] = clean_multiline(parsed["extracted_text"], max_chars)
                    parsed["metadata"]["text_length"] = len(parsed["extracted_text"])
                    return {
                        "tool": "x_oembed",
                        "status": "success",
                        "http_status": http_status,
                        "final_url": requested_post_url,
                        "title": parsed["title"],
                        "extracted_text": parsed["extracted_text"],
                        "metadata": parsed["metadata"],
                        "error_type": None,
                        "error_message": None,
                        "duration_ms": int((time.perf_counter() - started) * 1000),
                    }
                continue

            body_snippet = clean_inline(response.text, 1_000)
            attempt_info.update(
                {
                    "candidate_status": status_from_http(http_status),
                    "error_message": body_snippet,
                }
            )
            candidate_attempts.append(attempt_info)
        except Exception as exc:
            candidate_attempts.append(
                {
                    "requested_post_url": requested_post_url,
                    "endpoint_url": endpoint_url,
                    "candidate_status": status_from_exception(exc),
                    "error_type": type(exc).__name__,
                    "error_message": str(exc)[:1000],
                    "duration_ms": int((time.perf_counter() - attempt_started) * 1000),
                }
            )

    statuses = [str(item.get("candidate_status")) for item in candidate_attempts]
    if any(status == "retry_pending" for status in statuses):
        status = "retry_pending"
    elif statuses and all(status == "inaccessible" for status in statuses):
        status = "inaccessible"
    elif any(status == "failed" for status in statuses):
        status = "failed"
    else:
        status = "retry_pending"
    http_statuses = [item.get("http_status") for item in candidate_attempts if item.get("http_status") is not None]
    error_parts = []
    for item in candidate_attempts[:4]:
        detail = item.get("error_message") or item.get("error_type") or item.get("candidate_status")
        error_parts.append(f"{item.get('requested_post_url')}: {detail}")
    return {
        "tool": "x_oembed",
        "status": status,
        "http_status": int(http_statuses[-1]) if http_statuses else None,
        "final_url": requested_post_urls[0] if requested_post_urls else None,
        "title": None,
        "extracted_text": None,
        "metadata": {
            "method": "x_oembed",
            "parsed_content": False,
            "post_id": post_id,
            "source_endpoint": OEMBED_ENDPOINT,
            "candidate_attempts": candidate_attempts,
        },
        "error_type": "NoParsedOEmbedContent",
        "error_message": " | ".join(error_parts)[:2000],
        "duration_ms": int((time.perf_counter() - started) * 1000),
    }


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.create_function("domain", 1, domain)
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = PERSIST")
    return conn


def commit_with_retry(conn: sqlite3.Connection, attempts: int = 5, delay: float = 0.5) -> None:
    for attempt in range(1, attempts + 1):
        try:
            conn.commit()
            return
        except sqlite3.OperationalError:
            if attempt == attempts:
                raise
            time.sleep(delay * attempt)


def record_attempt(
    conn: sqlite3.Connection,
    link_ids: list[int],
    result: dict[str, Any],
    attempted_at: str | None = None,
) -> None:
    payload = json.dumps(result.get("metadata") or {}, ensure_ascii=False, sort_keys=True)
    attempted_at = attempted_at or utc_now()
    for attempt in range(1, 6):
        try:
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
                        result.get("tool", "x_oembed"),
                        result["status"],
                        result.get("http_status"),
                        result.get("final_url"),
                        result.get("title"),
                        result.get("extracted_text"),
                        payload,
                        result.get("error_type"),
                        result.get("error_message"),
                        result.get("duration_ms"),
                    ),
                )
            commit_with_retry(conn)
            return
        except sqlite3.OperationalError:
            conn.rollback()
            if attempt == 5:
                raise
            time.sleep(0.5 * attempt)


def load_x_links(conn: sqlite3.Connection) -> list[LinkRecord]:
    rows = conn.execute(
        """
        SELECT id, raw_url, normalized_url
        FROM links
        WHERE domain(normalized_url) IN ('x.com', 'twitter.com', 'mobile.twitter.com')
        ORDER BY id
        """
    ).fetchall()
    return [link_record_from_row(row) for row in rows]


def parsed_link_ids(conn: sqlite3.Connection) -> set[int]:
    rows = conn.execute(
        """
        SELECT link_id, metadata_json, extracted_text
        FROM scrape_attempts
        WHERE tool IN ('x_oembed', 'x_sandbox_browser')
          AND status = 'success'
          AND LENGTH(TRIM(COALESCE(extracted_text, ''))) > 0
        """
    ).fetchall()
    parsed: set[int] = set()
    for row in rows:
        try:
            metadata = json.loads(row["metadata_json"] or "{}")
        except json.JSONDecodeError:
            metadata = {}
        if metadata.get("parsed_content") is True:
            parsed.add(int(row["link_id"]))
    return parsed


def parsed_counts_by_normalized_url(records: list[LinkRecord], parsed_ids: set[int]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for record in records:
        item = grouped.setdefault(record.normalized_url, {"normalized_url": record.normalized_url, "total_link_rows": 0, "parsed_link_rows": 0})
        item["total_link_rows"] += 1
        if record.link_id in parsed_ids:
            item["parsed_link_rows"] += 1
    return sorted(grouped.values(), key=lambda item: item["normalized_url"])


def latest_x_status_counts(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute(
        """
        WITH latest AS (
          SELECT
            sa.status,
            ROW_NUMBER() OVER (PARTITION BY sa.link_id ORDER BY sa.attempted_at DESC, sa.id DESC) AS rn
          FROM scrape_attempts sa
          JOIN links l ON l.id = sa.link_id
          WHERE domain(l.normalized_url) IN ('x.com', 'twitter.com', 'mobile.twitter.com')
        )
        SELECT status, COUNT(*) AS count
        FROM latest
        WHERE rn = 1
        GROUP BY status
        ORDER BY status
        """
    ).fetchall()
    return {row["status"]: int(row["count"]) for row in rows}


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(item, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    paths: list[str] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key.endswith("_path") and isinstance(child, str) and child:
                    paths.append(child)
                else:
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(metadata or {})
    return sorted(set(paths))


def append_goal_attempts(
    path: Path | None,
    link_ids: list[int],
    normalized_urls_by_link_id: dict[int, str],
    previous_attempt_counts: dict[int, int],
    result: dict[str, Any],
    attempted_at: str,
    source_script: str,
) -> None:
    if path is None:
        return
    for link_id in link_ids:
        normalized_url = normalized_urls_by_link_id.get(link_id, result.get("final_url") or "")
        append_jsonl(
            path,
            {
                "timestamp": attempted_at,
                "link_id": link_id,
                "normalized_url": normalized_url,
                "domain": domain(normalized_url),
                "tool": result.get("tool", "x_oembed"),
                "status": result.get("status"),
                "http_status": result.get("http_status"),
                "error_type": result.get("error_type"),
                "error_message": result.get("error_message"),
                "artifact_paths": artifact_paths(result.get("metadata")),
                "retry_count": previous_attempt_counts.get(link_id, 0) + 1,
                "duration_ms": result.get("duration_ms"),
                "source_script": source_script,
            },
        )


def write_heartbeat(
    conn: sqlite3.Connection,
    records: list[LinkRecord],
    heartbeat_path: Path,
    phase: str,
    stats: dict[str, Any],
    goal_id: str,
    browser_sandbox_dir: str | None = None,
) -> dict[str, Any]:
    parsed_ids = parsed_link_ids(conn)
    total = len(records)
    threshold = math.ceil(0.50 * total)
    heartbeat = {
        "goal_id": goal_id,
        "phase": phase,
        "updated_at": local_now(),
        "total_x_link_rows": total,
        "parsed_x_link_rows": len(parsed_ids),
        "threshold_x_link_rows": threshold,
        "threshold_passed": len(parsed_ids) >= threshold,
        "latest_scrape_status_counts": latest_x_status_counts(conn),
        "methods_used": ["x_oembed"] if phase.startswith("oembed") or stats.get("attempted_post_groups", 0) or stats.get("skipped_link_rows", 0) else [],
        "browser_sandbox_dir": browser_sandbox_dir,
        "no_personal_browser_profile_cookies_or_credentials_used": True,
        "imports_read_only": True,
        "oembed": stats,
    }
    write_json(heartbeat_path, heartbeat)
    return heartbeat


def representative_samples(conn: sqlite3.Connection, limit: int = 5) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT l.id AS link_id, l.normalized_url, sa.title, sa.extracted_text, sa.metadata_json
        FROM scrape_attempts sa
        JOIN links l ON l.id = sa.link_id
        WHERE sa.tool = 'x_oembed'
          AND sa.status = 'success'
          AND LENGTH(TRIM(COALESCE(sa.extracted_text, ''))) > 0
        ORDER BY sa.id
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    samples: list[dict[str, Any]] = []
    for row in rows:
        try:
            metadata = json.loads(row["metadata_json"] or "{}")
        except json.JSONDecodeError:
            metadata = {}
        samples.append(
            {
                "link_id": int(row["link_id"]),
                "normalized_url": row["normalized_url"],
                "title": row["title"],
                "author_name": metadata.get("author_name"),
                "post_date": metadata.get("post_date"),
                "post_text_excerpt": clean_inline(metadata.get("post_text") or row["extracted_text"], 500),
                "outbound_links": metadata.get("outbound_links", [])[:3],
            }
        )
    return samples


def group_records(records: list[LinkRecord], already_parsed: set[int]) -> tuple[list[LinkRecord], list[dict[str, Any]]]:
    unsupported: list[LinkRecord] = []
    grouped: dict[str, dict[str, Any]] = {}
    for record in records:
        if record.link_id in already_parsed:
            continue
        if not record.post_id:
            unsupported.append(record)
            continue
        item = grouped.setdefault(
            record.post_id,
            {
                "post_id": record.post_id,
                "link_ids": [],
                "normalized_urls": [],
                "candidate_urls": [],
                "first_link_id": record.link_id,
            },
        )
        item["link_ids"].append(record.link_id)
        item["normalized_urls"].append(record.normalized_url)
        item["candidate_urls"].extend(record.candidate_urls)
        item["first_link_id"] = min(int(item["first_link_id"]), record.link_id)
    groups = sorted(grouped.values(), key=lambda item: int(item["first_link_id"]))
    for group in groups:
        group["candidate_urls"] = unique_ordered(group["candidate_urls"])
        group["normalized_urls"] = unique_ordered(group["normalized_urls"])
    return unsupported, groups


def run(args: argparse.Namespace) -> dict[str, Any]:
    conn = connect(args.db)
    records = load_x_links(conn)
    normalized_urls_by_link_id = {record.link_id: record.normalized_url for record in records}
    threshold = math.ceil(0.50 * len(records))
    already_parsed = parsed_link_ids(conn)
    unsupported, groups = group_records(records, already_parsed)
    unparsed_post_groups_available = len(groups)
    if args.limit_post_groups is not None:
        groups = groups[: args.limit_post_groups]
    stats: dict[str, Any] = {
        "started_at": local_now(),
        "finished_at": None,
        "endpoint": OEMBED_ENDPOINT,
        "unparsed_post_groups_available": unparsed_post_groups_available,
        "selected_post_groups": len(groups),
        "attempted_post_groups": 0,
        "success_post_groups": 0,
        "success_link_rows": 0,
        "retry_pending_post_groups": 0,
        "inaccessible_post_groups": 0,
        "failed_post_groups": 0,
        "skipped_link_rows": 0,
        "unsupported_link_rows": len(unsupported),
        "terminal_unsupported_link_rows": 0,
        "selected_unparsed_link_rows": sum(len(group["link_ids"]) for group in groups) + len(unsupported),
        "total_x_link_rows": len(records),
        "threshold_x_link_rows": threshold,
        "parsed_x_link_rows_start": len(already_parsed),
        "parsed_x_link_rows_current": len(already_parsed),
        "log_dir": str(args.log_dir),
        "raw_dir": str(args.raw_dir),
        "command": " ".join(args.command_for_log),
        "confirmation": "No personal browser/profile/cookies/credentials were used; oEmbed only.",
    }
    args.log_dir.mkdir(parents=True, exist_ok=True)
    write_heartbeat(conn, records, args.heartbeat_file, "oembed_start", stats, args.goal_id)

    if args.stop_at_threshold and len(already_parsed) >= threshold:
        stats["finished_at"] = local_now()
        write_heartbeat(conn, records, args.heartbeat_file, "threshold_already_met", stats, args.goal_id)
        conn.close()
        return stats

    for record in unsupported:
        result = {
            "tool": "x_oembed",
            "status": "unsupported",
            "http_status": None,
            "final_url": record.normalized_url,
            "title": None,
            "extracted_text": None,
            "metadata": {
                "method": "x_oembed",
                "parsed_content": False,
                "reason": "No status/post ID found; oEmbed pass only supports individual public post URLs.",
                "raw_url": record.raw_url,
                "normalized_url": record.normalized_url,
            },
            "error_type": "UnsupportedXUrl",
            "error_message": "No status/post ID found; oEmbed pass only supports individual public post URLs.",
            "duration_ms": 0,
        }
        previous_attempt_counts = attempt_counts(conn, [record.link_id])
        attempted_at = utc_now()
        record_attempt(conn, [record.link_id], result, attempted_at=attempted_at)
        stats["terminal_unsupported_link_rows"] += 1
        append_goal_attempts(
            args.attempts_log,
            [record.link_id],
            normalized_urls_by_link_id,
            previous_attempt_counts,
            result,
            attempted_at,
            "scripts/x_oembed_parse.py",
        )
        append_jsonl(
            args.log_dir / "oembed_attempts.jsonl",
            {
                "kind": "unsupported",
                "link_id": record.link_id,
                "raw_url": record.raw_url,
                "normalized_url": record.normalized_url,
                "result": result,
                "logged_at": local_now(),
            },
        )

    timeout = httpx.Timeout(args.timeout)
    headers = {"User-Agent": "agentic-workflow-x-oembed-parser/1.0"}
    with httpx.Client(timeout=timeout, follow_redirects=True, trust_env=False, headers=headers) as client:
        for index, group in enumerate(groups, start=1):
            result = fetch_oembed_group(
                client,
                str(group["post_id"]),
                tuple(group["candidate_urls"]),
                args.raw_dir,
                args.save_raw,
                args.max_chars,
            )
            link_ids = [int(item) for item in group["link_ids"]]
            previous_attempt_counts = attempt_counts(conn, link_ids)
            attempted_at = utc_now()
            record_attempt(conn, link_ids, result, attempted_at=attempted_at)
            append_goal_attempts(
                args.attempts_log,
                link_ids,
                normalized_urls_by_link_id,
                previous_attempt_counts,
                result,
                attempted_at,
                "scripts/x_oembed_parse.py",
            )
            stats["attempted_post_groups"] += 1
            if result["status"] == "success":
                stats["success_post_groups"] += 1
                stats["success_link_rows"] += len(link_ids)
            elif result["status"] == "retry_pending":
                stats["retry_pending_post_groups"] += 1
            elif result["status"] == "inaccessible":
                stats["inaccessible_post_groups"] += 1
            elif result["status"] == "failed":
                stats["failed_post_groups"] += 1

            parsed_now = len(parsed_link_ids(conn))
            stats["parsed_x_link_rows_current"] = parsed_now
            log_item = {
                "kind": "oembed_group",
                "index": index,
                "of": len(groups),
                "post_id": group["post_id"],
                "link_ids": link_ids,
                "normalized_urls": group["normalized_urls"],
                "candidate_urls": group["candidate_urls"],
                "status": result["status"],
                "http_status": result.get("http_status"),
                "title": result.get("title"),
                "error_type": result.get("error_type"),
                "error_message": result.get("error_message"),
                "duration_ms": result.get("duration_ms"),
                "parsed_x_link_rows": parsed_now,
                "threshold_x_link_rows": threshold,
                "logged_at": local_now(),
            }
            append_jsonl(args.log_dir / "oembed_attempts.jsonl", log_item)
            print(json.dumps(log_item, ensure_ascii=True, sort_keys=True))

            if index % args.heartbeat_interval == 0:
                write_heartbeat(conn, records, args.heartbeat_file, "oembed_batch", stats, args.goal_id)

            if args.stop_at_threshold and parsed_now >= threshold:
                stats["finished_at"] = local_now()
                write_heartbeat(conn, records, args.heartbeat_file, "oembed_threshold_reached", stats, args.goal_id)
                break

            if args.delay:
                time.sleep(args.delay)

    if stats["finished_at"] is None:
        stats["finished_at"] = local_now()
    parsed_ids = parsed_link_ids(conn)
    stats["parsed_x_link_rows_current"] = len(parsed_ids)
    stats["threshold_passed"] = len(parsed_ids) >= threshold
    summary = {
        "stats": stats,
        "parsed_counts_by_normalized_url": parsed_counts_by_normalized_url(records, parsed_ids),
        "representative_samples": representative_samples(conn),
        "latest_x_status_counts": latest_x_status_counts(conn),
        "confirmation": "No personal browser/profile/cookies/credentials were used; oEmbed only.",
    }
    write_json(args.log_dir / "summary.json", summary)
    write_heartbeat(conn, records, args.heartbeat_file, "oembed_complete" if stats["threshold_passed"] else "oembed_complete_below_threshold", stats, args.goal_id)
    conn.close()
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse X/Twitter post content through X's unauthenticated official oEmbed endpoint.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--heartbeat-file", type=Path, default=DEFAULT_HEARTBEAT)
    parser.add_argument("--goal-id", default="goal-003-x-oembed-parse")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--delay", type=float, default=0.2)
    parser.add_argument("--max-chars", type=int, default=200_000)
    parser.add_argument("--heartbeat-interval", type=int, default=25)
    parser.add_argument("--limit-post-groups", type=int)
    parser.add_argument("--save-raw", action="store_true")
    parser.add_argument("--stop-at-threshold", action="store_true", default=True)
    parser.add_argument("--no-stop-at-threshold", dest="stop_at_threshold", action="store_false")
    parser.add_argument("--attempts-log", type=Path)
    args = parser.parse_args()
    args.command_for_log = ["uv", "run", "--no-cache", "python", "-B"] + sys.argv
    stats = run(args)
    print("SUMMARY " + json.dumps(stats, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
