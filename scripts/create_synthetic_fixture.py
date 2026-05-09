from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ingest_whatsapp import run_ingest


WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_IMPORTS = WORKSPACE / "fixtures" / "synthetic" / "imports"
DEFAULT_DB = WORKSPACE / "data" / "fixtures" / "synthetic" / "agentic_workflow.db"
DEFAULT_INTERMEDIATE = WORKSPACE / "data" / "fixtures" / "synthetic" / "intermediate"

CLASSIFICATION_METHOD = "synthetic-fixture-rule-based-v1"
SAFETY_METHOD = "synthetic-fixture-static-review-v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_safety_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS kb_safety_reviews (
          id INTEGER PRIMARY KEY,
          candidate_id INTEGER REFERENCES kb_candidates(id),
          candidate_name TEXT NOT NULL,
          source_urls TEXT NOT NULL,
          promptfoo_config TEXT NOT NULL,
          promptfoo_result_path TEXT NOT NULL,
          risk_rating TEXT,
          fit_rating TEXT,
          final_disposition TEXT,
          rationale TEXT,
          risk_dimensions_json TEXT,
          evidence_path TEXT,
          reviewed_at TEXT NOT NULL,
          reviewer_method TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_kb_safety_reviews_candidate_method
        ON kb_safety_reviews(candidate_name, reviewer_method)
        """
    )


def first_message(conn: sqlite3.Connection, phrase: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM messages WHERE raw_text LIKE ? ORDER BY id LIMIT 1",
        (f"%{phrase}%",),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Synthetic fixture message not found for phrase: {phrase}")
    return row


def first_link(conn: sqlite3.Connection, message_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM links WHERE message_id = ? ORDER BY id LIMIT 1",
        (message_id,),
    ).fetchone()


def add_scrape_attempts(conn: sqlite3.Connection, now: str) -> int:
    rows_written = 0
    for link in conn.execute("SELECT * FROM links ORDER BY id").fetchall():
        title = "Synthetic source: " + link["normalized_url"].rsplit("/", 1)[-1].replace("-", " ").title()
        extracted = (
            f"{title}. This synthetic linked-content artifact exists only to exercise "
            "the public KB pipeline without private corpus data."
        )
        conn.execute(
            """
            INSERT INTO scrape_attempts(
              link_id, attempted_at, tool, status, http_status, final_url, title,
              extracted_text, metadata_json, error_type, error_message, duration_ms
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                link["id"],
                now,
                "synthetic_fixture",
                "success",
                200,
                link["normalized_url"],
                title,
                extracted,
                json.dumps({"fixture": True, "source": "synthetic"}),
                None,
                None,
                1,
            ),
        )
        rows_written += 1
    return rows_written


