from __future__ import annotations

import argparse
import html
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_DB = WORKSPACE / "data" / "db" / "agentic_workflow.db"
DEFAULT_HEARTBEAT = WORKSPACE / "learnings" / "goal-004-broad-classification.heartbeat.json"
DEFAULT_LOG_DIR = WORKSPACE / "learnings" / "goal-004-broad-classification"
DEFAULT_METHOD = "goal-004-rule-based-broad-v1"

X_DOMAINS = {"x.com", "twitter.com", "mobile.twitter.com"}
CATEGORY_SET = [
    "Tools",
    "Skills",
    "Methods_Workflows",
    "Memory",
    "Knowledge_Base",
    "Graphs_Knowledge_Graphs",
    "Prompts",
    "Verification_Loops",
    "Agents_Multiagent",
    "Context_Engineering",
    "Search_Retrieval",
    "Browser_Web_Automation",
    "Evaluation_Benchmarking",
    "Safety_Security",
    "Infrastructure_Devtools",
    "Models_Reasoning",
    "UX_Productivity",
    "Uncategorized",
]

LOW_CONFIDENCE_THRESHOLD = 0.45
MIN_CATEGORY_CONFIDENCE = 0.56


@dataclass(frozen=True)
class LinkEvidence:
    link_id: int
    normalized_url: str
    domain: str
    title: str
    description: str
    extracted_text: str
    tool: str


@dataclass(frozen=True)
class MessageEvidence:
    message_id: int
    source_group: str
    raw_text: str
    normalized_text: str
    is_exact_duplicate: bool
    duplicate_of_message_id: int | None
    tags: tuple[str, ...]
    links: tuple[LinkEvidence, ...]


@dataclass
class Hit:
    confidence: float
    reasons: list[str]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def local_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def clean_text(value: str | None, max_chars: int = 20_000) -> str:
    if not value:
        return ""
    normalized = html.unescape(value).replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized[:max_chars]


def lower_compact(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def truncate(value: str, max_chars: int) -> str:
    value = clean_text(value, max_chars * 2)
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 3].rstrip() + "..."


def safe_json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    tmp_path.write_text(serialized, encoding="utf-8")
    try:
        tmp_path.replace(path)
    except PermissionError:
        # Some Windows-backed workspaces reject atomic replacement of watched files.
        path.write_text(serialized, encoding="utf-8")
        try:
            tmp_path.unlink()
        except (FileNotFoundError, PermissionError):
            pass


def metadata_description(metadata_json: str | None) -> str:
    if not metadata_json:
        return ""
    try:
        metadata = json.loads(metadata_json)
    except json.JSONDecodeError:
        return ""
    fields: list[str] = []
    for key in (
        "og_title",
        "og_description",
        "twitter_title",
        "twitter_description",
        "description",
        "post_text",
    ):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            fields.append(value)
    cards = metadata.get("cards")
    if isinstance(cards, list):
        for card in cards[:3]:
            if isinstance(card, dict):
                text = card.get("text")
                if isinstance(text, str) and text.strip():
                    fields.append(text)
    return clean_text(" | ".join(fields), 5_000)


def latest_success_by_link(conn: sqlite3.Connection) -> dict[int, sqlite3.Row]:
    rows = conn.execute(
        """
        SELECT
          sa.*,
          l.normalized_url
        FROM scrape_attempts sa
        JOIN links l ON l.id = sa.link_id
        WHERE sa.status = 'success'
        ORDER BY sa.link_id, sa.attempted_at DESC, sa.id DESC
        """
    ).fetchall()
    latest: dict[int, sqlite3.Row] = {}
    for row in rows:
        link_id = int(row["link_id"])
        if link_id in latest:
            continue
        host = domain(row["normalized_url"])
        if host in X_DOMAINS and row["tool"] != "x_oembed":
            continue
        if host not in X_DOMAINS and row["tool"] == "x_oembed":
            continue
        latest[link_id] = row
    return latest


