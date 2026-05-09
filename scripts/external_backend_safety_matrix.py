from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


DEFAULT_DB = Path("data/db/agentic_workflow.db")
DEFAULT_STATUSES = (
    "deferred_later_graph_memory",
    "deferred_later_graph_overlay",
    "deferred_later_semantic_search",
    "deferred_supporting_agent_interface",
)


@dataclass
class BackendRow:
    candidate_id: int
    candidate_name: str
    candidate_type: str
    review_status: str
    risk_rating: str
    fit_rating: str
    final_disposition: str
    next_gate: str
    reviewed_at: str
    reviewer_method: str
    summary: str
    limitations: str
    safety_notes: str
    safety_rationale: str
    source_urls: list[str]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect_readonly(db_path: Path) -> sqlite3.Connection:
    resolved = db_path.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"SQLite database not found: {resolved}")
    uri = f"file:{quote(resolved.as_posix())}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (name,),
    ).fetchone()
    return row is not None


def parse_source_urls(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return [line.strip() for line in value.splitlines() if line.strip()]
    if isinstance(parsed, list):
        return [str(item) for item in parsed if str(item).strip()]
    if isinstance(parsed, str):
        return [parsed]
    return []


def next_gate_for(row: sqlite3.Row) -> str:
    final_disposition = str(row["final_disposition"] or "").lower()
    risk_rating = str(row["risk_rating"] or "").lower()
    fit_rating = str(row["fit_rating"] or "").lower()
    safety_rationale = str(row["safety_rationale"] or "").lower()

    if not row["reviewer_method"]:
        return "collect_static_evidence"
    if risk_rating in {"high", "critical"}:
        return "do_not_execute_without_user_approval"
    if "execute" in final_disposition and "approved" in final_disposition:
        return "sandbox_prototype_plan"
    if "defer" in final_disposition or "unknown" in safety_rationale:
        return "promptfoo_followup_required"
    if fit_rating in {"high", "medium"}:
        return "orchestrator_architecture_review"
    return "manual_review"


def load_rows(conn: sqlite3.Connection, statuses: tuple[str, ...]) -> list[BackendRow]:
    if not table_exists(conn, "kb_candidates"):
        raise RuntimeError("Missing required table: kb_candidates")
    has_safety_reviews = table_exists(conn, "kb_safety_reviews")

    placeholders = ",".join("?" for _ in statuses)
    if has_safety_reviews:
        sql = f"""
        SELECT
          c.id AS candidate_id,
          c.candidate_name,
          COALESCE(c.candidate_type, '') AS candidate_type,
          c.review_status,
          COALESCE(c.summary, '') AS summary,
          COALESCE(c.limitations, '') AS limitations,
          COALESCE(c.safety_notes, '') AS safety_notes,
          COALESCE(sr.risk_rating, '') AS risk_rating,
          COALESCE(sr.fit_rating, '') AS fit_rating,
          COALESCE(sr.final_disposition, '') AS final_disposition,
          COALESCE(sr.reviewed_at, '') AS reviewed_at,
          COALESCE(sr.reviewer_method, '') AS reviewer_method,
          COALESCE(sr.rationale, '') AS safety_rationale,
          COALESCE(sr.source_urls, '') AS source_urls
        FROM kb_candidates c
        LEFT JOIN kb_safety_reviews sr
          ON sr.id = (
            SELECT id
            FROM kb_safety_reviews
            WHERE candidate_name = c.candidate_name
            ORDER BY reviewed_at DESC, id DESC
            LIMIT 1
          )
        WHERE c.review_status IN ({placeholders})
        ORDER BY c.review_status, c.candidate_name
        """
    else:
        sql = f"""
        SELECT
          c.id AS candidate_id,
          c.candidate_name,
          COALESCE(c.candidate_type, '') AS candidate_type,
          c.review_status,
          COALESCE(c.summary, '') AS summary,
          COALESCE(c.limitations, '') AS limitations,
          COALESCE(c.safety_notes, '') AS safety_notes,
          '' AS risk_rating,
          '' AS fit_rating,
          '' AS final_disposition,
          '' AS reviewed_at,
          '' AS reviewer_method,
          '' AS safety_rationale,
          '' AS source_urls
        FROM kb_candidates c
        WHERE c.review_status IN ({placeholders})
        ORDER BY c.review_status, c.candidate_name
        """

    rows: list[BackendRow] = []
    for row in conn.execute(sql, statuses).fetchall():
        rows.append(
            BackendRow(
                candidate_id=int(row["candidate_id"]),
                candidate_name=str(row["candidate_name"]),
                candidate_type=str(row["candidate_type"]),
                review_status=str(row["review_status"]),
                risk_rating=str(row["risk_rating"] or "unreviewed"),
                fit_rating=str(row["fit_rating"] or "unreviewed"),
                final_disposition=str(row["final_disposition"] or "unreviewed"),
                next_gate=next_gate_for(row),
                reviewed_at=str(row["reviewed_at"]),
                reviewer_method=str(row["reviewer_method"]),
                summary=str(row["summary"]),
                limitations=str(row["limitations"]),
                safety_notes=str(row["safety_notes"]),
                safety_rationale=str(row["safety_rationale"]),
                source_urls=parse_source_urls(row["source_urls"]),
            )
        )
    return rows


def markdown_table(rows: list[BackendRow], generated_at: str, db_path: Path) -> str:
    lines = [
        "# External Backend Safety Matrix",
        "",
        f"- Generated at: `{generated_at}`",
        f"- SQLite source: `{db_path}`",
        "- Scope: deferred graph, overlay, semantic-search, and supporting-agent-interface candidates.",
        "- Policy: this report is read-only inventory only; it does not install, clone, import, execute, or run external projects.",
        "",
        "| Candidate | Type | Candidate Status | Risk | Fit | Disposition | Next Gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    if not rows:
        lines.append("| None | NA | NA | NA | NA | NA | NA |")
    for row in rows:
        lines.append(
            "| {name} | `{type}` | `{status}` | `{risk}` | `{fit}` | {disposition} | `{gate}` |".format(
                name=escape_cell(row.candidate_name),
                type=escape_cell(row.candidate_type),
                status=escape_cell(row.review_status),
                risk=escape_cell(row.risk_rating),
                fit=escape_cell(row.fit_rating),
                disposition=escape_cell(row.final_disposition),
                gate=escape_cell(row.next_gate),
            )
        )
    lines.extend(["", "## Candidate Notes", ""])
    for row in rows:
        lines.extend(
            [
                f"### {row.candidate_name}",
                "",
                f"- Candidate ID: `{row.candidate_id}`",
                f"- Latest review: `{row.reviewed_at or 'unreviewed'}` via `{row.reviewer_method or 'NA'}`",
                f"- Next gate: `{row.next_gate}`",
                f"- Summary: {row.summary or 'NA'}",
                f"- Limitations: {row.limitations or 'NA'}",
                f"- Safety notes: {row.safety_notes or 'NA'}",
                f"- Safety rationale: {row.safety_rationale or 'NA'}",
                "- Source URLs:",
            ]
        )
        if row.source_urls:
            lines.extend(f"  - {url}" for url in row.source_urls)
        else:
            lines.append("  - None recorded.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a read-only safety matrix for deferred external graph/vector/search candidates."
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--status",
        action="append",
        dest="statuses",
        help="Candidate review_status to include. May be repeated. Defaults to deferred external backend statuses.",
    )
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--print-markdown", action="store_true")
    args = parser.parse_args()

    statuses = tuple(args.statuses or DEFAULT_STATUSES)
    generated_at = utc_now()
    with connect_readonly(args.db) as conn:
        rows = load_rows(conn, statuses)

    payload = {
        "generated_at": generated_at,
        "db_path": str(args.db),
        "statuses": list(statuses),
        "policy": "read_only_static_inventory_no_external_project_execution",
        "count": len(rows),
        "rows": [asdict(row) for row in rows],
    }

    if args.json_output:
        write_text(args.json_output, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    markdown = markdown_table(rows, generated_at, args.db)
    if args.markdown_output:
        write_text(args.markdown_output, markdown)
    if args.print_markdown or not args.json_output and not args.markdown_output:
        print(markdown, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