def add_classifications(conn: sqlite3.Connection, now: str) -> int:
    categories_by_phrase = {
        "SQLite-backed Markdown wiki": [
            ("Knowledge_Base", 0.98, "Synthetic fixture explicitly requests a SQLite-backed Markdown wiki."),
            ("Search_Retrieval", 0.91, "Synthetic fixture mentions local FTS search."),
        ],
        "Verification loops": [
            ("Verification_Evals", 0.96, "Synthetic fixture describes post-build validation failures."),
            ("Methods_Workflows", 0.88, "Synthetic fixture describes a repeatable validation workflow."),
        ],
        "Graph overlays": [
            ("Graphs_Knowledge_Graphs", 0.97, "Synthetic fixture discusses graph overlays and graph databases."),
            ("Safety_Verification", 0.84, "Synthetic fixture gates optional graph databases by static review."),
        ],
        "Intent search": [
            ("Search_Retrieval", 0.94, "Synthetic fixture discusses deterministic intent search."),
            ("Memory", 0.82, "Synthetic fixture uses memory and retrieval terms."),
        ],
    }
    rows_written = 0
    seen: set[tuple[int, str]] = set()
    for phrase, rows in categories_by_phrase.items():
        for message in conn.execute(
            "SELECT * FROM messages WHERE raw_text LIKE ? ORDER BY id",
            (f"%{phrase}%",),
        ).fetchall():
            for category, confidence, rationale in rows:
                key = (int(message["id"]), category)
                if key in seen:
                    continue
                seen.add(key)
                conn.execute(
                    """
                    INSERT INTO classifications(
                      message_id, category, confidence, rationale, classified_at, model_or_method
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (message["id"], category, confidence, rationale, now, CLASSIFICATION_METHOD),
                )
                rows_written += 1
    return rows_written


def candidate_payloads(conn: sqlite3.Connection) -> list[dict[str, object]]:
    wiki_message = first_message(conn, "SQLite-backed Markdown wiki")
    graph_message = first_message(conn, "Graph overlays")
    intent_message = first_message(conn, "Intent search")
    wiki_link = first_link(conn, int(wiki_message["id"]))
    graph_link = first_link(conn, int(graph_message["id"]))
    intent_link = first_link(conn, int(intent_message["id"]))
    return [
        {
            "message_id": wiki_message["id"],
            "link_id": wiki_link["id"] if wiki_link else None,
            "candidate_name": "Project-owned Obsidian-compatible Markdown wiki backed by SQLite",
            "candidate_type": "recommended_architecture",
            "summary": "Generate source-provenanced Markdown pages from SQLite with wikilinks and local search.",
            "evidence": "Synthetic fixture message recommends SQLite-backed Markdown with Obsidian-style links.",
            "limitations": "Synthetic fixture is small and only exercises the pipeline shape.",
            "safety_notes": "Project-owned local implementation; no external project execution required.",
            "review_status": "recommended_primary",
        },
        {
            "message_id": wiki_message["id"],
            "link_id": wiki_link["id"] if wiki_link else None,
            "candidate_name": "Karpathy LLM Wiki pattern",
            "candidate_type": "method_pattern",
            "summary": "Keep raw sources immutable and compile durable interlinked Markdown synthesis.",
            "evidence": "Synthetic fixture exercises source-backed wiki generation.",
            "limitations": "Pattern only; project still owns schema and generation rules.",
            "safety_notes": "Architectural pattern only.",
            "review_status": "recommended_pattern",
        },
        {
            "message_id": wiki_message["id"],
            "link_id": wiki_link["id"] if wiki_link else None,
            "candidate_name": "Obsidian-compatible local Markdown vault",
            "candidate_type": "markdown_wiki_format",
            "summary": "Emit ordinary Markdown with wikilinks that can be viewed in Obsidian.",
            "evidence": "Synthetic fixture asks for Obsidian-style links.",
            "limitations": "Obsidian remains optional; generated Markdown must stay portable.",
            "safety_notes": "No Obsidian dependency is needed to generate the fixture KB.",
            "review_status": "recommended_format",
        },
        {
            "message_id": intent_message["id"],
            "link_id": intent_link["id"] if intent_link else None,
            "candidate_name": "SQLite FTS5 lexical search layer",
            "candidate_type": "supporting_search_layer",
            "summary": "Use SQLite FTS5 for local lexical search over generated KB pages.",
            "evidence": "Synthetic fixture mentions local FTS and deterministic intent search.",
            "limitations": "Lexical matching is not semantic embedding search.",
            "safety_notes": "Uses local SQLite features only.",
            "review_status": "recommended_component",
        },
        {
            "message_id": graph_message["id"],
            "link_id": graph_link["id"] if graph_link else None,
            "candidate_name": "Synthetic Graph Overlay Backend",
            "candidate_type": "external_graph_overlay",
            "summary": "Placeholder external graph overlay used to test deferred backend reporting.",
            "evidence": "Synthetic fixture says graph overlays belong after the Markdown baseline is stable.",
            "limitations": "Synthetic candidate only; not a real project.",
            "safety_notes": "Do not execute external graph systems before safety review.",
            "review_status": "deferred_later_graph_overlay",
        },
    ]


def add_candidates(conn: sqlite3.Connection) -> int:
    rows = candidate_payloads(conn)
    conn.executemany("DELETE FROM kb_candidates WHERE candidate_name = ?", [(row["candidate_name"],) for row in rows])
    conn.executemany(
        """
        INSERT INTO kb_candidates(
          message_id, link_id, candidate_name, candidate_type, summary, evidence,
          limitations, safety_notes, review_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            for row in rows
        ],
    )
    return len(rows)