def load_messages(conn: sqlite3.Connection) -> list[MessageEvidence]:
    latest = latest_success_by_link(conn)
    link_rows: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for row in conn.execute("SELECT * FROM links ORDER BY id"):
        link_rows[int(row["message_id"])].append(row)

    tags_by_message: dict[int, list[str]] = defaultdict(list)
    for row in conn.execute("SELECT message_id, tag FROM message_tags ORDER BY id"):
        tags_by_message[int(row["message_id"])].append(row["tag"])

    messages: list[MessageEvidence] = []
    for row in conn.execute("SELECT * FROM messages ORDER BY id"):
        links: list[LinkEvidence] = []
        for link in link_rows.get(int(row["id"]), []):
            attempt = latest.get(int(link["id"]))
            title = clean_text(attempt["title"] if attempt else "", 2_000)
            description = metadata_description(attempt["metadata_json"] if attempt else None)
            extracted = clean_text(attempt["extracted_text"] if attempt else "", 20_000)
            tool = str(attempt["tool"]) if attempt else ""
            links.append(
                LinkEvidence(
                    link_id=int(link["id"]),
                    normalized_url=link["normalized_url"],
                    domain=domain(link["normalized_url"]),
                    title=title,
                    description=description,
                    extracted_text=extracted,
                    tool=tool,
                )
            )
        messages.append(
            MessageEvidence(
                message_id=int(row["id"]),
                source_group=row["source_group"],
                raw_text=row["raw_text"],
                normalized_text=row["normalized_text"],
                is_exact_duplicate=bool(row["is_exact_duplicate"]),
                duplicate_of_message_id=(
                    int(row["duplicate_of_message_id"]) if row["duplicate_of_message_id"] is not None else None
                ),
                tags=tuple(tags_by_message.get(int(row["id"]), [])),
                links=tuple(links),
            )
        )
    return messages


TAG_RULES: list[tuple[tuple[str, ...], tuple[tuple[str, float, str], ...]]] = [
    (("claude_code_tag", "claude code", "codex_tag", "codex"), (("Tools", 0.78, "coding-assistant tag"), ("Infrastructure_Devtools", 0.78, "coding-assistant tag"))),
    (("claude code tips and tricks",), (("UX_Productivity", 0.72, "tips-and-tricks tag"), ("Methods_Workflows", 0.68, "tips-and-tricks tag"))),
    (("openclaw_tag", "openclaw", "openclaw setup"), (("Agents_Multiagent", 0.74, "OpenClaw tag"), ("Infrastructure_Devtools", 0.70, "OpenClaw tag"))),
    (("openclaw memory",), (("Memory", 0.86, "OpenClaw Memory tag"), ("Knowledge_Base", 0.70, "OpenClaw Memory tag"))),
    (("claude_skill_tag", "add_to_skills"), (("Skills", 0.86, "skill tag"), ("Tools", 0.66, "skill tag"))),
    (("agentic_systems_tag", "agentic systems", "add_to_agentic_systems", "ai agents", "agents"), (("Agents_Multiagent", 0.82, "agentic-systems tag"), ("Methods_Workflows", 0.68, "agentic-systems tag"))),
    (("prompt engineering", "prompt engineering bookmarks", "add_to_prompt_engineering"), (("Prompts", 0.86, "prompt-engineering tag"), ("Methods_Workflows", 0.68, "prompt-engineering tag"))),
    (("super llm", "super llms", "add_to_super_llm"), (("Models_Reasoning", 0.82, "Super LLM tag"),)),
    (("project ideas",), (("Methods_Workflows", 0.64, "Project Ideas tag"),)),
    (("software",), (("Infrastructure_Devtools", 0.62, "Software tag"), ("Tools", 0.60, "Software tag"))),
    (("ml articles", "ai research", "ai", "ml books"), (("Models_Reasoning", 0.72, "AI/ML tag"), ("Search_Retrieval", 0.58, "research tag"))),
    (("exotic architectures", "rl environments"), (("Models_Reasoning", 0.72, "architecture/RL tag"), ("Evaluation_Benchmarking", 0.58, "RL tag"))),
    (("verification_loop_tag",), (("Verification_Loops", 0.90, "verification-loop tag"), ("Evaluation_Benchmarking", 0.70, "verification-loop tag"))),
    (("datasets",), (("Search_Retrieval", 0.66, "dataset tag"), ("Evaluation_Benchmarking", 0.58, "dataset tag"))),
    (("study techniques",), (("UX_Productivity", 0.64, "study-techniques tag"), ("Methods_Workflows", 0.58, "study-techniques tag"))),
    (("business ideas", "trading ideas", "sports ai", "polymarket"), (("Methods_Workflows", 0.58, "domain-idea tag"), ("Models_Reasoning", 0.56, "AI-domain tag"))),
]


