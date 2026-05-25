from __future__ import annotations

import json

from pydantic import ValidationError

from orchestrator.domain.models.review import ReviewResult
from orchestrator.domain.models.task import TaskConfig
from orchestrator.domain.services.exceptions import MalformedReview


class ReviewValidator:
    def parse_and_validate(self, raw_output: str, task: TaskConfig) -> ReviewResult:
        try:
            payload = self._extract_json(raw_output)
            review = ReviewResult.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise MalformedReview("review_json_malformed") from exc

        if review.task_id != task.task_id:
            raise MalformedReview("task_id_mismatch", expected=task.task_id, actual=review.task_id)
        return review

    def build_repair_prompt(self, task_id: str) -> str:
        return (
            "你的上一次输出不是合法 JSON，无法被系统解析。\n"
            "请参考以下字段模板重新输出，只返回 JSON，不要输出 Markdown、注释或解释文字。\n"
            f"注意：task_id 必须使用当前任务 ID：{task_id}\n\n"
            "{\n"
            '  "schema_version": "1.0",\n'
            f'  "task_id": "{task_id}",\n'
            '  "pass": true,\n'
            '  "confidence": 80,\n'
            '  "summary": "一句话总结审查结果",\n'
            '  "issues": [],\n'
            '  "blocking": false,\n'
            '  "recommended_next_action": "pass"\n'
            "}\n"
        )

    def _extract_json(self, raw_output: str) -> dict:
        stripped = raw_output.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`")
            stripped = stripped.removeprefix("json").strip()
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise json.JSONDecodeError("no json object found", stripped, 0)
        return json.loads(stripped[start : end + 1])
