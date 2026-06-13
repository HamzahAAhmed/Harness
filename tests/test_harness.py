from journey.harness.controller import JourneyHarness
from journey.models import WorkerResponse
from journey.workers.deterministic_worker import DeterministicJourneyWorker


def test_normal_scenario_completes_with_validated_map(trip_request):
    result = JourneyHarness().run(trip_request, DeterministicJourneyWorker())
    assert result.run_record.status == "completed"
    assert result.itinerary
    valid_ids = {item.place.place_id for item in JourneyHarness._ranked_from_record(result.run_record)}
    map_ids = {item.place_id for day in result.itinerary.days for item in day.activities}
    assert map_ids <= valid_ids
    assert result.map_geojson["features"]


def test_fail_once_feedback_changes_worker_and_passes(trip_request):
    result = JourneyHarness().run(trip_request, DeterministicJourneyWorker(), "fail_once_then_repair")
    drafts = [item for item in result.run_record.materials if item.material_type == "DraftItineraryMaterial"]
    feedback = [item for item in result.run_record.materials if item.material_type == "CheckpointFeedbackMaterial"]
    assert result.run_record.status == "completed"
    assert result.run_record.repair_attempts == 1
    assert "unknown-999" in str(drafts[0].payload)
    assert "unknown-999" not in str(drafts[1].payload)
    assert feedback
    assert any(alarm.alarm_type == "GROUNDING_VIOLATION" for alarm in result.run_record.alarms)


def test_fail_twice_stops_for_human(trip_request):
    result = JourneyHarness().run(trip_request, DeterministicJourneyWorker(), "fail_twice")
    alarm_types = {alarm.alarm_type for alarm in result.run_record.alarms}
    assert result.run_record.status == "needs_human"
    assert {"REPAIR_EXHAUSTED", "HUMAN_REVIEW_REQUIRED"} <= alarm_types
    assert result.escalation


class SpyWorker:
    worker_name = "Spy Worker"

    def __init__(self):
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return WorkerResponse(worker_name=self.worker_name, error="not used")


def test_invalid_destination_cannot_invoke_worker(trip_request):
    worker = SpyWorker()
    invalid = trip_request.model_copy(update={"destination": "Dallas, Texas"})
    result = JourneyHarness().run(invalid, worker)
    assert result.run_record.status == "blocked"
    assert not worker.requests


def test_transformed_candidates_reach_worker(trip_request, monkeypatch):
    from journey.harness import controller
    from journey.tools.demo_tools import find_nearby_places

    originals = find_nearby_places(trip_request.preferences.interests)
    oversized = [originals[index % len(originals)].model_copy(update={"place_id": f"extra-{index:02d}"}) for index in range(13)]
    monkeypatch.setattr(controller, "find_nearby_places", lambda interests: oversized)
    worker = SpyWorker()
    JourneyHarness().run(trip_request, worker)
    assert len(worker.requests[0].ranked_places) == 12


def test_acceptance_is_harness_owned_and_materialized(trip_request):
    harness = JourneyHarness()
    result = harness.run(trip_request, DeterministicJourneyWorker())
    record, payload = harness.accept(result.run_record, result.itinerary)
    assert record.status == "accepted"
    assert payload.run_id == record.run_id
    assert any(item.material_type == "AcceptedTripMaterial" for item in record.materials)
    assert any(event.event_type == "plan_accepted" for event in record.trace_events)


def test_refinement_changes_deterministic_itinerary_and_adds_museums(trip_request):
    harness = JourneyHarness()
    all_interests = trip_request.preferences.model_copy(
        update={"interests": ["Food", "History", "Art", "Nature", "Shopping", "Entertainment"]}
    )
    request = trip_request.model_copy(update={"preferences": all_interests})
    original = harness.run(request, DeterministicJourneyWorker())
    refined = harness.refine(original.run_record, "Add some meseums", DeterministicJourneyWorker())
    original_ids = [item.place_id for day in original.itinerary.days for item in day.activities]
    refined_items = [item for day in refined.itinerary.days for item in day.activities]
    assert refined.run_record.status == "completed"
    assert [item.place_id for item in refined_items] != original_ids
    assert any(item.category == "History" for item in refined_items)
    assert len(refined_items) > len(original_ids)
    assert any("museum" in item.reason.casefold() or "history" in item.reason.casefold() for item in refined_items)
    refined_ranked = JourneyHarness._ranked_from_record(refined.run_record)
    assert any(item.place.place_id == "demo-013" for item in refined_ranked)


def test_refinement_can_add_category_that_was_not_initially_selected(trip_request):
    harness = JourneyHarness()
    assert "History" not in trip_request.preferences.interests
    original = harness.run(trip_request, DeterministicJourneyWorker())
    refined = harness.refine(
        original.run_record,
        "Add some museums to my day",
        DeterministicJourneyWorker(),
    )
    original_ids = {
        item.place_id for day in original.itinerary.days for item in day.activities
    }
    added_items = [
        item
        for day in refined.itinerary.days
        for item in day.activities
        if item.place_id not in original_ids
    ]
    assert refined.run_record.status == "completed"
    assert added_items
    assert added_items[0].category == "History"
    assert "museum" in (
        added_items[0].name + " " + added_items[0].short_description
    ).casefold()
    assert len(JourneyHarness._ranked_from_record(refined.run_record)) <= 12


