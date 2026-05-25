from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/run_external_agent.py")


def test_external_agent_wrapper_dry_run_reviewer_outputs_review_json(tmp_path: Path):
    run_dir = tmp_path / "run"
    prompt = tmp_path / "reviewer_prompt.txt"
    prompt.write_text("Review task", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--runtime",
            "codex",
            "--role",
            "reviewer",
            "--task-id",
            "task-001",
            "--prompt-file",
            str(prompt),
            "--run-dir",
            str(run_dir),
            "--dry-run",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["task_id"] == "task-001"
    assert payload["pass"] is True
    wrapper_log = run_dir / "logs" / "external_agent_wrapper.log"
    assert "role=reviewer" in wrapper_log.read_text(encoding="utf-8")


def test_external_agent_wrapper_passes_rendered_backend_command(tmp_path: Path):
    run_dir = tmp_path / "run"
    prompt = tmp_path / "coder_prompt.txt"
    marker = tmp_path / "marker.txt"
    backend = tmp_path / "backend.py"
    prompt.write_text("Code task", encoding="utf-8")
    backend.write_text(
        "\n".join(
            [
                "import pathlib, sys",
                "pathlib.Path(sys.argv[1]).write_text(sys.argv[2], encoding='utf-8')",
                "print('backend ok')",
            ]
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--runtime",
            "codex",
            "--role",
            "coder",
            "--task-id",
            "task-002",
            "--prompt-file",
            str(prompt),
            "--run-dir",
            str(run_dir),
            "--worktree",
            str(tmp_path),
            "--backend-command",
            f"\"{sys.executable}\" \"{backend}\" \"{marker}\" {{task_id}}",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "backend ok" in completed.stdout
    assert marker.read_text(encoding="utf-8") == "task-002"


def test_external_agent_wrapper_can_pipe_prompt_to_backend_stdin(tmp_path: Path):
    run_dir = tmp_path / "run"
    prompt = tmp_path / "coder_prompt.txt"
    marker = tmp_path / "stdin_marker.txt"
    backend = tmp_path / "stdin_backend.py"
    prompt.write_text("Code task from prompt file", encoding="utf-8")
    backend.write_text(
        "\n".join(
            [
                "import pathlib, sys",
                "payload = sys.stdin.read()",
                "pathlib.Path(sys.argv[1]).write_text(payload, encoding='utf-8')",
                "print('stdin ok')",
            ]
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--runtime",
            "omx",
            "--role",
            "coder",
            "--task-id",
            "task-stdin",
            "--prompt-file",
            str(prompt),
            "--run-dir",
            str(run_dir),
            "--worktree",
            str(tmp_path),
            "--stdin-prompt",
            "--backend-command",
            f"\"{sys.executable}\" \"{backend}\" \"{marker}\"",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "stdin ok" in completed.stdout
    assert marker.read_text(encoding="utf-8") == "Code task from prompt file"


def test_external_agent_wrapper_reads_output_last_message_file(tmp_path: Path):
    run_dir = tmp_path / "run"
    prompt = tmp_path / "reviewer_prompt.txt"
    output = tmp_path / "last_message.txt"
    backend = tmp_path / "review_backend.py"
    prompt.write_text("Review task", encoding="utf-8")
    backend.write_text(
        "\n".join(
            [
                "import json, pathlib, sys",
                "payload = {'schema_version':'1.0','task_id':'task-review','pass':True,'confidence':91,'summary':'ok','issues':[],'blocking':False,'recommended_next_action':'pass'}",
                "pathlib.Path(sys.argv[1]).write_text(json.dumps(payload), encoding='utf-8')",
                "print('backend chatter')",
            ]
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--runtime",
            "omx",
            "--role",
            "reviewer",
            "--task-id",
            "task-review",
            "--prompt-file",
            str(prompt),
            "--run-dir",
            str(run_dir),
            "--output-last-message",
            str(output),
            "--backend-command",
            f"\"{sys.executable}\" \"{backend}\" {{output_last_message}}",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["task_id"] == "task-review"
    assert "backend chatter" not in completed.stdout


def test_external_agent_wrapper_replaces_invalid_backend_output_bytes(tmp_path: Path):
    run_dir = tmp_path / "run"
    prompt = tmp_path / "coder_prompt.txt"
    backend = tmp_path / "bytes_backend.py"
    prompt.write_text("Code task", encoding="utf-8")
    backend.write_text(
        "\n".join(
            [
                "import sys",
                "sys.stdout.buffer.write(b'ok\\\\xff')",
            ]
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--runtime",
            "omx",
            "--role",
            "coder",
            "--task-id",
            "task-bytes",
            "--prompt-file",
            str(prompt),
            "--run-dir",
            str(run_dir),
            "--backend-command",
            f"\"{sys.executable}\" \"{backend}\"",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "ok" in completed.stdout


def test_external_agent_wrapper_requires_existing_reason_file_for_fixer(tmp_path: Path):
    prompt = tmp_path / "fixer_prompt.txt"
    prompt.write_text("Fix task", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--runtime",
            "codex",
            "--role",
            "fixer",
            "--task-id",
            "task-003",
            "--prompt-file",
            str(prompt),
            "--reason-file",
            str(tmp_path / "missing.json"),
            "--run-dir",
            str(tmp_path / "run"),
            "--dry-run",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 2
    assert "reason file does not exist" in completed.stderr
