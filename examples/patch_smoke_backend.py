from __future__ import annotations

import json
import sys


def main() -> int:
    task_id = sys.argv[1]
    payload = {
        "schema_version": "1.0",
        "task_id": task_id,
        "summary": "Replace subtraction with addition in calculator.add.",
        "operations": [
            {
                "op": "replace_text",
                "path": "calculator.py",
                "old": "return a - b",
                "new": "return a + b",
            }
        ],
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
