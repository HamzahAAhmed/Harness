from journey.config import SETTINGS
from journey.harness.guardrails import (
    GUARDRAIL_REGISTRY,
    evaluate_trip,
    finite_limits,
    transform_candidate_limit,
)
from journey.harness.materials import MaterialHandler


def test_guardrails_are_declared_and_valid_input_passes(trip_request):
    material = MaterialHandler().create(run_id="run", material_type="TripRequestMaterial", stage="input", payload=trip_request, source="user")
    results = evaluate_trip(trip_request, material.material_id, "Austin, Texas")
    assert GUARDRAIL_REGISTRY
    assert all(result.passed for result in results)
    assert all(value > 0 for value in finite_limits().values())


def test_candidate_guardrail_transforms_to_limit():
    handler = MaterialHandler()
    original = handler.create(run_id="run", material_type="CandidatePlacesMaterial", stage="candidates", payload={"places": [{"place_id": str(index)} for index in range(15)]}, source="demo_fixture")
    transformed, result = transform_candidate_limit(original, handler)
    assert result.action == "transform"
    assert result.output_material_id == transformed.material_id
    assert len(transformed.payload["places"]) == SETTINGS.max_candidate_places
