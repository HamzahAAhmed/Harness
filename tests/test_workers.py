from journey.models import WorkerRequest
from journey.tools.demo_tools import find_nearby_places, locate_destination, rank_places
from journey.workers.deterministic_worker import DeterministicJourneyWorker
from journey.workers.protocol import JourneyWorker


def test_deterministic_worker_implements_protocol(trip_request):
    worker = DeterministicJourneyWorker()
    ranked = rank_places(find_nearby_places(trip_request.preferences.interests), locate_destination(trip_request.destination), trip_request)
    response = worker.execute(WorkerRequest(run_id="run", trip=trip_request, ranked_places=ranked))
    assert isinstance(worker, JourneyWorker)
    assert response.draft


def test_deterministic_worker_interprets_misspelled_museum_refinement(trip_request):
    worker = DeterministicJourneyWorker()
    all_interests = trip_request.preferences.model_copy(
        update={"interests": ["Food", "History", "Art", "Nature", "Shopping", "Entertainment"]}
    )
    refined_trip = trip_request.model_copy(
        update={"preferences": all_interests, "refinement": "Add some meseums"}
    )
    ranked = rank_places(find_nearby_places(refined_trip.preferences.interests), locate_destination(refined_trip.destination), refined_trip)
    response = worker.execute(WorkerRequest(run_id="run", trip=refined_trip, ranked_places=ranked))
    selected = [item.place_id for day in response.draft.days for item in day.activities]
    history_ids = {item.place.place_id for item in ranked if item.place.category == "History"}
    assert history_ids.intersection(selected)
    assert len(selected) == 3


def test_fixture_catalog_expands_without_exceeding_declared_demo_scope(trip_request):
    places = find_nearby_places(["Food", "History", "Art", "Nature", "Shopping", "Entertainment"])
    assert len(places) >= 20
    assert all(sum(place.category == category for place in places) >= 2 for category in trip_request.preferences.interests)
    assert any("swimming" in place.capabilities for place in places)
