from __future__ import annotations

import json
import sys
from pathlib import Path

from orchestrator.interfaces.cli import main as cli_main


def test_omx_team_patch_agent_applies_team_result_and_reuses_review(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    task_path = tmp_path / "team-task.json"
    backend = tmp_path / "team_backend.py"
    (tmp_path / "calculator.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    backend.write_text(
        "\n".join(
            [
                "import json, sys",
                "task_id = sys.argv[1]",
                "print(json.dumps({",
                "  'schema_version': '1.0',",
                "  'task_id': task_id,",
                "  'status': 'completed',",
                "  'roles': {",
                "    'planner': {'status': 'completed', 'artifact': 'team_plan.json'},",
                "    'coder': {'status': 'completed', 'artifact': 'patch_plan.json'},",
                "    'reviewer': {'status': 'completed', 'artifact': 'review.json'}",
                "  },",
                "  'artifacts': {",
                "    'patch_plan': {",
                "      'schema_version': '1.0',",
                "      'task_id': task_id,",
                "      'summary': 'Fix add',",
                "      'operations': [{'op': 'replace_text', 'path': 'calculator.py', 'old': 'return a - b', 'new': 'return a + b'}]",
                "    },",
                "    'review': {",
                "      'schema_version': '1.0',",
                "      'task_id': task_id,",
                "      'pass': True,",
                "      'confidence': 91,",
                "      'summary': 'Team review passed',",
                "      'issues': [],",
                "      'blocking': False,",
                "      'recommended_next_action': 'pass'",
                "    }",
                "  },",
                "  'diagnostics': []",
                "}))",
            ]
        ),
        encoding="utf-8",
    )
    task_path.write_text(
        json.dumps(
            {
                "task_id": "task-team-001",
                "title": "Team task",
                "description": "Fix calculator add.",
                "change_type": "bugfix",
                "repo_path": str(tmp_path),
                "worktree_path": str(tmp_path),
                "allowed_paths": ["calculator.py"],
                "forbidden_paths": [".env"],
                "allowed_command_prefixes": ["python", "python.exe"],
                "agent_mode": "omx_team_patch",
                "agent_commands": {
                    "patch_coder": f"\"{sys.executable}\" \"{backend}\" {{task_id}} {{prompt_file}}"
                },
                "max_attempts": 1,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["orchestrator", "--task", str(task_path), "--agent", "omx_team_patch"])

    exit_code = cli_main.main()

    assert exit_code == 0
    assert "return a + b" in (tmp_path / "calculator.py").read_text(encoding="utf-8")
    run_dirs = sorted((tmp_path / ".omx" / "runs").glob("run-*"))
    assert run_dirs
    assert (run_dirs[-1] / "attempts" / "001" / "team_result.json").exists()
    review = json.loads((run_dirs[-1] / "attempts" / "001" / "review.json").read_text(encoding="utf-8"))
    assert review["summary"] == "Team review passed"


def test_omx_team_patch_agent_writes_diagnostics_for_bad_team_result(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    task_path = tmp_path / "team-task.json"
    backend = tmp_path / "bad_team_backend.py"
    (tmp_path / "calculator.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    backend.write_text("print('not-json')\n", encoding="utf-8")
    task_path.write_text(
        json.dumps(
            {
                "task_id": "task-team-001",
                "title": "Team task",
                "description": "Fix calculator add.",
                "change_type": "bugfix",
                "repo_path": str(tmp_path),
                "worktree_path": str(tmp_path),
                "allowed_paths": ["calculator.py"],
                "forbidden_paths": [".env"],
                "allowed_command_prefixes": ["python", "python.exe"],
                "agent_mode": "omx_team_patch",
                "agent_commands": {
                    "patch_coder": f"\"{sys.executable}\" \"{backend}\" {{task_id}}"
                },
                "max_attempts": 1,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["orchestrator", "--task", str(task_path), "--agent", "omx_team_patch"])

    exit_code = cli_main.main()

    assert exit_code == 0
    run_dirs = sorted((tmp_path / ".omx" / "runs").glob("run-*"))
    diagnostics = run_dirs[-1] / "attempts" / "001" / "team_diagnostics.json"
    assert diagnostics.exists()
    payload = json.loads(diagnostics.read_text(encoding="utf-8"))
    assert payload["error_type"] == "MalformedReview"
    assert "not-json" in payload["raw_output_preview"]