CATEGORY_TERMS: dict[str, tuple[str, ...]] = {
    "Tools": (
        " tool",
        " tools",
        "toolkit",
        "app",
        "platform",
        "plugin",
        "extension",
        "framework",
        "library",
        "package",
        "open source",
        "open-source",
        "repo",
        "github",
        "mcp server",
        "cli",
        "sdk",
        "install",
        "npm ",
        "brew install",
        "cursor",
        "browser-use",
    ),
    "Skills": (
        " skill",
        " skills",
        "skill system",
        "claude skills",
        "commands",
        "slash command",
        "capability",
        "copy-paste templates",
    ),
    "Methods_Workflows": (
        "workflow",
        "workflows",
        "method",
        "methods",
        "recipe",
        "recipes",
        "setup",
        "best practices",
        "howto",
        "how to",
        "structured",
        "architecture",
        "harness engineering",
        "agent-first",
        "pipeline",
        "orchestration",
        "orchestrate",
        "runbook",
        "quick wins",
        "to do",
        "project ideas",
        "brainstorm",
        "plan, review, fix",
        "worktrees",
        "delegate",
        "delegation",
    ),
    "Memory": (
        "memory",
        "remember",
        "persistent",
        "persistence",
        "retention",
        "second brain",
        "context database",
        "self-maintains",
        "self-maintaining",
        "mempalace",
        "gbrain",
        "obsidian vault",
        "markdown vault",
        "personal agent that learns",
    ),
    "Knowledge_Base": (
        "knowledge base",
        "knowledge bases",
        "wiki",
        "llm wiki",
        "obsidian",
        "vault",
        "notebook",
        "notes",
        "note-taking",
        "notetaking",
        "markdown files",
        "research papers",
        "open notebook",
        "notebooklm",
        "personal knowledge",
        "knowledge companion",
    ),
    "Graphs_Knowledge_Graphs": (
        "knowledge graph",
        "knowledge graphs",
        "code graph",
        "code graphs",
        "graph traversal",
        "wikilinks",
        "queryable knowledge graph",
        "graphify",
        "graph database",
    ),
    "Prompts": (
        "prompt",
        "prompts",
        "prompting",
        "prompt engineering",
        "instructions",
        "system prompt",
        "dspy",
        "signatures",
        "programming - not prompting",
        "prompt strings",
        "prompt-guidance",
        "custom instructions",
    ),
    "Verification_Loops": (
        "verification loop",
        "verification loops",
        "self verification",
        "verify",
        "verifier",
        "verifiers",
        "validated",
        "validation",
        "health checks",
        "reviewer",
        "reviewers",
        "critic",
        "judge",
        "auto-research",
        "autoresearch",
        "autoreason",
    ),
    "Agents_Multiagent": (
        "agent",
        "agents",
        "agentic",
        "multi-agent",
        "multi agent",
        "multiagent",
        "swarm",
        "managed agents",
        "subagent",
        "subagents",
        "autonomous",
        "orchestrate",
        "orchestration",
        "team",
        "teammates",
        "parallel execution",
        "planner",
        "coders",
        "verifiers",
        "openclaw",
    ),
    "Context_Engineering": (
        "context engineering",
        "context window",
        "long context",
        "limitless context",
        "context database",
        "context delivery",
        "context management",
        "repo context",
        "tokens",
        "token limit",
        "token limits",
        "compaction",
        "semantic compression",
        "hierarchical context",
    ),
    "Search_Retrieval": (
        "search",
        "retrieval",
        "retrieve",
        "retriever",
        "rag",
        "index",
        "indexes",
        "indexing",
        "query",
        "queryable",
        "deep research",
        "researcher",
        "research platform",
        "code search",
        "find all",
        "web search",
        "datasets",
    ),
    "Browser_Web_Automation": (
        "browser",
        "web automation",
        "computer use",
        "click",
        "click through",
        "playwright",
        "chromium",
        "browser-use",
        "web browsing",
        "sandboxed agents",
        "linux os in the browser",
        "ui test",
        "test what it built",
    ),
    "Evaluation_Benchmarking": (
        "benchmark",
        "benchmarks",
        "eval",
        "evals",
        "evaluation",
        "score",
        "metric",
        "metrics",
        "arc-agi",
        "swe-bench",
        "reward",
        "rewards",
        "rl",
        "reinforcement learning",
        "grader",
        "test suite",
        "verifier",
        "verifiers",
    ),
    "Safety_Security": (
        "safety",
        "security",
        "secure",
        "sandbox",
        "sandboxed",
        "prompt injection",
        "jailbreak",
        "credentials",
        "vulnerability",
        "attack",
        "leaked source code",
        "source code has been leaked",
        "permission",
        "isolation",
    ),
    "Infrastructure_Devtools": (
        "github",
        "git ",
        "worktree",
        "worktrees",
        "cli",
        "mcp",
        "hook",
        "hooks",
        "codex",
        "claude code",
        "cursor",
        "codebase",
        "repo",
        "repository",
        "ide",
        "sdk",
        "api docs",
        "developer",
        "devtools",
        "terminal",
        "docker",
        "filesystem",
        "rust",
        "npm",
        "brew",
    ),
    "Models_Reasoning": (
        "model",
        "models",
        "llm",
        "llms",
        "reasoning",
        "reason",
        "gpt",
        "haiku",
        "conductor model",
        "hierarchical",
        "architecture",
        "architectures",
        "self attention",
        "attention",
        "transformer",
        "neural",
        "rl",
        "reinforcement learning",
        "natural language encoders",
        "super llm",
    ),
    "UX_Productivity": (
        "productivity",
        "ux",
        "ui",
        "frontend",
        "design",
        "craft",
        "faster",
        "speed",
        "tokens",
        "save",
        "efficient",
        "learning",
        "personalized learning",
        "study",
        "quick wins",
        "tips and tricks",
        "take control of your learning",
    ),
}