def add_safety_reviews(conn: sqlite3.Connection, now: str) -> int:
    ensure_safety_schema(conn)
    candidates = conn.execute("SELECT * FROM kb_candidates ORDER BY id").fetchall()
    rows_written = 0
    for candidate in candidates:
        risk = "low" if str(candidate["review_status"]).startswith("recommended") else "medium"
        fit = "high" if str(candidate["review_status"]).startswith("recommended") else "medium"
        disposition = "fixture_recommended" if risk == "low" else "fixture_deferred"
        dimensions = {
            "fixture_only": True,
            "external_execution": "not_performed",
            "private_data_access": "not_allowed",
        }
        conn.execute(
            """
            INSERT INTO kb_safety_reviews(
              candidate_id, candidate_name, source_urls, promptfoo_config, promptfoo_result_path,
              risk_rating, fit_rating, final_disposition, rationale, risk_dimensions_json,
              evidence_path, reviewed_at, reviewer_method
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(candidate_name, reviewer_method) DO UPDATE SET
              candidate_id = excluded.candidate_id,
              source_urls = excluded.source_urls,
              risk_rating = excluded.risk_rating,
              fit_rating = excluded.fit_rating,
              final_disposition = excluded.final_disposition,
              rationale = excluded.rationale,
              risk_dimensions_json = excluded.risk_dimensions_json,
              reviewed_at = excluded.reviewed_at
            """,
            (
                candidate["id"],
                candidate["candidate_name"],
                json.dumps(["fixtures/synthetic/imports/Primary/WhatsApp Chat with Synthetic Agentic Workflow Lab.txt"]),
                "synthetic_fixture",
                "",
                risk,
                fit,
                disposition,
                "Synthetic fixture review only; no external project code exists or runs.",
                json.dumps(dimensions, sort_keys=True),
                "",
                now,
                SAFETY_METHOD,
            ),
        )
        rows_written += 1
    return rows_written


def add_decision(conn: sqlite3.Connection, now: str) -> int:
    conn.execute(
        """
        INSERT INTO decisions(decision_key, decision_value, rationale, decided_at, supersedes_decision_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "synthetic_fixture_kb_approach",
            "Use the project-owned SQLite-backed Markdown KB baseline for the synthetic fixture.",
            "The fixture is designed to validate local generation, provenance, wikilinks, FTS search, and intent search without private data.",
            now,
            None,
        ),
    )
    return 1


def create_fixture(args: argparse.Namespace) -> dict[str, int | str]:
    args.db.parent.mkdir(parents=True, exist_ok=True)
    args.intermediate_dir.mkdir(parents=True, exist_ok=True)
    ingest_stats = run_ingest(args.imports_dir.resolve(), args.db.resolve(), args.intermediate_dir.resolve(), rebuild=True)
    now = utc_now()
    with connect(args.db) as conn:
        scrape_attempts = add_scrape_attempts(conn, now)
        classifications = add_classifications(conn, now)
        candidates = add_candidates(conn)
        safety_reviews = add_safety_reviews(conn, now)
        decisions = add_decision(conn, now)
        conn.commit()
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    return {
        "db": str(args.db),
        "imports_dir": str(args.imports_dir),
        "intermediate_dir": str(args.intermediate_dir),
        "messages": int(ingest_stats["in_scope_message_count"]),
        "links": int(ingest_stats["link_count"]),
        "scrape_attempts": scrape_attempts,
        "classifications": classifications,
        "kb_candidates": candidates,
        "kb_safety_reviews": safety_reviews,
        "decisions": decisions,
        "integrity_check": str(integrity),
        "fixture_hash": sha256_text(json.dumps(ingest_stats, sort_keys=True)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a synthetic public SQLite fixture for smoke-testing the KB pipeline.")
    parser.add_argument("--imports-dir", type=Path, default=DEFAULT_IMPORTS)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--intermediate-dir", type=Path, default=DEFAULT_INTERMEDIATE)
    return parser.parse_args()


def main() -> None:
    summary = create_fixture(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
