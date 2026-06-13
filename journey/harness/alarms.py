from __future__ import annotations

from typing import Any
from uuid import uuid4

from journey.models import HarnessAlarm

ALARM_TYPES = {"INPUT_GUARDRAIL_BLOCKED", "MATERIAL_VALIDATION_FAILED", "CHECKPOINT_FAILED", "GROUNDING_VIOLATION", "REPAIR_REQUESTED", "REPAIR_EXHAUSTED", "WORKER_EXECUTION_FAILED", "LIMIT_REACHED", "HUMAN_REVIEW_REQUIRED", "BROWSER_PERSISTENCE_FAILED"}


def create_alarm(*, run_id: str, alarm_type: str, severity: str, stage: str, context: dict[str, Any], recommended_action: str, requires_human: bool = False) -> HarnessAlarm:
    if alarm_type not in ALARM_TYPES:
        raise ValueError(f"unknown alarm type: {alarm_type}")
    return HarnessAlarm(alarm_id=f"alarm-{uuid4().hex}", run_id=run_id, alarm_type=alarm_type, severity=severity, stage=stage, context=context, recommended_action=recommended_action, requires_human=requires_human)
