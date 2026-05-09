from __future__ import annotations

import argparse
import html
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_DB = WORKSPACE / "data" / "db" / "agentic_workflow.db"
DEFAULT_KB = WORKSPACE / "kb"
DEFAULT_REPORT = WORKSPACE / "learnings" / "checkpoint-011-baseline-kb.md"
GENERATOR = "scripts/build_kb.py"
GENERATOR_VERSION = "baseline-kb-v1"
MAX_EXCERPT_CHARS = 2200
INTENT_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}
INTENT_ALIASES: dict[str, tuple[str, ...]] = {
    "agent": ("agents", "multiagent", "orchestration", "workflow", "autonomous"),
    "browser": ("computer use", "web automation", "click", "chromium", "playwright"),
    "context": ("context engineering", "tokens", "long context", "compression"),
    "eval": ("evaluation", "benchmark", "metric", "verification", "test"),
    "graph": ("knowledge graph", "co-occurrence", "relationship", "wikilink", "backlink"),
    "knowledge": ("knowledge base", "wiki", "obsidian", "markdown", "llm wiki"),
    "memory": ("persistent memory", "agent memory", "obsidian vault", "knowledge graph"),
    "prompt": ("prompts", "prompt engineering", "system prompt", "instructions"),
    "rag": ("retrieval", "search", "semantic search", "vector", "index"),
    "safety": ("security", "prompt injection", "verification", "sandbox"),
    "search": ("retrieval", "fts", "keyword", "semantic", "query"),
    "skill": ("skills", "commands", "slash command", "agent interface"),
    "tool": ("tools", "devtools", "cli", "github", "open source"),
}


@dataclass
class Page:
    rel_path: str
    title: str
    page_type: str
    body: str
    source_message_ids: list[int] = field(default_factory=list)
    source_link_ids: list[int] = field(default_factory=list)
    candidate_ids: list[int] = field(default_factory=list)
    decision_ids: list[int] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def metadata(self, generated_at: str) -> dict[str, Any]:
        return {
            "title": self.title,
            "page_type": self.page_type,
            "generated_by": GENERATOR,
            "generator_version": GENERATOR_VERSION,
            "generated_at": generated_at,
            "source_message_ids": sorted(set(self.source_message_ids)),
            "source_link_ids": sorted(set(self.source_link_ids)),
            "candidate_ids": sorted(set(self.candidate_ids)),
            "decision_ids": sorted(set(self.decision_ids)),
            "tags": sorted(set(self.tags)),
        }

    def markdown(self, generated_at: str) -> str:
        return frontmatter(self.metadata(generated_at)) + "\n" + self.body.rstrip() + "\n"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean_text(value: Any, max_chars: int | None = None) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value)).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if max_chars is not None and len(text) > max_chars:
        return text[: max_chars - 3].rstrip() + "..."
    return text


def inline_text(value: Any, max_chars: int = 180) -> str:
    text = re.sub(r"\s+", " ", clean_text(value)).strip()
    if len(text) > max_chars:
        return text[: max_chars - 3].rstrip() + "..."
    return text


def slugify(value: str, fallback: str = "page") -> str:
    lowered = value.lower().strip()
    lowered = lowered.replace("&", " and ")
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    lowered = re.sub(r"-+", "-", lowered).strip("-")
    return lowered or fallback


def yaml_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True)


