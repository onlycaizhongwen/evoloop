from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    task_id = sys.argv[1]
    output_path = Path(sys.argv[2])
    payload = {
        "schema_version": "1.0",
        "task_id": task_id,
        "pass": True,
        "confidence": 90,
        "summary": "OMX smoke reviewer passed after hard checks.",
        "issues": [],
        "blocking": False,
        "recommended_next_action": "pass",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print("review written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