DOMAIN_RULES: dict[str, tuple[tuple[str, float, str], ...]] = {
    "github.com": (("Tools", 0.58, "GitHub repository domain"), ("Infrastructure_Devtools", 0.60, "GitHub repository domain")),
    "arxiv.org": (("Models_Reasoning", 0.62, "arXiv research domain"),),
    "openai.com": (("Models_Reasoning", 0.58, "OpenAI domain"), ("Methods_Workflows", 0.56, "OpenAI domain")),
    "cookbook.openai.com": (("Methods_Workflows", 0.64, "OpenAI Cookbook domain"), ("Prompts", 0.58, "OpenAI Cookbook domain")),
    "developers.openai.com": (("Infrastructure_Devtools", 0.62, "OpenAI developer docs domain"), ("Prompts", 0.58, "OpenAI developer docs domain")),
    "anthropic.com": (("Agents_Multiagent", 0.58, "Anthropic agent engineering domain"), ("Methods_Workflows", 0.58, "Anthropic agent engineering domain")),
    "cursor.com": (("Infrastructure_Devtools", 0.64, "Cursor domain"), ("Tools", 0.60, "Cursor domain")),
    "dspy.ai": (("Prompts", 0.70, "DSPy domain"), ("Methods_Workflows", 0.62, "DSPy domain")),
}


