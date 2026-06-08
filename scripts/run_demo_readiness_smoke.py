from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SMOKE_DIR = ROOT / ".tmp" / "demo-readiness-smoke"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.infrastructure.persistence.sqlite_job_repository import SQLiteJobRepository
from orchestrator.interfaces.web.main import app


def main() -> int:
    reset_smoke_workspace()
    previous_cwd = Path.cwd()
    try:
        os.chdir(SMOKE_DIR)
        seed_readiness_inputs()
        response = TestClient(app).get("/tasks/health.json")
    finally:
        os.chdir(previous_cwd)

    print(f"health_status_code={response.status_code}")
    if response.status_code != 200:
        print(response.text)
        return 1

    payload = response.json()
    summary = payload["summary"]
    print(f"health_overall={summary['overall']}")
    print(f"health_pass={summary['pass']} warn={summary['warn']} fail={summary['fail']}")
    for check in payload["checks"]:
        print(f"check={check['name']} status={check['status']} message={check['message']}")

    if summary["overall"] != "pass":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    print("demo_readiness_smoke=passed")
    return 0


def reset_smoke_workspace() -> None:
    if SMOKE_DIR.exists():
        shutil.rmtree(SMOKE_DIR)
    SMOKE_DIR.mkdir(parents=True)


def seed_readiness_inputs() -> None:
    examples_dir = SMOKE_DIR / "examples"
    examples_dir.mkdir()
    (examples_dir / "task.mock.json").write_text("{}", encoding="utf-8")
    repository = SQLiteJobRepository(SMOKE_DIR / ".omx" / "orchestrator.db")
    repository.create(
        {
            "job_id": "job-demo-readiness-smoke",
            "status": "done",
            "message": "done",
            "task_path": "",
            "run_id": "",
        }
    )
    audit_path = SMOKE_DIR / ".omx" / "web-job-audit.jsonl"
    audit_path.write_text(json.dumps({"event_type": "maintenance_prune"}, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
