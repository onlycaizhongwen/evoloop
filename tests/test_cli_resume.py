from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path

import pytest

from orchestrator.infrastructure.persistence.file_state_repository import FileStateRepository
from orchestrator.interfaces.cli import main as cli_main


def run_cli(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> tuple[int, str]:
    stdout = StringIO()
    monkeypatch.setattr(sys, "argv", ["orchestrator", *argv])
    monkeypatch.setattr(sys, "stdout", stdout)
    exit_code = cli_main.main()
    return exit_code, stdout.getvalue()


def write_task(path: Path, test_command: str | None = None) -> None:
    payload = {
        "task_id": "task-cli-001",
        "title": "CLI task",
        "description": "CLI resume task",
        "change_type": "bugfix",
        "repo_path": str(path.parent),
        "worktree_path": str(path.parent),
        "allowed_paths": ["."],
        "forbidden_paths": [".env"],
        "allowed_command_prefixes": ["python", "python.exe"],
        "check_commands": {"test": test_command, "lint": None, "typecheck": None},
        "agent_mode": "mock",
        "max_attempts": 1,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_patch_task(path: Path, test_command: str | None = None) -> None:
    payload = {
        "task_id": "task-patch-001",
        "title": "Patch task",
        "description": "Patch task",
        "change_type": "bugfix",
        "repo_path": str(path.parent),
        "worktree_path": str(path.parent),
        "allowed_paths": ["old_file.py"],
        "forbidden_paths": [".env"],
        "allowed_command_prefixes": ["python", "python.exe"],
        "check_commands": {"test": test_command, "lint": None, "typecheck": None},
        "agent_mode": "omx_patch",
        "agent_commands": {
            "patch_coder": f"\"{sys.executable}\" \"{path.parent / 'patch_backend.py'}\" {{task_id}}",
            "reviewer": f"\"{sys.executable}\" \"{path.parent / 'reviewer.py'}\" {{task_id}}",
        },
        "patch_require_approval_on_delete": True,
        "max_attempts": 1,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_patch_helpers(directory: Path) -> None:
    (directory / "patch_backend.py").write_text(
        "\n".join(
            [
                "import json, sys",
                "print(json.dumps({'schema_version':'1.0','task_id':sys.argv[1],'summary':'delete','operations':[{'op':'delete_file','path':'old_file.py','must_exist':True}]}))",
            ]
        ),
        encoding="utf-8",
    )
    (directory / "reviewer.py").write_text(
        "\n".join(
            [
                "import json, sys",
                "print(json.dumps({'schema_version':'1.0','task_id':sys.argv[1],'pass':True,'confidence':90,'summary':'ok','issues':[],'blocking':False,'recommended_next_action':'pass'}))",
            ]
        ),
        encoding="utf-8",
    )


def write_unified_diff_patch_task(path: Path, test_command: str | None = None) -> None:
    payload = {
        "task_id": "task-patch-unified-001",
        "title": "Unified diff patch task",
        "description": "Unified diff patch task",
        "change_type": "bugfix",
        "repo_path": str(path.parent),
        "worktree_path": str(path.parent),
        "allowed_paths": ["calculator.py"],
        "forbidden_paths": [".env"],
        "allowed_command_prefixes": ["python", "python.exe"],
        "check_commands": {"test": test_command, "lint": None, "typecheck": None},
        "agent_mode": "omx_patch",
        "agent_commands": {
            "patch_coder": f"\"{sys.executable}\" \"{path.parent / 'patch_backend.py'}\" {{task_id}}",
            "reviewer": f"\"{sys.executable}\" \"{path.parent / 'reviewer.py'}\" {{task_id}}",
        },
        "max_attempts": 1,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_unified_diff_patch_helpers(directory: Path) -> None:
    diff = "\n".join(
        [
            "--- a/calculator.py",
            "+++ b/calculator.py",
            "@@ -1,2 +1,2 @@",
            " def add(a, b):",
            "-    return a - b",
            "+    return a + b",
            "",
        ]
    )
    (directory / "patch_backend.py").write_text(
        "\n".join(
            [
                "import json, sys",
                f"diff = {diff!r}",
                "print(json.dumps({'schema_version':'1.0','task_id':sys.argv[1],'summary':'unified','operations':[{'op':'unified_diff','path':'calculator.py','diff':diff}]}))",
            ]
        ),
        encoding="utf-8",
    )
    (directory / "reviewer.py").write_text(
        "\n".join(
            [
                "import json, sys",
                "print(json.dumps({'schema_version':'1.0','task_id':sys.argv[1],'pass':True,'confidence':90,'summary':'ok','issues':[],'blocking':False,'recommended_next_action':'pass'}))",
            ]
        ),
        encoding="utf-8",
    )


def write_malformed_patch_helpers(directory: Path) -> None:
    (directory / "patch_backend.py").write_text("print('not-json')\n", encoding="utf-8")
    (directory / "reviewer.py").write_text(
        "\n".join(
            [
                "import json, sys",
                "print(json.dumps({'schema_version':'1.0','task_id':sys.argv[1],'pass':True,'confidence':90,'summary':'ok','issues':[],'blocking':False,'recommended_next_action':'pass'}))",
            ]
        ),
        encoding="utf-8",
    )


def test_resume_inspects_previous_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    task_path = Path.cwd() / "task.json"
    write_task(task_path)
    exit_code, output = run_cli(monkeypatch, ["--task", str(task_path)])
    assert exit_code == 0

    run_id = output.split("run_id=", 1)[1].split(" ", 1)[0]
    exit_code, resume_output = run_cli(monkeypatch, ["resume", "--run-id", run_id])

    assert exit_code == 0
    assert f"run_id={run_id}" in resume_output
    assert "resume_action=inspect" in resume_output
    assert "task=.omx" in resume_output


def test_resume_rerun_starts_new_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    task_path = Path.cwd() / "task.json"
    write_task(task_path)
    exit_code, output = run_cli(monkeypatch, ["--task", str(task_path)])
    assert exit_code == 0
    old_run_id = output.split("run_id=", 1)[1].split(" ", 1)[0]

    exit_code, rerun_output = run_cli(monkeypatch, ["resume", "--run-id", old_run_id, "--rerun"])

    assert exit_code == 0
    assert "resume_action=rerun" in rerun_output
    new_run_id = rerun_output.split("new_run_id=", 1)[1].split(" ", 1)[0]
    assert new_run_id != old_run_id
    assert Path(".omx/runs", new_run_id, "run_state.json").exists()


def test_repository_loads_state_and_task_path(tmp_path: Path):
    from orchestrator.domain.enums import ChangeType
    from orchestrator.domain.models.task import TaskConfig

    task = TaskConfig(
        task_id="task-001",
        title="Task",
        description="Task",
        change_type=ChangeType.BUGFIX,
        repo_path=tmp_path,
        worktree_path=tmp_path,
    )
    repository = FileStateRepository(tmp_path / "runs")
    state = repository.create_run(task)

    loaded = repository.load_state(state.run_id)

    assert loaded.run_id == state.run_id
    assert repository.task_path_for_run(state.run_id).exists()


def test_rules_list_and_review_cluster(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    task_path = Path.cwd() / "task.json"
    write_task(task_path, test_command=f"\"{sys.executable}\" -c \"import sys; sys.exit(1)\"")
    exit_code, _ = run_cli(monkeypatch, ["--task", str(task_path), "--real-checks"])
    assert exit_code == 0

    exit_code, list_output = run_cli(monkeypatch, ["rules", "list"])
    assert exit_code == 0
    assert "cluster_key=" in list_output
    cluster_key = list_output.split("cluster_key=", 1)[1].split(" ", 1)[0]

    exit_code, review_output = run_cli(
        monkeypatch,
        [
            "rules",
            "review",
            "--cluster-key",
            cluster_key,
            "--status",
            "approved",
            "--reviewer",
            "lead",
            "--note",
            "looks good",
        ],
    )

    assert exit_code == 0
    assert f"cluster_key={cluster_key}" in review_output
    assert "status=approved" in review_output

    index = json.loads(Path(".omx/runs/rule_proposals_index.json").read_text(encoding="utf-8"))
    cluster = index["clusters"][cluster_key]
    assert cluster["review_status"] == "approved"
    assert cluster["reviewed_by"] == "lead"
    assert cluster["review_note"] == "looks good"


def test_patches_list_apply_and_reject(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    task_path = Path.cwd() / "patch-task.json"
    (Path.cwd() / "old_file.py").write_text("obsolete", encoding="utf-8")
    write_patch_helpers(Path.cwd())
    check_command = f"\"{sys.executable}\" -c \"import pathlib; assert not pathlib.Path('old_file.py').exists()\""
    write_patch_task(task_path, test_command=check_command)

    exit_code, output = run_cli(monkeypatch, ["--task", str(task_path), "--agent", "omx_patch", "--real-checks"])
    assert exit_code == 0
    run_id = output.split("run_id=", 1)[1].split(" ", 1)[0]
    assert (Path.cwd() / "old_file.py").exists()


def test_omx_patch_unified_diff_smoke(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    task_path = Path.cwd() / "patch-task.json"
    (Path.cwd() / "calculator.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (Path.cwd() / "test_calculator.py").write_text(
        "from calculator import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n",
        encoding="utf-8",
    )
    write_unified_diff_patch_helpers(Path.cwd())
    check_command = f"\"{sys.executable}\" -m pytest -q"
    write_unified_diff_patch_task(task_path, test_command=check_command)

    exit_code, output = run_cli(monkeypatch, ["--task", str(task_path), "--agent", "omx_patch", "--real-checks"])

    assert exit_code == 0
    assert "status=done" in output
    assert "return a + b" in (Path.cwd() / "calculator.py").read_text(encoding="utf-8")


def test_omx_patch_malformed_json_writes_diagnostics(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    task_path = Path.cwd() / "patch-task.json"
    (Path.cwd() / "calculator.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    write_malformed_patch_helpers(Path.cwd())
    write_unified_diff_patch_task(task_path)

    exit_code, output = run_cli(monkeypatch, ["--task", str(task_path), "--agent", "omx_patch", "--real-checks"])

    assert exit_code == 0
    assert "status=halted" in output
    run_id = output.split("run_id=", 1)[1].split(" ", 1)[0]
    attempt_dir = Path(".omx/runs", run_id, "attempts", "001")
    raw_output = attempt_dir / "patch_coder_patch_raw_output.txt"
    diagnostics = attempt_dir / "patch_coder_patch_diagnostics.json"
    assert raw_output.read_text(encoding="utf-8").strip() == "not-json"
    payload = json.loads(diagnostics.read_text(encoding="utf-8"))
    assert payload["error_type"] == "MalformedReview"
    assert "not-json" in payload["raw_output_preview"]


def test_patches_apply_rerun_task_records_fresh_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    task_path = Path.cwd() / "patch-task.json"
    (Path.cwd() / "old_file.py").write_text("obsolete", encoding="utf-8")
    write_patch_helpers(Path.cwd())
    check_command = f"\"{sys.executable}\" -c \"import pathlib; assert not pathlib.Path('old_file.py').exists()\""
    write_patch_task(task_path, test_command=check_command)

    exit_code, output = run_cli(monkeypatch, ["--task", str(task_path), "--agent", "omx_patch", "--real-checks"])
    assert exit_code == 0
    run_id = output.split("run_id=", 1)[1].split(" ", 1)[0]
    exit_code, list_output = run_cli(monkeypatch, ["patches", "list", "--run-id", run_id])
    assert "checks_status=not_run" in list_output
    assert "rerun_status=None" in list_output
    patch_name = list_output.split("patch=", 1)[1].split(" ", 1)[0]

    exit_code, apply_output = run_cli(
        monkeypatch,
        ["patches", "apply", "--run-id", run_id, "--patch", patch_name, "--rerun-task"],
    )

    assert exit_code == 0
    assert "rerun_run_id=run-" in apply_output
    assert "rerun_status=done" in apply_output
    assert "rerun_phase=done" in apply_output
    assert "rerun_attempt=1" in apply_output
    assert "rerun_reason=quality gate passed" in apply_output
    payload = json.loads(Path(".omx/runs", run_id, "pending-patches", patch_name).read_text(encoding="utf-8"))
    rerun_id = payload["post_apply_rerun"]["run_id"]
    assert Path(".omx/runs", rerun_id, "final_report.md").exists()
    assert payload["status"] == "applied"
    assert not (Path.cwd() / "old_file.py").exists()
    exit_code, list_output = run_cli(monkeypatch, ["patches", "list", "--run-id", run_id])
    assert exit_code == 0
    assert "status=applied" in list_output
    assert "checks_status=not_run" in list_output
    assert "rerun_status=done" in list_output
    assert f"rerun_run_id={rerun_id}" in list_output

    (Path.cwd() / "old_file.py").write_text("obsolete", encoding="utf-8")
    exit_code, output = run_cli(monkeypatch, ["--task", str(task_path), "--agent", "omx_patch", "--real-checks"])
    assert exit_code == 0
    checks_run_id = output.split("run_id=", 1)[1].split(" ", 1)[0]
    exit_code, list_output = run_cli(monkeypatch, ["patches", "list", "--run-id", checks_run_id])
    assert exit_code == 0
    assert "status=pending" in list_output
    patch_name = list_output.split("patch=", 1)[1].split(" ", 1)[0]

    exit_code, apply_output = run_cli(
        monkeypatch,
        ["patches", "apply", "--run-id", checks_run_id, "--patch", patch_name, "--reviewer", "lead", "--rerun-checks"],
    )
    assert exit_code == 0
    assert "status=applied" in apply_output
    assert "checks_status=passed" in apply_output
    assert "checks_passed=True" in apply_output
    assert not (Path.cwd() / "old_file.py").exists()
    patch_payload = json.loads(Path(".omx/runs", checks_run_id, "pending-patches", patch_name).read_text(encoding="utf-8"))
    assert patch_payload["post_apply_checks"]["commands"][0]["passed"] is True
    exit_code, list_output = run_cli(monkeypatch, ["patches", "list", "--run-id", checks_run_id])
    assert exit_code == 0
    assert "checks_status=passed" in list_output
    assert "checks_passed=True" in list_output

    (Path.cwd() / "old_file.py").write_text("obsolete", encoding="utf-8")
    exit_code, output = run_cli(monkeypatch, ["--task", str(task_path), "--agent", "omx_patch", "--real-checks"])
    second_run_id = output.split("run_id=", 1)[1].split(" ", 1)[0]
    exit_code, list_output = run_cli(monkeypatch, ["patches", "list", "--run-id", second_run_id])
    patch_name = list_output.split("patch=", 1)[1].split(" ", 1)[0]

    exit_code, reject_output = run_cli(
        monkeypatch,
        ["patches", "reject", "--run-id", second_run_id, "--patch", patch_name, "--note", "too risky"],
    )
    assert exit_code == 0
    assert "status=rejected" in reject_output
    assert (Path.cwd() / "old_file.py").exists()


def test_patches_apply_rerun_task_records_failure_reason(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    task_path = Path.cwd() / "patch-task.json"
    (Path.cwd() / "old_file.py").write_text("obsolete", encoding="utf-8")
    write_patch_helpers(Path.cwd())
    check_command = f"\"{sys.executable}\" -c \"import sys; sys.exit(1)\""
    write_patch_task(task_path, test_command=check_command)

    exit_code, output = run_cli(monkeypatch, ["--task", str(task_path), "--agent", "omx_patch", "--real-checks"])
    assert exit_code == 0
    run_id = output.split("run_id=", 1)[1].split(" ", 1)[0]
    exit_code, list_output = run_cli(monkeypatch, ["patches", "list", "--run-id", run_id])
    patch_name = list_output.split("patch=", 1)[1].split(" ", 1)[0]

    exit_code, apply_output = run_cli(
        monkeypatch,
        ["patches", "apply", "--run-id", run_id, "--patch", patch_name, "--rerun-task"],
    )

    assert exit_code == 0
    assert "rerun_status=halted" in apply_output
    assert "rerun_reason=test failed" in apply_output
    payload = json.loads(Path(".omx/runs", run_id, "pending-patches", patch_name).read_text(encoding="utf-8"))
    assert payload["post_apply_rerun"]["reason"] == "test failed"
