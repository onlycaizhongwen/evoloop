from __future__ import annotations

import json
import sys


def main() -> int:
    task_id = sys.argv[1] if len(sys.argv) > 1 else "task-shell-001"
    print(
        json.dumps(
            {
                "schema_version": "1.0",
                "task_id": task_id,
                "pass": True,
                "confidence": 91,
                "summary": "Shell reviewer passed.",
                "issues": [],
                "blocking": False,
                "recommended_next_action": "pass",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
