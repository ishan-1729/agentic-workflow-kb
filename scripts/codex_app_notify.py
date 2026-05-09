from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_LOG = WORKSPACE / "data" / "cli_goal_logs" / "codex_app_notify.log"


class AppServerClient:
    def __init__(self, log_path: Path, timeout: float) -> None:
        self.log_path = log_path
        self.timeout = timeout
        self.proc: subprocess.Popen[str] | None = None
        self._next_id = 1
        self._responses: dict[int, dict[str, Any]] = {}
        self._notifications: list[dict[str, Any]] = []
        self._condition = threading.Condition()
        self._reader: threading.Thread | None = None

    def start(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.proc = subprocess.Popen(
            ["codex", "app-server", "--listen", "stdio://"],
            cwd=str(WORKSPACE),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        self._reader = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader.start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def close(self) -> None:
        if not self.proc:
            return
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass

    def _append_log(self, prefix: str, line: str) -> None:
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{prefix} {line}\n")

    def _read_stdout(self) -> None:
        assert self.proc and self.proc.stdout
        for line in self.proc.stdout:
            line = line.rstrip("\n")
            if not line:
                continue
            self._append_log("stdout", line)
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            with self._condition:
                msg_id = message.get("id")
                if isinstance(msg_id, int):
                    self._responses[msg_id] = message
                else:
                    self._notifications.append(message)
                self._condition.notify_all()

    def _read_stderr(self) -> None:
        assert self.proc and self.proc.stderr
        for line in self.proc.stderr:
            self._append_log("stderr", line.rstrip("\n"))

    def send_notification(self, method: str, params: dict[str, Any] | None = None) -> None:
        assert self.proc and self.proc.stdin
        message: dict[str, Any] = {"method": method}
        if params is not None:
            message["params"] = params
        encoded = json.dumps(message, ensure_ascii=False)
        self._append_log("send", encoded)
        self.proc.stdin.write(encoded + "\n")
        self.proc.stdin.flush()

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        assert self.proc and self.proc.stdin
        msg_id = self._next_id
        self._next_id += 1
        message: dict[str, Any] = {"method": method, "id": msg_id}
        if params is not None:
            message["params"] = params
        encoded = json.dumps(message, ensure_ascii=False)
        self._append_log("send", encoded)
        self.proc.stdin.write(encoded + "\n")
        self.proc.stdin.flush()

        deadline = time.monotonic() + self.timeout
        with self._condition:
            while msg_id not in self._responses:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"Timed out waiting for {method} response id={msg_id}")
                self._condition.wait(timeout=remaining)
            response = self._responses.pop(msg_id)
        if "error" in response:
            raise RuntimeError(f"{method} failed: {response['error']}")
        return response


def build_prompt(args: argparse.Namespace) -> str:
    if args.message:
        return args.message
    done_text = ""
    if args.done_file and args.done_file.exists():
        done_text = args.done_file.read_text(encoding="utf-8", errors="replace").strip()
    goal = args.goal_id or "unknown-goal"
    return (
        f"CLI goal completion notification for {goal}.\n\n"
        f"Done marker: {args.done_file}\n"
        f"Summary: {done_text}\n\n"
        "Autonomous continuation instructions for the orchestrator:\n"
        "1. Treat the CLI goal named above as closed. Do not keep working inside that same goal or repeat its batches unless the audit finds a concrete defect.\n"
        "2. If the marker begins with GOAL_*_DONE, audit the goal outputs, run the smallest validation needed, and apply any local integration fixes that are clearly in scope.\n"
        "3. If the marker begins with GOAL_*_BLOCKED, inspect the blocker and either fix it locally if safe or stop with the exact user/orchestrator decision needed.\n"
        "4. After audit/fixes, read docs/handoff.md and the latest learnings checkpoint, update the project plan, and continue with the next eligible project task without waiting for the user.\n"
        "5. Do short deterministic work directly in the app thread. Launch the next bounded interactive CLI /goal only for genuinely long-running work with a clear stopping condition.\n"
        "6. Stop only if the project is actually complete, a precise blocker requires user judgment, or safety rules prevent continuing."
    )


def compact_result(result: dict[str, Any]) -> dict[str, Any]:
    compact = dict(result)
    resume = compact.get("thread_resume")
    if isinstance(resume, dict):
        thread = resume.get("thread")
        if isinstance(thread, dict):
            compact["thread_resume"] = {
                "thread": {
                    "id": thread.get("id"),
                    "name": thread.get("name"),
                    "ephemeral": thread.get("ephemeral"),
                    "turn_count": len(thread.get("turns") or []),
                }
            }
    turn_start = compact.get("turn_start")
    if isinstance(turn_start, dict):
        turn = turn_start.get("turn")
        if isinstance(turn, dict):
            compact["turn_start"] = {
                "turn": {
                    "id": turn.get("id"),
                    "status": turn.get("status"),
                    "error": turn.get("error"),
                    "item_count": len(turn.get("items") or []),
                }
            }
    return compact


def notify(args: argparse.Namespace) -> dict[str, Any]:
    thread_id = args.thread_id
    if not thread_id:
        raise SystemExit("--thread-id is required")
    client = AppServerClient(args.log, args.timeout)
    client.start()
    try:
        client.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "agentic_workflow_goal_notifier",
                    "title": "Agentic Workflow Goal Notifier",
                    "version": "0.1.0",
                },
                "capabilities": {"experimentalApi": True},
            },
        )
        client.send_notification("initialized", {})
        resume = client.request("thread/resume", {"threadId": thread_id})
        if args.resume_only:
            return {"ok": True, "mode": "resume_only", "thread_resume": resume.get("result")}
        prompt = build_prompt(args)
        turn = client.request(
            "turn/start",
            {
                "threadId": thread_id,
                "input": [{"type": "text", "text": prompt}],
                "cwd": str(WORKSPACE),
                "approvalPolicy": "never",
                "sandboxPolicy": {
                    "type": "workspaceWrite",
                    "writableRoots": [str(WORKSPACE)],
                    "networkAccess": True,
                },
                "model": args.model,
                "effort": args.reasoning,
            },
        )
        return {"ok": True, "thread_resume": resume.get("result"), "turn_start": turn.get("result")}
    finally:
        client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Notify a Codex app thread using codex app-server JSON-RPC.")
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--goal-id")
    parser.add_argument("--done-file", type=Path)
    parser.add_argument("--message")
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--reasoning", default="xhigh")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--resume-only", action="store_true", help="Only test thread/resume; do not start a turn.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = notify(args)
    print(json.dumps(compact_result(result), indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
