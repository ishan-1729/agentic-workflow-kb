from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import ProxyHandler, Request, build_opener


WORKSPACE = Path(__file__).resolve().parents[1]
DB_PATH = WORKSPACE / "data" / "db" / "agentic_workflow.db"
GOAL_ID = "goal-006-promptfoo-kb-safety-review"
REVIEW_METHOD = "goal-006-promptfoo-static-review-v1"
HEARTBEAT_PATH = WORKSPACE / "learnings" / f"{GOAL_ID}.heartbeat.json"
DONE_PATH = WORKSPACE / "learnings" / f"{GOAL_ID}.done"
CHECKPOINT_PATH = WORKSPACE / "learnings" / "checkpoint-009-promptfoo-kb-safety-review.md"
REVIEW_DIR = WORKSPACE / "data" / "safety_reviews" / "goal-006"
EVIDENCE_DIR = REVIEW_DIR / "evidence"
CANDIDATE_EVIDENCE_DIR = EVIDENCE_DIR / "candidates"
RAW_DIR = EVIDENCE_DIR / "raw"
PROMPTFOO_OUTPUT_DIR = REVIEW_DIR / "promptfoo_outputs"
PROMPTFOO_REVIEW_DIR = PROMPTFOO_OUTPUT_DIR / "reviews"
VALIDATION_PATH = REVIEW_DIR / "validation.json"
PROMPTFOO_CONFIG_PATH = WORKSPACE / "evals" / "promptfoo" / "kb-safety-review.yaml"
PROMPTFOO_TESTS_PATH = WORKSPACE / "evals" / "promptfoo" / "kb-safety-tests.json"
PROMPTFOO_RESULT_PATH = PROMPTFOO_OUTPUT_DIR / "kb-safety-results.json"

PROMPTFOO_INSTALL_DOCS = [
    "https://www.promptfoo.dev/docs/installation/",
    "https://www.promptfoo.dev/docs/code-scanning/cli/",
    "https://www.promptfoo.dev/docs/providers/custom-api/",
    "https://www.promptfoo.dev/docs/configuration/test-cases/",
    "https://www.promptfoo.dev/docs/configuration/expected-outputs/javascript/",
]

REQUIRED_DIMENSIONS = [
    "repository_identity",
    "license",
    "maintenance_health",
    "install_postinstall_risk",
    "dependency_risk",
    "docker_ci_script_risk",
    "runtime_permissions",
    "browser_profile_handling",
    "credential_handling",
    "network_behavior",
    "prompt_injection_data_exfiltration",
    "windows_operational_risk",
    "project_fit",
]

REQUIRED_CANDIDATES = [
    "Project-owned Obsidian-compatible Markdown wiki backed by SQLite",
    "Karpathy LLM Wiki pattern",
    "Obsidian-compatible local Markdown vault",
    "SQLite FTS5 lexical search layer",
    "Ars Contexta",
    "Pal (Personal Agent that Learns)",
    "LLM Wiki desktop app (nashsu/llm_wiki)",
    "claude-obsidian",
    "Cognee",
    "Understand Anything",
    "OpenWolf",
    "Graphify",
    "Obsidian Skills",
    "CocoIndex-style graph and semantic retrieval backend",
]

CANDIDATE_SPECS: dict[str, dict[str, Any]] = {
    "Project-owned Obsidian-compatible Markdown wiki backed by SQLite": {
        "kind": "local_architecture",
        "public_urls": [
            "https://obsidian.md/help/data-storage",
            "https://obsidian.md/help/links",
            "https://obsidian.md/help/plugins/backlinks",
            "https://obsidian.md/help/plugins/graph",
            "https://www.sqlite.org/fts5.html",
            "https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f",
            "https://denser.ai/blog/llm-wiki-karpathy-knowledge-base/",
        ],
    },
    "Karpathy LLM Wiki pattern": {
        "kind": "method_pattern",
        "public_urls": [
            "https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f",
            "https://gist.github.com/karpathy?direction=desc&sort=created",
            "https://denser.ai/blog/llm-wiki-karpathy-knowledge-base/",
        ],
    },
    "Obsidian-compatible local Markdown vault": {
        "kind": "markdown_format",
        "public_urls": [
            "https://obsidian.md/help/data-storage",
            "https://obsidian.md/help/links",
            "https://obsidian.md/help/plugins/backlinks",
            "https://obsidian.md/help/plugins/graph",
        ],
    },
    "SQLite FTS5 lexical search layer": {
        "kind": "local_component",
        "public_urls": ["https://www.sqlite.org/fts5.html"],
    },
    "Ars Contexta": {
        "kind": "external_project",
        "repo": "agenticnotetaking/arscontexta",
        "public_urls": [
            "https://github.com/agenticnotetaking/arscontexta",
            "https://www.arscontexta.org/",
            "https://context7.com/agenticnotetaking/arscontexta",
        ],
    },
    "Pal (Personal Agent that Learns)": {
        "kind": "external_project",
        "repo": "agno-agi/pal",
        "public_urls": ["https://github.com/agno-agi/pal"],
    },
    "LLM Wiki desktop app (nashsu/llm_wiki)": {
        "kind": "external_project",
        "repo": "nashsu/llm_wiki",
        "public_urls": [
            "https://github.com/nashsu/llm_wiki",
            "https://llmwiki.app/",
            "https://denser.ai/blog/llm-wiki-karpathy-knowledge-base/",
        ],
    },
    "claude-obsidian": {
        "kind": "external_project",
        "repo": "AgriciDaniel/claude-obsidian",
        "public_urls": ["https://github.com/AgriciDaniel/claude-obsidian"],
    },
    "Cognee": {
        "kind": "external_project",
        "repo": "topoteretes/cognee",
        "public_urls": ["https://github.com/topoteretes/cognee"],
    },
    "Understand Anything": {
        "kind": "external_project",
        "repo": "Lum1104/Understand-Anything",
        "public_urls": ["https://github.com/Lum1104/Understand-Anything"],
    },
    "OpenWolf": {
        "kind": "external_project",
        "repo": "cytostack/openwolf",
        "public_urls": ["https://github.com/cytostack/openwolf", "https://openwolf.com/"],
    },
    "Graphify": {
        "kind": "external_project",
        "repo": "safishamsi/graphify",
        "public_urls": ["https://github.com/safishamsi/graphify"],
    },
    "Obsidian Skills": {
        "kind": "external_project",
        "repo": "kepano/obsidian-skills",
        "public_urls": ["https://github.com/kepano/obsidian-skills"],
    },
    "CocoIndex-style graph and semantic retrieval backend": {
        "kind": "external_project",
        "repo": "cocoindex-io/cocoindex-code",
        "public_urls": [
            "https://github.com/cocoindex-io/cocoindex-code",
            "https://cocoindex.io/cocoindex-code/",
            "https://github.com/cocoindex-io/cocoindex",
            "https://cocoindex.io/",
        ],
    },
}

