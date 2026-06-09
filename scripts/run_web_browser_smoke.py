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
SMOKE_DIR = ROOT / ".tmp" / "web-browser-smoke"
ARCHIVE_AUDIT_NAME = "web-job-audit.20260609120000000000.jsonl"
TIMEOUT_SECONDS = 90


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
        print("web_browser_smoke=passed")
        return 0
    finally:
        stop_server(process)


def reset_smoke_workspace() -> None:
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
