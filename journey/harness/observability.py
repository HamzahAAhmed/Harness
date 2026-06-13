from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

from journey.models import TraceEvent

LOGGER = logging.getLogger("journey.harness")
if not LOGGER.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    LOGGER.addHandler(handler)
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False


def trace(run_id: str, event_type: str, stage: str, **details: Any) -> TraceEvent:
    event = TraceEvent(event_id=f"trace-{uuid4().hex}", run_id=run_id, event_type=event_type, stage=stage, details=details)
    LOGGER.info(json.dumps(event.model_dump(mode="json"), separators=(",", ":")))
    return event
