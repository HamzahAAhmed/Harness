import os

from app import app, server
from journey.harness.controller import JourneyHarness
from journey.harness.persistence import serialize_run
from journey.workers.deterministic_worker import DeterministicJourneyWorker


def test_dash_exposes_server_and_required_stores():
    assert server is app.server
    rendered = str(app.layout())
    for store_id in ("active-run-store", "active-itinerary-store", "accepted-trip-store", "run-history-store", "map-data-store"):
        assert store_id in rendered


def test_server_key_never_enters_client_run_payload(trip_request, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret-test-key")
    result = JourneyHarness().run(trip_request, DeterministicJourneyWorker())
    assert os.environ["OPENAI_API_KEY"] not in str(serialize_run(result.run_record))
    assert os.environ["OPENAI_API_KEY"] not in str(app.layout())
