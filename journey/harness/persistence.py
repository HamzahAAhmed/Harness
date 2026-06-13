from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from journey.models import RunRecord


def serialize_run(record: RunRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")


def restore_run(data: dict[str, Any] | str) -> RunRecord:
    raw = json.loads(data) if isinstance(data, str) else data
    return RunRecord.model_validate(raw)


def try_restore_run(data: dict[str, Any] | str) -> tuple[RunRecord | None, str | None]:
    try:
        return restore_run(data), None
    except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return None, str(exc)