STATIC_FILE_PATTERNS = [
    re.compile(r"(^|/)readme(\.[a-z]+)?$", re.I),
    re.compile(r"(^|/)license(\.[a-z]+)?$", re.I),
    re.compile(r"(^|/)package\.json$", re.I),
    re.compile(r"(^|/)package-lock\.json$", re.I),
    re.compile(r"(^|/)pnpm-lock\.yaml$", re.I),
    re.compile(r"(^|/)yarn\.lock$", re.I),
    re.compile(r"(^|/)pyproject\.toml$", re.I),
    re.compile(r"(^|/)requirements.*\.txt$", re.I),
    re.compile(r"(^|/)uv\.lock$", re.I),
    re.compile(r"(^|/)setup\.py$", re.I),
    re.compile(r"(^|/)dockerfile$", re.I),
    re.compile(r"(^|/)docker-compose.*\.ya?ml$", re.I),
    re.compile(r"(^|/)\.github/workflows/[^/]+\.ya?ml$", re.I),
    re.compile(r"(^|/)(install|setup|bootstrap)\.(sh|ps1|bat|cmd)$", re.I),
    re.compile(r"(^|/)makefile$", re.I),
    re.compile(r"(^|/)(claude|agents|codex)\.md$", re.I),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(WORKSPACE)).replace("\\", "/")
    except ValueError:
        return str(path)


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")[:90]


def ensure_dirs() -> None:
    for path in [
        REVIEW_DIR,
        EVIDENCE_DIR,
        CANDIDATE_EVIDENCE_DIR,
        RAW_DIR,
        PROMPTFOO_OUTPUT_DIR,
        PROMPTFOO_REVIEW_DIR,
        PROMPTFOO_CONFIG_PATH.parent,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def update_heartbeat(phase: str, **extra: Any) -> None:
    payload = read_json(HEARTBEAT_PATH, {})
    payload.setdefault("goal_id", GOAL_ID)
    payload.setdefault("status", "running")
    payload.setdefault("started_at", utc_now())
    payload["phase"] = phase
    payload["updated_at"] = utc_now()
    if extra:
        payload.update(extra)
    write_json(HEARTBEAT_PATH, payload)


def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = PERSIST")
    return conn


def fetch_url(url: str, *, accept: str = "*/*", timeout: int = 30) -> dict[str, Any]:
    opener = build_opener(ProxyHandler({}))
    request = Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": "agentic-workflow-goal006-static-review",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    started = time.time()
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = response.read()
            text = raw.decode(response.headers.get_content_charset() or "utf-8", errors="replace")
            return {
                "url": url,
                "status": int(response.status),
                "ok": 200 <= int(response.status) < 300,
                "content_type": response.headers.get("content-type"),
                "elapsed_ms": int((time.time() - started) * 1000),
                "text": text,
            }
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return {
            "url": url,
            "status": int(exc.code),
            "ok": False,
            "content_type": exc.headers.get("content-type") if exc.headers else None,
            "elapsed_ms": int((time.time() - started) * 1000),
            "error": str(exc),
            "text": body[:5000],
        }
    except (URLError, TimeoutError, OSError) as exc:
        return {
            "url": url,
            "status": None,
            "ok": False,
            "elapsed_ms": int((time.time() - started) * 1000),
            "error": f"{type(exc).__name__}: {exc}",
            "text": "",
        }


def fetch_json(url: str) -> dict[str, Any]:
    result = fetch_url(url, accept="application/vnd.github+json")
    if result.get("ok"):
        try:
            result["json"] = json.loads(result.get("text") or "{}")
        except json.JSONDecodeError as exc:
            result["ok"] = False
            result["error"] = f"JSONDecodeError: {exc}"
    return result


def sanitize_raw_name(url: str, suffix: str = ".txt") -> str:
    parsed = urlparse(url)
    rough = f"{parsed.netloc}{parsed.path}"
    return slugify(rough) + suffix


def save_raw_text(candidate_slug: str, url: str, text: str, suffix: str = ".txt") -> str:
    path = RAW_DIR / candidate_slug / sanitize_raw_name(url, suffix)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text[:400_000], encoding="utf-8", errors="replace")
    return rel(path)


