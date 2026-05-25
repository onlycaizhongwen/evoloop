from __future__ import annotations

import json
import sys


def main() -> int:
    task_id = sys.argv[1] if len(sys.argv) > 1 else "task-omx-team-patch-smoke-001"
    payload = {
        "schema_version": "1.0",
        "task_id": task_id,
        "status": "completed",
        "roles": {
            "planner": {
                "status": "completed",
                "artifact": "team_plan.json",
                "summary": "Use a narrow calculator.py patch.",
            },
            "coder": {
                "status": "completed",
                "artifact": "patch_plan.json",
                "summary": "Generated a replace_text patch.",
            },
            "reviewer": {
                "status": "completed",
                "artifact": "review.json",
                "summary": "Reviewed patch as scoped and safe.",
            },
        },
        "artifacts": {
            "patch_plan": {
                "schema_version": "1.0",
                "task_id": task_id,
                "summary": "Replace subtraction with addition.",
                "operations": [
                    {
                        "op": "replace_text",
                        "path": "calculator.py",
                        "old": "return a - b",
                        "new": "return a + b",
                    }
                ],
            },
            "review": {
                "schema_version": "1.0",
                "task_id": task_id,
                "pass": True,
                "confidence": 91,
                "summary": "Team review passed.",
                "issues": [],
                "blocking": False,
                "recommended_next_action": "pass",
            },
        },
        "diagnostics": [],
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