SYSTEM_MESSAGE_PATTERNS = (
    "messages and calls are end-to-end encrypted",
    "you created this group",
    " was added",
    "you pinned a message",
)


def add_hit(hits: dict[str, Hit], category: str, confidence: float, reason: str) -> None:
    if category not in CATEGORY_SET:
        raise ValueError(f"Unknown category: {category}")
    current = hits.get(category)
    if not current:
        hits[category] = Hit(confidence=confidence, reasons=[reason])
        return
    current.confidence = max(current.confidence, confidence)
    if reason not in current.reasons:
        current.reasons.append(reason)


def evidence_text(message: MessageEvidence) -> tuple[str, str]:
    parts: list[str] = [
        message.raw_text,
        " ".join(message.tags),
        " ".join(link.normalized_url for link in message.links),
        " ".join(link.domain for link in message.links),
    ]
    snippet_parts: list[str] = [message.raw_text]
    for link in message.links:
        parts.extend([link.title, link.description])
        snippet_parts.extend([link.title, link.description])
        if link.tool == "x_oembed":
            parts.append(link.extracted_text)
            snippet_parts.append(link.extracted_text)
        elif link.domain != "github.com":
            parts.append(truncate(link.extracted_text, 3_000))
    combined = clean_text(" | ".join(part for part in parts if part), 60_000)
    snippet_source = clean_text(" | ".join(part for part in snippet_parts if part), 5_000)
    return combined, snippet_source


def matched_phrase(text_lower: str, terms: tuple[str, ...]) -> str | None:
    for term in sorted(terms, key=len, reverse=True):
        phrase = term.strip().lower()
        if not phrase:
            continue
        left = r"(?<![a-z0-9])" if phrase[0].isalnum() else ""
        right = r"(?![a-z0-9])" if phrase[-1].isalnum() else ""
        if re.search(left + re.escape(phrase) + right, text_lower):
            return phrase
    return None


def tag_hits(message: MessageEvidence, hits: dict[str, Hit]) -> None:
    tag_text = lower_compact(" | ".join(message.tags))
    if not tag_text:
        return
    for needles, categories in TAG_RULES:
        if any(needle in tag_text for needle in needles):
            for category, confidence, reason in categories:
                add_hit(hits, category, confidence, reason)


def domain_hits(message: MessageEvidence, hits: dict[str, Hit]) -> None:
    for link in message.links:
        host = link.domain
        rules = DOMAIN_RULES.get(host)
        if not rules:
            continue
        if host in X_DOMAINS and not (link.title or link.description or link.extracted_text):
            continue
        for category, confidence, reason in rules:
            add_hit(hits, category, confidence, reason)


def term_hits(text_lower: str, hits: dict[str, Hit]) -> None:
    for category, terms in CATEGORY_TERMS.items():
        phrase = matched_phrase(text_lower, terms)
        if not phrase:
            continue
        confidence = 0.68
        if category in {"Memory", "Knowledge_Base", "Graphs_Knowledge_Graphs", "Verification_Loops", "Browser_Web_Automation"}:
            confidence = 0.74
        if category in {"Prompts", "Agents_Multiagent", "Models_Reasoning"}:
            confidence = 0.72
        add_hit(hits, category, confidence, f"phrase '{phrase}'")


def is_system_or_empty(message: MessageEvidence, text_lower: str) -> bool:
    if any(pattern in text_lower for pattern in SYSTEM_MESSAGE_PATTERNS):
        return True
    without_urls = re.sub(r"https?://\S+", "", message.raw_text).strip()
    return not without_urls and not message.tags and not any(
        link.title or link.description or link.extracted_text for link in message.links
    )