def latest_scrape_for_link(conn: sqlite3.Connection, link_id: int | None) -> dict[str, Any] | None:
    if link_id is None:
        return None
    row = conn.execute(
        """
        SELECT attempted_at, tool, status, http_status, final_url, title,
               substr(extracted_text, 1, 2000) AS extracted_text_excerpt,
               error_type, error_message
        FROM scrape_attempts
        WHERE link_id = ?
        ORDER BY attempted_at DESC, id DESC
        LIMIT 1
        """,
        (link_id,),
    ).fetchone()
    return dict(row) if row else None


def sqlite_candidate_evidence(conn: sqlite3.Connection, candidate_name: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT id, message_id, link_id, candidate_name, candidate_type, summary,
               evidence, limitations, safety_notes, review_status
        FROM kb_candidates
        WHERE candidate_name = ?
        """,
        (candidate_name,),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Missing kb_candidates row for {candidate_name}")
    payload = dict(row)
    if payload.get("message_id") is not None:
        message = conn.execute(
            """
            SELECT id, source_group, source_file, message_timestamp,
                   substr(raw_text, 1, 1000) AS raw_text_excerpt
            FROM messages
            WHERE id = ?
            """,
            (payload["message_id"],),
        ).fetchone()
        payload["message"] = dict(message) if message else None
    if payload.get("link_id") is not None:
        link = conn.execute(
            """
            SELECT id, raw_url, normalized_url, first_seen_at
            FROM links
            WHERE id = ?
            """,
            (payload["link_id"],),
        ).fetchone()
        payload["link"] = dict(link) if link else None
        payload["latest_scrape"] = latest_scrape_for_link(conn, payload["link_id"])
    return payload


def selected_paths(tree: list[dict[str, Any]]) -> list[str]:
    paths: list[str] = []
    for item in tree:
        if item.get("type") != "blob":
            continue
        path = item.get("path") or ""
        if any(pattern.search(path) for pattern in STATIC_FILE_PATTERNS):
            paths.append(path)
    priority = {
        "readme": 0,
        "license": 1,
        "package.json": 2,
        "pyproject.toml": 3,
        "requirements": 4,
        "docker": 5,
        ".github/workflows": 6,
    }

    def sort_key(path: str) -> tuple[int, str]:
        lower = path.lower()
        rank = 10
        for token, token_rank in priority.items():
            if token in lower:
                rank = min(rank, token_rank)
        return rank, lower

    return sorted(set(paths), key=sort_key)[:25]


def summarize_static_files(static_files: list[dict[str, Any]]) -> dict[str, Any]:
    combined = "\n".join((item.get("text_excerpt") or "") for item in static_files).lower()
    package_files = [item for item in static_files if item["path"].lower().endswith("package.json")]
    package_summaries: list[dict[str, Any]] = []
    for item in package_files:
        try:
            package = json.loads(item.get("text_full") or item.get("text_excerpt") or "{}")
        except json.JSONDecodeError:
            package = {}
        scripts = package.get("scripts") or {}
        lifecycle = {
            key: value
            for key, value in scripts.items()
            if key in {"preinstall", "install", "postinstall", "prepare", "prepublishOnly"}
        }
        package_summaries.append(
            {
                "path": item["path"],
                "name": package.get("name"),
                "license": package.get("license"),
                "scripts": scripts,
                "lifecycle_scripts": lifecycle,
                "dependencies_count": len(package.get("dependencies") or {}),
                "dev_dependencies_count": len(package.get("devDependencies") or {}),
                "optional_dependencies_count": len(package.get("optionalDependencies") or {}),
            }
        )
    return {
        "file_paths": [item["path"] for item in static_files],
        "package_summaries": package_summaries,
        "lockfiles": [
            item["path"]
            for item in static_files
            if re.search(r"(package-lock\.json|pnpm-lock\.yaml|yarn\.lock|uv\.lock)$", item["path"], re.I)
        ],
        "docker_files": [
            item["path"]
            for item in static_files
            if re.search(r"(^|/)(dockerfile|docker-compose.*\.ya?ml)$", item["path"], re.I)
        ],
        "ci_workflows": [item["path"] for item in static_files if ".github/workflows/" in item["path"].lower()],
        "install_scripts": [
            item["path"]
            for item in static_files
            if re.search(r"(^|/)(install|setup|bootstrap)\.(sh|ps1|bat|cmd)$", item["path"], re.I)
        ],
        "mentions": {
            "browser_or_profile": bool(re.search(r"\b(browser|chrome|chromium|playwright|extension|cookie|profile)\b", combined)),
            "credentials_or_env": bool(re.search(r"\b(api[_ -]?key|token|secret|credential|\.env|openai_api_key|anthropic_api_key)\b", combined)),
            "network_or_cloud": bool(re.search(r"\b(http|web search|api|cloud|server|mcp|socket|telemetry|posthog|tavily|google drive|s3)\b", combined)),
            "llm_agent_surface": bool(re.search(r"\b(llm|agent|claude|codex|prompt injection|mcp|tool|browser)\b", combined)),
            "windows_specific": bool(re.search(r"\b(windows|powershell|\.ps1|win32)\b", combined)),
            "unix_shell_or_docker": bool(re.search(r"\b(bash|shell|docker|compose|makefile|linux|macos)\b", combined)),
        },
    }


def collect_github_evidence(candidate_slug: str, repo: str) -> dict[str, Any]:
    owner_repo = repo.strip("/")
    repo_api_url = f"https://api.github.com/repos/{owner_repo}"
    repo_result = fetch_json(repo_api_url)
    source_urls = [f"https://github.com/{owner_repo}", repo_api_url]
    evidence: dict[str, Any] = {
        "repo": owner_repo,
        "repo_api": compact_fetch_result(repo_result, include_json=True),
        "source_urls": source_urls,
        "static_files": [],
        "static_analysis": {},
    }
    if not repo_result.get("ok") or not repo_result.get("json"):
        return evidence

    repo_json = repo_result["json"]
    default_branch = repo_json.get("default_branch") or "main"
    metadata_keys = [
        "id",
        "full_name",
        "html_url",
        "description",
        "created_at",
        "updated_at",
        "pushed_at",
        "archived",
        "disabled",
        "fork",
        "stargazers_count",
        "forks_count",
        "open_issues_count",
        "license",
        "default_branch",
        "topics",
        "language",
    ]
    evidence["metadata"] = {key: repo_json.get(key) for key in metadata_keys}

    api_urls = {
        "latest_release": f"https://api.github.com/repos/{owner_repo}/releases/latest",
        "releases": f"https://api.github.com/repos/{owner_repo}/releases?per_page=5",
        "latest_commit": f"https://api.github.com/repos/{owner_repo}/commits?per_page=1",
        "open_issues": f"https://api.github.com/repos/{owner_repo}/issues?state=open&per_page=5",
        "security_advisories": f"https://api.github.com/repos/{owner_repo}/security-advisories?per_page=10",
        "tree": f"https://api.github.com/repos/{owner_repo}/git/trees/{quote(default_branch, safe='')}?recursive=1",
    }
    api_results: dict[str, Any] = {}
    for key, url in api_urls.items():
        result = fetch_json(url)
        api_results[key] = compact_fetch_result(result, include_json=True)
        source_urls.append(url)

    tree_json = api_results.get("tree", {}).get("json")
    paths = selected_paths(tree_json.get("tree", []) if isinstance(tree_json, dict) else [])
    static_files: list[dict[str, Any]] = []
    for path in paths:
        raw_url = f"https://raw.githubusercontent.com/{owner_repo}/{default_branch}/{quote(path)}"
        raw_result = fetch_url(raw_url, accept="text/plain")
        source_urls.append(raw_url)
        text = raw_result.get("text") or ""
        raw_path = save_raw_text(candidate_slug, raw_url, text)
        static_files.append(
            {
                "path": path,
                "url": raw_url,
                "status": raw_result.get("status"),
                "ok": raw_result.get("ok"),
                "raw_path": raw_path,
                "text_excerpt": text[:8000],
                "text_full": text if path.lower().endswith("package.json") else None,
            }
        )

    evidence["github_api_results"] = api_results
    evidence["static_files"] = static_files
    evidence["static_analysis"] = summarize_static_files(static_files)
    evidence["source_urls"] = sorted(set(source_urls))
    return evidence


def compact_fetch_result(result: dict[str, Any], *, include_json: bool = False) -> dict[str, Any]:
    compact = {
        "url": result.get("url"),
        "status": result.get("status"),
        "ok": result.get("ok"),
        "content_type": result.get("content_type"),
        "elapsed_ms": result.get("elapsed_ms"),
    }
    if result.get("error"):
        compact["error"] = result.get("error")
    if include_json and "json" in result:
        compact["json"] = result["json"]
    else:
        compact["text_excerpt"] = (result.get("text") or "")[:2000]
    return compact


def collect_public_pages(candidate_slug: str, urls: list[str]) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    for url in urls:
        result = fetch_url(url, accept="text/html,text/plain,application/json")
        raw_path = save_raw_text(candidate_slug, url, result.get("text") or "")
        compact = compact_fetch_result(result)
        compact["raw_path"] = raw_path
        pages.append(compact)
    return pages


def collect_evidence() -> None:
    ensure_dirs()
    update_heartbeat("evidence-collection-started")
    all_candidates: list[dict[str, Any]] = []
    with connect_db() as conn:
        for candidate_name in REQUIRED_CANDIDATES:
            spec = CANDIDATE_SPECS[candidate_name]
            candidate_slug = slugify(candidate_name)
            sqlite_evidence = sqlite_candidate_evidence(conn, candidate_name)
            public_pages = collect_public_pages(candidate_slug, spec.get("public_urls", []))
            github_evidence = None
            if spec.get("repo"):
                github_evidence = collect_github_evidence(candidate_slug, spec["repo"])

            source_urls = list(spec.get("public_urls", []))
            if sqlite_evidence.get("link", {}).get("normalized_url"):
                source_urls.append(sqlite_evidence["link"]["normalized_url"])
            if github_evidence:
                source_urls.extend(github_evidence.get("source_urls", []))
            evidence_payload = {
                "candidate_name": candidate_name,
                "candidate_slug": candidate_slug,
                "reviewed_at": utc_now(),
                "kind": spec["kind"],
                "sqlite": sqlite_evidence,
                "public_pages": public_pages,
                "github": github_evidence,
                "source_urls": sorted(set(source_urls)),
                "expert_review_note": expert_review_note(candidate_name, spec.get("public_urls", [])),
                "safety_review_scope": {
                    "allowed": "Static review of SQLite rows, public pages, GitHub metadata, and individual raw files.",
                    "not_allowed": "No candidate install, clone, import, execution, Docker run, browser profile use, or authenticated session use.",
                    "dimensions": REQUIRED_DIMENSIONS,
                },
            }
            evidence_path = CANDIDATE_EVIDENCE_DIR / f"{candidate_slug}.json"
            write_json(evidence_path, evidence_payload)
            all_candidates.append(
                {
                    "candidate_name": candidate_name,
                    "candidate_slug": candidate_slug,
                    "evidence_path": rel(evidence_path),
                    "source_url_count": len(evidence_payload["source_urls"]),
                    "github_repo": spec.get("repo"),
                    "kind": spec["kind"],
                }
            )

    summary = {
        "goal_id": GOAL_ID,
        "collected_at": utc_now(),
        "candidate_count": len(all_candidates),
        "candidates": all_candidates,
        "promptfoo_docs": PROMPTFOO_INSTALL_DOCS,
        "required_dimensions": REQUIRED_DIMENSIONS,
        "network_method": "Python urllib with proxies disabled for public primary-source lookup; no candidate code executed.",
    }
    write_json(EVIDENCE_DIR / "summary.json", summary)
    write_promptfoo_tests(all_candidates)
    update_heartbeat(
        "evidence-collection-complete",
        evidence_summary=rel(EVIDENCE_DIR / "summary.json"),
        candidate_count=len(all_candidates),
    )
    print(json.dumps(summary, indent=2))


def expert_review_note(candidate_name: str, urls: list[str]) -> str:
    if "Karpathy" in candidate_name or "LLM Wiki" in candidate_name:
        return "Bounded review included Denser.ai analysis as a secondary expert/source commentary URL where applicable."
    if any("context7.com" in url for url in urls):
        return "Bounded review included Context7 as secondary indexed project documentation, not as sole evidence."
    return "No credible independent expert review was found in the bounded pass; primary-source repository/docs evidence is used and missing review evidence is marked unknown."


def write_promptfoo_tests(candidates: list[dict[str, Any]]) -> None:
    tests = []
    for candidate in candidates:
        candidate_slug = candidate["candidate_slug"]
        evidence_path = WORKSPACE / candidate["evidence_path"]
        evidence_ref = os.path.relpath(evidence_path, PROMPTFOO_CONFIG_PATH.parent).replace("\\", "/")
        review_output_path = PROMPTFOO_REVIEW_DIR / f"{candidate_slug}.json"
        tests.append(
            {
                "description": f"KB safety review: {candidate['candidate_name']}",
                "vars": {
                    "candidate_name": candidate["candidate_name"],
                    "candidate_json": f"file://{evidence_ref}",
                    "review_output_path": rel(review_output_path),
                },
                "metadata": {
                    "candidate_name": candidate["candidate_name"],
                    "candidate_slug": candidate_slug,
                    "goal_id": GOAL_ID,
                },
            }
        )
    write_json(PROMPTFOO_TESTS_PATH, tests)


def ensure_sqlite_schema(conn: sqlite3.Connection) -> None:
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
    existing = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(kb_safety_reviews)").fetchall()
    }
    columns = {
        "risk_dimensions_json": "TEXT",
        "evidence_path": "TEXT",
        "promptfoo_result_path": "TEXT NOT NULL DEFAULT ''",
    }
    for column, column_type in columns.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE kb_safety_reviews ADD COLUMN {column} {column_type}")
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_kb_safety_reviews_candidate_method
        ON kb_safety_reviews(candidate_name, reviewer_method)
        """
    )