def test_validated_itinerary_and_map_include_fixture_details(trip_request):
    result = JourneyHarness().run(trip_request, DeterministicJourneyWorker())
    first_item = result.itinerary.days[0].activities[0]
    first_point = next(feature for feature in result.map_geojson["features"] if feature["geometry"]["type"] == "Point")
    assert first_item.short_description
    assert first_item.demo_rating > 0
    assert first_point["properties"]["description"] == first_item.short_description
    assert first_point["properties"]["rating"] == first_item.demo_rating
    assert first_point["properties"]["estimated_cost"] == first_item.estimated_cost


def test_refinement_adds_to_existing_day_and_preserves_current_stops(trip_request):
    harness = JourneyHarness()
    original = harness.run(trip_request, DeterministicJourneyWorker())
    refined = harness.refine(original.run_record, "Add another stop to my day", DeterministicJourneyWorker())
    original_ids = [item.place_id for item in original.itinerary.days[0].activities]
    refined_ids = [item.place_id for item in refined.itinerary.days[0].activities]
    assert refined.run_record.status == "completed"
    assert refined_ids[: len(original_ids)] == original_ids
    assert len(refined_ids) == len(original_ids) + 1


def test_refinement_removes_matching_category_and_preserves_other_stops(trip_request):
    harness = JourneyHarness()
    original = harness.run(trip_request, DeterministicJourneyWorker())
    category = original.itinerary.days[0].activities[0].category
    original_ids = [item.place_id for item in original.itinerary.days[0].activities]
    removed_id = original.itinerary.days[0].activities[0].place_id
    refined = harness.refine(
        original.run_record,
        f"Remove the {category.lower()} stop from my day",
        DeterministicJourneyWorker(),
    )
    refined_ids = [item.place_id for item in refined.itinerary.days[0].activities]
    assert refined.run_record.status == "completed"
    assert removed_id not in refined_ids
    assert refined_ids == original_ids[1:]


def test_chained_add_then_remove_keeps_added_place_grounded(trip_request):
    harness = JourneyHarness()
    all_interests = trip_request.preferences.model_copy(
        update={"interests": ["Food", "History", "Art", "Nature", "Shopping", "Entertainment"]}
    )
    request = trip_request.model_copy(update={"preferences": all_interests})
    original = harness.run(request, DeterministicJourneyWorker())
    added = harness.refine(
        original.run_record,
        "Add another museum stop to my day",
        DeterministicJourneyWorker(),
    )
    added_museum_ids = {
        item.place_id
        for item in added.itinerary.days[0].activities
        if item.category == "History"
    }
    added_food_count = sum(
        item.category == "Food" for item in added.itinerary.days[0].activities
    )
    removed = harness.refine(
        added.run_record,
        "Remove the food stop from my day",
        DeterministicJourneyWorker(),
    )
    removed_ids = {item.place_id for item in removed.itinerary.days[0].activities}
    assert removed.run_record.status == "completed"
    assert added_museum_ids <= removed_ids
    removed_food_count = sum(
        item.category == "Food" for item in removed.itinerary.days[0].activities
    )
    assert removed_food_count == max(0, added_food_count - 1)


def test_refinement_adds_swimming_place_when_nature_was_unchecked(trip_request):
    harness = JourneyHarness()
    assert "Nature" not in trip_request.preferences.interests
    original = harness.run(trip_request, DeterministicJourneyWorker())
    refined = harness.refine(
        original.run_record,
        "Add somewhere I can go swimming",
        DeterministicJourneyWorker(),
    )
    original_ids = {
        item.place_id for day in original.itinerary.days for item in day.activities
    }
    added = [
        item
        for day in refined.itinerary.days
        for item in day.activities
        if item.place_id not in original_ids
    ]
    assert refined.run_record.status == "completed"
    assert added
    assert "swimming" in added[0].capabilities
    assert "swimming" in refined.run_record.user_message.casefold()


def test_unsupported_refinement_preserves_itinerary_and_explains_result(trip_request):
    harness = JourneyHarness()
    original = harness.run(trip_request, DeterministicJourneyWorker())
    refined = harness.refine(
        original.run_record,
        "Add somewhere I can go skydiving",
        DeterministicJourneyWorker(),
    )
    original_ids = [
        item.place_id for day in original.itinerary.days for item in day.activities
    ]
    refined_ids = [
        item.place_id for day in refined.itinerary.days for item in day.activities
    ]
    assert refined_ids == original_ids
    assert "couldn't find" in refined.run_record.user_message.casefold()
    assert "skydiving" in refined.run_record.user_message.casefold()