def frontmatter(metadata: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in metadata.items():
        lines.append(f"{key}: {yaml_value(value)}")
    lines.append("---")
    return "\n".join(lines)


def fence(value: Any, language: str = "text") -> str:
    text = clean_text(value)
    text = text.replace("```", "` ` `")
    return f"```{language}\n{text}\n```"


def wikilink(title: str) -> str:
    return f"[[{title}]]"


def message_title(message_id: int) -> str:
    return f"Message {message_id:06d}"


def link_title(link_id: int) -> str:
    return f"Link {link_id:06d}"


def topic_title(category: str) -> str:
    return "Topic: " + category.replace("_", " ")


def candidate_title(name: str) -> str:
    return f"Candidate: {name}"


def domain(url: str | None) -> str:
    if not url:
        return ""
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def fetch_rows(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    return list(conn.execute(sql, params).fetchall())


def latest_attempts(conn: sqlite3.Connection) -> dict[int, sqlite3.Row]:
    rows = fetch_rows(
        conn,
        """
        SELECT sa.*, l.normalized_url
        FROM scrape_attempts sa
        JOIN links l ON l.id = sa.link_id
        ORDER BY sa.link_id, sa.attempted_at DESC, sa.id DESC
        """,
    )
    latest: dict[int, sqlite3.Row] = {}
    for row in rows:
        link_id = int(row["link_id"])
        if link_id not in latest:
            latest[link_id] = row
    return latest


def load_corpus(conn: sqlite3.Connection) -> dict[str, Any]:
    messages = fetch_rows(conn, "SELECT * FROM messages ORDER BY id")
    links = fetch_rows(conn, "SELECT * FROM links ORDER BY id")
    candidates = fetch_rows(conn, "SELECT * FROM kb_candidates ORDER BY id")
    safety = fetch_rows(conn, "SELECT * FROM kb_safety_reviews ORDER BY id")
    decisions = fetch_rows(conn, "SELECT * FROM decisions ORDER BY id")
    classifications = fetch_rows(conn, "SELECT * FROM classifications ORDER BY message_id, category")
    tags = fetch_rows(conn, "SELECT * FROM message_tags ORDER BY message_id, id")

    links_by_message: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for row in links:
        links_by_message[int(row["message_id"])].append(row)

    tags_by_message: dict[int, list[str]] = defaultdict(list)
    for row in tags:
        tags_by_message[int(row["message_id"])].append(str(row["tag"]))

    categories_by_message: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for row in classifications:
        categories_by_message[int(row["message_id"])].append(row)

    latest = latest_attempts(conn)
    safety_by_candidate = {str(row["candidate_name"]): row for row in safety}

    return {
        "messages": messages,
        "links": links,
        "candidates": candidates,
        "safety": safety,
        "decisions": decisions,
        "classifications": classifications,
        "links_by_message": links_by_message,
        "tags_by_message": tags_by_message,
        "categories_by_message": categories_by_message,
        "latest_attempts": latest,
        "safety_by_candidate": safety_by_candidate,
    }


def page_for_index(corpus: dict[str, Any]) -> Page:
    messages = corpus["messages"]
    links = corpus["links"]
    candidates = corpus["candidates"]
    classifications = corpus["classifications"]
    category_counts = Counter(row["category"] for row in classifications)
    decision = corpus["decisions"][-1] if corpus["decisions"] else None
    topics = [topic_title(category) for category, _count in category_counts.most_common()]
    body = [
        "# Agentic Workflow KB",
        "",
        "This is a generated, local Markdown knowledge base built from the SQLite source of truth. Raw WhatsApp exports stay outside the KB and remain read-only.",
        "",
        "## Current Decision",
        "",
        f"- {wikilink('Decision: Knowledge Base Approach')}",
        f"- Latest decision key: `{decision['decision_key'] if decision else 'NA'}`",
        "",
        "## Main Indexes",
        "",
        f"- {wikilink('Candidate Comparison')}",
        f"- {wikilink('Topic Co-occurrence Graph')}",
        f"- {wikilink('Graph, Memory, And Search Comparison')}",
        f"- {wikilink('Search Guide')}",
        f"- {wikilink('Backlink Index')}",
        f"- {wikilink('Unresolved Scrape Gaps')}",
        "",
        "## Corpus Snapshot",
        "",
        f"- Messages: {len(messages)}",
        f"- Links: {len(links)}",
        f"- KB candidates: {len(candidates)}",
        f"- Classification rows: {len(classifications)}",
        "",
        "## Topics",
        "",
    ]
    body.extend(f"- {wikilink(title)}" for title in topics)
    return Page(
        rel_path="index.md",
        title="Agentic Workflow KB",
        page_type="index",
        body="\n".join(body),
        decision_ids=[int(decision["id"])] if decision else [],
        tags=["index"],
    )


def page_for_decision(corpus: dict[str, Any]) -> Page:
    decisions = list(corpus["decisions"])
    latest = decisions[-1] if decisions else None
    decision_ids = [int(row["id"]) for row in decisions]
    body = [
        "# Decision: Knowledge Base Approach",
        "",
        f"Primary implementation: {wikilink('Candidate: Project-owned Obsidian-compatible Markdown wiki backed by SQLite')}.",
        "",
        "## Decision",
        "",
        clean_text(latest["decision_value"] if latest else "No decision recorded."),
        "",
        "## Rationale",
        "",
        clean_text(latest["rationale"] if latest else "No rationale recorded."),
        "",
        "## Related Pages",
        "",
        f"- {wikilink('Candidate Comparison')}",
        f"- {wikilink('Candidate: Karpathy LLM Wiki pattern')}",
        f"- {wikilink('Candidate: Obsidian-compatible local Markdown vault')}",
        f"- {wikilink('Candidate: SQLite FTS5 lexical search layer')}",
        f"- {wikilink('Search Guide')}",
        "",
        "## Decision History",
        "",
        "| ID | Key | Decided At | Supersedes |",
        "| ---: | --- | --- | ---: |",
    ]
    for row in decisions:
        supersedes = row["supersedes_decision_id"] if row["supersedes_decision_id"] is not None else ""
        body.append(f"| {row['id']} | `{row['decision_key']}` | {row['decided_at']} | {supersedes} |")
    return Page(
        rel_path="decisions/knowledge-base-approach.md",
        title="Decision: Knowledge Base Approach",
        page_type="decision",
        body="\n".join(body),
        candidate_ids=[1, 2, 3, 4],
        decision_ids=decision_ids,
        tags=["decision", "knowledge-base"],
    )


def page_for_candidate_comparison(corpus: dict[str, Any]) -> Page:
    candidates = corpus["candidates"]
    safety_by_candidate = corpus["safety_by_candidate"]
    body = [
        "# Candidate Comparison",
        "",
        "This page compares all KB candidates recorded in SQLite after the initial review and promptfoo-backed static safety pass.",
        "",
        "| Candidate | Type | Review Status | Safety Disposition | Risk | Fit | Source |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    source_messages: list[int] = []
    source_links: list[int] = []
    for row in candidates:
        safety = safety_by_candidate.get(row["candidate_name"])
        risk = safety["risk_rating"] if safety else "NA"
        fit = safety["fit_rating"] if safety else "NA"
        disposition = safety["final_disposition"] if safety else "NA"
        source = ""
        if row["message_id"]:
            source_messages.append(int(row["message_id"]))
            source = wikilink(message_title(int(row["message_id"])))
        if row["link_id"]:
            source_links.append(int(row["link_id"]))
        body.append(
            "| {candidate} | {ctype} | {status} | {disp} | {risk} | {fit} | {source} |".format(
                candidate=wikilink(candidate_title(row["candidate_name"])),
                ctype=row["candidate_type"] or "",
                status=row["review_status"] or "",
                disp=disposition or "",
                risk=risk or "",
                fit=fit or "",
                source=source,
            )
        )
    return Page(
        rel_path="comparisons/candidate-comparison.md",
        title="Candidate Comparison",
        page_type="comparison",
        body="\n".join(body),
        source_message_ids=source_messages,
        source_link_ids=source_links,
        candidate_ids=[int(row["id"]) for row in candidates],
        tags=["comparison", "knowledge-base"],
    )


def graph_relevant_candidates(corpus: dict[str, Any]) -> list[sqlite3.Row]:
    terms = ("graph", "semantic", "search", "memory", "retrieval", "wiki", "markdown", "fts")
    result: list[sqlite3.Row] = []
    for row in corpus["candidates"]:
        combined = " ".join(
            clean_text(row[key]).lower()
            for key in ("candidate_name", "candidate_type", "summary", "review_status", "limitations", "safety_notes")
        )
        if any(term in combined for term in terms):
            result.append(row)
    return result


def message_topic_sets(corpus: dict[str, Any]) -> dict[int, set[str]]:
    grouped: dict[int, set[str]] = defaultdict(set)
    for row in corpus["classifications"]:
        grouped[int(row["message_id"])].add(str(row["category"]))
    return grouped


def page_for_topic_graph(corpus: dict[str, Any]) -> Page:
    grouped = message_topic_sets(corpus)
    topic_messages: dict[str, set[int]] = defaultdict(set)
    edge_counts: Counter[tuple[str, str]] = Counter()
    for message_id, topics in grouped.items():
        ordered = sorted(topics)
        for topic in ordered:
            topic_messages[topic].add(message_id)
        for index, left in enumerate(ordered):
            for right in ordered[index + 1 :]:
                edge_counts[(left, right)] += 1

    body = [
        "# Topic Co-occurrence Graph",
        "",
        "This repo-owned graph view is generated from SQLite classification rows. It is an analysis artifact, not an external graph database.",
        "",
        "## Graph Model",
        "",
        "- Node: broad topic category.",
        "- Edge: one message classified into both topics.",
        "- Edge weight: count of messages sharing both topics.",
        "",
        "## Topic Nodes",
        "",
        "| Topic | Messages |",
        "| --- | ---: |",
    ]
    for topic, message_ids in sorted(topic_messages.items(), key=lambda item: (-len(item[1]), item[0])):
        body.append(f"| {wikilink(topic_title(topic))} | {len(message_ids)} |")

    body.extend(["", "## Strongest Edges", "", "| Topic A | Topic B | Shared Messages |", "| --- | --- | ---: |"])
    for (left, right), count in edge_counts.most_common(40):
        body.append(f"| {wikilink(topic_title(left))} | {wikilink(topic_title(right))} | {count} |")

    body.extend(["", "## Adjacency List", ""])
    for topic in sorted(topic_messages):
        neighbors = []
        for (left, right), count in edge_counts.items():
            if left == topic:
                neighbors.append((right, count))
            elif right == topic:
                neighbors.append((left, count))
        neighbors = sorted(neighbors, key=lambda item: (-item[1], item[0]))[:8]
        linked = ", ".join(f"{wikilink(topic_title(neighbor))} ({count})" for neighbor, count in neighbors)
        body.append(f"- {wikilink(topic_title(topic))}: {linked or 'No co-occurring topics.'}")

    return Page(
        rel_path="indexes/topic-cooccurrence-graph.md",
        title="Topic Co-occurrence Graph",
        page_type="graph_index",
        body="\n".join(body),
        source_message_ids=sorted(grouped),
        tags=["graph", "index", "topics"],
    )


def page_for_graph_memory_search_comparison(corpus: dict[str, Any]) -> Page:
    relevant = graph_relevant_candidates(corpus)
    candidate_ids = [int(row["id"]) for row in relevant]
    source_message_ids = [int(row["message_id"]) for row in relevant if row["message_id"]]
    source_link_ids = [int(row["link_id"]) for row in relevant if row["link_id"]]

    body = [
        "# Graph, Memory, And Search Comparison",
        "",
        "This comparison separates repo-owned artifacts that are already safe to generate from deferred external graph, memory, and semantic systems.",
        "",
        "## Venn-Style Capability Map",
        "",
        "| Capability | Markdown Wikilinks And Backlinks | Topic Co-occurrence Graph | SQLite FTS5 Lexical Search | Deferred Semantic Or Graph Backend |",
        "| --- | --- | --- | --- | --- |",
        "| Local-first source control | Yes | Yes | Yes | Depends on later safety review |",
        "| Human-readable knowledge base | Yes | Partial | Search results only | Depends on backend |",
        "| Relationship navigation | Yes, explicit wikilinks | Yes, inferred topic edges | No | Usually yes |",
        "| Fast keyword search | No | No | Yes | Usually yes |",
        "| Semantic equivalence search | No | No | No | Possible later |",
        "| Agent-safe baseline | Yes | Yes | Yes | Not approved as runtime dependency |",
        "| Current implementation status | Implemented | Implemented as generated page | Implemented | Deferred |",
        "",
        "## Current Project Choice",
        "",
        "- Keep SQLite as the source of truth.",
        "- Keep Markdown pages, wikilinks, backlinks, FTS5 search, and topic graph pages as repo-owned generated artifacts.",
        "- Treat external graph/vector/memory projects as comparison targets until a separate promptfoo-backed execution review approves a concrete integration.",
        "",
        "## Relevant Candidates",
        "",
        "| Candidate | Type | Review Status | Role In This Comparison |",
        "| --- | --- | --- | --- |",
    ]
    if not relevant:
        body.append("| NA | NA | NA | No graph/search/memory candidates recorded. |")
    for row in relevant:
        role = "current baseline" if str(row["review_status"]).startswith("recommended") else "deferred comparison target"
        body.append(
            f"| {wikilink(candidate_title(row['candidate_name']))} | `{row['candidate_type'] or 'NA'}` | `{row['review_status']}` | {role} |"
        )

    body.extend(
        [
            "",
            "## Related Generated Pages",
            "",
            f"- {wikilink('Candidate Comparison')}",
            f"- {wikilink('Topic Co-occurrence Graph')}",
            f"- {wikilink('Search Guide')}",
            f"- {wikilink('Backlink Index')}",
        ]
    )
    return Page(
        rel_path="comparisons/graph-memory-search-comparison.md",
        title="Graph, Memory, And Search Comparison",
        page_type="comparison",
        body="\n".join(body),
        source_message_ids=source_message_ids,
        source_link_ids=source_link_ids,
        candidate_ids=candidate_ids,
        tags=["comparison", "graph", "memory", "search"],
    )


def page_for_candidate(row: sqlite3.Row, corpus: dict[str, Any]) -> Page:
    safety = corpus["safety_by_candidate"].get(row["candidate_name"])
    evidence = json_loads(row["evidence"], {})
    local_evidence = evidence.get("local_evidence", []) if isinstance(evidence, dict) else []
    external_sources = evidence.get("external_sources_checked", []) if isinstance(evidence, dict) else []
    safety_sources = json_loads(safety["source_urls"], []) if safety else []
    source_message_ids = [int(row["message_id"])] if row["message_id"] else []
    source_link_ids = [int(row["link_id"])] if row["link_id"] else []
    source_link = wikilink(message_title(source_message_ids[0])) if source_message_ids else "NA"

    body = [
        f"# Candidate: {row['candidate_name']}",
        "",
        f"- Type: `{row['candidate_type'] or 'NA'}`",
        f"- Review status: `{row['review_status']}`",
        f"- Source message: {source_link}",
        f"- Promptfoo disposition: `{safety['final_disposition'] if safety else 'NA'}`",
        f"- Risk: `{safety['risk_rating'] if safety else 'NA'}`",
        f"- Fit: `{safety['fit_rating'] if safety else 'NA'}`",
        "",
        "## Summary",
        "",
        clean_text(row["summary"]),
        "",
        "## Limitations",
        "",
        clean_text(row["limitations"]),
        "",
        "## Safety Notes",
        "",
        clean_text(row["safety_notes"]),
        "",
        "## Promptfoo Review",
        "",
        clean_text(safety["rationale"] if safety else "No promptfoo safety row found."),
        "",
        "## Local Evidence",
        "",
    ]
    if local_evidence:
        body.extend(f"- {clean_text(item)}" for item in local_evidence)
    else:
        body.append("- No structured local evidence JSON was recorded.")
    body.extend(["", "## External Sources Checked", ""])
    combined_sources = list(dict.fromkeys([*external_sources, *safety_sources]))
    if combined_sources:
        body.extend(f"- {url}" for url in combined_sources)
    else:
        body.append("- None recorded.")
    body.extend(
        [
            "",
            "## Related",
            "",
            f"- {wikilink('Candidate Comparison')}",
            f"- {wikilink('Decision: Knowledge Base Approach')}",
        ]
    )
    return Page(
        rel_path=f"candidates/{slugify(row['candidate_name'])}.md",
        title=candidate_title(row["candidate_name"]),
        page_type="candidate",
        body="\n".join(body),
        source_message_ids=source_message_ids,
        source_link_ids=source_link_ids,
        candidate_ids=[int(row["id"])],
        tags=["candidate", "knowledge-base"],
    )


def page_for_topic(category: str, rows: list[sqlite3.Row], corpus: dict[str, Any]) -> Page:
    messages_by_id = {int(row["id"]): row for row in corpus["messages"]}
    links_by_message = corpus["links_by_message"]
    source_ids = [int(row["message_id"]) for row in rows]
    source_links: list[int] = []
    body = [
        f"# {topic_title(category)}",
        "",
        f"Messages classified under `{category}`.",
        "",
        f"- Message count: {len(set(source_ids))}",
        "",
        "## Representative Messages",
        "",
        "| Message | Confidence | Link Domains | Snippet |",
        "| --- | ---: | --- | --- |",
    ]
    seen: set[int] = set()
    for row in sorted(rows, key=lambda item: (float(item["confidence"] or 0), -int(item["message_id"])), reverse=True):
        message_id = int(row["message_id"])
        if message_id in seen:
            continue
        seen.add(message_id)
        message = messages_by_id[message_id]
        links = links_by_message.get(message_id, [])
        source_links.extend(int(link["id"]) for link in links)
        domains = ", ".join(sorted({domain(link["normalized_url"]) for link in links if link["normalized_url"]}))
        snippet = inline_text(message["raw_text"], 140).replace("|", "\\|")
        body.append(f"| {wikilink(message_title(message_id))} | {row['confidence'] or ''} | {domains} | {snippet} |")
        if len(seen) >= 30:
            break
    body.extend(["", "## Related Indexes", "", f"- {wikilink('Candidate Comparison')}", f"- {wikilink('Backlink Index')}"])
    return Page(
        rel_path=f"topics/{slugify(category)}.md",
        title=topic_title(category),
        page_type="topic",
        body="\n".join(body),
        source_message_ids=source_ids,
        source_link_ids=source_links,
        tags=["topic", category],
    )


def page_for_message(row: sqlite3.Row, corpus: dict[str, Any]) -> Page:
    message_id = int(row["id"])
    categories = corpus["categories_by_message"].get(message_id, [])
    tags = corpus["tags_by_message"].get(message_id, [])
    links = corpus["links_by_message"].get(message_id, [])
    latest = corpus["latest_attempts"]
    source_link_ids = [int(link["id"]) for link in links]
    body = [
        f"# {message_title(message_id)}",
        "",
        f"- Source group: `{row['source_group']}`",
        f"- Source file: `{row['source_file']}`",
        f"- Timestamp: `{row['timestamp_iso'] or row['message_timestamp'] or 'NA'}`",
        f"- Exact duplicate: `{bool(row['is_exact_duplicate'])}`",
        f"- Duplicate of: `{row['duplicate_of_message_id'] if row['duplicate_of_message_id'] else 'NA'}`",
        "",
        "## Categories",
        "",
    ]
    if categories:
        for cat in categories:
            body.append(f"- {wikilink(topic_title(cat['category']))} (`{cat['confidence']}`): {clean_text(cat['rationale'], 220)}")
    else:
        body.append("- No classification rows found.")
    body.extend(["", "## Tags", ""])
    body.extend(f"- `{tag}`" for tag in tags) if tags else body.append("- None recorded.")
    body.extend(["", "## Raw Text", "", fence(row["raw_text"])])
    body.extend(["", "## Links And Latest Extraction", ""])
    if not links:
        body.append("- No links recorded.")
    for link in links:
        link_id = int(link["id"])
        attempt = latest.get(link_id)
        status = attempt["status"] if attempt else "no_attempt"
        tool = attempt["tool"] if attempt else "NA"
        title = inline_text(attempt["title"], 120) if attempt else ""
        body.extend(
            [
                f"### {link_title(link_id)}",
                "",
                f"- URL: {link['normalized_url']}",
                f"- Domain: `{domain(link['normalized_url'])}`",
                f"- Latest status: `{status}`",
                f"- Latest tool: `{tool}`",
                f"- Latest title: {title or 'NA'}",
            ]
        )
        if attempt and attempt["error_type"]:
            body.append(f"- Error: `{attempt['error_type']}` {inline_text(attempt['error_message'], 220)}")
        if attempt and attempt["extracted_text"]:
            body.extend(["", "Extracted excerpt:", "", fence(attempt["extracted_text"][:MAX_EXCERPT_CHARS])])
    return Page(
        rel_path=f"sources/messages/message-{message_id:06d}.md",
        title=message_title(message_id),
        page_type="source_message",
        body="\n".join(body),
        source_message_ids=[message_id],
        source_link_ids=source_link_ids,
        tags=["source-message", *[cat["category"] for cat in categories]],
    )


def page_for_scrape_gaps(corpus: dict[str, Any]) -> Page:
    latest = corpus["latest_attempts"]
    links = corpus["links"]
    status_counts: Counter[str] = Counter()
    unresolved: list[sqlite3.Row] = []
    terminal_gaps: list[sqlite3.Row] = []
    source_link_ids: list[int] = []
    for link in links:
        attempt = latest.get(int(link["id"]))
        status = attempt["status"] if attempt else "no_attempt"
        status_counts[status] += 1
        if status in {"retry_pending", "no_attempt"}:
            unresolved.append(link)
            source_link_ids.append(int(link["id"]))
        elif status != "success":
            terminal_gaps.append(link)
            source_link_ids.append(int(link["id"]))
    body = [
        "# Unresolved Scrape Gaps",
        "",
        "This page records the current latest scrape state, unresolved links, and terminal scrape gaps.",
        "",
        "## Latest Status Counts",
        "",
        "| Status | Links |",
        "| --- | ---: |",
    ]
    for status, count in status_counts.most_common():
        body.append(f"| `{status}` | {count} |")
    body.extend(["", "## Retry Pending Or No Attempt", "", "| Link ID | Message | Domain | URL |", "| ---: | --- | --- | --- |"])
    if not unresolved:
        body.append("| NA | NA | NA | No latest `retry_pending` or `no_attempt` links. |")
    for link in unresolved[:200]:
        body.append(
            f"| {link['id']} | {wikilink(message_title(int(link['message_id'])))} | `{domain(link['normalized_url'])}` | {link['normalized_url']} |"
        )
    if len(unresolved) > 200:
        body.append(f"| ... | ... | ... | {len(unresolved) - 200} more unresolved links omitted from this page. |")
    body.extend(["", "## Terminal Non-Success Links", "", "| Link ID | Message | Domain | Latest Status | URL |", "| ---: | --- | --- | --- | --- |"])
    if not terminal_gaps:
        body.append("| NA | NA | NA | NA | No latest terminal non-success links. |")
    for link in terminal_gaps[:200]:
        attempt = latest.get(int(link["id"]))
        status = attempt["status"] if attempt else "no_attempt"
        body.append(
            f"| {link['id']} | {wikilink(message_title(int(link['message_id'])))} | `{domain(link['normalized_url'])}` | `{status}` | {link['normalized_url']} |"
        )
    if len(terminal_gaps) > 200:
        body.append(f"| ... | ... | ... | ... | {len(terminal_gaps) - 200} more terminal gaps omitted from this page. |")
    return Page(
        rel_path="indexes/unresolved-scrape-gaps.md",
        title="Unresolved Scrape Gaps",
        page_type="scrape_gaps",
        body="\n".join(body),
        source_link_ids=source_link_ids,
        tags=["scraping", "gaps"],
    )


def page_for_search_guide(decision_ids: list[int]) -> Page:
    body = """# Search Guide

Keyword search is backed by SQLite FTS5 over generated KB pages. Intent search is a repo-owned deterministic baseline that expands common project concepts before ranking generated KB pages; it does not use embeddings or an external vector backend.

## Commands

```powershell
uv run --no-cache python -B scripts\\build_kb.py search "Obsidian" --limit 10
uv run --no-cache python -B scripts\\build_kb.py search "knowledge base" --json
uv run --no-cache python -B scripts\\build_kb.py intent-search "agent memory graph" --limit 10
uv run --no-cache python -B scripts\\build_kb.py intent-search "safe browser automation" --json
uv run --no-cache python -B scripts\\build_kb.py validate
```

## Notes

- FTS5 is the reliable lexical baseline.
- Intent search is deterministic query expansion plus local page scoring; it is useful for semantic-ish exploration without new dependencies.
- Any external vector, graph, or embedding backend still needs a separate safety review before execution.

## Related

- [[Decision: Knowledge Base Approach]]
- [[Candidate: SQLite FTS5 lexical search layer]]
- [[Topic Co-occurrence Graph]]
- [[Graph, Memory, And Search Comparison]]
- [[Unresolved Scrape Gaps]]
"""
    return Page(
        rel_path="search.md",
        title="Search Guide",
        page_type="search_guide",
        body=body,
        decision_ids=decision_ids,
        tags=["search"],
    )


WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")


def extract_wikilinks(markdown: str) -> list[str]:
    return [match.group(1).strip() for match in WIKILINK_RE.finditer(markdown)]


def page_for_backlinks(pages: list[Page], title_to_path: dict[str, str], generated_at: str) -> Page:
    backlinks: dict[str, list[str]] = defaultdict(list)
    unresolved: dict[str, list[str]] = defaultdict(list)
    for page in pages:
        for label in extract_wikilinks(page.markdown(generated_at)):
            if label in title_to_path:
                backlinks[label].append(page.title)
            else:
                unresolved[label].append(page.title)
    body = [
        "# Backlink Index",
        "",
        "Generated from Obsidian-style wikilinks in the KB.",
        "",
        "## Backlinks",
        "",
    ]
    for target in sorted(title_to_path):
        sources = sorted(set(backlinks.get(target, [])))
        if not sources:
            continue
        body.append(f"### {wikilink(target)}")
        body.append("")
        body.extend(f"- {wikilink(source)}" for source in sources)
        body.append("")
    body.extend(["## Unresolved Wikilinks", ""])
    if unresolved:
        for label, sources in sorted(unresolved.items()):
            body.append(f"- `{label}` from {', '.join(sorted(set(sources)))}")
    else:
        body.append("- None.")
    return Page(
        rel_path="indexes/backlinks.md",
        title="Backlink Index",
        page_type="backlink_index",
        body="\n".join(body),
        tags=["backlinks", "index"],
    )


def build_pages(corpus: dict[str, Any], generated_at: str) -> list[Page]:
    pages: list[Page] = [
        page_for_index(corpus),
        page_for_decision(corpus),
        page_for_candidate_comparison(corpus),
        page_for_topic_graph(corpus),
        page_for_graph_memory_search_comparison(corpus),
    ]
    pages.extend(page_for_candidate(row, corpus) for row in corpus["candidates"])

    category_rows: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in corpus["classifications"]:
        category_rows[row["category"]].append(row)
    for category in sorted(category_rows):
        pages.append(page_for_topic(category, category_rows[category], corpus))

    pages.extend(page_for_message(row, corpus) for row in corpus["messages"])
    pages.append(page_for_scrape_gaps(corpus))
    pages.append(page_for_search_guide([int(row["id"]) for row in corpus["decisions"]]))

    title_to_path = {page.title: page.rel_path for page in pages}
    pages.append(page_for_backlinks(pages, title_to_path, generated_at))
    return pages


def ensure_kb_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS kb_pages (
            path TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            page_type TEXT NOT NULL,
            body TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            generated_at TEXT NOT NULL,
            generator TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS kb_page_links (
            id INTEGER PRIMARY KEY,
            from_path TEXT NOT NULL,
            from_title TEXT NOT NULL,
            link_label TEXT NOT NULL,
            to_path TEXT,
            unresolved INTEGER NOT NULL,
            generated_at TEXT NOT NULL,
            generator TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS kb_pages_fts
        USING fts5(path UNINDEXED, title, page_type UNINDEXED, body, tokenize='porter unicode61')
        """
    )


def write_pages(kb_dir: Path, pages: list[Page], generated_at: str) -> list[Path]:
    written: list[Path] = []
    for page in pages:
        target = kb_dir / page.rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page.markdown(generated_at), encoding="utf-8")
        written.append(target)
    manifest = {
        "generated_at": generated_at,
        "generator": GENERATOR,
        "generator_version": GENERATOR_VERSION,
        "pages": [page.rel_path for page in pages],
    }
    (kb_dir / ".kb_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return written


def index_pages(conn: sqlite3.Connection, pages: list[Page], generated_at: str) -> dict[str, Any]:
    ensure_kb_tables(conn)
    title_to_path = {page.title: page.rel_path for page in pages}
    conn.execute("DELETE FROM kb_pages WHERE generator = ?", (GENERATOR_VERSION,))
    conn.execute("DELETE FROM kb_page_links WHERE generator = ?", (GENERATOR_VERSION,))
    conn.execute("DELETE FROM kb_pages_fts")
    for page in pages:
        metadata = page.metadata(generated_at)
        conn.execute(
            """
            INSERT INTO kb_pages (path, title, page_type, body, metadata_json, generated_at, generator)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                page.rel_path,
                page.title,
                page.page_type,
                page.body,
                json.dumps(metadata, sort_keys=True, ensure_ascii=True),
                generated_at,
                GENERATOR_VERSION,
            ),
        )
        for label in extract_wikilinks(page.body):
            to_path = title_to_path.get(label)
            conn.execute(
                """
                INSERT INTO kb_page_links (
                    from_path, from_title, link_label, to_path, unresolved, generated_at, generator
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (page.rel_path, page.title, label, to_path, 0 if to_path else 1, generated_at, GENERATOR_VERSION),
            )
        rowid = conn.execute("SELECT rowid FROM kb_pages WHERE path = ?", (page.rel_path,)).fetchone()[0]
        conn.execute(
            "INSERT INTO kb_pages_fts(rowid, path, title, page_type, body) VALUES (?, ?, ?, ?, ?)",
            (rowid, page.rel_path, page.title, page.page_type, page.body),
        )
    conn.commit()
    unresolved_links = conn.execute(
        "SELECT COUNT(*) FROM kb_page_links WHERE generator = ? AND unresolved = 1", (GENERATOR_VERSION,)
    ).fetchone()[0]
    return {
        "indexed_pages": len(pages),
        "unresolved_wikilinks": int(unresolved_links),
    }


def generate(args: argparse.Namespace) -> dict[str, Any]:
    generated_at = utc_now()
    with connect(args.db) as conn:
        corpus = load_corpus(conn)
        pages = build_pages(corpus, generated_at)
        written = write_pages(args.kb_dir, pages, generated_at)
        index_summary = index_pages(conn, pages, generated_at)
    summary = {
        "generated_at": generated_at,
        "kb_dir": str(args.kb_dir),
        "pages_written": len(written),
        **index_summary,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def parse_frontmatter(markdown: str) -> dict[str, Any] | None:
    if not markdown.startswith("---\n"):
        return None
    end = markdown.find("\n---\n", 4)
    if end == -1:
        return None
    result: dict[str, Any] = {}
    for line in markdown[4:end].splitlines():
        if ": " not in line:
            continue
        key, raw = line.split(": ", 1)
        try:
            result[key] = json.loads(raw)
        except json.JSONDecodeError:
            result[key] = raw
    return result


def validate(args: argparse.Namespace) -> dict[str, Any]:
    md_files = sorted(path for path in args.kb_dir.rglob("*.md") if path.is_file())
    title_to_path: dict[str, Path] = {}
    missing_frontmatter: list[str] = []
    missing_provenance: list[str] = []
    generated_pages = 0
    for path in md_files:
        text = path.read_text(encoding="utf-8")
        metadata = parse_frontmatter(text)
        rel_path = path.relative_to(args.kb_dir).as_posix()
        if not metadata:
            missing_frontmatter.append(rel_path)
            continue
        title = metadata.get("title")
        if title:
            title_to_path[str(title)] = path
        if metadata.get("generated_by") == GENERATOR:
            generated_pages += 1
        page_type = metadata.get("page_type")
        exempt = {"index", "backlink_index", "search_guide"}
        has_source = any(
            metadata.get(key)
            for key in ("source_message_ids", "source_link_ids", "candidate_ids", "decision_ids")
        )
        if page_type not in exempt and not has_source:
            missing_provenance.append(rel_path)

    unresolved: list[dict[str, str]] = []
    for path in md_files:
        text = path.read_text(encoding="utf-8")
        metadata = parse_frontmatter(text) or {}
        source_title = str(metadata.get("title", path.name))
        for label in extract_wikilinks(text):
            if label not in title_to_path:
                unresolved.append({"from": source_title, "label": label})

    with connect(args.db) as conn:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        page_rows = conn.execute("SELECT COUNT(*) FROM kb_pages WHERE generator = ?", (GENERATOR_VERSION,)).fetchone()[0]
        fts_rows = conn.execute("SELECT COUNT(*) FROM kb_pages_fts").fetchone()[0]
        sample_hits = search_db(conn, "Obsidian", 5)
        sample_intent_hits = intent_search_db(conn, "agent memory graph", 5)

    result = {
        "validated_at": utc_now(),
        "integrity_check": integrity,
        "markdown_files": len(md_files),
        "generated_pages": generated_pages,
        "kb_pages_rows": int(page_rows),
        "fts_rows": int(fts_rows),
        "sample_search_hits": len(sample_hits),
        "sample_intent_search_hits": len(sample_intent_hits),
        "missing_frontmatter": missing_frontmatter,
        "missing_provenance": missing_provenance,
        "unresolved_wikilinks": unresolved[:50],
        "unresolved_wikilink_count": len(unresolved),
        "ok": (
            integrity == "ok"
            and not missing_frontmatter
            and not missing_provenance
            and not unresolved
            and int(page_rows) == generated_pages
            and int(fts_rows) == generated_pages
            and len(sample_hits) > 0
            and len(sample_intent_hits) > 0
        ),
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print_validation(result)
    if not result["ok"]:
        raise SystemExit(1)
    return result


def print_validation(result: dict[str, Any]) -> None:
    print(f"validated_at: {result['validated_at']}")
    print(f"integrity_check: {result['integrity_check']}")
    print(f"markdown_files: {result['markdown_files']}")
    print(f"generated_pages: {result['generated_pages']}")
    print(f"kb_pages_rows: {result['kb_pages_rows']}")
    print(f"fts_rows: {result['fts_rows']}")
    print(f"sample_search_hits: {result['sample_search_hits']}")
    print(f"sample_intent_search_hits: {result['sample_intent_search_hits']}")
    print(f"unresolved_wikilink_count: {result['unresolved_wikilink_count']}")
    print(f"ok: {result['ok']}")


def fts_query(query: str) -> str:
    terms = re.findall(r"[A-Za-z0-9_]+", query)
    if not terms:
        return '""'
    return " OR ".join(f'"{term}"' for term in terms)


def search_db(conn: sqlite3.Connection, query: str, limit: int) -> list[sqlite3.Row]:
    ensure_kb_tables(conn)
    match = fts_query(query)
    return fetch_rows(
        conn,
        """
        SELECT p.path, p.title, p.page_type,
               snippet(kb_pages_fts, 3, '[', ']', '...', 18) AS snippet
        FROM kb_pages_fts
        JOIN kb_pages p ON p.rowid = kb_pages_fts.rowid
        WHERE kb_pages_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (match, limit),
    )


def search(args: argparse.Namespace) -> list[dict[str, Any]]:
    with connect(args.db) as conn:
        rows = search_db(conn, args.query, args.limit)
    results = [dict(row) for row in rows]
    if args.json:
        print(json.dumps(results, indent=2, sort_keys=True))
    else:
        for row in results:
            print(f"{row['title']} [{row['page_type']}]")
            print(f"  {row['path']}")
            print(f"  {clean_text(row['snippet'], 300)}")
    return results


def intent_terms(query: str) -> tuple[set[str], set[str]]:
    base = {
        token.lower()
        for token in re.findall(r"[A-Za-z0-9_]+", query)
        if token.lower() not in INTENT_STOPWORDS and len(token) > 1
    }
    expanded = set(base)
    query_lower = query.lower()
    for key, aliases in INTENT_ALIASES.items():
        alias_tokens = {
            token.lower()
            for alias in aliases
            for token in re.findall(r"[A-Za-z0-9_]+", alias)
            if token.lower() not in INTENT_STOPWORDS and len(token) > 1
        }
        if key in base or key in query_lower or base.intersection(alias_tokens):
            expanded.add(key)
            expanded.update(alias_tokens)
    return base, expanded


def tokenize_for_intent(value: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[A-Za-z0-9_]+", value)
        if token.lower() not in INTENT_STOPWORDS and len(token) > 1
    }


def intent_snippet(title: str, body: str, terms: set[str], max_chars: int = 260) -> str:
    combined = clean_text(f"{title}\n{body}")
    lowered = combined.lower()
    positions = [lowered.find(term.lower()) for term in terms if lowered.find(term.lower()) >= 0]
    if not positions:
        return inline_text(combined, max_chars)
    start = max(0, min(positions) - 80)
    end = min(len(combined), start + max_chars)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(combined) else ""
    return prefix + inline_text(combined[start:end], max_chars) + suffix


def intent_search_db(conn: sqlite3.Connection, query: str, limit: int) -> list[dict[str, Any]]:
    ensure_kb_tables(conn)
    base_terms, expanded_terms = intent_terms(query)
    rows = fetch_rows(
        conn,
        """
        SELECT path, title, page_type, body, metadata_json
        FROM kb_pages
        WHERE generator = ?
        """,
        (GENERATOR_VERSION,),
    )
    scored: list[dict[str, Any]] = []
    query_lower = query.lower().strip()
    for row in rows:
        title = str(row["title"])
        body = str(row["body"])
        metadata = json_loads(row["metadata_json"], {})
        tags = set(str(tag).lower() for tag in metadata.get("tags", []) if tag)
        title_terms = tokenize_for_intent(title)
        body_terms = tokenize_for_intent(body)
        path_terms = tokenize_for_intent(str(row["path"]))
        matched_base = base_terms.intersection(title_terms | body_terms | path_terms | tags)
        matched_expanded = expanded_terms.intersection(title_terms | body_terms | path_terms | tags)
        if not matched_expanded and query_lower not in (title + "\n" + body).lower():
            continue
        score = 0.0
        score += 12.0 * len(base_terms.intersection(title_terms))
        score += 8.0 * len(base_terms.intersection(tags | path_terms))
        score += 5.0 * len(matched_base)
        score += 2.0 * len(expanded_terms.intersection(title_terms | tags))
        score += min(24.0, 0.6 * len(matched_expanded))
        if query_lower and query_lower in title.lower():
            score += 18.0
        if query_lower and query_lower in body.lower():
            score += 10.0
        if row["page_type"] in {"topic", "comparison", "candidate", "graph_index"}:
            score += 2.0
        scored.append(
            {
                "path": row["path"],
                "title": title,
                "page_type": row["page_type"],
                "score": round(score, 3),
                "matched_terms": sorted(matched_expanded)[:20],
                "snippet": intent_snippet(title, body, matched_expanded or expanded_terms),
            }
        )
    scored.sort(key=lambda item: (-float(item["score"]), item["title"], item["path"]))
    return scored[:limit]


def intent_search(args: argparse.Namespace) -> list[dict[str, Any]]:
    with connect(args.db) as conn:
        results = intent_search_db(conn, args.query, args.limit)
    if args.json:
        print(json.dumps(results, indent=2, sort_keys=True))
    else:
        for row in results:
            print(f"{row['title']} [{row['page_type']}] score={row['score']}")
            print(f"  {row['path']}")
            print(f"  terms: {', '.join(row['matched_terms'])}")
            print(f"  {clean_text(row['snippet'], 300)}")
    return results


def checkpoint(args: argparse.Namespace) -> dict[str, Any]:
    with connect(args.db) as conn:
        page_count = conn.execute("SELECT COUNT(*) FROM kb_pages WHERE generator = ?", (GENERATOR_VERSION,)).fetchone()[0]
        link_count = conn.execute("SELECT COUNT(*) FROM kb_page_links WHERE generator = ?", (GENERATOR_VERSION,)).fetchone()[0]
        unresolved = conn.execute(
            "SELECT COUNT(*) FROM kb_page_links WHERE generator = ? AND unresolved = 1", (GENERATOR_VERSION,)
        ).fetchone()[0]
        source_messages = conn.execute(
            "SELECT COUNT(*) FROM kb_pages WHERE generator = ? AND page_type = 'source_message'", (GENERATOR_VERSION,)
        ).fetchone()[0]
        candidate_pages = conn.execute(
            "SELECT COUNT(*) FROM kb_pages WHERE generator = ? AND page_type = 'candidate'", (GENERATOR_VERSION,)
        ).fetchone()[0]
        decision_pages = conn.execute(
            "SELECT COUNT(*) FROM kb_pages WHERE generator = ? AND page_type = 'decision'", (GENERATOR_VERSION,)
        ).fetchone()[0]
    payload = {
        "generated_at": utc_now(),
        "kb_pages": int(page_count),
        "kb_page_links": int(link_count),
        "unresolved_wikilinks": int(unresolved),
        "source_message_pages": int(source_messages),
        "candidate_pages": int(candidate_pages),
        "decision_pages": int(decision_pages),
    }
    body = f"""# Checkpoint 011: Baseline KB Implementation

Date: 2026-05-09

## Scope

- Implemented the project-owned SQLite-to-Markdown baseline KB locally from the orchestrator app.
- Generated Obsidian-compatible Markdown under `kb/`.
- Added SQLite-backed KB page tables, backlink rows, and FTS5 lexical search.
- Added validation for frontmatter, provenance, wikilinks, SQLite integrity, and FTS health.
- Raw WhatsApp exports and `imports/` remained read-only.
- No external GitHub project was installed, cloned, imported, executed, or adopted.

## Output

- KB pages indexed in SQLite: {payload['kb_pages']}
- Source message pages: {payload['source_message_pages']}
- Candidate pages: {payload['candidate_pages']}
- Decision pages: {payload['decision_pages']}
- Wikilink rows: {payload['kb_page_links']}
- Unresolved wikilinks: {payload['unresolved_wikilinks']}

## Commands

- `uv run --no-cache python -B scripts\\build_kb.py generate`
- `uv run --no-cache python -B scripts\\build_kb.py validate --json`
- `uv run --no-cache python -B scripts\\build_kb.py search "Obsidian" --limit 5`

## Next Work

Launch the next real CLI `/goal`: exhaustive unresolved-link scrape retry. The goal should use oEmbed first for X/Twitter, no Nitter, sandboxed Playwright only as fallback, and stop only when every link is captured or has a terminal logged reason.
"""
    args.report.write_text(body, encoding="utf-8")
    print(json.dumps({"checkpoint": str(args.report), **payload}, indent=2, sort_keys=True))
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build, validate, and search the generated Markdown KB.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--kb-dir", type=Path, default=DEFAULT_KB)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("generate", help="Generate Markdown pages and rebuild SQLite FTS index.")

    validate_parser = sub.add_parser("validate", help="Validate generated KB pages and search index.")
    validate_parser.add_argument("--json", action="store_true")

    search_parser = sub.add_parser("search", help="Search generated KB pages through SQLite FTS5.")
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=10)
    search_parser.add_argument("--json", action="store_true")

    intent_parser = sub.add_parser("intent-search", help="Search generated KB pages with deterministic intent expansion.")
    intent_parser.add_argument("query")
    intent_parser.add_argument("--limit", type=int, default=10)
    intent_parser.add_argument("--json", action="store_true")

    checkpoint_parser = sub.add_parser("checkpoint", help="Write the baseline KB implementation checkpoint.")
    checkpoint_parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "generate":
        generate(args)
    elif args.command == "validate":
        validate(args)
    elif args.command == "search":
        search(args)
    elif args.command == "intent-search":
        intent_search(args)
    elif args.command == "checkpoint":
        checkpoint(args)
    else:
        raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    try:
        main()
    except sqlite3.OperationalError as exc:
        print(f"SQLite error: {exc}", file=sys.stderr)
        raise