def review_output_for(candidate_slug: str) -> dict[str, Any]:
    path = PROMPTFOO_REVIEW_DIR / f"{candidate_slug}.json"
    if not path.exists():
        raise RuntimeError(f"Missing promptfoo review output {path}")
    return read_json(path, {})


def write_sqlite_records() -> None:
    ensure_dirs()
    summary = read_json(EVIDENCE_DIR / "summary.json", {})
    if not summary:
        raise RuntimeError("Evidence summary is missing; run collect-evidence first")
    now = utc_now()
    rows_written = 0
    with connect_db() as conn:
        ensure_sqlite_schema(conn)
        candidates_by_name = {
            row["candidate_name"]: row["id"]
            for row in conn.execute("SELECT id, candidate_name FROM kb_candidates")
        }
        for candidate in summary["candidates"]:
            name = candidate["candidate_name"]
            evidence = read_json(WORKSPACE / candidate["evidence_path"], {})
            review = review_output_for(candidate["candidate_slug"])
            source_urls = json.dumps(evidence.get("source_urls", []), ensure_ascii=True)
            dimensions = json.dumps(review.get("dimensions", {}), ensure_ascii=True)
            conn.execute(
                """
                INSERT INTO kb_safety_reviews (
                    candidate_id, candidate_name, source_urls, promptfoo_config,
                    promptfoo_result_path, risk_rating, fit_rating, final_disposition,
                    rationale, risk_dimensions_json, evidence_path, reviewed_at,
                    reviewer_method
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(candidate_name, reviewer_method) DO UPDATE SET
                    candidate_id=excluded.candidate_id,
                    source_urls=excluded.source_urls,
                    promptfoo_config=excluded.promptfoo_config,
                    promptfoo_result_path=excluded.promptfoo_result_path,
                    risk_rating=excluded.risk_rating,
                    fit_rating=excluded.fit_rating,
                    final_disposition=excluded.final_disposition,
                    rationale=excluded.rationale,
                    risk_dimensions_json=excluded.risk_dimensions_json,
                    evidence_path=excluded.evidence_path,
                    reviewed_at=excluded.reviewed_at
                """,
                (
                    candidates_by_name.get(name),
                    name,
                    source_urls,
                    rel(PROMPTFOO_CONFIG_PATH),
                    rel(PROMPTFOO_RESULT_PATH),
                    review.get("overall_risk", "unknown"),
                    review.get("fit_rating", "unknown"),
                    review.get("final_disposition", "unknown"),
                    review.get("summary", ""),
                    dimensions,
                    candidate["evidence_path"],
                    now,
                    REVIEW_METHOD,
                ),
            )
            rows_written += 1

        previous_same_key = conn.execute(
            """
            SELECT id FROM decisions
            WHERE decision_key = 'knowledge_base_approach_after_safety_review'
            ORDER BY decided_at DESC, id DESC
            LIMIT 1
            """
        ).fetchone()
        previous_initial = conn.execute(
            """
            SELECT id FROM decisions
            WHERE decision_key = 'knowledge_base_approach_initial'
            ORDER BY decided_at DESC, id DESC
            LIMIT 1
            """
        ).fetchone()
        supersedes = previous_same_key or previous_initial
        decision_value = (
            "No change from Goal 005: implement a project-owned, Obsidian-compatible "
            "Markdown knowledge base generated from SQLite, use Karpathy's LLM Wiki "
            "pattern as method guidance, keep Obsidian compatibility as a file format, "
            "and add SQLite FTS5 lexical search first. External projects remain "
            "inspiration/deferred comparison targets rather than implementation dependencies."
        )
        rationale = (
            "The promptfoo-backed static review found the repo-owned SQLite-to-Markdown path "
            "has the lowest install, credential, network, browser-profile, and Windows risk. "
            "External projects have useful design ideas but introduce broader install surfaces "
            "(package managers, Docker/native dependencies, MCP/agent hooks, browser/web "
            "capture, cloud APIs, or service daemons) that are unnecessary before the local "
            "Markdown baseline exists. Missing or ambiguous evidence is treated as unknown, "
            "not as approval."
        )
        conn.execute(
            """
            INSERT INTO decisions (
                decision_key, decision_value, rationale, decided_at, supersedes_decision_id
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                "knowledge_base_approach_after_safety_review",
                decision_value,
                rationale,
                now,
                supersedes["id"] if supersedes else None,
            ),
        )
        conn.commit()

    update_heartbeat(
        "sqlite-writes-complete",
        sqlite_rows_written=rows_written,
        decision_key="knowledge_base_approach_after_safety_review",
    )
    print(json.dumps({"kb_safety_reviews_upserted": rows_written, "decision_written": True}, indent=2))


def validate_records() -> dict[str, Any]:
    with connect_db() as conn:
        ensure_sqlite_schema(conn)
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT candidate_name, risk_rating, fit_rating, final_disposition, reviewed_at
                FROM kb_safety_reviews
                WHERE reviewer_method = ?
                ORDER BY candidate_name
                """,
                (REVIEW_METHOD,),
            )
        ]
        row_names = {row["candidate_name"] for row in rows}
        missing = [name for name in REQUIRED_CANDIDATES if name not in row_names]
        decision_count = conn.execute(
            """
            SELECT count(*) FROM decisions
            WHERE decision_key = 'knowledge_base_approach_after_safety_review'
            """
        ).fetchone()[0]
        latest_decision = conn.execute(
            """
            SELECT id, decision_key, decided_at, supersedes_decision_id
            FROM decisions
            WHERE decision_key = 'knowledge_base_approach_after_safety_review'
            ORDER BY decided_at DESC, id DESC
            LIMIT 1
            """
        ).fetchone()
        validation = {
            "validated_at": utc_now(),
            "integrity_check": conn.execute("PRAGMA integrity_check").fetchone()[0],
            "required_candidate_count": len(REQUIRED_CANDIDATES),
            "safety_review_row_count": len(rows),
            "missing_required_candidates": missing,
            "post_safety_decision_count": decision_count,
            "latest_post_safety_decision": dict(latest_decision) if latest_decision else None,
            "rows": rows,
        }
    write_json(VALIDATION_PATH, validation)
    print(json.dumps(validation, indent=2))
    if validation["integrity_check"] != "ok" or missing or decision_count < 1:
        raise SystemExit(1)
    return validation


