from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


DEFAULT_EXEC_BACKEND_COMMAND = 'omx exec --skip-git-repo-check --sandbox read-only --output-last-message "{output_last_message}" -'
DEFAULT_TEAM_LAUNCH_COMMAND = 'omx team {workers}:{agent_type} "{task_description}"'
DEFAULT_TEAM_AWAIT_COMMAND = 'omx team await {team_name} --timeout-ms {timeout_ms} --json'


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a real OMX/Codex backend that returns team_result JSON.")
    parser.add_argument("task_id")
    parser.add_argument("prompt_file")
    parser.add_argument("run_dir", nargs="?")
    parser.add_argument("--runtime", choices=["exec", "team"], default=os.environ.get("OMX_TEAM_PATCH_RUNTIME", "exec"))
    parser.add_argument("--backend-command", default=None)
    parser.add_argument("--output-last-message", default=None)
    parser.add_argument("--team-launch-command", default=None)
    parser.add_argument("--team-await-command", default=None)
    parser.add_argument("--team-name", default=None)
    parser.add_argument("--team-workers", default=os.environ.get("OMX_TEAM_PATCH_TEAM_WORKERS", "3"))
    parser.add_argument("--team-agent-type", default=os.environ.get("OMX_TEAM_PATCH_TEAM_AGENT_TYPE", "executor"))
    parser.add_argument("--team-timeout-ms", default=os.environ.get("OMX_TEAM_PATCH_TEAM_TIMEOUT_MS", "600000"))
    args = parser.parse_args()

    prompt_file = Path(args.prompt_file)
    if not prompt_file.exists():
        print(f"prompt file does not exist: {prompt_file}", file=sys.stderr)
        return 2

    run_dir = Path(args.run_dir or ".")
    run_dir.mkdir(parents=True, exist_ok=True)
    output_last_message = Path(args.output_last_message) if args.output_last_message else _default_output_path(run_dir)
    output_last_message.parent.mkdir(parents=True, exist_ok=True)

    prompt = _build_prompt(args.task_id, prompt_file)
    if args.runtime == "team":
        completed = _run_team_runtime(args, prompt_file, run_dir, output_last_message, prompt)
    else:
        command = _render_exec_backend_command(args.backend_command, args.task_id, prompt_file, run_dir, output_last_message)
        completed = subprocess.run(
            command,
            shell=True,
            input=prompt,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
        _write_backend_logs(run_dir, {"runtime": "exec", "command": command, "completed": completed})

    raw_output = output_last_message.read_text(encoding="utf-8", errors="replace") if output_last_message.exists() else completed.stdout
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0:
        if raw_output:
            print(raw_output, end="" if raw_output.endswith("\n") else "\n")
        return completed.returncode

    try:
        payload = json.loads(_extract_json(raw_output))
    except json.JSONDecodeError:
        print(raw_output, end="" if raw_output.endswith("\n") else "\n")
        return 0

    print(json.dumps(payload, ensure_ascii=False))
    return 0


def _default_output_path(run_dir: Path) -> Path:
    return run_dir / "attempts" / "omx_team_patch_last_message.txt"


def _runtime_prompt_path(run_dir: Path) -> Path:
    return run_dir / "attempts" / "omx_team_runtime_prompt.txt"


def _render_exec_backend_command(
    backend_command: str | None,
    task_id: str,
    prompt_file: Path,
    run_dir: Path,
    output_last_message: Path,
) -> str:
    template = backend_command or os.environ.get("OMX_TEAM_PATCH_COMMAND") or DEFAULT_EXEC_BACKEND_COMMAND
    return template.format(
        task_id=task_id,
        prompt_file=str(prompt_file),
        run_dir=str(run_dir),
        output_last_message=str(output_last_message),
    )


def _run_team_runtime(
    args: argparse.Namespace,
    prompt_file: Path,
    run_dir: Path,
    output_last_message: Path,
    prompt: str,
) -> subprocess.CompletedProcess[str]:
    runtime_prompt_file = _runtime_prompt_path(run_dir)
    runtime_prompt_file.parent.mkdir(parents=True, exist_ok=True)
    task_description = _build_team_task_description(args.task_id, prompt_file, runtime_prompt_file, output_last_message)
    runtime_prompt_file.write_text(
        "\n".join(
            [
                prompt,
                "",
                "Durable OMX team runtime contract:",
                f"- Write the final team_result JSON to: {output_last_message}",
                "- Do not edit the target worktree directly.",
                "- The Orchestrator will validate and apply the embedded patch_plan.",
            ]
        ),
        encoding="utf-8",
    )

    launch_command = _render_team_command(
        args.team_launch_command or os.environ.get("OMX_TEAM_PATCH_TEAM_LAUNCH_COMMAND") or DEFAULT_TEAM_LAUNCH_COMMAND,
        args=args,
        prompt_file=prompt_file,
        run_dir=run_dir,
        runtime_prompt_file=runtime_prompt_file,
        output_last_message=output_last_message,
        task_description=task_description,
        team_name=args.team_name or "",
    )
    launch = subprocess.run(
        launch_command,
        shell=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    team_name = args.team_name or _extract_team_name(launch.stdout + "\n" + launch.stderr)
    await_result: subprocess.CompletedProcess[str] | None = None
    await_command = ""
    if launch.returncode == 0 and team_name:
        await_command = _render_team_command(
            args.team_await_command or os.environ.get("OMX_TEAM_PATCH_TEAM_AWAIT_COMMAND") or DEFAULT_TEAM_AWAIT_COMMAND,
            args=args,
            prompt_file=prompt_file,
            run_dir=run_dir,
            runtime_prompt_file=runtime_prompt_file,
            output_last_message=output_last_message,
            task_description=task_description,
            team_name=team_name,
        )
        if await_command.strip():
            await_result = subprocess.run(
                await_command,
                shell=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
            )

    completed = _merge_team_completed_process(
        launch_command,
        launch,
        await_command,
        await_result,
        output_last_message,
        team_name,
    )
    _write_backend_logs(
        run_dir,
        {
            "runtime": "team",
            "command": launch_command,
            "completed": completed,
            "team_name": team_name,
            "runtime_prompt_file": str(runtime_prompt_file),
            "team_result_path": str(output_last_message),
            "launch": launch,
            "await_command": await_command,
            "await": await_result,
        },
    )
    return completed


def _build_team_task_description(
    task_id: str,
    prompt_file: Path,
    runtime_prompt_file: Path,
    output_last_message: Path,
) -> str:
    return (
        f"Run task {task_id}. Read the full Orchestrator prompt from {runtime_prompt_file}. "
        f"Write only valid team_result JSON to {output_last_message}. "
        f"Original prompt file: {prompt_file}. Do not edit the worktree directly."
    )


def _render_team_command(
    template: str,
    *,
    args: argparse.Namespace,
    prompt_file: Path,
    run_dir: Path,
    runtime_prompt_file: Path,
    output_last_message: Path,
    task_description: str,
    team_name: str,
) -> str:
    return template.format(
        task_id=args.task_id,
        prompt_file=str(prompt_file),
        run_dir=str(run_dir),
        runtime_prompt_file=str(runtime_prompt_file),
        output_last_message=str(output_last_message),
        team_result_path=str(output_last_message),
        task_description=task_description.replace('"', '\\"'),
        workers=args.team_workers,
        agent_type=args.team_agent_type,
        timeout_ms=args.team_timeout_ms,
        team_name=team_name,
    )


def _extract_team_name(output: str) -> str:
    try:
        payload = json.loads(_extract_json(output))
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        for key in ("team_name", "name", "team"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    for token in output.replace("=", " ").replace(":", " ").split():
        cleaned = token.strip().strip(",.;")
        if cleaned.startswith("team-") or cleaned.startswith("team_"):
            return cleaned
    return ""


def _merge_team_completed_process(
    command: str,
    launch: subprocess.CompletedProcess[str],
    await_command: str,
    await_result: subprocess.CompletedProcess[str] | None,
    output_last_message: Path,
    team_name: str,
) -> subprocess.CompletedProcess[str]:
    stdout_parts = [launch.stdout or ""]
    stderr_parts = [launch.stderr or ""]
    returncode = launch.returncode
    if await_result is not None:
        stdout_parts.append(await_result.stdout or "")
        stderr_parts.append(await_result.stderr or "")
        if await_result.returncode != 0:
            returncode = await_result.returncode
    if output_last_message.exists():
        stdout_parts.append(output_last_message.read_text(encoding="utf-8", errors="replace"))
    elif launch.returncode == 0:
        if returncode == 0:
            returncode = 2
        if not team_name:
            stderr_parts.append("team runtime did not expose a team name and did not write team_result JSON")
        else:
            stderr_parts.append(f"team runtime finished without writing team_result JSON: team_name={team_name}")
    return subprocess.CompletedProcess(
        args=command,
        returncode=returncode,
        stdout="\n".join(part for part in stdout_parts if part),
        stderr="\n".join(part for part in stderr_parts if part),
    )


def _build_prompt(task_id: str, prompt_file: Path) -> str:
    original = prompt_file.read_text(encoding="utf-8", errors="replace")
    schema = {
        "schema_version": "1.0",
        "task_id": task_id,
        "status": "completed",
        "roles": {
            "planner": {"status": "completed", "artifact": "team_plan.json", "summary": "short plan"},
            "coder": {"status": "completed", "artifact": "patch_plan.json", "summary": "patch generated"},
            "reviewer": {"status": "completed", "artifact": "review.json", "summary": "review passed"},
        },
        "artifacts": {
            "patch_plan": {
                "schema_version": "1.0",
                "task_id": task_id,
                "summary": "short summary",
                "operations": [
                    {
                        "op": "replace_text",
                        "path": "relative/path.py",
                        "old": "exact old text",
                        "new": "replacement text",
                    }
                ],
            },
            "review": {
                "schema_version": "1.0",
                "task_id": task_id,
                "pass": True,
                "confidence": 90,
                "summary": "safe and scoped",
                "issues": [],
                "blocking": False,
                "recommended_next_action": "pass",
            },
        },
        "diagnostics": [],
    }
    return "\n".join(
        [
            "You are OMX orchestrating a coding team through Codex.",
            "Return only one valid team_result JSON object. Do not output Markdown, prose, or fenced code.",
            "Do not edit files directly. Orchestrator will validate and apply the embedded patch_plan.",
            "The JSON must use this exact shape and the same task_id:",
            json.dumps(schema, ensure_ascii=False),
            "",
            "Original Orchestrator prompt:",
            original,
        ]
    )


def _extract_json(raw_output: str) -> str:
    text = raw_output.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    if text.startswith("{"):
        return text
    return text


def _write_backend_logs(run_dir: Path, details: dict[str, object]) -> None:
    log_dir = run_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    completed = details["completed"]
    if not isinstance(completed, subprocess.CompletedProcess):
        raise TypeError("completed must be a subprocess.CompletedProcess")
    payload = {
        "runtime": details.get("runtime", "exec"),
        "command": details.get("command", ""),
        "returncode": completed.returncode,
        "stdout_preview": completed.stdout[:4000],
        "stderr_preview": completed.stderr[:4000],
    }
    if details.get("runtime") == "team":
        payload.update(
            {
                "team_name": details.get("team_name", ""),
                "runtime_prompt_file": details.get("runtime_prompt_file", ""),
                "team_result_path": details.get("team_result_path", ""),
                "await_command": details.get("await_command", ""),
            }
        )
        launch = details.get("launch")
        if isinstance(launch, subprocess.CompletedProcess):
            payload["launch_returncode"] = launch.returncode
            payload["launch_stdout_preview"] = launch.stdout[:4000]
            payload["launch_stderr_preview"] = launch.stderr[:4000]
        await_result = details.get("await")
        if isinstance(await_result, subprocess.CompletedProcess):
            payload["await_returncode"] = await_result.returncode
            payload["await_stdout_preview"] = await_result.stdout[:4000]
            payload["await_stderr_preview"] = await_result.stderr[:4000]
    (log_dir / "omx_team_patch_backend.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
