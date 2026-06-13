from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import ValidationError

from journey.config import SETTINGS
from journey.models import (
    CheckpointDeclaration,
    CheckpointResult,
    MaterialEnvelope,
    Place,
    RankedPlace,
    TripRequest,
    WorkerItineraryDraft,
)

CHECKPOINT_REGISTRY = {
    item.checkpoint_id: item
    for item in [
        CheckpointDeclaration(checkpoint_id="input_integrity", name="Input Integrity Checkpoint", stage="input", criteria=["Required fields exist", "Destination matches fixture", "Dates and duration are valid", "Travelers, budget, interests, and pace are supported"], repairable=False),
        CheckpointDeclaration(checkpoint_id="candidate_quality", name="Candidate Quality Checkpoint", stage="candidates", criteria=["Candidates are non-empty", "Place IDs are unique", "Coordinates are valid", "Sources and demo flags are valid", "Candidate count is within limit"], repairable=False),
        CheckpointDeclaration(checkpoint_id="itinerary_schema", name="Itinerary Schema Checkpoint", stage="worker_output", criteria=["Output parses as WorkerItineraryDraft", "Day count matches request", "Every day and activity has required fields"], repairable=True),
        CheckpointDeclaration(checkpoint_id="grounding", name="Grounding Checkpoint", stage="worker_output", criteria=["Every place ID is ranked", "No unsupported place is introduced", "Canonical fields are supplied only by harness hydration"], repairable=True),
        CheckpointDeclaration(checkpoint_id="schedule", name="Schedule Checkpoint", stage="worker_output", criteria=["Dates are in range", "Times parse and are chronological", "Activities do not overlap", "Durations are positive", "Repeats are justified", "Activity count matches pace"], repairable=True),
    ]
}


def result(checkpoint_id: str, material_id: str, failures: list[str], output_material_id: str | None = None) -> CheckpointResult:
    declaration = CHECKPOINT_REGISTRY[checkpoint_id]
    return CheckpointResult(checkpoint_id=checkpoint_id, checkpoint_name=declaration.name, stage=declaration.stage, status="fail" if failures else "pass", criteria=declaration.criteria, failures=failures, feedback_for_worker=failures if declaration.repairable else [], input_material_id=material_id, output_material_id=output_material_id)


def input_integrity(request: TripRequest, material: MaterialEnvelope, supported_destination: str) -> CheckpointResult:
    failures = []
    if request.destination.casefold() != supported_destination.casefold():
        failures.append("Destination does not match the supported demo fixture.")
    days = (request.end_date - request.start_date).days + 1
    if not 1 <= days <= SETTINGS.max_trip_days:
        failures.append("Trip duration is outside one to three days.")
    return result("input_integrity", material.material_id, failures)


def candidate_quality(places: list[Place], material: MaterialEnvelope) -> CheckpointResult:
    failures = []
    ids = [place.place_id for place in places]
    if not places:
        failures.append("Candidate collection is empty.")
    if len(ids) != len(set(ids)):
        failures.append("Candidate place IDs are not unique.")
    if any(place.source != "demo_fixture" or not place.is_demo_data for place in places):
        failures.append("Candidates must identify local demonstration fixture data.")
    if len(places) > SETTINGS.max_candidate_places:
        failures.append("Candidate count exceeds the configured limit.")
    return result("candidate_quality", material.material_id, failures)


def itinerary_schema(raw: object, request: TripRequest, material: MaterialEnvelope) -> tuple[WorkerItineraryDraft | None, CheckpointResult]:
    failures = []
    try:
        draft = raw if isinstance(raw, WorkerItineraryDraft) else WorkerItineraryDraft.model_validate(raw)
    except ValidationError as exc:
        return None, result("itinerary_schema", material.material_id, [str(exc)])
    expected_days = (request.end_date - request.start_date).days + 1
    if len(draft.days) != expected_days:
        failures.append(f"Expected {expected_days} itinerary days, received {len(draft.days)}.")
    return draft, result("itinerary_schema", material.material_id, failures)


def grounding(draft: WorkerItineraryDraft, ranked: list[RankedPlace], material: MaterialEnvelope) -> CheckpointResult:
    valid_ids = {item.place.place_id for item in ranked}
    unknown = sorted({activity.place_id for day in draft.days for activity in day.activities if activity.place_id not in valid_ids})
    failures = [f'Unknown place ID "{place_id}". Valid IDs: {sorted(valid_ids)}' for place_id in unknown]
    return result("grounding", material.material_id, failures)


def schedule(draft: WorkerItineraryDraft, request: TripRequest, material: MaterialEnvelope) -> CheckpointResult:
    failures: list[str] = []
    pace_limits = {"relaxed": (2, 3), "balanced": (3, 4), "busy": (4, 5)}
    low, high = pace_limits[request.preferences.pace]
    if request.refinement and any(
        term in request.refinement.casefold()
        for term in ("remove", "delete", "drop", "less", "fewer")
    ):
        low = max(0, low - 1)
    seen: set[str] = set()
    for day in draft.days:
        if not request.start_date <= day.date <= request.end_date:
            failures.append(f"Date {day.date} is outside the trip range.")
        if not low <= len(day.activities) <= high:
            failures.append(f"{day.date} has {len(day.activities)} activities; {request.preferences.pace} requires {low}-{high}.")
        previous_end = None
        for activity in day.activities:
            try:
                start = datetime.strptime(activity.start_time, "%H:%M")
            except ValueError:
                failures.append(f"Invalid start time {activity.start_time}.")
                continue
            if previous_end and start < previous_end:
                failures.append(f"Activity at {activity.start_time} overlaps or is not chronological.")
            previous_end = start + timedelta(minutes=activity.duration_minutes)
            if activity.place_id in seen and "repeat" not in activity.reason.casefold():
                failures.append(f"Repeated place {activity.place_id} lacks an explicit reason.")
            seen.add(activity.place_id)
    return result("schedule", material.material_id, failures)
