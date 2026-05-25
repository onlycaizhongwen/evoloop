from __future__ import annotations

import json
from json import JSONDecodeError

from pydantic import ValidationError

from orchestrator.domain.models.patch_plan import PatchPlan
from orchestrator.domain.models.task import TaskConfig
from orchestrator.domain.services.exceptions import MalformedReview


class PatchValidator:
    def parse_and_validate(self, raw_output: str, task: TaskConfig) -> PatchPlan:
        try:
            payload = json.loads(self._extract_json(raw_output))
            plan = PatchPlan.model_validate(payload)
        except (JSONDecodeError, ValidationError) as exc:
            raise MalformedReview(f"patch_json_malformed: {exc}") from exc
        if plan.task_id != task.task_id:
            raise MalformedReview(f"patch task_id mismatch: expected={task.task_id} actual={plan.task_id}")
        if not plan.operations:
            raise MalformedReview("patch operations must not be empty")
        return plan

    def _extract_json(self, raw_output: str) -> str:
        text = raw_output.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        if text.startswith("{"):
            return text
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return text[start : end + 1]
        return text