def rationale_for(message: MessageEvidence, category: str, hit: Hit, snippet_source: str) -> str:
    reasons = "; ".join(hit.reasons[:3])
    evidence = truncate(snippet_source, 150)
    prefix = ""
    if message.is_exact_duplicate and message.duplicate_of_message_id is not None:
        prefix = f"Exact duplicate of message {message.duplicate_of_message_id}. "
    if category == "Uncategorized":
        return truncate(f"{prefix}{reasons}", 260)
    return truncate(f"{prefix}Matched {reasons}. Evidence: {evidence}", 320)


def classify_message(message: MessageEvidence) -> list[tuple[str, float, str]]:
    combined, snippet_source = evidence_text(message)
    text_lower = lower_compact(combined)
    hits: dict[str, Hit] = {}

    tag_hits(message, hits)
    domain_hits(message, hits)
    term_hits(text_lower, hits)

    # Give messages with several independent weak signals a small confidence lift.
    for hit in hits.values():
        if len(hit.reasons) > 1:
            hit.confidence = min(0.94, hit.confidence + min(0.12, 0.03 * (len(hit.reasons) - 1)))

    chosen = {
        category: hit
        for category, hit in hits.items()
        if category != "Uncategorized" and hit.confidence >= MIN_CATEGORY_CONFIDENCE
    }

    if not chosen:
        if is_system_or_empty(message, text_lower):
            reason = "System, pinned, empty, or URL-only message without parsed topical content."
            confidence = 0.18
        else:
            reason = "No taxonomy signal beyond available message/link evidence."
            confidence = 0.34
        chosen["Uncategorized"] = Hit(confidence=confidence, reasons=[reason])

    return [
        (category, round(hit.confidence, 2), rationale_for(message, category, hit, snippet_source))
        for category, hit in sorted(chosen.items(), key=lambda item: CATEGORY_SET.index(item[0]))
    ]


def database_counts(conn: sqlite3.Connection, method: str) -> dict[str, Any]:
    total_messages = int(conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0])
    non_duplicate_messages = int(conn.execute("SELECT COUNT(*) FROM messages WHERE is_exact_duplicate = 0").fetchone()[0])
    duplicate_messages = total_messages - non_duplicate_messages
    classification_rows = int(
        conn.execute("SELECT COUNT(*) FROM classifications WHERE model_or_method = ?", (method,)).fetchone()[0]
    )
    classified_messages = int(
        conn.execute(
            "SELECT COUNT(DISTINCT message_id) FROM classifications WHERE model_or_method = ?",
            (method,),
        ).fetchone()[0]
    )
    classified_non_duplicates = int(
        conn.execute(
            """
            SELECT COUNT(DISTINCT c.message_id)
            FROM classifications c
            JOIN messages m ON m.id = c.message_id
            WHERE c.model_or_method = ? AND m.is_exact_duplicate = 0
            """,
            (method,),
        ).fetchone()[0]
    )
    unclassified_non_duplicates = int(
        conn.execute(
            """
            SELECT COUNT(*)
            FROM messages m
            WHERE m.is_exact_duplicate = 0
              AND NOT EXISTS (
                SELECT 1
                FROM classifications c
                WHERE c.message_id = m.id AND c.model_or_method = ?
              )
            """,
            (method,),
        ).fetchone()[0]
    )
    return {
        "total_messages": total_messages,
        "non_duplicate_messages": non_duplicate_messages,
        "duplicate_messages": duplicate_messages,
        "classification_rows": classification_rows,
        "classified_messages": classified_messages,
        "classified_non_duplicate_messages": classified_non_duplicates,
        "unclassified_non_duplicate_messages": unclassified_non_duplicates,
    }


