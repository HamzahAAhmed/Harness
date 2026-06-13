from datetime import date

from journey.harness.checkpoints import CHECKPOINT_REGISTRY, grounding, schedule
from journey.harness.materials import MaterialHandler
from journey.models import ItineraryDayDraft, ItineraryItemDraft, WorkerItineraryDraft
from journey.tools.demo_tools import find_nearby_places, locate_destination, rank_places


def _ranked(trip_request):
    places = find_nearby_places(trip_request.preferences.interests)
    return rank_places(places, locate_destination(trip_request.destination), trip_request)


def test_checkpoint_registry_has_exact_five():
    assert set(CHECKPOINT_REGISTRY) == {"input_integrity", "candidate_quality", "itinerary_schema", "grounding", "schedule"}
    assert all(item.criteria for item in CHECKPOINT_REGISTRY.values())


def test_unknown_place_fails_grounding(trip_request):
    draft = WorkerItineraryDraft(days=[ItineraryDayDraft(date=date(2026, 7, 1), day_theme="Test", activities=[ItineraryItemDraft(place_id="unknown", start_time="09:00", duration_minutes=60, reason="Test")])], short_trip_summary="Test")
    material = MaterialHandler().create(run_id="run", material_type="DraftItineraryMaterial", stage="output", payload=draft, source="worker")
    assert grounding(draft, _ranked(trip_request), material).status == "fail"


def test_overlapping_schedule_fails(trip_request):
    valid_id = _ranked(trip_request)[0].place.place_id
    draft = WorkerItineraryDraft(days=[ItineraryDayDraft(date=date(2026, 7, 1), day_theme="Test", activities=[ItineraryItemDraft(place_id=valid_id, start_time="09:00", duration_minutes=120, reason="First"), ItineraryItemDraft(place_id=valid_id, start_time="10:00", duration_minutes=60, reason="repeat visit")])], short_trip_summary="Test")
    material = MaterialHandler().create(run_id="run", material_type="DraftItineraryMaterial", stage="output", payload=draft, source="worker")
    assert any("overlap" in failure for failure in schedule(draft, trip_request, material).failures)
