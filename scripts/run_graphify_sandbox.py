from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_WORK_ROOT = WORKSPACE / "data" / "external_sandbox"
FORBIDDEN_ROOTS = (
    WORKSPACE / "imports",
    WORKSPACE / "data" / "db",
    WORKSPACE / "data" / "scraped",
    WORKSPACE / "data" / "browser_sandbox",
    WORKSPACE / "kb",
)
API_ENV_VARS = (
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "MOONSHOT_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "AWS_PROFILE",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in value).strip("-") or "source"


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def assert_allowed_source(source: Path) -> Path:
    resolved = source.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Source path does not exist: {resolved}")
    for root in FORBIDDEN_ROOTS:
        if root.exists() and is_relative_to(resolved, root.resolve()):
            raise SystemExit(f"Refusing to run Graphify against private/generated root: {resolved}")
    return resolved


def ignore_names(_dir: str, names: list[str]) -> set[str]:
    ignored = {
        ".git",
        ".venv",
        ".uv_cache",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".codex",
        ".tools",
        "graphify-out",
    }
    ignored.update(name for name in names if name.endswith((".pyc", ".pyo", ".pyd")))
    return ignored.intersection(names)


def copy_source(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    if source.is_dir():
        shutil.copytree(source, destination, ignore=ignore_names)
    else:
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination / source.name)


def scrubbed_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in API_ENV_VARS:
        env[key] = ""
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_graphify(graphify_project: Path, copied_source: Path, log_path: Path) -> int:
    command = [
        "uv",
        "run",
        "--no-cache",
        "--project",
        str(graphify_project),
        "python",
        "-m",
        "graphify",
        "update",
        str(copied_source),
    ]
    result = subprocess.run(
        command,
        cwd=WORKSPACE,
        env=scrubbed_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log_path.write_text(result.stdout, encoding="utf-8")
    print(result.stdout, end="")
    return int(result.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Graphify code-only update against a sandboxed copy of an allowed source path.")
    parser.add_argument("--graphify-project", type=Path, required=True, help="Sandboxed Graphify checkout/project path.")
    parser.add_argument("--source", type=Path, required=True, help="Public-safe source path to copy into the sandbox before running.")
    parser.add_argument("--work-root", type=Path, default=DEFAULT_WORK_ROOT)
    args = parser.parse_args()

    graphify_project = args.graphify_project.resolve()
    if not graphify_project.exists():
        raise FileNotFoundError(f"Graphify project path does not exist: {graphify_project}")
    source = assert_allowed_source(args.source)

    run_dir = args.work_root / f"graphify-wrapper-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    copied_source = run_dir / safe_name(source.name)
    run_dir.mkdir(parents=True, exist_ok=True)
    copy_source(source, copied_source)

    log_path = run_dir / "graphify-update.stdout.log"
    return_code = run_graphify(graphify_project, copied_source, log_path)
    graph_dir = copied_source / "graphify-out"
    metadata = {
        "started_at": utc_now(),
        "graphify_project": str(graphify_project),
        "source": str(source),
        "copied_source": str(copied_source),
        "graph_dir": str(graph_dir),
        "log_path": str(log_path),
        "return_code": return_code,
        "api_env_vars_cleared": list(API_ENV_VARS),
        "private_roots_refused": [str(path) for path in FORBIDDEN_ROOTS],
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
