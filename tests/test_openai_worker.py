from types import SimpleNamespace

from journey.models import WorkerRequest
from journey.tools.demo_tools import find_nearby_places, locate_destination, rank_places
from journey.workers.openai_worker import OpenAIJourneyWorker


class FakeResponses:
    def __init__(self, draft):
        self.draft = draft
        self.kwargs = None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(output_parsed=self.draft, usage=SimpleNamespace(total_tokens=42))


def test_openai_worker_uses_structured_sdk_without_network(trip_request):
    ranked = rank_places(find_nearby_places(trip_request.preferences.interests), locate_destination(trip_request.destination), trip_request)
    deterministic = __import__("journey.workers.deterministic_worker", fromlist=["DeterministicJourneyWorker"]).DeterministicJourneyWorker()
    draft = deterministic.execute(WorkerRequest(run_id="run", trip=trip_request, ranked_places=ranked)).draft
    responses = FakeResponses(draft)
    worker = OpenAIJourneyWorker(client=SimpleNamespace(responses=responses), model="test-model")
    result = worker.execute(WorkerRequest(run_id="run", trip=trip_request, ranked_places=ranked))
    assert result.draft == draft
    assert result.token_usage == 42
    assert responses.kwargs["text_format"].__name__ == "WorkerItineraryDraft"
    assert "OPENAI_API_KEY" not in str(responses.kwargs)


def test_openai_worker_without_key_returns_typed_error(monkeypatch, trip_request):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = OpenAIJourneyWorker().execute(WorkerRequest(run_id="run", trip=trip_request, ranked_places=[]))
    assert result.error == "OPENAI_API_KEY is not configured."
