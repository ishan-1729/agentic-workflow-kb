from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from winpty import PtyProcess


WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = WORKSPACE / "data" / "cli_goal_logs"
ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07]*(?:\x07|\x1b\\)|\x1b[()][A-Za-z0-9]")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def extract_goal(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8")
    blocks = re.findall(r"```text\s*(.*?)```", text, flags=re.DOTALL)
    for block in blocks:
        candidate = block.strip()
        if candidate.startswith("/goal"):
            return candidate
    raise ValueError(f"No fenced text block starting with /goal found in {md_path}")


def write_status(status_file: Path, payload: dict) -> None:
    status_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = status_file.with_suffix(status_file.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(status_file)


def reader_loop(process: PtyProcess, raw_log: Path, clean_log: Path, stop: threading.Event) -> None:
    with raw_log.open("a", encoding="utf-8", errors="replace", newline="") as raw_handle, clean_log.open(
        "a", encoding="utf-8", errors="replace", newline=""
    ) as clean_handle:
        while not stop.is_set():
            try:
                chunk = process.read(4096)
            except EOFError:
                break
            except Exception as exc:
                raw_handle.write(f"\n[runner-read-error {type(exc).__name__}: {exc}]\n")
                clean_handle.write(f"\n[runner-read-error {type(exc).__name__}: {exc}]\n")
                raw_handle.flush()
                clean_handle.flush()
                break
            if not chunk:
                time.sleep(0.1)
                continue
            raw_handle.write(chunk)
            clean_handle.write(strip_ansi(chunk))
            raw_handle.flush()
            clean_handle.flush()


def notify_orchestrator(args: argparse.Namespace, runner_log: Path) -> None:
    if not args.notify_thread_id:
        return
    notifier = args.workspace / "scripts" / "codex_app_notify.py"
    command = [
        sys.executable,
        "-B",
        str(notifier),
        "--thread-id",
        args.notify_thread_id,
        "--goal-id",
        args.goal_id,
        "--done-file",
        str(args.done_file),
        "--timeout",
        str(args.notify_timeout),
    ]
    if args.notify_message:
        command.extend(["--message", args.notify_message])
    with runner_log.open("a", encoding="utf-8") as handle:
        handle.write(f"[{utc_now()}] notifying orchestrator thread {args.notify_thread_id}\n")
        handle.write(f"[{utc_now()}] notify argv: {command}\n")
    try:
        completed = subprocess.run(
            command,
            cwd=str(args.workspace),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=args.notify_timeout + 10,
        )
    except Exception as exc:
        with runner_log.open("a", encoding="utf-8") as handle:
            handle.write(f"[{utc_now()}] notify exception {type(exc).__name__}: {exc}\n")
        return
    with runner_log.open("a", encoding="utf-8") as handle:
        handle.write(f"[{utc_now()}] notify returncode={completed.returncode}\n")
        if completed.stdout.strip():
            handle.write(f"[{utc_now()}] notify stdout: {completed.stdout.strip()}\n")
        if completed.stderr.strip():
            handle.write(f"[{utc_now()}] notify stderr: {completed.stderr.strip()}\n")


def wait_for_stop_hook_notification(
    args: argparse.Namespace,
    status_file: Path,
    runner_log: Path,
    process: PtyProcess,
    started_at: str,
    start_time: float,
) -> bool:
    notification_file = args.workspace / "data" / "orchestrator_bridge" / "notifications" / f"{args.goal_id}.json"
    deadline = time.time() + args.post_done_hook_wait
    with runner_log.open("a", encoding="utf-8") as handle:
        handle.write(
            f"[{utc_now()}] waiting up to {args.post_done_hook_wait}s for CLI Stop hook notification "
            f"{notification_file}\n"
        )
    while time.time() < deadline:
        notification_exists = notification_file.exists()
        write_status(
            status_file,
            {
                "goal_id": args.goal_id,
                "state": "waiting_for_stop_hook_notification",
                "started_at": started_at,
                "updated_at": utc_now(),
                "elapsed_seconds": round(time.time() - start_time, 1),
                "process_alive": process.isalive(),
                "done_file": str(args.done_file),
                "done_file_exists": args.done_file.exists(),
                "goal_md": str(args.goal_md),
                "notification_file": str(notification_file),
                "notification_file_exists": notification_exists,
            },
        )
        if notification_exists:
            with runner_log.open("a", encoding="utf-8") as handle:
                handle.write(f"[{utc_now()}] Stop hook notification marker detected\n")
            return True
        time.sleep(2)
    with runner_log.open("a", encoding="utf-8") as handle:
        handle.write(f"[{utc_now()}] Stop hook notification marker was not detected before timeout\n")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an interactive Codex CLI /goal inside a Windows PTY.")
    parser.add_argument("--goal-md", type=Path, required=True)
    parser.add_argument("--goal-id", required=True)
    parser.add_argument("--done-file", type=Path, required=True)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--workspace", type=Path, default=WORKSPACE)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--reasoning", default="xhigh")
    parser.add_argument("--sandbox", default="workspace-write")
    parser.add_argument("--approval", default="never")
    parser.add_argument("--startup-wait", type=float, default=6.0)
    parser.add_argument("--submit-wait", type=float, default=1.0)
    parser.add_argument("--submit-enters", type=int, default=2)
    parser.add_argument("--submit-enter-interval", type=float, default=1.0)
    parser.add_argument("--poll-interval", type=float, default=10.0)
    parser.add_argument("--max-seconds", type=int, default=0, help="0 means no runner timeout.")
    parser.add_argument("--status-file", type=Path)
    parser.add_argument("--notify-thread-id", default=os.environ.get("CODEX_ORCHESTRATOR_THREAD_ID"))
    parser.add_argument("--notify-timeout", type=float, default=45.0)
    parser.add_argument("--notify-message")
    parser.add_argument("--post-done-hook-wait", type=float, default=120.0)
    args = parser.parse_args()

    args.log_dir.mkdir(parents=True, exist_ok=True)
    args.done_file.parent.mkdir(parents=True, exist_ok=True)
    raw_log = args.log_dir / f"{args.goal_id}.raw.log"
    clean_log = args.log_dir / f"{args.goal_id}.clean.log"
    runner_log = args.log_dir / f"{args.goal_id}.runner.log"
    status_file = args.status_file or (args.log_dir / f"{args.goal_id}.status.json")

    goal_text = extract_goal(args.goal_md)
    start_marker = f"[{utc_now()}] starting {args.goal_id}\n"
    runner_log.write_text(start_marker, encoding="utf-8")
    raw_log.write_text(start_marker, encoding="utf-8")
    clean_log.write_text(start_marker, encoding="utf-8")
    start_time = time.time()
    started_at = utc_now()
    write_status(
        status_file,
        {
            "goal_id": args.goal_id,
            "state": "starting",
            "started_at": started_at,
            "updated_at": started_at,
            "elapsed_seconds": 0,
            "process_alive": False,
            "done_file": str(args.done_file),
            "done_file_exists": args.done_file.exists(),
            "goal_md": str(args.goal_md),
            "raw_log": str(raw_log),
            "clean_log": str(clean_log),
            "runner_log": str(runner_log),
        },
    )

    argv = [
        "codex",
        "--disable",
        "fast_mode",
        "-C",
        str(args.workspace),
        "-a",
        args.approval,
        "-s",
        args.sandbox,
        "-m",
        args.model,
        "-c",
        f'model_reasoning_effort="{args.reasoning}"',
        "--no-alt-screen",
    ]
    child_env = os.environ.copy()
    for key in [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ]:
        child_env.pop(key, None)
    child_env["NO_PROXY"] = "localhost,127.0.0.1,::1"
    child_env["no_proxy"] = "localhost,127.0.0.1,::1"
    child_env["UV_CACHE_DIR"] = str(args.workspace / ".uv_cache")
    child_env["UV_LINK_MODE"] = "copy"
    with runner_log.open("a", encoding="utf-8") as handle:
        handle.write(f"[{utc_now()}] argv: {argv}\n")
        handle.write(f"[{utc_now()}] goal_md: {args.goal_md}\n")
        handle.write(f"[{utc_now()}] done_file: {args.done_file}\n")
        handle.write(f"[{utc_now()}] scrubbed proxy env and set UV_CACHE_DIR={child_env['UV_CACHE_DIR']}\n")

    process = PtyProcess.spawn(argv, cwd=str(args.workspace), env=child_env, dimensions=(50, 180))
    write_status(
        status_file,
        {
            "goal_id": args.goal_id,
            "state": "spawned",
            "started_at": started_at,
            "updated_at": utc_now(),
            "elapsed_seconds": round(time.time() - start_time, 1),
            "process_alive": process.isalive(),
            "done_file": str(args.done_file),
            "done_file_exists": args.done_file.exists(),
            "goal_md": str(args.goal_md),
            "raw_log": str(raw_log),
            "clean_log": str(clean_log),
            "runner_log": str(runner_log),
        },
    )
    stop = threading.Event()
    reader = threading.Thread(target=reader_loop, args=(process, raw_log, clean_log, stop), daemon=True)
    reader.start()

    time.sleep(args.startup_wait)
    with runner_log.open("a", encoding="utf-8") as handle:
        handle.write(f"[{utc_now()}] sending goal text ({len(goal_text)} chars)\n")
    process.write("\x1b[200~" + goal_text + "\x1b[201~")
    time.sleep(args.submit_wait)
    for enter_index in range(max(args.submit_enters, 1)):
        with runner_log.open("a", encoding="utf-8") as handle:
            handle.write(f"[{utc_now()}] sending submit enter {enter_index + 1}/{max(args.submit_enters, 1)}\n")
        process.write("\r")
        time.sleep(args.submit_enter_interval)

    detected_done = False
    try:
        while process.isalive():
            write_status(
                status_file,
                {
                    "goal_id": args.goal_id,
                    "state": "running",
                    "started_at": started_at,
                    "updated_at": utc_now(),
                    "elapsed_seconds": round(time.time() - start_time, 1),
                    "process_alive": process.isalive(),
                    "done_file": str(args.done_file),
                    "done_file_exists": args.done_file.exists(),
                    "goal_md": str(args.goal_md),
                    "raw_log": str(raw_log),
                    "clean_log": str(clean_log),
                    "runner_log": str(runner_log),
                },
            )
            if args.done_file.exists():
                detected_done = True
                with runner_log.open("a", encoding="utf-8") as handle:
                    handle.write(f"[{utc_now()}] done file detected; sending /quit\n")
                write_status(
                    status_file,
                    {
                        "goal_id": args.goal_id,
                        "state": "done_file_detected",
                        "started_at": started_at,
                        "updated_at": utc_now(),
                        "elapsed_seconds": round(time.time() - start_time, 1),
                        "process_alive": process.isalive(),
                        "done_file": str(args.done_file),
                        "done_file_exists": True,
                        "goal_md": str(args.goal_md),
                        "raw_log": str(raw_log),
                        "clean_log": str(clean_log),
                        "runner_log": str(runner_log),
                    },
                )
                notified_by_hook = wait_for_stop_hook_notification(
                    args, status_file, runner_log, process, started_at, start_time
                )
                if not notified_by_hook:
                    notify_orchestrator(args, runner_log)
                process.write("/quit\r")
                time.sleep(30)
                if process.isalive():
                    with runner_log.open("a", encoding="utf-8") as handle:
                        handle.write(f"[{utc_now()}] process still alive after /quit; closing PTY without force\n")
                    try:
                        process.close()
                    except Exception as exc:
                        with runner_log.open("a", encoding="utf-8") as handle:
                            handle.write(f"[{utc_now()}] close warning {type(exc).__name__}: {exc}\n")
                break
            if args.max_seconds and time.time() - start_time > args.max_seconds:
                with runner_log.open("a", encoding="utf-8") as handle:
                    handle.write(f"[{utc_now()}] max-seconds reached; leaving process status={process.isalive()}\n")
                write_status(
                    status_file,
                    {
                        "goal_id": args.goal_id,
                        "state": "timeout",
                        "started_at": started_at,
                        "updated_at": utc_now(),
                        "elapsed_seconds": round(time.time() - start_time, 1),
                        "process_alive": process.isalive(),
                        "done_file": str(args.done_file),
                        "done_file_exists": args.done_file.exists(),
                        "goal_md": str(args.goal_md),
                        "raw_log": str(raw_log),
                        "clean_log": str(clean_log),
                        "runner_log": str(runner_log),
                    },
                )
                try:
                    process.terminate(force=True)
                except PermissionError as exc:
                    with runner_log.open("a", encoding="utf-8") as handle:
                        handle.write(f"[{utc_now()}] terminate denied: {exc}\n")
                return 124
            time.sleep(args.poll_interval)
    finally:
        stop.set()
        reader.join(timeout=5)
        with runner_log.open("a", encoding="utf-8") as handle:
            handle.write(f"[{utc_now()}] finished alive={process.isalive()} exit={process.exitstatus}\n")
        pty_reported_alive = process.isalive()
        write_status(
            status_file,
            {
                "goal_id": args.goal_id,
                "state": "finished_done" if detected_done else "finished_without_done",
                "started_at": started_at,
                "updated_at": utc_now(),
                "elapsed_seconds": round(time.time() - start_time, 1),
                "process_alive": False if detected_done else pty_reported_alive,
                "pty_reported_alive": pty_reported_alive,
                "exitstatus": process.exitstatus,
                "done_file": str(args.done_file),
                "done_file_exists": args.done_file.exists(),
                "goal_md": str(args.goal_md),
                "raw_log": str(raw_log),
                "clean_log": str(clean_log),
                "runner_log": str(runner_log),
            },
        )

    if detected_done:
        return 0
    return int(process.exitstatus or 0)


if __name__ == "__main__":
    sys.exit(main())
