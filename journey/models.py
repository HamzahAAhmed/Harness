from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from journey.config import SUPPORTED_CATEGORIES


def utc_now() -> datetime:
    return datetime.now(UTC)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TripPreferences(StrictModel):
    interests: list[str] = Field(min_length=1)
    pace: Literal["relaxed", "balanced", "busy"]

    @field_validator("interests")
    @classmethod
    def supported_interests(cls, value: list[str]) -> list[str]:
        if set(value) - set(SUPPORTED_CATEGORIES):
            raise ValueError("interests contain unsupported categories")
        return list(dict.fromkeys(value))


class TripRequest(StrictModel):
    destination: str = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date
    travelers: int = Field(ge=1, le=6)
    budget: float = Field(gt=0)
    preferences: TripPreferences
    refinement: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def valid_dates(self) -> TripRequest:
        days = (self.end_date - self.start_date).days + 1
        if days < 1 or days > 3:
            raise ValueError("trip duration must be between one and three days")
        return self


class Destination(StrictModel):
    fixture_version: str
    destination_id: str
    name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    source: Literal["demo_fixture"]
    is_demo_data: Literal[True]


class Place(StrictModel):
    place_id: str
    name: str
    category: Literal["Food", "History", "Art", "Nature", "Shopping", "Entertainment"]
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    estimated_cost: float = Field(ge=0)
    demo_rating: float = Field(ge=0, le=5)
    demo_review_count: int = Field(ge=0)
    short_description: str = Field(max_length=240)
    capabilities: list[str] = Field(default_factory=list)
    source: Literal["demo_fixture"]
    is_demo_data: Literal[True]
    fixture_version: str


class RankedPlace(StrictModel):
    place: Place
    total_score: float
    score_components: dict[str, float]
    explanation: str


class ItineraryItemDraft(StrictModel):
    place_id: str
    start_time: str
    duration_minutes: int = Field(gt=0, le=720)
    reason: str = Field(min_length=1, max_length=240)


class ItineraryDayDraft(StrictModel):
    date: date
    day_theme: str = Field(min_length=1, max_length=120)
    activities: list[ItineraryItemDraft]


class WorkerItineraryDraft(StrictModel):
    days: list[ItineraryDayDraft]
    short_trip_summary: str = Field(min_length=1, max_length=500)


class ValidatedItineraryItem(ItineraryItemDraft):
    name: str
    category: str
    short_description: str
    capabilities: list[str]
    latitude: float
    longitude: float
    estimated_cost: float
    demo_rating: float
    demo_review_count: int
    source: Literal["demo_fixture"]
    is_demo_data: Literal[True]


class ValidatedItineraryDay(StrictModel):
    date: date
    day_theme: str
    activities: list[ValidatedItineraryItem]


class ValidatedItinerary(StrictModel):
    days: list[ValidatedItineraryDay]
    short_trip_summary: str


class CheckpointFeedback(StrictModel):
    failed_checkpoint_id: str
    failed_criteria: list[str]
    validation_errors: list[str]
    valid_place_ids: list[str]
    required_correction: str
    repair_attempt: int


class WorkerRequest(StrictModel):
    run_id: str
    trip: TripRequest
    ranked_places: list[RankedPlace]
    existing_itinerary: WorkerItineraryDraft | None = None
    checkpoint_feedback: CheckpointFeedback | None = None
    attempt: int = 1
    scenario: Literal["normal", "fail_once_then_repair", "fail_twice"] = "normal"


class WorkerResponse(StrictModel):
    worker_name: str
    draft: WorkerItineraryDraft | None = None
    raw_output: dict[str, Any] | None = None
    token_usage: int | None = None
    latency_ms: float | None = None
    error: str | None = None
    user_message: str | None = None


class HumanEscalation(StrictModel):
    reason: str
    question: str
    available_options: list[str]
    blocking_checkpoint: str | None
    related_alarm_id: str


class MaterialEnvelope(StrictModel):
    run_id: str
    material_id: str
    material_type: str
    stage: str
    schema_version: str
    created_at: datetime
    payload_hash: str
    payload: dict[str, Any]
    source: str


class GuardrailDeclaration(StrictModel):
    guardrail_id: str
    name: str
    stage: str
    description: str
    action_on_failure: Literal["block", "transform", "retry", "escalate"]
    severity: Literal["info", "warning", "error", "critical"]


class GuardrailResult(StrictModel):
    guardrail_id: str
    passed: bool
    action: str
    reason: str | None
    input_material_id: str
    output_material_id: str | None = None


class CheckpointDeclaration(StrictModel):
    checkpoint_id: str
    name: str
    stage: str
    criteria: list[str]
    repairable: bool


class CheckpointResult(StrictModel):
    checkpoint_id: str
    checkpoint_name: str
    stage: str
    status: Literal["pass", "fail", "needs_human"]
    criteria: list[str]
    failures: list[str]
    feedback_for_worker: list[str]
    input_material_id: str
    output_material_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class HarnessAlarm(StrictModel):
    alarm_id: str
    run_id: str
    alarm_type: str
    severity: Literal["info", "warning", "error", "critical"]
    stage: str
    context: dict[str, Any]
    recommended_action: str
    requires_human: bool
    created_at: datetime = Field(default_factory=utc_now)


class TraceEvent(StrictModel):
    event_id: str
    run_id: str
    event_type: str
    stage: str
    created_at: datetime = Field(default_factory=utc_now)
    duration_ms: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class RunRecord(StrictModel):
    run_id: str
    parent_run_id: str | None = None
    replay_checkpoint_id: str | None = None
    worker_name: str
    current_stage: str
    trip_request: TripRequest
    scenario: str = "normal"
    materials: list[MaterialEnvelope] = Field(default_factory=list)
    guardrail_results: list[GuardrailResult] = Field(default_factory=list)
    checkpoint_results: list[CheckpointResult] = Field(default_factory=list)
    alarms: list[HarnessAlarm] = Field(default_factory=list)
    trace_events: list[TraceEvent] = Field(default_factory=list)
    repair_attempts: int = 0
    refinement_turns: int = 0
    status: str
    user_message: str | None = None


class HarnessRunResult(StrictModel):
    run_record: RunRecord
    itinerary: ValidatedItinerary | None = None
    escalation: HumanEscalation | None = None
    map_geojson: dict[str, Any] | None = None


class SaveTripPayload(StrictModel):
    run_id: str
    accepted_at: datetime = Field(default_factory=utc_now)
    itinerary: ValidatedItinerary
    demo_data_disclaimer: str