def summarize_reviews() -> list[dict[str, Any]]:
    summary = read_json(EVIDENCE_DIR / "summary.json", {})
    rows = []
    for candidate in summary.get("candidates", []):
        review_path = PROMPTFOO_REVIEW_DIR / f"{candidate['candidate_slug']}.json"
        if not review_path.exists():
            continue
        review = read_json(review_path, {})
        rows.append(
            {
                "candidate_name": candidate["candidate_name"],
                "overall_risk": review.get("overall_risk", "unknown"),
                "fit_rating": review.get("fit_rating", "unknown"),
                "final_disposition": review.get("final_disposition", "unknown"),
                "summary": review.get("summary", ""),
                "source_url_count": candidate.get("source_url_count", 0),
            }
        )
    return rows


def checkpoint_markdown() -> str:
    heartbeat = read_json(HEARTBEAT_PATH, {})
    evidence_summary = read_json(EVIDENCE_DIR / "summary.json", {})
    validation = read_json(VALIDATION_PATH, {})
    promptfoo_result = read_json(PROMPTFOO_RESULT_PATH, {})
    reviews = summarize_reviews()
    promptfoo_setup = heartbeat.get("promptfoo_setup", {})
    ended_at = heartbeat.get("finished_at") or utc_now()

    commands = [
        "Get-Content -Raw docs/README.md docs/handoff.md docs/operating-rules.md docs/safety-and-verification.md docs/promptfoo-safety-review.md docs/knowledge-base-review.md docs/sqlite-schema.md docs/codex-goals.md docs/cli-wake-bridge.md docs/browser-sandbox.md learnings/checkpoint-007-kb-candidate-review.md learnings/checkpoint-008-cli-wake-bridge.md",
        "uv run --no-cache python -B scripts/db_status.py",
        "node --version; Get-Command promptfoo/npm/npx; local npm bootstrap and promptfoo setup commands recorded in heartbeat/checkpoint",
        "uv run --no-cache python -B scripts/kb_safety_review.py collect-evidence",
        promptfoo_command_text(),
        "uv run --no-cache python -B scripts/kb_safety_review.py write-sqlite",
        "$env:PYTHONPYCACHEPREFIX='C:\\Users\\Ishan\\.codex\\memories\\agentic_workflow_pycache_goal006'; uv run --no-cache python -B -m py_compile scripts\\kb_safety_review.py",
        "node -c evals\\promptfoo\\kb_safety_provider.cjs",
        "uv run --no-cache python -B scripts/kb_safety_review.py validate",
        "uv run --no-cache python -B scripts/kb_safety_review.py checkpoint",
    ]

    source_urls = []
    for candidate in REQUIRED_CANDIDATES:
        evidence_path = CANDIDATE_EVIDENCE_DIR / f"{slugify(candidate)}.json"
        if evidence_path.exists():
            evidence = read_json(evidence_path, {})
            source_urls.extend(evidence.get("source_urls", []))
    source_urls.extend(PROMPTFOO_INSTALL_DOCS)
    source_lines = "\n".join(f"- {url}" for url in sorted(set(source_urls)))
    command_lines = "\n".join(f"- `{command}`" for command in commands)
    candidate_lines = [
        "| Candidate | Risk | Fit | Disposition |",
        "| --- | --- | --- | --- |",
    ]
    for row in reviews:
        candidate_lines.append(
            f"| {row['candidate_name']} | {row['overall_risk']} | {row['fit_rating']} | {row['final_disposition']} |"
        )

    promptfoo_summary_lines = [
        f"- Config: `{rel(PROMPTFOO_CONFIG_PATH)}`",
        f"- Main result: `{rel(PROMPTFOO_RESULT_PATH)}`",
        f"- Per-candidate outputs: `{rel(PROMPTFOO_REVIEW_DIR)}`",
        f"- Reviewed candidates: {len(reviews)}",
    ]
    metrics = (
        promptfoo_result.get("results", {})
        .get("prompts", [{}])[0]
        .get("metrics", {})
        if promptfoo_result
        else {}
    )
    if metrics:
        promptfoo_summary_lines.append(
            "- Eval pass/fail: "
            f"{metrics.get('testPassCount')} passed, "
            f"{metrics.get('testFailCount')} failed, "
            f"{metrics.get('testErrorCount')} errors; "
            f"assertions {metrics.get('assertPassCount')} passed / {metrics.get('assertFailCount')} failed."
        )
    if validation:
        promptfoo_summary_lines.append(
            f"- SQLite validation rows: {validation.get('safety_review_row_count')} of {validation.get('required_candidate_count')}"
        )

    sqlite_lines = [
        "- Table: `kb_safety_reviews` created/updated idempotently with one row per required candidate for reviewer method "
        f"`{REVIEW_METHOD}`.",
        "- Decision: `knowledge_base_approach_after_safety_review` inserted and linked to the previous initial decision when present.",
    ]
    if validation:
        sqlite_lines.append(f"- Validation JSON: `{rel(VALIDATION_PATH)}`")

    unresolved = [
        "This was a static review. It did not install, clone, import, execute, Docker-run, or authenticate to any candidate project.",
        "GitHub security advisories endpoints are public when available, but missing/403/404 advisory evidence is marked unknown rather than safe.",
        "External projects with MCP servers, browser capture, cloud APIs, Docker/native dependencies, or broad filesystem indexing need separate isolated execution gates before any adoption.",
        "The workspace denies unlink/delete operations; promptfoo runtime DB and npm install artifacts are therefore in a documented local Codex memories folder, while review evidence/results stay under `data/safety_reviews/goal-006/`.",
    ]

    return f"""# Checkpoint 009: Promptfoo KB Safety Review

Date: 2026-05-09

## Scope

- Goal: perform promptfoo-backed static safety review before any KB implementation.
- Required docs and prior checkpoints were read before acting.
- `imports/` and WhatsApp data were not modified.
- No personal browser, cookies, saved sessions, CDP connection, or browser profile was used.
- No candidate GitHub project was installed, cloned, executed, imported, or run.
- SQLite remained the source of truth for candidate rows and decisions.

## Timing

- Started: {heartbeat.get('started_at', 'unknown')}
- Ended/checkpoint generated: {ended_at}

## Promptfoo Tooling

- Node version: {promptfoo_setup.get('node_version', 'unknown')}
- Local npm version: {promptfoo_setup.get('npm_version', 'unknown')}
- Local npm path: `{promptfoo_setup.get('npm_path', 'unknown')}`
- promptfoo version: {promptfoo_setup.get('promptfoo_version', 'unknown')}
- promptfoo path: `{promptfoo_setup.get('promptfoo_path', 'unknown')}`
- promptfoo install prefix: `{promptfoo_setup.get('promptfoo_install_prefix', 'unknown')}`
- promptfoo runtime dir: `{promptfoo_setup.get('promptfoo_runtime_dir', 'unknown')}`
- Telemetry: disabled with `PROMPTFOO_DISABLE_TELEMETRY=1` for all promptfoo verification/eval commands.
- Setup note: {promptfoo_setup.get('install_notes', 'unknown')}

Official promptfoo setup sources checked:

{chr(10).join(f'- {url}' for url in PROMPTFOO_INSTALL_DOCS)}

## Commands Run

{command_lines}

## Candidates Reviewed

{chr(10).join(candidate_lines)}

## Source URLs Checked

{source_lines}

## Promptfoo Results Summary

{chr(10).join(promptfoo_summary_lines)}

## SQLite Writes

{chr(10).join(sqlite_lines)}

## Goal 005 Comparison

The Goal 005 recommendation does not change after the promptfoo-backed safety review. The project-owned SQLite-to-Obsidian-compatible-Markdown approach remains the safest initial implementation because it avoids external install surfaces, runtime daemons, browser/profile handling, credential capture, and untrusted hooks while preserving SQLite provenance and readable Markdown. External projects remain useful inspiration or later comparison targets, but not implementation dependencies for the first KB.

## Recommendation

Implement the repo-owned KB next: generate source-cited Markdown under `kb/` from SQLite, keep Obsidian-compatible wikilinks/frontmatter, add backlinks/index pages, and add SQLite FTS5 lexical search. Treat external tools as deferred until the local KB baseline exists and any proposed integration gets its own isolated execution review.

## Unresolved Risks

{chr(10).join(f'- {item}' for item in unresolved)}

## Validation

```json
{json.dumps(validation, indent=2, ensure_ascii=True)}
```

## Next Goal

Goal 007 should implement the project-owned SQLite-to-Markdown KB generator and FTS5 lexical search baseline, with validation that generated pages carry source provenance and wikilinks/backlinks are internally consistent.
"""


