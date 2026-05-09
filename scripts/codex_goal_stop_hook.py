from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[1]
LEARNINGS_DIR = WORKSPACE / "learnings"
BRIDGE_DIR = WORKSPACE / "data" / "orchestrator_bridge"
CONFIG_PATH = BRIDGE_DIR / "config.json"
STATE_PATH = BRIDGE_DIR / "notified_goals.json"
LOG_PATH = BRIDGE_DIR / "stop_hook.log"
NOTIFICATIONS_DIR = BRIDGE_DIR / "notifications"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def casefold_path(path: Path) -> str:
    return str(path.resolve()).casefold()


def inside_workspace(path: Path) -> bool:
    try:
        resolved = casefold_path(path)
        workspace = casefold_path(WORKSPACE)
    except OSError:
        return False
    return resolved == workspace or resolved.startswith(workspace + os.sep)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def log_event(message: str, payload: Any | None = None) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"[{utc_now()}] {message}\n")
        if payload is not None:
            handle.write(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n")


def done_files() -> list[Path]:
    return sorted(LEARNINGS_DIR.glob("goal-*.done"), key=lambda path: path.stat().st_mtime_ns)


def file_fingerprint(path: Path) -> dict[str, Any]:
    stat = path.stat()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "path": str(path),
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
        "sha256": digest,
    }


def goal_id_from_done(path: Path) -> str:
    return path.name.removesuffix(".done")


def baseline_state(reason: str) -> dict[str, Any]:
    state = {
        "version": 1,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "notified": {},
    }
    for done in done_files():
        goal_id = goal_id_from_done(done)
        state["notified"][goal_id] = {
            **file_fingerprint(done),
            "notified_at": None,
            "result": "baseline",
            "reason": reason,
        }
    return state


def load_state() -> dict[str, Any]:
    state = read_json(STATE_PATH, None)
    if not isinstance(state, dict) or not isinstance(state.get("notified"), dict):
        state = baseline_state("preexisting_done_marker")
        atomic_write_json(STATE_PATH, state)
        log_event("initialized notification baseline", {"done_count": len(state["notified"])})
    return state


def load_config() -> dict[str, Any]:
    config = read_json(CONFIG_PATH, {})
    if not isinstance(config, dict):
        config = {}
    return config


def build_message(goal_id: str, done_file: Path) -> str:
    done_text = done_file.read_text(encoding="utf-8", errors="replace").strip()
    return (
        f"CLI Stop hook notification: {goal_id} wrote a done/blocker marker.\n\n"
        f"Done marker: {done_file}\n"
        f"Summary: {done_text}\n\n"
        "Autonomous continuation instructions for the orchestrator:\n"
        "1. Treat the CLI goal named above as closed. Do not keep working inside that same goal or repeat its batches unless the audit finds a concrete defect.\n"
        "2. If the marker begins with GOAL_*_DONE, audit the goal outputs, run the smallest validation needed, and apply any local integration fixes that are clearly in scope.\n"
        "3. If the marker begins with GOAL_*_BLOCKED, inspect the blocker and either fix it locally if safe or stop with the exact user/orchestrator decision needed.\n"
        "4. After audit/fixes, read docs/handoff.md and the latest learnings checkpoint, update the project plan, and continue with the next eligible project task without waiting for the user.\n"
        "5. Do short deterministic work directly in the app thread. Launch the next bounded interactive CLI /goal only for genuinely long-running work with a clear stopping condition.\n"
        "6. Stop only if the project is actually complete, a precise blocker requires user judgment, or safety rules prevent continuing."
    )


def notify_goal(goal_id: str, done_file: Path, config: dict[str, Any]) -> dict[str, Any]:
    thread_id = config.get("orchestrator_thread_id")
    if not thread_id:
        raise RuntimeError(f"Missing orchestrator_thread_id in {CONFIG_PATH}")
    timeout = float(config.get("notify_timeout_seconds") or 45)
    command = [
        sys.executable,
        "-B",
        str(WORKSPACE / "scripts" / "codex_app_notify.py"),
        "--thread-id",
        str(thread_id),
        "--goal-id",
        goal_id,
        "--done-file",
        str(done_file),
        "--message",
        build_message(goal_id, done_file),
        "--model",
        str(config.get("model") or "gpt-5.5"),
        "--reasoning",
        str(config.get("reasoning") or "xhigh"),
        "--timeout",
        str(timeout),
        "--log",
        str(BRIDGE_DIR / "codex_app_notify.log"),
    ]
    log_event("notifying orchestrator", {"goal_id": goal_id, "command": command})
    completed = subprocess.run(
        command,
        cwd=str(WORKSPACE),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout + 15,
    )
    result = {
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }
    if completed.returncode != 0:
        raise RuntimeError(f"notify command failed: {result}")
    return result


