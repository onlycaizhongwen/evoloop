from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[1]
SMOKE_ROOT = ROOT / ".tmp" / "web-browser-smoke"
SMOKE_DIR = SMOKE_ROOT / f"run-{os.getpid()}"
ARCHIVE_AUDIT_NAME = "web-job-audit.20260609120000000000.jsonl"
TIMEOUT_SECONDS = 90
STALE_WORKSPACE_SECONDS = 24 * 60 * 60


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = build_opener(NoRedirectHandler)


def main() -> int:
    reset_smoke_workspace()
    port = find_free_port()
    process = start_server(port)
    base_url = f"http://127.0.0.1:{port}"
    try:
        wait_for_server(base_url)
        assert_page_contains(base_url + "/", ["Auto Evolution Orchestrator", "/templates/run", "mock_demo"])
        assert_page_contains(base_url + "/tasks", ["/tasks/maintenance/prune", "/tasks/audit", "Demo Readiness"])
        health_payload = get_json(base_url + "/tasks/health.json")
        print(f"health_overall={health_payload['summary']['overall']}")
        if health_payload["summary"]["overall"] != "pass":
            print(json.dumps(health_payload, ensure_ascii=False, indent=2))
            return 1
        assert_page_contains(
            base_url + "/tasks/audit?scope=all&q=job-archived-smoke",
            [
                "1 / 2",
                "job-archived-smoke",
                f"source: archive / {ARCHIVE_AUDIT_NAME}",
                "All sources (2)",
                "Archives only (1)",
            ],
        )
        assert_page_contains(
            base_url + "/tasks/audit?source=archive",
            ["1 / 2", "job-archived-smoke", "Archives only (1)"],
        )
        assert_page_contains(
            base_url + "/tasks/audit?" + urlencode({"source_file": ARCHIVE_AUDIT_NAME}),
            ["1 / 2", f"source: archive / {ARCHIVE_AUDIT_NAME}", f"{ARCHIVE_AUDIT_NAME} (1)"],
        )
        assert_page_contains(
            base_url + "/tasks/audit.md?source=archive",
            [f"- Source files: {ARCHIVE_AUDIT_NAME} (1)", f"- Source: archive ({ARCHIVE_AUDIT_NAME})"],
        )
        print("audit_archive_smoke=passed")

        job_path = post_form(base_url + "/templates/run", {"template_id": "mock_demo"})
        print(f"job_path={job_path}")
        if not job_path.startswith("/jobs/job-"):
            print(f"unexpected_job_redirect={job_path}")
            return 1

        final_path = wait_for_job_redirect(base_url, job_path)
        print(f"final_path={final_path}")
        if not final_path.startswith("/runs/run-"):
            return 1

        assert_page_contains(base_url + final_path, ["Run", "task-mock-web-001"])
        assert_page_contains(base_url + "/tasks", ["task-mock-web-001", "mock_demo"])

        external_run_id = run_external_agent_web_provenance()
        external_run_path = f"/runs/{external_run_id}"
        assert_page_contains(
            base_url + external_run_path,
            [
                "Wrapper Command Provenance",
                "External agent wrapper 日志",
                "codex",
                "coder",
                "reviewer",
                "python",
            ],
        )
        assert_page_contains(
            base_url + external_run_path + "/audit.md",
            [
                "## External Agent Wrapper",
                "- Invocations: 2",
                "- Runtime: codex",
                "- Roles: coder, reviewer",
                "exit=0",
                "command=python",
            ],
        )
        print("web_external_agent_provenance_smoke=passed")

        print("web_browser_smoke=passed")
        return 0
    finally:
        stop_server(process)