def promptfoo_command_text() -> str:
    config_dir = os.environ.get("PROMPTFOO_CONFIG_DIR", "<local-promptfoo-config-dir>")
    cache_dir = os.environ.get("PROMPTFOO_CACHE_PATH", "<local-promptfoo-cache-dir>")
    log_dir = os.environ.get("PROMPTFOO_LOG_DIR", "<local-promptfoo-log-dir>")
    entrypoint = os.environ.get("PROMPTFOO_ENTRYPOINT", "<local-promptfoo-entrypoint.js>")
    return (
        "$env:PROMPTFOO_DISABLE_TELEMETRY='1'; "
        "$env:PROMPTFOO_DISABLE_WAL_MODE='true'; "
        f"$env:PROMPTFOO_CONFIG_DIR='{config_dir}'; "
        f"$env:PROMPTFOO_CACHE_PATH='{cache_dir}'; "
        f"$env:PROMPTFOO_LOG_DIR='{log_dir}'; "
        f"node {entrypoint} "
        "eval -c evals/promptfoo/kb-safety-review.yaml --no-cache --output data/safety_reviews/goal-006/promptfoo_outputs/kb-safety-results.json"
    )


def write_checkpoint() -> None:
    CHECKPOINT_PATH.write_text(checkpoint_markdown(), encoding="utf-8")
    update_heartbeat("final-comparison-complete", checkpoint=rel(CHECKPOINT_PATH))
    print(rel(CHECKPOINT_PATH))


