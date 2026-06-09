from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


REVIEW_ACTIONS = {"pass", "fix", "halt"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Stable wrapper for Codex/OMX style external agents.")
    parser.add_argument("--runtime", choices=["codex", "omx", "shell"], required=True)
    parser.add_argument("--role", choices=["coder", "fixer", "reviewer"], required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--reason-file")
    parser.add_argument("--worktree", default=".")
    parser.add_argument("--backend-command")
    parser.add_argument("--stdin-prompt", action="store_true")
    parser.add_argument("--output-last-message")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    prompt_file = Path(args.prompt_file)
    run_dir = Path(args.run_dir)
    worktree = Path(args.worktree)
    reason_file = Path(args.reason_file) if args.reason_file else None
    if not prompt_file.exists():
        print(f"prompt file does not exist: {prompt_file}", file=sys.stderr)
        return 2
    if reason_file and not reason_file.exists():
        print(f"reason file does not exist: {reason_file}", file=sys.stderr)
        return 2

    if args.dry_run or not _resolve_backend_command(args):
        return _dry_run(args, prompt_file, run_dir, reason_file)

    command = _render_backend_command(args, prompt_file, run_dir, reason_file, worktree)
    prompt_text = prompt_file.read_text(encoding="utf-8") if args.stdin_prompt else None
    completed = subprocess.run(
        command,
        cwd=worktree,
        shell=True,
        encoding="utf-8",
        errors="replace",
        input=prompt_text,
        capture_output=True,
    )
    _write_wrapper_log(
        run_dir,
        [
            f"runtime={args.runtime}",
            f"role={args.role}",
            f"task_id={args.task_id}",
            f"prompt_file={prompt_file}",
            f"reason_file={reason_file or ''}",
            f"backend_command={command}",
            f"exit_code={completed.returncode}",
            "---",
        ],
    )
    stdout = _read_output_last_message(args, completed.stdout)
    if stdout:
        print(stdout, end="" if stdout.endswith("\n") else "\n")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    return completed.returncode


def _resolve_backend_command(args: argparse.Namespace) -> str | None:
    if args.backend_command:
        return args.backend_command
    env_key = f"OMX_{args.runtime.upper()}_{args.role.upper()}_COMMAND"
    return os.environ.get(env_key)


def _render_backend_command(
    args: argparse.Namespace,
    prompt_file: Path,
    run_dir: Path,
    reason_file: Path | None,
    worktree: Path,
) -> str:
    template = _resolve_backend_command(args)
    if not template:
        raise ValueError("backend command is required outside dry-run mode")
    return template.format(
        runtime=args.runtime,
        role=args.role,
        task_id=args.task_id,
        prompt_file=str(prompt_file),
        run_dir=str(run_dir),
        reason_file=str(reason_file or ""),
        worktree=str(worktree),
        output_last_message=str(_output_last_message_path(args, run_dir)),
    )


def _output_last_message_path(args: argparse.Namespace, run_dir: Path) -> Path:
    if args.output_last_message:
        return Path(args.output_last_message)
    return run_dir / "attempts" / "external_agent_last_message.txt"


def _read_output_last_message(args: argparse.Namespace, fallback_stdout: str) -> str:
    if not args.output_last_message:
        return fallback_stdout
    path = Path(args.output_last_message)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return fallback_stdout


def _dry_run(args: argparse.Namespace, prompt_file: Path, run_dir: Path, reason_file: Path | None) -> int:
    prompt_text = prompt_file.read_text(encoding="utf-8")
    reason_text = reason_file.read_text(encoding="utf-8") if reason_file else ""
    _write_wrapper_log(
        run_dir,
        [
            f"runtime={args.runtime}",
            f"role={args.role}",
            f"task_id={args.task_id}",
            f"prompt_file={prompt_file}",
            f"reason_file={reason_file or ''}",
            f"prompt_chars={len(prompt_text)}",
            f"reason_chars={len(reason_text)}",
            "dry_run=true",
            "---",
        ],
    )

    if args.role == "reviewer":
        print(json.dumps(_review_payload(args.task_id), ensure_ascii=False))
    else:
        print(f"{args.runtime} {args.role} dry-run completed for {args.task_id}")
    return 0


def _write_wrapper_log(run_dir: Path, lines: list[str]) -> None:
    log_dir = run_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / "external_agent_wrapper.log").open("a", encoding="utf-8") as file:
        file.write("\n".join(lines) + "\n")


def _review_payload(task_id: str) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "task_id": task_id,
        "pass": True,
        "confidence": 90,
        "summary": "dry-run wrapper review passed",
        "issues": [],
        "blocking": False,
        "recommended_next_action": "pass" if "pass" in REVIEW_ACTIONS else "halt",
    }


if __name__ == "__main__":
    raise SystemExit(main())
