from __future__ import annotations

from typing import Any
from uuid import uuid4

from journey.config import SUPPORTED_CATEGORIES, activity_from_text, category_from_text
from journey.harness.alarms import create_alarm
from journey.harness.checkpoints import (
    candidate_quality,
    grounding,
    input_integrity,
    itinerary_schema,
    schedule,
)
from journey.harness.guardrails import evaluate_trip, transform_candidate_limit
from journey.harness.materials import MaterialHandler
from journey.harness.observability import trace
from journey.models import (
    CheckpointFeedback,
    HarnessRunResult,
    HumanEscalation,
    Place,
    RankedPlace,
    RunRecord,
    SaveTripPayload,
    TripRequest,
    ValidatedItinerary,
    ValidatedItineraryDay,
    ValidatedItineraryItem,
    WorkerItineraryDraft,
    WorkerRequest,
)
from journey.tools.demo_tools import find_nearby_places, locate_destination, rank_places, save_trip
from journey.workers.protocol import JourneyWorker


class JourneyHarness:
    def __init__(self) -> None:
        self.materials = MaterialHandler()

    def run(self, trip_request: TripRequest, worker: JourneyWorker, scenario: str = "normal") -> HarnessRunResult:
        run_id = f"run-{uuid4().hex}"
        record = RunRecord(run_id=run_id, worker_name=worker.worker_name, current_stage="input", trip_request=trip_request, scenario=scenario, status="running")
        record.trace_events.append(trace(run_id, "run_started", "input", worker=worker.worker_name))
        request_material = self.materials.create(run_id=run_id, material_type="TripRequestMaterial", stage="input", payload=trip_request, source="user_input")
        record.materials.append(request_material)
        try:
            destination = locate_destination(trip_request.destination)
        except ValueError as exc:
            return self._blocked(record, request_material.material_id, str(exc))
        record.guardrail_results.extend(evaluate_trip(trip_request, request_material.material_id, destination.name))
        if any(not item.passed for item in record.guardrail_results):
            return self._blocked(record, request_material.material_id, "Trip input failed a declared guardrail.")
        input_result = input_integrity(trip_request, request_material, destination.name)
        record.checkpoint_results.append(input_result)
        if input_result.status != "pass":
            return self._blocked(record, request_material.material_id, "; ".join(input_result.failures))
        places = find_nearby_places(trip_request.preferences.interests)
        candidate_material = self.materials.create(run_id=run_id, material_type="CandidatePlacesMaterial", stage="candidates", payload={"places": [item.model_dump(mode="json") for item in places]}, source="demo_fixture")
        record.materials.append(candidate_material)
        candidate_material, candidate_guardrail = transform_candidate_limit(candidate_material, self.materials)
        record.guardrail_results.append(candidate_guardrail)
        if candidate_guardrail.action == "transform":
            record.materials.append(candidate_material)
        places = [Place.model_validate(item) for item in candidate_material.payload["places"]]
        candidate_result = candidate_quality(places, candidate_material)
        record.checkpoint_results.append(candidate_result)
        if candidate_result.status != "pass":
            return self._escalate(record, "No valid candidate places matched the request.", "candidate_quality")
        ranked = rank_places(places, destination, trip_request)
        ranked_material = self.materials.create(run_id=run_id, material_type="RankedPlacesMaterial", stage="ranking", payload={"ranked_places": [item.model_dump(mode="json") for item in ranked]}, source="demo_tool")
        record.materials.append(ranked_material)
        return self._execute_from_ranked(record, ranked, worker)

    def _execute_from_ranked(self, record: RunRecord, ranked: list[RankedPlace], worker: JourneyWorker, existing: WorkerItineraryDraft | None = None) -> HarnessRunResult:
        feedback = None
        for attempt in (1, 2):
            request = WorkerRequest(run_id=record.run_id, trip=record.trip_request, ranked_places=ranked, existing_itinerary=existing, checkpoint_feedback=feedback, attempt=attempt, scenario=record.scenario)
            request_material = self.materials.create(run_id=record.run_id, material_type="WorkerRequestMaterial", stage="worker", payload=request, source="harness")
            record.materials.append(request_material)
            record.trace_events.append(trace(record.run_id, "worker_started", "worker", attempt=attempt))
            try:
                response = worker.execute(request)
            except Exception as exc:
                alarm = create_alarm(run_id=record.run_id, alarm_type="WORKER_EXECUTION_FAILED", severity="error", stage="worker", context={"error": str(exc)}, recommended_action="Review worker configuration or choose deterministic mode.", requires_human=True)
                self._record_alarm(record, alarm)
                return self._escalate(record, str(exc), "worker")
            if response.error:
                alarm = create_alarm(run_id=record.run_id, alarm_type="WORKER_EXECUTION_FAILED", severity="error", stage="worker", context={"error": response.error}, recommended_action="Review worker configuration or choose deterministic mode.", requires_human=True)
                self._record_alarm(record, alarm)
                return self._escalate(record, response.error, "worker")
            record.user_message = response.user_message
            raw: Any = response.draft or response.raw_output
            draft_material = self.materials.create(run_id=record.run_id, material_type="DraftItineraryMaterial", stage="worker_output", payload=raw.model_dump(mode="json") if raw else {"error": response.error}, source=response.worker_name)
            record.materials.append(draft_material)
            draft, schema_result = itinerary_schema(raw, record.trip_request, draft_material)
            record.checkpoint_results.append(schema_result)
            output_results = [schema_result]
            if draft is not None and schema_result.status == "pass":
                output_results.extend([grounding(draft, ranked, draft_material), schedule(draft, record.trip_request, draft_material)])
                record.checkpoint_results.extend(output_results[1:])
            failures = [item for item in output_results if item.status != "pass"]
            if not failures and draft is not None:
                itinerary = self._hydrate(draft, ranked)
                validated_material = self.materials.create(run_id=record.run_id, material_type="ValidatedItineraryMaterial", stage="validated", payload=itinerary, source="harness")
                record.materials.append(validated_material)
                record.current_stage = "completed"
                record.status = "completed"
                record.trace_events.append(trace(record.run_id, "run_completed", "completed", repairs=record.repair_attempts))
                return HarnessRunResult(run_record=record, itinerary=itinerary, map_geojson=self._geojson(itinerary))
            failed = failures[0]
            alarm_type = "GROUNDING_VIOLATION" if failed.checkpoint_id == "grounding" else "CHECKPOINT_FAILED"
            self._record_alarm(record, create_alarm(run_id=record.run_id, alarm_type=alarm_type, severity="error", stage=failed.stage, context={"failures": failed.failures}, recommended_action="Apply checkpoint feedback using supplied place IDs."))
            if attempt == 2:
                self._record_alarm(record, create_alarm(run_id=record.run_id, alarm_type="REPAIR_EXHAUSTED", severity="critical", stage=failed.stage, context={"checkpoint": failed.checkpoint_id}, recommended_action="Stop and request human review.", requires_human=True))
                return self._escalate(record, "The worker failed the same validation flow after one repair.", failed.checkpoint_id)
            record.repair_attempts = 1
            feedback = CheckpointFeedback(failed_checkpoint_id=failed.checkpoint_id, failed_criteria=failed.criteria, validation_errors=failed.failures, valid_place_ids=[item.place.place_id for item in ranked], required_correction="Replace unsupported values using supplied place IDs and preserve valid itinerary items.", repair_attempt=1)
            feedback_material = self.materials.create(run_id=record.run_id, material_type="CheckpointFeedbackMaterial", stage="repair", payload=feedback, source="harness")
            record.materials.append(feedback_material)
            self._record_alarm(record, create_alarm(run_id=record.run_id, alarm_type="REPAIR_REQUESTED", severity="warning", stage="repair", context={"checkpoint": failed.checkpoint_id}, recommended_action="Invoke the same worker once with checkpoint feedback."))
            record.trace_events.append(trace(record.run_id, "repair_requested", "repair", checkpoint=failed.checkpoint_id))
        raise AssertionError("unreachable")

    def refine(self, run_record: RunRecord, refinement: str, worker: JourneyWorker) -> HarnessRunResult:
        record = run_record.model_copy(deep=True)
        record.run_id = f"run-{uuid4().hex}"
        record.parent_run_id = run_record.run_id
        record.refinement_turns += 1
        if record.refinement_turns > 3:
            return self._escalate(record, "Refinement limit reached.", "worker_limits")
        record.trip_request = record.trip_request.model_copy(update={"refinement": refinement})
        ranked = self._ranked_for_refinement(record, run_record)
        existing = self._draft_from_record(run_record)
        return self._execute_from_ranked(record, ranked, worker, existing)

    def replay(self, run_record: RunRecord, checkpoint_id: str, worker: JourneyWorker) -> HarnessRunResult:
        record = RunRecord(run_id=f"run-{uuid4().hex}", parent_run_id=run_record.run_id, replay_checkpoint_id=checkpoint_id, worker_name=worker.worker_name, current_stage="replay", trip_request=run_record.trip_request, scenario=run_record.scenario, status="running")
        ranked_material = next(item for item in run_record.materials if item.material_type == "RankedPlacesMaterial")
        record.materials.append(ranked_material.model_copy(update={"run_id": record.run_id, "material_id": f"mat-{uuid4().hex}"}))
        record.trace_events.append(trace(record.run_id, "replay_started", "replay", parent_run_id=run_record.run_id, checkpoint=checkpoint_id, reused_ranked_material=True))
        return self._execute_from_ranked(record, self._ranked_from_record(run_record), worker)

    def accept(self, run_record: RunRecord, itinerary: ValidatedItinerary) -> tuple[RunRecord, SaveTripPayload]:
        record = run_record.model_copy(deep=True)
        payload = save_trip(record.run_id, itinerary)
        material = self.materials.create(run_id=record.run_id, material_type="AcceptedTripMaterial", stage="accepted", payload=payload, source="user_acceptance")
        record.materials.append(material)
        record.current_stage = "accepted"
        record.status = "accepted"
        record.trace_events.append(trace(record.run_id, "plan_accepted", "accepted"))
        return record, payload

    @staticmethod
    def _ranked_from_record(record: RunRecord) -> list[RankedPlace]:
        material = next(
            item
            for item in reversed(record.materials)
            if item.material_type == "RankedPlacesMaterial"
        )
        return [RankedPlace.model_validate(item) for item in material.payload["ranked_places"]]

    def _ranked_for_refinement(
        self,
        record: RunRecord,
        source_record: RunRecord,
    ) -> list[RankedPlace]:
        places = find_nearby_places(list(SUPPORTED_CATEGORIES))
        category = category_from_text(record.trip_request.refinement)
        activity = activity_from_text(record.trip_request.refinement)
        existing = self._draft_from_record(source_record)
        existing_ids = {
            activity.place_id
            for day in existing.days
            for activity in day.activities
        } if existing else set()
        places.sort(
            key=lambda place: (
                place.place_id not in existing_ids,
                activity not in place.capabilities if activity else False,
                place.category != category if category else False,
                place.place_id,
            )
        )
        material = self.materials.create(
            run_id=record.run_id,
            material_type="CandidatePlacesMaterial",
            stage="refinement_candidates",
            payload={"places": [place.model_dump(mode="json") for place in places]},
            source="demo_fixture",
        )
        record.materials.append(material)
        material, guardrail = transform_candidate_limit(material, self.materials)
        record.guardrail_results.append(guardrail)
        if guardrail.action == "transform":
            record.materials.append(material)
        selected = [Place.model_validate(item) for item in material.payload["places"]]
        checkpoint = candidate_quality(selected, material)
        record.checkpoint_results.append(checkpoint)
        destination = locate_destination(record.trip_request.destination)
        ranked = rank_places(selected, destination, record.trip_request)
        ranked_material = self.materials.create(
            run_id=record.run_id,
            material_type="RankedPlacesMaterial",
            stage="refinement_ranking",
            payload={"ranked_places": [item.model_dump(mode="json") for item in ranked]},
            source="demo_tool",
        )
        record.materials.append(ranked_material)
        return ranked

    @staticmethod
    def _draft_from_record(record: RunRecord) -> WorkerItineraryDraft | None:
        drafts = [item for item in record.materials if item.material_type == "DraftItineraryMaterial"]
        return WorkerItineraryDraft.model_validate(drafts[-1].payload) if drafts else None

    def _blocked(self, record: RunRecord, material_id: str, reason: str) -> HarnessRunResult:
        record.status = "blocked"
        record.current_stage = "input"
        self._record_alarm(record, create_alarm(run_id=record.run_id, alarm_type="INPUT_GUARDRAIL_BLOCKED", severity="error", stage="input", context={"reason": reason, "material_id": material_id}, recommended_action="Correct the trip input before invoking a worker."))
        return HarnessRunResult(run_record=record)

    def _escalate(self, record: RunRecord, reason: str, checkpoint: str) -> HarnessRunResult:
        alarm = create_alarm(run_id=record.run_id, alarm_type="HUMAN_REVIEW_REQUIRED", severity="critical", stage=checkpoint, context={"reason": reason}, recommended_action="Ask the user to revise constraints, retry, or start over.", requires_human=True)
        self._record_alarm(record, alarm)
        record.status = "needs_human"
        record.current_stage = checkpoint
        escalation = HumanEscalation(
            reason=reason,
            question="How should Journey continue?",
            available_options=[
                "Change the trip fields on the left, then click Generate itinerary.",
                "Open Demo controls, select Normal, then click Generate itinerary.",
                "Click Start over to clear the current run and begin again.",
            ],
            blocking_checkpoint=checkpoint,
            related_alarm_id=alarm.alarm_id,
        )
        return HarnessRunResult(run_record=record, escalation=escalation)

    @staticmethod
    def _record_alarm(record: RunRecord, alarm) -> None:
        record.alarms.append(alarm)
        record.trace_events.append(trace(record.run_id, "alarm_created", alarm.stage, alarm_type=alarm.alarm_type, severity=alarm.severity))

    @staticmethod
    def _hydrate(draft: WorkerItineraryDraft, ranked: list[RankedPlace]) -> ValidatedItinerary:
        places = {item.place.place_id: item.place for item in ranked}
        days = []
        for day in draft.days:
            activities = []
            for item in day.activities:
                place = places[item.place_id]
                activities.append(ValidatedItineraryItem(**item.model_dump(), name=place.name, category=place.category, short_description=place.short_description, capabilities=place.capabilities, latitude=place.latitude, longitude=place.longitude, estimated_cost=place.estimated_cost, demo_rating=place.demo_rating, demo_review_count=place.demo_review_count, source=place.source, is_demo_data=True))
            days.append(ValidatedItineraryDay(date=day.date, day_theme=day.day_theme, activities=activities))
        return ValidatedItinerary(days=days, short_trip_summary=draft.short_trip_summary)

    @staticmethod
    def _geojson(itinerary: ValidatedItinerary) -> dict[str, Any]:
        activities = [item for day in itinerary.days for item in day.activities]
        features = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [item.longitude, item.latitude]}, "properties": {"order": index + 1, "name": item.name, "category": item.category, "capabilities": ", ".join(item.capabilities), "time": item.start_time, "duration_minutes": item.duration_minutes, "reason": item.reason, "description": item.short_description, "rating": item.demo_rating, "review_count": item.demo_review_count, "estimated_cost": item.estimated_cost}} for index, item in enumerate(activities)]
        if activities:
            features.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[item.longitude, item.latitude] for item in activities]}, "properties": {"kind": "route"}})
        return {"type": "FeatureCollection", "features": features}
