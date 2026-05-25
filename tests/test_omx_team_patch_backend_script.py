from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/run_omx_team_patch.py")


def test_run_omx_team_patch_extracts_json_from_last_message(tmp_path: Path):
    prompt = tmp_path / "team_prompt.txt"
    run_dir = tmp_path / "run"
    output = tmp_path / "last_message.txt"
    backend = tmp_path / "backend.py"
    prompt.write_text("Task context", encoding="utf-8")
    backend.write_text(
        "\n".join(
            [
                "import json, pathlib, sys",
                "task_id = sys.argv[1]",
                "output = pathlib.Path(sys.argv[2])",
                "payload = {'schema_version':'1.0','task_id':task_id,'status':'completed','roles':{},'artifacts':{'patch_plan':{'schema_version':'1.0','task_id':task_id,'summary':'fix','operations':[{'op':'replace_text','path':'calculator.py','old':'return a - b','new':'return a + b'}]},'review':{'schema_version':'1.0','task_id':task_id,'pass':True,'confidence':90,'summary':'ok','issues':[],'blocking':False,'recommended_next_action':'pass'}},'diagnostics':[]}",
                "output.write_text('```json\\\\n' + json.dumps(payload) + '\\\\n```', encoding='utf-8')",
                "print('backend chatter')",
            ]
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "task-real-team",
            str(prompt),
            str(run_dir),
            "--output-last-message",
            str(output),
            "--backend-command",
            f'"{sys.executable}" "{backend}" {{task_id}} {{output_last_message}}',
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["task_id"] == "task-real-team"
    assert payload["artifacts"]["patch_plan"]["operations"][0]["new"] == "return a + b"
    log = json.loads((run_dir / "logs" / "omx_team_patch_backend.json").read_text(encoding="utf-8"))
    assert log["returncode"] == 0
    assert "backend chatter" in log["stdout_preview"]


def test_run_omx_team_patch_forwards_raw_output_when_json_is_invalid(tmp_path: Path):
    prompt = tmp_path / "team_prompt.txt"
    run_dir = tmp_path / "run"
    backend = tmp_path / "bad_backend.py"
    prompt.write_text("Task context", encoding="utf-8")
    backend.write_text("print('not json')\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "task-bad-team",
            str(prompt),
            str(run_dir),
            "--backend-command",
            f'"{sys.executable}" "{backend}"',
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "not json" in completed.stdout
    assert (run_dir / "logs" / "omx_team_patch_backend.json").exists()


def test_run_omx_team_patch_team_runtime_collects_result_file(tmp_path: Path):
    prompt = tmp_path / "team_prompt.txt"
    run_dir = tmp_path / "run"
    result_path = tmp_path / "team_result.json"
    launcher = tmp_path / "team_launcher.py"
    awaiter = tmp_path / "team_awaiter.py"
    prompt.write_text("Task context", encoding="utf-8")
    launcher.write_text(
        "\n".join(
            [
                "import json, pathlib, sys",
                "task_id = sys.argv[1]",
                "result = pathlib.Path(sys.argv[2])",
                "runtime_prompt = pathlib.Path(sys.argv[3])",
                "assert runtime_prompt.exists()",
                "payload = {'schema_version':'1.0','task_id':task_id,'status':'completed','roles':{},'artifacts':{'patch_plan':{'schema_version':'1.0','task_id':task_id,'summary':'fix','operations':[{'op':'replace_text','path':'calculator.py','old':'return a - b','new':'return a + b'}]},'review':{'schema_version':'1.0','task_id':task_id,'pass':True,'confidence':90,'summary':'ok','issues':[],'blocking':False,'recommended_next_action':'pass'}},'diagnostics':[]}",
                "result.write_text(json.dumps(payload), encoding='utf-8')",
                "print(json.dumps({'team_name': 'team-test'}))",
            ]
        ),
        encoding="utf-8",
    )
    awaiter.write_text("import json, sys; print(json.dumps({'awaited': sys.argv[1]}))\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "task-team-runtime",
            str(prompt),
            str(run_dir),
            "--runtime",
            "team",
            "--output-last-message",
            str(result_path),
            "--team-launch-command",
            f'"{sys.executable}" "{launcher}" {{task_id}} "{{team_result_path}}" "{{runtime_prompt_file}}"',
            "--team-await-command",
            f'"{sys.executable}" "{awaiter}" {{team_name}}',
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["task_id"] == "task-team-runtime"
    assert payload["artifacts"]["patch_plan"]["operations"][0]["new"] == "return a + b"
    runtime_prompt = run_dir / "attempts" / "omx_team_runtime_prompt.txt"
    assert runtime_prompt.exists()
    assert "Durable OMX team runtime contract" in runtime_prompt.read_text(encoding="utf-8")
    log = json.loads((run_dir / "logs" / "omx_team_patch_backend.json").read_text(encoding="utf-8"))
    assert log["runtime"] == "team"
    assert log["team_name"] == "team-test"
    assert log["await_returncode"] == 0


def test_run_omx_team_patch_team_runtime_fails_without_team_name_or_result(tmp_path: Path):
    prompt = tmp_path / "team_prompt.txt"
    run_dir = tmp_path / "run"
    launcher = tmp_path / "team_launcher.py"
    prompt.write_text("Task context", encoding="utf-8")
    launcher.write_text("print('team launched but name is hidden')\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "task-team-runtime-no-name",
            str(prompt),
            str(run_dir),
            "--runtime",
            "team",
            "--team-launch-command",
            f'"{sys.executable}" "{launcher}"',
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 2
    assert "did not expose a team name" in completed.stderr
    log = json.loads((run_dir / "logs" / "omx_team_patch_backend.json").read_text(encoding="utf-8"))
    assert log["returncode"] == 2