def select_new_done(state: dict[str, Any]) -> Path | None:
    notified = state.get("notified", {})
    for done in reversed(done_files()):
        goal_id = goal_id_from_done(done)
        fingerprint = file_fingerprint(done)
        previous = notified.get(goal_id)
        if not isinstance(previous, dict):
            return done
        if previous.get("sha256") != fingerprint["sha256"] or previous.get("mtime_ns") != fingerprint["mtime_ns"]:
            return done
    return None


def mark_result(state: dict[str, Any], goal_id: str, done_file: Path, result: str, details: dict[str, Any]) -> None:
    state.setdefault("notified", {})[goal_id] = {
        **file_fingerprint(done_file),
        "notified_at": utc_now(),
        "result": result,
        "details": details,
    }
    state["updated_at"] = utc_now()
    atomic_write_json(STATE_PATH, state)
    NOTIFICATIONS_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_json(NOTIFICATIONS_DIR / f"{goal_id}.json", state["notified"][goal_id])


def hook_response(system_message: str | None = None) -> int:
    payload: dict[str, Any] = {"continue": True, "suppressOutput": True}
    if system_message:
        payload["systemMessage"] = system_message
    sys.stdout.write(json.dumps(payload, ensure_ascii=True))
    return 0


def run_hook(event: dict[str, Any], dry_run: bool = False) -> tuple[str, dict[str, Any]]:
    hook_event_name = event.get("hook_event_name")
    cwd = Path(str(event.get("cwd") or os.getcwd()))
    if hook_event_name and hook_event_name != "Stop":
        return "ignored non-Stop hook event", {"hook_event_name": hook_event_name}
    if not inside_workspace(cwd):
        return "ignored hook outside workspace", {"cwd": str(cwd)}

    BRIDGE_DIR.mkdir(parents=True, exist_ok=True)
    state = load_state()
    done = select_new_done(state)
    if done is None:
        return "no new goal done marker", {"known_goals": len(state.get("notified", {}))}

    goal_id = goal_id_from_done(done)
    if dry_run:
        return "dry-run would notify orchestrator", {"goal_id": goal_id, "done_file": str(done)}

    try:
        result = notify_goal(goal_id, done, load_config())
    except Exception as exc:
        details = {"error_type": type(exc).__name__, "error": str(exc)}
        log_event("notify failed", {"goal_id": goal_id, **details})
        return f"notify failed for {goal_id}", details

    mark_result(state, goal_id, done, "notified", result)
    log_event("notify succeeded", {"goal_id": goal_id, "result": result})
    return f"notified orchestrator for {goal_id}", {"goal_id": goal_id}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Codex CLI Stop hook for goal completion notifications.")
    parser.add_argument("--initialize-baseline", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.initialize_baseline:
        state = baseline_state("preexisting_done_marker_at_install")
        atomic_write_json(STATE_PATH, state)
        log_event("baseline initialized by explicit command", {"done_count": len(state["notified"])})
        print(json.dumps({"ok": True, "baselined": sorted(state["notified"].keys())}, indent=2))
        return 0

    raw_stdin = sys.stdin.read()
    try:
        event = json.loads(raw_stdin) if raw_stdin.strip() else {}
    except json.JSONDecodeError as exc:
        log_event("invalid hook stdin", {"error": str(exc), "stdin": raw_stdin[:1000]})
        return hook_response("Goal Stop hook received invalid JSON; see bridge log.")

    try:
        message, details = run_hook(event, dry_run=args.dry_run)
        log_event(message, details)
        return hook_response(message if message.startswith("notify failed") else None)
    except Exception as exc:
        log_event("unexpected hook failure", {"error_type": type(exc).__name__, "error": str(exc)})
        return hook_response("Goal Stop hook failed unexpectedly; see bridge log.")


if __name__ == "__main__":
    sys.exit(main())