def write_heartbeat(
    heartbeat_path: Path,
    *,
    status: str,
    phase: str,
    started_at: str,
    method: str,
    command: str,
    counts: dict[str, Any],
    category_counts: Counter[str] | None = None,
    notes: list[str] | None = None,
) -> None:
    progress = {
        "classified_non_duplicate_messages": counts.get("classified_non_duplicate_messages", 0),
        "unclassified_non_duplicate_messages": counts.get("unclassified_non_duplicate_messages", 0),
        "classification_rows": counts.get("classification_rows", 0),
    }
    payload: dict[str, Any] = {
        "goal_id": "goal-004-broad-classification",
        "status": status,
        "phase": phase,
        "started_at": started_at,
        "last_updated_at": local_now(),
        "method": method,
        "commands_run": [command],
        "baseline": {
            "messages": counts.get("total_messages", 0),
            "non_duplicate_messages": counts.get("non_duplicate_messages", 0),
            "duplicate_messages": counts.get("duplicate_messages", 0),
        },
        "progress": progress,
        "category_counts": dict(sorted((category_counts or Counter()).items())),
        "notes": notes or [],
    }
    safe_json_dump(heartbeat_path, payload)


def build_summary(
    *,
    started_at: str,
    finished_at: str,
    method: str,
    command: str,
    counts: dict[str, Any],
    category_counts: Counter[str],
    low_confidence_rows: int,
    low_confidence_messages: int,
    examples: dict[str, list[dict[str, Any]]],
    duplicate_classified_messages: int,
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "goal_id": "goal-004-broad-classification",
        "started_at": started_at,
        "finished_at": finished_at,
        "command": command,
        "method": method,
        "dry_run": dry_run,
        "total_messages": counts["total_messages"],
        "non_duplicate_messages": counts["non_duplicate_messages"],
        "duplicate_messages": counts["duplicate_messages"],
        "classified_messages": counts["classified_messages"],
        "classified_non_duplicate_messages": counts["classified_non_duplicate_messages"],
        "unclassified_non_duplicate_messages": counts["unclassified_non_duplicate_messages"],
        "classification_rows": counts["classification_rows"],
        "duplicate_classified_messages": duplicate_classified_messages,
        "duplicate_handling": "Duplicates receive their own classification rows; duplicate rationales name the original message when duplicate_of_message_id is present.",
        "category_counts": dict(sorted(category_counts.items())),
        "low_confidence_rows": low_confidence_rows,
        "low_confidence_messages": low_confidence_messages,
        "low_confidence_threshold": LOW_CONFIDENCE_THRESHOLD,
        "representative_category_examples": examples,
        "additional_categories_added": [],
        "unresolved_questions": [
            "URL-only X/Twitter messages without parsed oEmbed content and without tags were classified as low-confidence Uncategorized because no topical evidence was available in SQLite."
        ],
    }


