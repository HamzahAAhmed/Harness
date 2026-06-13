from __future__ import annotations

from journey.config import SETTINGS, SUPPORTED_CATEGORIES, SUPPORTED_PACES
from journey.harness.materials import MaterialHandler
from journey.models import GuardrailDeclaration, GuardrailResult, MaterialEnvelope, TripRequest

GUARDRAIL_REGISTRY = {
    declaration.guardrail_id: declaration
    for declaration in [
        GuardrailDeclaration(guardrail_id="destination", name="Supported destination", stage="input", description="Destination is present and matches the fixture.", action_on_failure="block", severity="error"),
        GuardrailDeclaration(guardrail_id="dates", name="Trip dates", stage="input", description="Dates define a one-to-three-day trip.", action_on_failure="block", severity="error"),
        GuardrailDeclaration(guardrail_id="travelers_budget", name="Travelers and budget", stage="input", description="Travelers and budget are within bounds.", action_on_failure="block", severity="error"),
        GuardrailDeclaration(guardrail_id="preferences", name="Supported preferences", stage="input", description="Interests and pace are supported.", action_on_failure="block", severity="error"),
        GuardrailDeclaration(guardrail_id="refinement", name="Refinement length", stage="input", description="Refinement text is at most 500 characters.", action_on_failure="block", severity="warning"),
        GuardrailDeclaration(guardrail_id="candidate_limit", name="Candidate limit", stage="material", description="Candidate collection is capped at the configured limit.", action_on_failure="transform", severity="warning"),
        GuardrailDeclaration(guardrail_id="worker_context", name="Worker context allowlist", stage="material", description="Worker receives only typed request fields.", action_on_failure="block", severity="critical"),
        GuardrailDeclaration(guardrail_id="worker_limits", name="Worker limits", stage="worker", description="Attempts, refinements, session time, and tokens are finite.", action_on_failure="escalate", severity="error"),
        GuardrailDeclaration(guardrail_id="unsupported_actions", name="Unsupported actions", stage="worker", description="Booking, payment, URL, file, and code execution requests are blocked.", action_on_failure="escalate", severity="critical"),
    ]
}


def evaluate_trip(request: TripRequest, material_id: str, supported_destination: str) -> list[GuardrailResult]:
    days = (request.end_date - request.start_date).days + 1
    checks = {
        "destination": request.destination.casefold() == supported_destination.casefold(),
        "dates": 1 <= days <= SETTINGS.max_trip_days,
        "travelers_budget": 1 <= request.travelers <= 6 and request.budget > 0,
        "preferences": set(request.preferences.interests) <= set(SUPPORTED_CATEGORIES) and request.preferences.pace in SUPPORTED_PACES,
        "refinement": not request.refinement or len(request.refinement) <= 500,
    }
    return [GuardrailResult(guardrail_id=key, passed=value, action="allow" if value else "block", reason=None if value else GUARDRAIL_REGISTRY[key].description, input_material_id=material_id) for key, value in checks.items()]


def transform_candidate_limit(material: MaterialEnvelope, handler: MaterialHandler) -> tuple[MaterialEnvelope, GuardrailResult]:
    places = material.payload["places"]
    if len(places) <= SETTINGS.max_candidate_places:
        return material, GuardrailResult(guardrail_id="candidate_limit", passed=True, action="allow", reason=None, input_material_id=material.material_id, output_material_id=material.material_id)
    transformed = handler.create(run_id=material.run_id, material_type="CandidatePlacesMaterial", stage="candidate_guardrails", payload={"places": places[: SETTINGS.max_candidate_places]}, source=material.source)
    return transformed, GuardrailResult(guardrail_id="candidate_limit", passed=False, action="transform", reason=f"Retained top {SETTINGS.max_candidate_places} candidates.", input_material_id=material.material_id, output_material_id=transformed.material_id)


def finite_limits() -> dict[str, int]:
    return {"repair_attempts": SETTINGS.max_repair_attempts, "refinement_turns": SETTINGS.max_refinement_turns, "session_seconds": SETTINGS.max_session_seconds, "tokens": SETTINGS.max_tokens}
