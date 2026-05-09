from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path("data/db/agentic_workflow.db")
CHECKPOINT_PATH = Path("learnings/checkpoint-007-kb-candidate-review.md")
HEARTBEAT_PATH = Path("learnings/goal-005-kb-candidate-review.heartbeat.json")

DECISION_KEY = "knowledge_base_approach_initial"
METHOD = "goal-005-kb-candidate-review-v1"

SOURCE_URLS = [
    "https://gist.github.com/karpathy?direction=desc&sort=updated",
    "https://obsidian.md/help/data-storage",
    "https://obsidian.md/help/links",
    "https://obsidian.md/help/plugins/backlinks",
    "https://obsidian.md/help/plugins/graph",
    "https://www.sqlite.org/fts5.html",
    "https://github.com/agenticnotetaking/arscontexta",
    "https://github.com/agno-agi/pal",
    "https://github.com/nashsu/llm_wiki",
    "https://github.com/AgriciDaniel/claude-obsidian",
    "https://github.com/topoteretes/cognee",
    "https://github.com/Lum1104/Understand-Anything",
    "https://github.com/cytostack/openwolf",
    "https://openwolf.com/",
    "https://github.com/kepano/obsidian-skills",
    "https://github.com/safishamsi/graphify",
    "https://github.com/cocoindex-io/cocoindex-code",
]

COMPARISON_CRITERIA = [
    "Factual alignment with WhatsApp/SQLite KB evidence",
    "Readable local Markdown and wiki-style backlinks",
    "Agent consumption/editing without a fragile app dependency",
    "SQLite provenance/importability from messages, links, and scrape rows",
    "Lexical search now and semantic/graph search later",
    "Graph/relationship support without making graph infra the primary source",
    "Low Windows operational risk",
    "Minimal untrusted install/execute surface before promptfoo review",
]


def evidence(local: list[str], external: list[str], score: int) -> str:
    return json.dumps(
        {
            "method": METHOD,
            "local_evidence": local,
            "external_sources_checked": external,
            "comparison_score_40": score,
        },
        indent=2,
        ensure_ascii=True,
    )


