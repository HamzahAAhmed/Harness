from journey.harness.persistence import restore_run, serialize_run, try_restore_run
from journey.models import RunRecord


def test_run_record_round_trip_revalidates_browser_data(trip_request):
    record = RunRecord(run_id="run", worker_name="deterministic", current_stage="input", trip_request=trip_request, status="running")
    assert restore_run(serialize_run(record)) == record
    tampered = serialize_run(record)
    tampered["repair_attempts"] = "not-an-int"
    restored, error = try_restore_run(tampered)
    assert restored is None
    assert error
