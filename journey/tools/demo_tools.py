from __future__ import annotations

import json
import math
from pathlib import Path

from journey.models import (
    Destination,
    Place,
    RankedPlace,
    SaveTripPayload,
    TripRequest,
    ValidatedItinerary,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "demo"


def locate_destination(requested: str) -> Destination:
    destination = Destination.model_validate_json((DATA_DIR / "destination.json").read_text())
    if requested.casefold() != destination.name.casefold():
        raise ValueError(f"Only {destination.name} is supported in this demonstration.")
    return destination


def find_nearby_places(interests: list[str]) -> list[Place]:
    payload = json.loads((DATA_DIR / "places.json").read_text())
    return [Place.model_validate(item) for item in payload if item["category"] in interests]


def rank_places(places: list[Place], destination: Destination, request: TripRequest) -> list[RankedPlace]:
    ranked = []
    per_activity_budget = request.budget / max(1, ((request.end_date - request.start_date).days + 1) * 3)
    for place in places:
        distance = math.hypot(place.latitude - destination.latitude, place.longitude - destination.longitude)
        components = {"interest": 4.0, "budget": max(0.0, 2.0 - abs(place.estimated_cost - per_activity_budget) / 50), "distance": max(0.0, 2.0 - distance * 20), "rating_confidence": place.demo_rating * min(1.0, place.demo_review_count / 1000) / 2.5, "diversity": 1.0}
        score = round(sum(components.values()), 4)
        ranked.append(RankedPlace(place=place, total_score=score, score_components=components, explanation=f"Fixture score {score:.2f}: interest, budget, proximity, simulated rating confidence, and diversity."))
    return sorted(ranked, key=lambda item: (-item.total_score, item.place.place_id))


def save_trip(run_id: str, itinerary: ValidatedItinerary) -> SaveTripPayload:
    return SaveTripPayload(run_id=run_id, itinerary=itinerary, demo_data_disclaimer="Place data is local demonstration data; ratings and costs are simulated.")