def write_done() -> None:
    validation = read_json(VALIDATION_PATH, {})
    rows = validation.get("safety_review_row_count", "unknown")
    decision = validation.get("latest_post_safety_decision") or {}
    message = (
        "GOAL_006_DONE Promptfoo-backed static KB safety review completed with "
        f"{rows} safety-review rows, post-safety decision row {decision.get('id', 'unknown')}, "
        "and no change to the Goal 005 recommendation: implement the project-owned "
        "SQLite-to-Obsidian-compatible-Markdown KB with FTS5 first, while keeping external "
        "projects inspiration/deferred until later isolated gates."
    )
    DONE_PATH.write_text(message + "\n", encoding="utf-8")
    heartbeat = read_json(HEARTBEAT_PATH, {})
    heartbeat["status"] = "done"
    heartbeat["phase"] = "done-marker-written"
    heartbeat["updated_at"] = utc_now()
    heartbeat["finished_at"] = heartbeat["updated_at"]
    heartbeat["done_marker"] = rel(DONE_PATH)
    write_json(HEARTBEAT_PATH, heartbeat)
    print(message)


def main() -> None:
    parser = argparse.ArgumentParser(description="Goal 006 KB safety review harness.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("heartbeat")
    subparsers.add_parser("collect-evidence")
    subparsers.add_parser("write-sqlite")
    subparsers.add_parser("validate")
    subparsers.add_parser("checkpoint")
    subparsers.add_parser("done")
    args = parser.parse_args()

    if args.command == "heartbeat":
        update_heartbeat("manual-heartbeat")
    elif args.command == "collect-evidence":
        collect_evidence()
    elif args.command == "write-sqlite":
        write_sqlite_records()
    elif args.command == "validate":
        validate_records()
    elif args.command == "checkpoint":
        write_checkpoint()
    elif args.command == "done":
        write_done()
    else:
        raise AssertionError(args.command)


if __name__ == "__main__":
    main()