def candidates() -> list[dict[str, object]]:
    github_safety = (
        "GitHub or external project code was not installed, cloned, executed, or imported. "
        "Treat as untrusted until a later promptfoo-backed safety and dependency review."
    )
    return [
        {
            "candidate_name": "Project-owned Obsidian-compatible Markdown wiki backed by SQLite",
            "candidate_type": "recommended_architecture",
            "message_id": 17,
            "link_id": 14,
            "score": 38,
            "summary": (
                "Use SQLite as source of truth and generate a local Markdown wiki under kb/ "
                "with stable frontmatter, message/link provenance, wikilinks/backlinks, "
                "comparison pages, and SQLite FTS5 lexical search."
            ),
            "evidence": evidence(
                [
                    "Message 17 introduces LLM Knowledge Bases; messages 23-25 discuss agent-maintained personal KBs and Obsidian MD vaults.",
                    "Message 33 explicitly calls out Obsidian wikilinks and graph traversal for agents.",
                    "Project docs require SQLite as source of truth, local generated outputs, wiki-style backlinks, and later search/graph enrichment.",
                ],
                [
                    "https://obsidian.md/help/data-storage",
                    "https://obsidian.md/help/links",
                    "https://obsidian.md/help/plugins/backlinks",
                    "https://obsidian.md/help/plugins/graph",
                    "https://www.sqlite.org/fts5.html",
                ],
                38,
            ),
            "limitations": (
                "Requires implementing page generation, backlink extraction, source citation discipline, "
                "and validation scripts. Semantic search and graph visualization remain later phases."
            ),
            "safety_notes": (
                "Lowest-risk path because it uses this repo's SQLite DB and Markdown files instead of executing external projects."
            ),
            "review_status": "recommended_primary",
            "disposition": "Recommended initial implementation direction.",
        },
        {
            "candidate_name": "Karpathy LLM Wiki pattern",
            "candidate_type": "method_pattern",
            "message_id": 17,
            "link_id": 14,
            "score": 36,
            "summary": (
                "A method where raw sources stay immutable while an LLM incrementally compiles "
                "persistent interlinked Markdown articles, indexes, and lint/health checks."
            ),
            "evidence": evidence(
                [
                    "Message 17 oEmbed identifies Andrej Karpathy's LLM Knowledge Bases post.",
                    "Messages 23-25 reference the pattern, daily paper curation, health checks, and an LLM KB diagram.",
                    "Message 90 describes the pattern as persistent Markdown with backlinks and cross-references.",
                ],
                ["https://gist.github.com/karpathy?direction=desc&sort=updated"],
                36,
            ),
            "limitations": (
                "It is a pattern, not a complete product. The project still needs local schemas, generation rules, and review gates."
            ),
            "safety_notes": "Safe as an architectural pattern; no external code execution required.",
            "review_status": "recommended_pattern",
            "disposition": "Use as the core mental model for the KB.",
        },
        {
            "candidate_name": "Obsidian-compatible local Markdown vault",
            "candidate_type": "markdown_wiki_format",
            "message_id": 18,
            "link_id": 15,
            "score": 35,
            "summary": (
                "Emit ordinary Markdown files that can be opened as an Obsidian vault while remaining editable by agents and other tools."
            ),
            "evidence": evidence(
                [
                    "Messages 18, 20, 23, 32, 33, 41, 52-54, and 74 repeatedly point to Obsidian vaults for Claude/agent memory and KB work.",
                    "Message 33 names Obsidian wikilinks graph traversal as a topic to explore for agents.",
                ],
                [
                    "https://obsidian.md/help/data-storage",
                    "https://obsidian.md/help/links",
                    "https://obsidian.md/help/plugins/backlinks",
                    "https://obsidian.md/help/plugins/graph",
                ],
                35,
            ),
            "limitations": (
                "Obsidian-specific block links and some plugin metadata are less portable. The repo should keep core pages valid Markdown."
            ),
            "safety_notes": "No need to install Obsidian to generate or consume Markdown; treat Obsidian as an optional viewer.",
            "review_status": "recommended_format",
            "disposition": "Use compatible Markdown/wikilinks, not an Obsidian dependency.",
        },
        {
            "candidate_name": "SQLite FTS5 lexical search layer",
            "candidate_type": "supporting_search_layer",
            "message_id": None,
            "link_id": None,
            "score": 34,
            "summary": (
                "Add an FTS5 index over generated KB pages and/or source evidence for fast local lexical search before semantic search is introduced."
            ),
            "evidence": evidence(
                [
                    "Project docs require regular keyword search before intent-based semantic search.",
                    "Classification found 79 Search_Retrieval messages that can inform later retrieval design.",
                ],
                ["https://www.sqlite.org/fts5.html"],
                34,
            ),
            "limitations": "Lexical search does not cover semantic equivalence; later embedding or graph search should be evaluated separately.",
            "safety_notes": "Low-risk built-in SQLite extension path, subject to local SQLite FTS5 availability validation.",
            "review_status": "recommended_component",
            "disposition": "Implement with the initial KB if FTS5 is available locally.",
        },
        {
            "candidate_name": "Ars Contexta",
            "candidate_type": "external_claude_code_plugin",
            "message_id": 51,
            "link_id": 46,
            "score": 27,
            "summary": (
                "Claude Code plugin that generates individualized Markdown knowledge systems, hooks, navigation maps, and note templates."
            ),
            "evidence": evidence(
                [
                    "Message 51 links agenticnotetaking/arscontexta and classifies it as Memory and Knowledge_Base.",
                    "Local scrape title says it generates individualized knowledge systems and markdown files the user owns.",
                ],
                ["https://github.com/agenticnotetaking/arscontexta", "https://www.arscontexta.org/"],
                27,
            ),
            "limitations": (
                "Claude Code plugin orientation, hook surface, generated automation, and token-intensive setup are broader than this initial KB need."
            ),
            "safety_notes": github_safety,
            "review_status": "deferred_promptfoo_required",
            "disposition": "Study as design inspiration after safety review; do not adopt initially.",
        },
        {
            "candidate_name": "Pal (Personal Agent that Learns)",
            "candidate_type": "external_personal_agent_kb",
            "message_id": 22,
            "link_id": 19,
            "score": 25,
            "summary": (
                "Personal agent that combines raw sources, a compiled wiki, SQL structured data, and a routing/learning loop."
            ),
            "evidence": evidence(
                [
                    "Messages 22 and 29 describe Pal as local, source-ingesting, structured-wiki-building, and SQL-maintaining.",
                    "The local evidence matches the project need for raw source plus compiled wiki separation, but Pal's scope is much larger.",
                ],
                ["https://github.com/agno-agi/pal"],
                25,
            ),
            "limitations": "Requires Docker/service setup and external integrations; too broad for the initial local KB generation phase.",
            "safety_notes": github_safety,
            "review_status": "deferred_promptfoo_required",
            "disposition": "Use as architecture reference for raw/wiki/SQL separation, not as initial implementation.",
        },
        {
            "candidate_name": "LLM Wiki desktop app (nashsu/llm_wiki)",
            "candidate_type": "external_desktop_kb_app",
            "message_id": 204,
            "link_id": 196,
            "score": 24,
            "summary": (
                "Cross-platform desktop app that ingests documents into an organized interlinked LLM-maintained wiki with graph/search features."
            ),
            "evidence": evidence(
                [
                    "Messages 204 and 237 link nashsu/llm_wiki and classify it as Knowledge_Base, Memory, and Search_Retrieval.",
                    "Local scrape title states it turns documents into an organized interlinked KB and maintains a persistent wiki from sources.",
                ],
                ["https://github.com/nashsu/llm_wiki"],
                24,
            ),
            "limitations": (
                "External app with a larger dependency footprint, GPL-3.0 licensing, and UI workflows that may not map cleanly to this repo."
            ),
            "safety_notes": github_safety,
            "review_status": "deferred_promptfoo_required",
            "disposition": "Compare later; initial repo-native Markdown is simpler and safer.",
        },
        {
            "candidate_name": "claude-obsidian",
            "candidate_type": "external_obsidian_companion",
            "message_id": 166,
            "link_id": 159,
            "score": 25,
            "summary": (
                "Claude plus Obsidian companion that implements a persistent compounding wiki vault based on the Karpathy LLM Wiki pattern."
            ),
            "evidence": evidence(
                [
                    "Message 166 links claude-obsidian and classifies it as Memory, Knowledge_Base, and Verification_Loops.",
                    "Local scrape and public README position it around /wiki, /save, and /autoresearch workflows.",
                ],
                ["https://github.com/AgriciDaniel/claude-obsidian"],
                25,
            ),
            "limitations": "Plugin-specific workflow and seeded-vault assumptions may be useful but are not necessary for this project's first KB pass.",
            "safety_notes": github_safety,
            "review_status": "deferred_promptfoo_required",
            "disposition": "Useful comparison target; do not run before safety review.",
        },
        {
            "candidate_name": "Cognee",
            "candidate_type": "external_graph_vector_memory_engine",
            "message_id": 205,
            "link_id": 197,
            "score": 22,
            "summary": (
                "Open-source knowledge/memory engine combining graph and vector retrieval for agent memory."
            ),
            "evidence": evidence(
                [
                    "Message 205 links Cognee and classifies it as Memory and agent infrastructure.",
                    "Related messages 61 and 260 point to knowledge graphs plus vector/semantic search as later memory support.",
                ],
                ["https://github.com/topoteretes/cognee"],
                22,
            ),
            "limitations": "Graph/vector database stack is heavier than needed for a first local Markdown KB and may introduce service/configuration risk.",
            "safety_notes": github_safety,
            "review_status": "deferred_later_graph_memory",
            "disposition": "Evaluate later for semantic/graph memory enrichment.",
        },
        {
            "candidate_name": "Understand Anything",
            "candidate_type": "external_graph_overlay",
            "message_id": 229,
            "link_id": 220,
            "score": 23,
            "summary": (
                "Graph overlay that can analyze code, docs, or a Karpathy-pattern LLM wiki into an explorable/searchable knowledge graph."
            ),
            "evidence": evidence(
                [
                    "Message 229 links Understand-Anything and classifies it as Knowledge_Base, Graphs_Knowledge_Graphs, and Search_Retrieval.",
                    "Local scrape title says it can turn a knowledge base into an interactive graph that works with Codex and Claude Code.",
                ],
                ["https://github.com/Lum1104/Understand-Anything"],
                23,
            ),
            "limitations": "Best suited after KB Markdown exists; it is not the source-of-truth layer itself.",
            "safety_notes": github_safety,
            "review_status": "deferred_later_graph_overlay",
            "disposition": "Potential graph visualization layer after initial KB and safety review.",
        },
        {
            "candidate_name": "OpenWolf",
            "candidate_type": "external_code_agent_memory",
            "message_id": 240,
            "link_id": 231,
            "score": 18,
            "summary": (
                "Claude Code middleware that creates project intelligence, learning memory, and token-aware file maps."
            ),
            "evidence": evidence(
                [
                    "Message 240 describes OpenWolf as a second brain for Claude Code with project file maps and bug/preference memory.",
                    "Local scrape and public docs emphasize context reduction for coding-agent sessions.",
                ],
                ["https://github.com/cytostack/openwolf", "https://openwolf.com/"],
                18,
            ),
            "limitations": "Optimized for coding-agent file reading and hooks, not for a WhatsApp-derived public knowledge base.",
            "safety_notes": github_safety,
            "review_status": "not_initial_primary",
            "disposition": "Not a primary KB candidate; keep as a memory design reference.",
        },
        {
            "candidate_name": "Graphify",
            "candidate_type": "external_folder_to_graph_skill",
            "message_id": 153,
            "link_id": 146,
            "score": 21,
            "summary": (
                "AI coding assistant skill that turns folders of code, docs, schemas, and other assets into a queryable knowledge graph."
            ),
            "evidence": evidence(
                [
                    "Message 65 describes Graphify as a graph tool inspired by the LLM Knowledge Bases workflow.",
                    "Message 153 links safishamsi/graphify and classifies it as Graphs_Knowledge_Graphs and Search_Retrieval.",
                ],
                ["https://github.com/safishamsi/graphify"],
                21,
            ),
            "limitations": "Graph generation should come after source-backed Markdown pages exist; first pass should not depend on graph tooling.",
            "safety_notes": github_safety,
            "review_status": "deferred_later_graph_overlay",
            "disposition": "Potential later graph extractor, not initial KB foundation.",
        },
        {
            "candidate_name": "Obsidian Skills",
            "candidate_type": "external_agent_obsidian_interface",
            "message_id": 249,
            "link_id": 240,
            "score": 20,
            "summary": (
                "Agent skills for working with Obsidian concepts such as Markdown, Bases, JSON Canvas, and CLI operations."
            ),
            "evidence": evidence(
                [
                    "Message 249 links kepano/obsidian-skills and classifies it as Knowledge_Base and Skills.",
                    "Public README describes agent skills for Obsidian use by Claude/Codex-style agents.",
                ],
                ["https://github.com/kepano/obsidian-skills"],
                20,
            ),
            "limitations": "Useful only if Obsidian operational integration becomes necessary; the initial repo can generate Markdown directly.",
            "safety_notes": github_safety,
            "review_status": "deferred_supporting_agent_interface",
            "disposition": "Possible later helper, not an initial dependency.",
        },
        {
            "candidate_name": "CocoIndex-style graph and semantic retrieval backend",
            "candidate_type": "external_retrieval_backend",
            "message_id": 260,
            "link_id": 250,
            "score": 19,
            "summary": (
                "Retrieval/indexing approach that can build graph and semantic stores from local files or object storage."
            ),
            "evidence": evidence(
                [
                    "Message 260 describes building knowledge from local files into a dual knowledge store with graph and semantic understanding.",
                    "This aligns with the project's later semantic/graph search phase, not the first Markdown KB decision.",
                ],
                ["https://github.com/cocoindex-io/cocoindex-code"],
                19,
            ),
            "limitations": "Likely requires extra services or indexes; unnecessary before lexical search and source-backed Markdown are working.",
            "safety_notes": github_safety,
            "review_status": "deferred_later_semantic_search",
            "disposition": "Future search/backend comparison candidate.",
        },
    ]