def reset_smoke_workspace() -> None:
    cleanup_stale_smoke_workspaces()
    if SMOKE_DIR.exists():
        shutil.rmtree(SMOKE_DIR)
    SMOKE_DIR.mkdir(parents=True)
    examples_dir = SMOKE_DIR / "examples"
    examples_dir.mkdir()
    (examples_dir / "task.mock.json").write_text("{}", encoding="utf-8")
    audit_path = SMOKE_DIR / ".omx" / "web-job-audit.jsonl"
    audit_path.parent.mkdir()
    audit_path.write_text(
        json.dumps(
            {
                "event_type": "web_browser_smoke_seed",
                "processed_job_ids": ["job-active-smoke"],
                "message": "active smoke audit event",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    archive_path = audit_path.parent / ARCHIVE_AUDIT_NAME
    archive_path.write_text(
        json.dumps(
            {
                "event_type": "web_browser_smoke_archive_seed",
                "processed_job_ids": ["job-archived-smoke"],
                "message": "archived smoke audit event",
            }
        )
        + "\n",
        encoding="utf-8",
    )


def cleanup_stale_smoke_workspaces(
    root: Path = SMOKE_ROOT,
    now: float | None = None,
    current_dir: Path = SMOKE_DIR,
) -> int:
    if not root.exists():
        return 0
    cutoff = (time.time() if now is None else now) - STALE_WORKSPACE_SECONDS
    removed = 0
    for path in root.iterdir():
        if path == current_dir or not path.is_dir() or not path.name.startswith("run-"):
            continue
        try:
            if path.stat().st_mtime >= cutoff:
                continue
            shutil.rmtree(path)
            removed += 1
        except OSError:
            continue
    if removed:
        print(f"stale_smoke_workspaces_removed={removed}")
    return removed


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_server(port: int) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "orchestrator.interfaces.web.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=SMOKE_DIR,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def wait_for_server(base_url: str) -> None:
    deadline = time.time() + TIMEOUT_SECONDS
    last_error = ""
    while time.time() < deadline:
        try:
            status, _headers, body = request("GET", base_url + "/tasks/health.json")
            if status == 200 and body:
                return
        except URLError as exc:
            last_error = str(exc)
        time.sleep(0.2)
    raise TimeoutError(f"web server did not become ready: {last_error}")


def request(method: str, url: str, data: dict[str, str] | None = None) -> tuple[int, dict[str, str], str]:
    encoded_data = None
    headers = {}
    if data is not None:
        encoded_data = urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = Request(url, data=encoded_data, headers=headers, method=method)
    try:
        with OPENER.open(req, timeout=10) as response:
            return response.status, dict(response.headers), response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, dict(exc.headers), body


def get_json(url: str) -> dict:
    status, _headers, body = request("GET", url)
    if status != 200:
        raise AssertionError(f"GET {url} returned {status}: {body[:400]}")
    return json.loads(body)


def assert_page_contains(url: str, expected: list[str]) -> None:
    status, _headers, body = request("GET", url)
    print(f"page={url} status={status}")
    if status != 200:
        raise AssertionError(f"GET {url} returned {status}: {body[:400]}")
    missing = [item for item in expected if item not in body]
    if missing:
        raise AssertionError(f"GET {url} missing {missing}")


def post_form(url: str, data: dict[str, str]) -> str:
    status, headers, body = request("POST", url, data)
    print(f"post={url} status={status}")
    if status != 303:
        raise AssertionError(f"POST {url} returned {status}: {body[:400]}")
    return get_header(headers, "Location")


def run_external_agent_web_provenance() -> str:
    task_path = write_external_agent_task()
    completed = run_orchestrator(task_path)
    print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0:
        raise AssertionError(f"external agent run failed: {completed.returncode}")
    run_id = extract_value(completed.stdout, "run_id")
    status = extract_value(completed.stdout, "status")
    print(f"web_external_agent_run_id={run_id}")
    if not run_id or status not in {"done", "RunStatus.DONE"}:
        raise AssertionError(f"external agent run did not complete: run_id={run_id} status={status}")
    wrapper_log = SMOKE_DIR / ".omx" / "runs" / run_id / "logs" / "external_agent_wrapper.log"
    wrapper_evidence = collect_wrapper_evidence(wrapper_log)
    for key, value in wrapper_evidence.items():
        print(f"{key}={value}")
    if (
        wrapper_evidence["wrapper_runtime"] != "codex"
        or wrapper_evidence["wrapper_roles"] != "coder,reviewer"
        or wrapper_evidence["wrapper_exit_codes"] != "0,0"
        or wrapper_evidence["wrapper_backend_commands"] != "2"
    ):
        raise AssertionError(f"unexpected wrapper evidence: {wrapper_evidence}")
    return run_id


def write_external_agent_task() -> Path:
    worktree = SMOKE_DIR / "external-agent-worktree"
    worktree.mkdir(exist_ok=True)
    (worktree / "calculator.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    backend = SMOKE_DIR / "external_agent_web_backend.py"
    backend.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "import json",
                "import pathlib",
                "import sys",
                "",
                "role = sys.argv[1]",
                "task_id = sys.argv[2]",
                "prompt_file = pathlib.Path(sys.argv[3])",
                "marker = pathlib.Path(sys.argv[4])",
                "prompt = prompt_file.read_text(encoding='utf-8')",
                "marker.parent.mkdir(parents=True, exist_ok=True)",
                "marker.write_text(role + ':' + task_id + ':' + str(len(prompt)), encoding='utf-8')",
                "if role == 'reviewer':",
                "    print(json.dumps({",
                "        'schema_version': '1.0',",
                "        'task_id': task_id,",
                "        'pass': True,",
                "        'confidence': 93,",
                "        'summary': 'web external agent provenance smoke review passed',",
                "        'issues': [],",
                "        'blocking': False,",
                "        'recommended_next_action': 'pass',",
                "    }))",
                "else:",
                "    print(role + ' backend ok')",
            ]
        ),
        encoding="utf-8",
    )
    marker = SMOKE_DIR / "external-agent-web-marker.txt"
    wrapper = ROOT / "scripts" / "run_external_agent.py"
    backend_env = {
        "OMX_CODEX_CODER_COMMAND": f'python "{backend}" coder {{task_id}} {{prompt_file}} "{marker}"',
        "OMX_CODEX_FIXER_COMMAND": f'python "{backend}" fixer {{task_id}} {{prompt_file}} "{marker}"',
        "OMX_CODEX_REVIEWER_COMMAND": f'python "{backend}" reviewer {{task_id}} {{prompt_file}} "{marker}"',
    }
    (SMOKE_DIR / "external-agent-web-env.json").write_text(
        json.dumps(backend_env, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    task = {
        "task_id": "task-web-external-agent-provenance",
        "title": "Web external agent provenance smoke",
        "description": "Exercise wrapper provenance over the real Web run-detail and audit export path.",
        "change_type": "bugfix",
        "repo_path": str(worktree),
        "worktree_path": str(worktree),
        "allowed_paths": ["calculator.py"],
        "forbidden_paths": [".env"],
        "allowed_command_prefixes": ["python", sys.executable],
        "check_commands": {"test": None, "lint": None, "typecheck": None},
        "agent_mode": "codex",
        "agent_commands": {
            "coder": external_wrapper_command("coder", wrapper),
            "fixer": external_wrapper_command("fixer", wrapper),
            "reviewer": external_wrapper_command("reviewer", wrapper),
        },
        "max_attempts": 1,
        "max_review_json_retries": 1,
    }
    task_path = SMOKE_DIR / "task.web-external-agent-provenance.json"
    task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    return task_path


def external_wrapper_command(role: str, wrapper: Path) -> str:
    return (
        f'python "{wrapper}" --runtime codex --role {role} --task-id {{task_id}} '
        f"--prompt-file {{prompt_file}} --run-dir {{run_dir}} --worktree {{worktree}}"
    )


def run_orchestrator(task_path: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env.update(json.loads((SMOKE_DIR / "external-agent-web-env.json").read_text(encoding="utf-8")))
    return subprocess.run(
        ["python", "-m", "orchestrator.interfaces.cli.main", "--task", str(task_path), "--agent", "codex"],
        cwd=SMOKE_DIR,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def collect_wrapper_evidence(path: Path) -> dict[str, str]:
    entries = parse_wrapper_log(path)
    roles = sorted({entry.get("role", "") for entry in entries if entry.get("role")})
    runtimes = sorted({entry.get("runtime", "") for entry in entries if entry.get("runtime")})
    exit_codes = [entry.get("exit_code", "") for entry in entries if entry.get("exit_code")]
    backend_commands = [entry.get("backend_command", "") for entry in entries if entry.get("backend_command")]
    return {
        "wrapper_runtime": ",".join(runtimes),
        "wrapper_roles": ",".join(roles),
        "wrapper_exit_codes": ",".join(exit_codes),
        "wrapper_backend_commands": str(len(backend_commands)),
    }


def parse_wrapper_log(path: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "---":
            if current:
                entries.append(current)
                current = {}
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        current[key.strip()] = value.strip()
    if current:
        entries.append(current)
    return entries


def extract_value(output: str, key: str) -> str:
    for line in output.splitlines():
        for part in line.split():
            if part.startswith(key + "="):
                return part.split("=", 1)[1]
    return ""


def wait_for_job_redirect(base_url: str, job_path: str) -> str:
    deadline = time.time() + TIMEOUT_SECONDS
    last_status = 0
    last_body = ""
    while time.time() < deadline:
        status, headers, body = request("GET", base_url + job_path)
        last_status = status
        last_body = body
        if status == 303:
            location = get_header(headers, "Location")
            if location.startswith("/runs/"):
                return location
        time.sleep(0.25)
    raise TimeoutError(f"job did not finish: status={last_status} body={last_body[:400]}")


def get_header(headers: dict[str, str], name: str) -> str:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return ""


def stop_server(process: subprocess.Popen[str]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            _stdout, stderr = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            _stdout, stderr = process.communicate(timeout=10)
    else:
        _stdout, stderr = process.communicate(timeout=10)
    if stderr.strip():
        print("server_stderr_begin")
        print(stderr.strip())
        print("server_stderr_end")


if __name__ == "__main__":
    raise SystemExit(main())
