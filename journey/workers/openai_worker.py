from __future__ import annotations

import os
from time import perf_counter
from typing import Any

from openai import OpenAI

from journey.config import SETTINGS
from journey.models import WorkerItineraryDraft, WorkerRequest, WorkerResponse


class OpenAIJourneyWorker:
    worker_name = "OpenAI Journey Worker"

    def __init__(self, client: Any | None = None, model: str | None = None) -> None:
        self._client = client
        self.model = model or SETTINGS.openai_model

    def execute(self, request: WorkerRequest) -> WorkerResponse:
        client = self._client
        if client is None:
            if not os.getenv("OPENAI_API_KEY"):
                return WorkerResponse(worker_name=self.worker_name, error="OPENAI_API_KEY is not configured.")
            client = OpenAI()
        place_context = [
            {
                "place_id": item.place.place_id,
                "category": item.place.category,
                "short_description": item.place.short_description,
                "score": item.total_score,
            }
            for item in request.ranked_places
        ]
        payload = {
            "trip": request.trip.model_dump(mode="json"),
            "ranked_places": place_context,
            "existing_itinerary": request.existing_itinerary.model_dump(mode="json") if request.existing_itinerary else None,
            "checkpoint_feedback": request.checkpoint_feedback.model_dump(mode="json") if request.checkpoint_feedback else None,
        }
        started = perf_counter()
        try:
            response = client.responses.parse(
                model=self.model,
                instructions=(
                    "Create or refine the itinerary using only supplied place_id values. "
                    "Return dates, place IDs, start times, durations, concise reasons, day themes, "
                    "and a short summary. Never invent names, coordinates, ratings, costs, review "
                    "counts, sources, live availability, or opening hours. Apply checkpoint feedback."
                ),
                input=str(payload),
                text_format=WorkerItineraryDraft,
            )
            draft = response.output_parsed
            usage = getattr(response, "usage", None)
            tokens = getattr(usage, "total_tokens", None) if usage else None
            return WorkerResponse(worker_name=self.worker_name, draft=draft, token_usage=tokens, latency_ms=(perf_counter() - started) * 1000)
        except Exception as exc:
            return WorkerResponse(worker_name=self.worker_name, error=str(exc), latency_ms=(perf_counter() - started) * 1000)