def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = PERSIST")
    return conn


def count_rows(conn: sqlite3.Connection) -> dict[str, int | str]:
    return {
        "integrity_check": conn.execute("PRAGMA integrity_check").fetchone()[0],
        "messages": conn.execute("SELECT count(*) FROM messages").fetchone()[0],
        "knowledge_base_messages": conn.execute(
            "SELECT count(DISTINCT message_id) FROM classifications WHERE category='Knowledge_Base'"
        ).fetchone()[0],
        "related_messages": conn.execute(
            """
            SELECT count(DISTINCT message_id)
            FROM classifications
            WHERE category IN ('Memory','Graphs_Knowledge_Graphs','Search_Retrieval','Methods_Workflows')
            """
        ).fetchone()[0],
        "kb_candidates_before": conn.execute("SELECT count(*) FROM kb_candidates").fetchone()[0],
        "decisions_before": conn.execute("SELECT count(*) FROM decisions").fetchone()[0],
    }


def write_candidates(conn: sqlite3.Connection, now: str) -> tuple[int, int]:
    candidate_rows = candidates()
    names = [row["candidate_name"] for row in candidate_rows]
    conn.executemany("DELETE FROM kb_candidates WHERE candidate_name = ?", [(name,) for name in names])
    conn.executemany(
        """
        INSERT INTO kb_candidates (
            message_id, link_id, candidate_name, candidate_type, summary, evidence,
            limitations, safety_notes, review_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["message_id"],
                row["link_id"],
                row["candidate_name"],
                row["candidate_type"],
                row["summary"],
                row["evidence"],
                row["limitations"],
                row["safety_notes"],
                row["review_status"],
            )
            for row in candidate_rows
        ],
    )

    previous = conn.execute(
        "SELECT id FROM decisions WHERE decision_key = ? ORDER BY decided_at DESC, id DESC LIMIT 1",
        (DECISION_KEY,),
    ).fetchone()
    decision_value = (
        "Implement a project-owned, Obsidian-compatible Markdown knowledge base under kb/ generated from "
        "SQLite source data. Keep raw WhatsApp/link evidence in SQLite, generate source-cited synthesis pages "
        "with stable frontmatter and wikilinks/backlinks, add SQLite FTS5 lexical search first, and defer any "
        "external GitHub project, semantic retrieval backend, or graph overlay until a promptfoo-backed safety "
        "review and a working local Markdown baseline exist."
    )
    rationale = (
        "This best matches the local Knowledge_Base evidence around Karpathy-style LLM Wikis and Obsidian MD vaults, "
        "the project requirement that SQLite remains source of truth, and the safety rule against running untrusted "
        "GitHub projects. External projects are useful references but introduce dependency, hook, service, licensing, "
        "or credential surfaces that are unnecessary for the first KB implementation."
    )
    conn.execute(
        """
        INSERT INTO decisions (
            decision_key, decision_value, rationale, decided_at, supersedes_decision_id
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (DECISION_KEY, decision_value, rationale, now, previous["id"] if previous else None),
    )
    conn.commit()
    return len(candidate_rows), 1


def update_heartbeat(phase: str, extra: dict[str, object] | None = None) -> None:
    payload: dict[str, object] = {}
    if HEARTBEAT_PATH.exists():
        payload = json.loads(HEARTBEAT_PATH.read_text(encoding="utf-8"))
    payload.update(
        {
            "goal_id": "goal-005-kb-candidate-review",
            "status": "running",
            "phase": phase,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    if extra:
        payload.update(extra)
    HEARTBEAT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def checkpoint_markdown(started_at: str | None, ended_at: str, counts: dict[str, int | str], inserted: int) -> str:
    candidate_rows = candidates()
    recommended = [
        row for row in candidate_rows if str(row["review_status"]).startswith("recommended")
    ]
    deferred = [row for row in candidate_rows if row not in recommended]

    def table(rows: list[dict[str, object]]) -> str:
        lines = [
            "| Candidate | Type | Score/40 | Status | Disposition |",
            "| --- | --- | ---: | --- | --- |",
        ]
        for row in rows:
            lines.append(
                "| {candidate_name} | {candidate_type} | {score} | {review_status} | {disposition} |".format(**row)
            )
        return "\n".join(lines)

    source_lines = "\n".join(f"- {url}" for url in SOURCE_URLS)
    criteria_lines = "\n".join(f"- {item}" for item in COMPARISON_CRITERIA)
    command_lines = "\n".join(
        f"- `{cmd}`"
        for cmd in [
            "Get-Content -Raw <required docs/checkpoints>",
            "uv run --no-cache python -B scripts/db_status.py",
            "uv run --no-cache python -B -  # SQLite schema/category/evidence queries",
            "web search/open for public source verification",
            "uv run --no-cache python -B scripts/review_kb_candidates.py --apply",
        ]
    )
    candidate_detail_lines = []
    for row in candidate_rows:
        candidate_detail_lines.append(
            "\n### {candidate_name}\n\n"
            "- Type: {candidate_type}\n"
            "- Local anchor: message_id={message_id}, link_id={link_id}\n"
            "- Summary: {summary}\n"
            "- Limitations: {limitations}\n"
            "- Safety: {safety_notes}\n"
            "- Status: {review_status}\n".format(**row)
        )

    return f"""# Checkpoint 007: Knowledge Base Candidate Review

Date: 2026-05-09

## Scope

- Goal: identify credible Knowledge Base candidates, compare them, write candidate/decision rows, and record an initial KB approach.
- Required docs and checkpoints were read before candidate extraction or DB writes.
- Raw `imports/` files remained read-only.
- WhatsApp was not opened or mutated.
- Browser automation was not used.
- No GitHub project was installed, cloned, executed, imported, or run.
- SQLite was used as source of truth for local evidence.

## Timing

- Started: {started_at or 'recorded in heartbeat before extraction'}
- Checkpoint generated: {ended_at}

## Commands Run

{command_lines}

## Local Evidence Reviewed

- Total messages in DB: {counts['messages']}
- Knowledge_Base messages reviewed: {counts['knowledge_base_messages']}
- Related Memory / Graphs_Knowledge_Graphs / Search_Retrieval / Methods_Workflows messages scanned: {counts['related_messages']}
- SQLite integrity check before write: {counts['integrity_check']}
- kb_candidates before write: {counts['kb_candidates_before']}
- decisions before write: {counts['decisions_before']}
- kb_candidates inserted/updated in this pass: {inserted}

## Public Sources Checked

{source_lines}

## Comparison Criteria

{criteria_lines}

## Candidate Comparison

{table(candidate_rows)}

## Recommendation

Implement a project-owned, Obsidian-compatible Markdown wiki under `kb/`, generated from SQLite. Keep SQLite as source of truth for messages, links, scrape attempts, classifications, candidates, and decisions. Generate source-cited synthesis pages with stable YAML frontmatter, Obsidian-compatible `[[wikilinks]]`, backlinks/comparison pages, and a generated index. Add SQLite FTS5 lexical search first. Defer external GitHub projects, semantic retrieval, and graph overlays until the repo-native Markdown KB is working and a promptfoo-backed safety review approves any code execution.

## Candidate Notes
{''.join(candidate_detail_lines)}

## Unresolved Risks

- External GitHub projects may contain unsafe install scripts, telemetry, credentials handling, broad hooks, or dependency risks. They require promptfoo-backed safety review before execution.
- Current X/Twitter oEmbed coverage is sufficient for this review but not complete; unresolved X rows may reveal more candidates later.
- Generated Markdown needs strict source citation rules so assistant synthesis remains separate from source content.
- FTS5 availability should be validated before relying on it for search.
- Semantic search and graph visualization should be introduced only after lexical search and page generation are reliable.

## Next Implementation Steps

1. Define `kb/` folder layout: `sources/`, `topics/`, `tools/`, `comparisons/`, `decisions/`, and `indexes/`.
2. Write a deterministic KB page generator from SQLite that preserves message/link provenance and source URLs.
3. Add backlink extraction and a generated relationship index from `[[wikilinks]]`.
4. Add SQLite FTS5 search over generated pages and selected source evidence.
5. Add validation that every generated synthesis page has source references and no orphaned links.
6. Run promptfoo safety review before considering any external GitHub project or plugin.

## Validation

Final validation is recorded after the DB status and explicit SQLite decision/candidate queries run.
"""


def apply_review() -> None:
    started_at = None
    if HEARTBEAT_PATH.exists():
        started_at = json.loads(HEARTBEAT_PATH.read_text(encoding="utf-8")).get("started_at")
    now = datetime.now(timezone.utc).isoformat()
    with connect_db() as conn:
        counts = count_rows(conn)
        inserted, decisions = write_candidates(conn, now)
    CHECKPOINT_PATH.write_text(checkpoint_markdown(started_at, now, counts, inserted), encoding="utf-8")
    update_heartbeat(
        "candidate-rows-and-initial-decision-written",
        {
            "knowledge_base_messages_reviewed": counts["knowledge_base_messages"],
            "related_messages_scanned": counts["related_messages"],
            "candidate_rows_written": inserted,
            "decision_rows_written": decisions,
            "checkpoint": str(CHECKPOINT_PATH),
            "commands_run": [
                "Get-Content -Raw <required docs/checkpoints>",
                "uv run --no-cache python -B scripts/db_status.py",
                "uv run --no-cache python -B -  # SQLite schema/category/evidence queries",
                "web search/open for public source verification",
                "uv run --no-cache python -B scripts/review_kb_candidates.py --apply",
            ],
        },
    )
    print(json.dumps({"inserted_candidates": inserted, "inserted_decisions": decisions}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Write KB candidate review rows and checkpoint.")
    parser.add_argument("--apply", action="store_true", help="Write kb_candidates, decisions, checkpoint, and heartbeat.")
    args = parser.parse_args()
    if not args.apply:
        parser.print_help()
        return
    apply_review()


if __name__ == "__main__":
    main()
