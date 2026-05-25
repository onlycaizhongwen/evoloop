from __future__ import annotations

import json
import sys


def main() -> int:
    task_id = sys.argv[1]
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
    payload = {
        "schema_version": "1.0",
        "task_id": task_id,
        "summary": "Apply unified diff to fix calculator.add.",
        "operations": [
            {
                "op": "unified_diff",
                "path": "calculator.py",
                "diff": diff,
            }
        ],
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
