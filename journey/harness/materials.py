from __future__ import annotations

import hashlib
import json
import re
from typing import Any, TypeVar
from uuid import uuid4

from pydantic import BaseModel

from journey.config import SETTINGS
from journey.models import MaterialEnvelope, utc_now

ModelT = TypeVar("ModelT", bound=BaseModel)
MATERIAL_TYPES = {
    "TripRequestMaterial",
    "ValidatedTripMaterial",
    "CandidatePlacesMaterial",
    "RankedPlacesMaterial",
    "WorkerRequestMaterial",
    "DraftItineraryMaterial",
    "CheckpointFeedbackMaterial",
    "ValidatedItineraryMaterial",
    "AcceptedTripMaterial",
}


def normalize_text(value: Any) -> Any:
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    if isinstance(value, list):
        return [normalize_text(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_text(item) for key, item in value.items()}
    return value


class MaterialHandler:
    def create(
        self,
        *,
        run_id: str,
        material_type: str,
        stage: str,
        payload: BaseModel | dict[str, Any] | list[Any],
        source: str,
    ) -> MaterialEnvelope:
        if material_type not in MATERIAL_TYPES:
            raise ValueError(f"unsupported material type: {material_type}")
        raw = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
        normalized = normalize_text(raw)
        wrapped = normalized if isinstance(normalized, dict) else {"items": normalized}
        canonical = json.dumps(wrapped, sort_keys=True, separators=(",", ":")).encode()
        if len(canonical) > SETTINGS.max_material_bytes:
            raise ValueError("material payload exceeds configured size limit")
        return MaterialEnvelope(
            run_id=run_id,
            material_id=f"mat-{uuid4().hex}",
            material_type=material_type,
            stage=stage,
            schema_version="1.0",
            created_at=utc_now(),
            payload_hash=hashlib.sha256(canonical).hexdigest(),
            payload=wrapped,
            source=source,
        )

    @staticmethod
    def restore(data: dict[str, Any]) -> MaterialEnvelope:
        return MaterialEnvelope.model_validate(data)

    @staticmethod
    def validate_payload(material: MaterialEnvelope, model: type[ModelT]) -> ModelT:
        return model.model_validate(material.payload)
