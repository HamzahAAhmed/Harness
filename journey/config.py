from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    max_repair_attempts: int = int(os.getenv("MAX_REPAIR_ATTEMPTS", "1"))
    max_refinement_turns: int = int(os.getenv("MAX_REFINEMENT_TURNS", "3"))
    max_candidate_places: int = int(os.getenv("MAX_CANDIDATE_PLACES", "12"))
    max_trip_days: int = int(os.getenv("MAX_TRIP_DAYS", "3"))
    max_material_bytes: int = 100_000
    max_session_seconds: int = 120
    max_tokens: int = 8_000
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


SETTINGS = Settings()
SUPPORTED_CATEGORIES = ("Food", "History", "Art", "Nature", "Shopping", "Entertainment")
SUPPORTED_PACES = ("relaxed", "balanced", "busy")
CATEGORY_TERMS = {
    "History": ("history", "historic", "museum", "museums", "meseum", "meseums"),
    "Art": ("art", "gallery", "galleries", "mural", "murals"),
    "Food": ("food", "restaurant", "restaurants", "taco", "tacos", "coffee", "cafe"),
    "Nature": ("nature", "park", "parks", "outdoor", "greenway", "water"),
    "Shopping": ("shop", "shops", "shopping", "market", "markets"),
    "Entertainment": ("music", "comedy", "entertainment", "show", "shows"),
}
ACTIVITY_TERMS = {
    "swimming": ("swim", "swimming", "pool", "splash"),
    "hiking": ("hike", "hiking", "trail", "trails"),
    "kayaking": ("kayak", "kayaking", "paddle", "paddling"),
    "cycling": ("bike", "biking", "bicycle", "cycling"),
    "picnic": ("picnic", "picnicking"),
    "coffee": ("coffee", "cafe", "espresso"),
    "brunch": ("brunch", "breakfast"),
    "live_music": ("live music", "concert", "band"),
    "comedy": ("comedy", "stand-up", "standup"),
    "dancing": ("dance", "dancing"),
    "family_friendly": ("family", "kids", "children"),
    "scenic_view": ("view", "views", "scenic", "sunset"),
    "museum": ("museum", "museums", "meseum", "meseums"),
}


def category_from_text(text: str | None) -> str | None:
    normalized = (text or "").casefold()
    return next(
        (
            category
            for category, terms in CATEGORY_TERMS.items()
            if any(term in normalized for term in terms)
        ),
        None,
    )


def activity_from_text(text: str | None) -> str | None:
    normalized = (text or "").casefold()
    return next(
        (
            activity
            for activity, terms in ACTIVITY_TERMS.items()
            if any(term in normalized for term in terms)
        ),
        None,
    )