def classify_items(args: argparse.Namespace) -> dict[str, Any]:
    started_at = local_now()
    command = "uv run --no-cache python -B " + " ".join(sys.argv)
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = PERSIST")

    messages = load_messages(conn)
    total_non_duplicates = sum(1 for message in messages if not message.is_exact_duplicate)
    total_duplicates = len(messages) - total_non_duplicates
    initial_counts = {
        "total_messages": len(messages),
        "non_duplicate_messages": total_non_duplicates,
        "duplicate_messages": total_duplicates,
        "classified_messages": 0,
        "classified_non_duplicate_messages": 0,
        "unclassified_non_duplicate_messages": total_non_duplicates,
        "classification_rows": 0,
    }
    write_heartbeat(
        args.heartbeat,
        status="running",
        phase="loaded_messages",
        started_at=started_at,
        method=args.method,
        command=command,
        counts=initial_counts,
        notes=[
            "Loaded messages, tags, links, latest successful non-X scrapes, and latest successful x_oembed rows from SQLite.",
            "No scraping or browser automation performed.",
        ],
    )

    assignments: dict[int, list[tuple[str, float, str]]] = {}
    category_counts: Counter[str] = Counter()
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    low_confidence_rows = 0
    low_confidence_message_ids: set[int] = set()

    if not args.dry_run:
        conn.execute("DELETE FROM classifications WHERE model_or_method = ?", (args.method,))
        conn.commit()

    classified_at = utc_now()
    inserted_rows = 0
    classified_non_duplicates = 0

    for index, message in enumerate(messages, start=1):
        rows = classify_message(message)
        assignments[message.message_id] = rows
        if not message.is_exact_duplicate:
            classified_non_duplicates += 1

        for category, confidence, rationale in rows:
            category_counts[category] += 1
            if confidence < LOW_CONFIDENCE_THRESHOLD:
                low_confidence_rows += 1
                low_confidence_message_ids.add(message.message_id)
            if len(examples[category]) < 3:
                examples[category].append(
                    {
                        "message_id": message.message_id,
                        "confidence": confidence,
                        "rationale": rationale,
                        "snippet": truncate(message.raw_text, 220),
                    }
                )
            if not args.dry_run:
                conn.execute(
                    """
                    INSERT INTO classifications (
                      message_id,
                      category,
                      confidence,
                      rationale,
                      classified_at,
                      model_or_method
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (message.message_id, category, confidence, rationale, classified_at, args.method),
                )
            inserted_rows += 1

        if not args.dry_run and (index % args.batch_size == 0 or index == len(messages)):
            conn.commit()
        if index % args.batch_size == 0 or index == len(messages):
            counts = {
                "total_messages": len(messages),
                "non_duplicate_messages": total_non_duplicates,
                "duplicate_messages": total_duplicates,
                "classified_messages": index,
                "classified_non_duplicate_messages": classified_non_duplicates,
                "unclassified_non_duplicate_messages": total_non_duplicates - classified_non_duplicates,
                "classification_rows": inserted_rows,
            }
            write_heartbeat(
                args.heartbeat,
                status="running",
                phase=f"classified_{index}_of_{len(messages)}",
                started_at=started_at,
                method=args.method,
                command=command,
                counts=counts,
                category_counts=category_counts,
                notes=[
                    "Classification is rule-based and evidence-grounded from SQLite-resident source fields.",
                    "Duplicates receive their own rows with duplicate status in rationale.",
                ],
            )

    if args.dry_run:
        counts = {
            "total_messages": len(messages),
            "non_duplicate_messages": total_non_duplicates,
            "duplicate_messages": total_duplicates,
            "classified_messages": len(messages),
            "classified_non_duplicate_messages": total_non_duplicates,
            "unclassified_non_duplicate_messages": 0,
            "classification_rows": inserted_rows,
        }
        duplicate_classified_messages = total_duplicates
    else:
        counts = database_counts(conn, args.method)
        duplicate_classified_messages = int(
            conn.execute(
                """
                SELECT COUNT(DISTINCT c.message_id)
                FROM classifications c
                JOIN messages m ON m.id = c.message_id
                WHERE c.model_or_method = ? AND m.is_exact_duplicate = 1
                """,
                (args.method,),
            ).fetchone()[0]
        )

    finished_at = local_now()
    summary = build_summary(
        started_at=started_at,
        finished_at=finished_at,
        method=args.method,
        command=command,
        counts=counts,
        category_counts=category_counts,
        low_confidence_rows=low_confidence_rows,
        low_confidence_messages=len(low_confidence_message_ids),
        examples=dict(examples),
        duplicate_classified_messages=duplicate_classified_messages,
        dry_run=args.dry_run,
    )
    safe_json_dump(args.log_dir / "summary.json", summary)
    write_heartbeat(
        args.heartbeat,
        status="complete" if counts["unclassified_non_duplicate_messages"] == 0 else "blocked",
        phase="classification_complete",
        started_at=started_at,
        method=args.method,
        command=command,
        counts=counts,
        category_counts=category_counts,
        notes=[
            f"Summary written to {args.log_dir / 'summary.json'}.",
            "No new categories were added beyond docs/classification.md.",
        ],
    )
    conn.close()
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify imported WhatsApp messages into broad categories.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--method", default=DEFAULT_METHOD)
    parser.add_argument("--heartbeat", type=Path, default=DEFAULT_HEARTBEAT)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true", help="Classify and write logs without mutating SQLite.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be positive")
    summary = classify_items(args)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
