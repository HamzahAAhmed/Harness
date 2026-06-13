from journey.harness.controller import JourneyHarness
from journey.harness.persistence import restore_run, serialize_run
from journey.workers.deterministic_worker import DeterministicJourneyWorker


def test_replay_reuses_ranked_material_and_links_parent(trip_request):
    harness = JourneyHarness()
    original = harness.run(trip_request, DeterministicJourneyWorker())
    restored = restore_run(serialize_run(original.run_record))
    replay = harness.replay(restored, "grounding", DeterministicJourneyWorker())
    assert replay.run_record.status == "completed"
    assert replay.run_record.parent_run_id == original.run_record.run_id
    assert replay.run_record.replay_checkpoint_id == "grounding"
    assert any(event.details.get("reused_ranked_material") for event in replay.run_record.trace_events)
    assert not any(item.material_type == "CandidatePlacesMaterial" for item in replay.run_record.materials)
