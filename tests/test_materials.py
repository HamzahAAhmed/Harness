import pytest

from journey.harness.materials import MaterialHandler
from journey.models import TripRequest


def test_material_ids_hashes_sources_and_restore(trip_request):
    handler = MaterialHandler()
    material = handler.create(run_id="run-1", material_type="TripRequestMaterial", stage="input", payload=trip_request, source="user_input")
    restored = handler.restore(material.model_dump(mode="json"))
    assert material.material_id.startswith("mat-")
    assert len(material.payload_hash) == 64
    assert restored == material
    assert restored.source == "user_input"
    assert handler.validate_payload(restored, TripRequest) == trip_request


def test_invalid_material_type_is_rejected(trip_request):
    with pytest.raises(ValueError, match="unsupported material"):
        MaterialHandler().create(run_id="run-1", material_type="Unknown", stage="input", payload=trip_request, source="test")
