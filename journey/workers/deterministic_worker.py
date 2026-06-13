from __future__ import annotations

from datetime import datetime, timedelta

from journey.config import activity_from_text, category_from_text
from journey.models import (
    ItineraryDayDraft,
    ItineraryItemDraft,
    WorkerItineraryDraft,
    WorkerRequest,
    WorkerResponse,
)


class DeterministicJourneyWorker:
    worker_name = "Deterministic Journey Worker"

    def execute(self, request: WorkerRequest) -> WorkerResponse:
        refinement = (request.trip.refinement or "").casefold()
        requested_category = category_from_text(refinement)
        requested_activity = activity_from_text(refinement)
        ranked_places = sorted(
            request.ranked_places,
            key=lambda item: (
                requested_activity not in item.place.capabilities
                if requested_activity
                else False,
                item.place.category != requested_category if requested_category else False,
                -item.total_score,
                item.place.place_id,
            ),
        )
        invalid = request.scenario == "fail_twice" or (request.scenario == "fail_once_then_repair" and request.checkpoint_feedback is None)
        pace_range = {"relaxed": (2, 3), "balanced": (3, 4), "busy": (4, 5)}
        minimum, maximum = pace_range[request.trip.preferences.pace]
        wants_more = any(term in refinement for term in ("add", "more", "include", "another"))
        wants_less = any(term in refinement for term in ("remove", "delete", "drop", "less", "fewer"))
        generic_addition = any(
            phrase in refinement
            for phrase in ("another stop", "add a stop", "add one stop", "more stops")
        )
        if (
            request.existing_itinerary
            and wants_more
            and not requested_category
            and not requested_activity
            and not generic_addition
        ):
            return WorkerResponse(
                worker_name=self.worker_name,
                draft=request.existing_itinerary,
                user_message=(
                    f"I couldn't find a local demo place matching '{request.trip.refinement}'. "
                    "Your itinerary was left unchanged."
                ),
            )
        if request.existing_itinerary and (wants_more or wants_less):
            draft = self._edit_existing(
                request,
                ranked_places,
                requested_category,
                requested_activity,
                wants_more=wants_more,
                wants_less=wants_less,
                maximum=maximum,
            )
            action = "removed a stop" if wants_less else "added a stop"
            qualifier = requested_activity or requested_category
            message = f"Refinement applied: {action}"
            if qualifier:
                message += f" matching {qualifier.replace('_', ' ')}"
            return WorkerResponse(worker_name=self.worker_name, draft=draft, user_message=message + ".")
        per_day = maximum if wants_more else minimum
        days = []
        cursor = 0
        used_place_ids: set[str] = set()
        total_days = (request.trip.end_date - request.trip.start_date).days + 1
        for day_offset in range(total_days):
            activities = []
            start = datetime(2000, 1, 1, 9)
            for activity_index in range(per_day):
                ranked = ranked_places[cursor % len(ranked_places)]
                place_id = ranked.place.place_id
                if invalid and day_offset == 0 and activity_index == 0:
                    place_id = "unknown-999" if request.attempt == 1 else "unknown-998"
                if requested_category and ranked.place.category == requested_category:
                    reason = (
                        f"Added for your {requested_category.lower()} refinement: "
                        f"{ranked.place.short_description}"
                    )
                else:
                    reason = (
                        f"A strong {ranked.place.category.lower()} match: "
                        f"{ranked.place.short_description}"
                    )
                if place_id in used_place_ids:
                    reason = f"Repeat visit requested to fit the selected pace. {reason}"
                activities.append(ItineraryItemDraft(place_id=place_id, start_time=start.strftime("%H:%M"), duration_minutes=90, reason=reason))
                used_place_ids.add(place_id)
                start += timedelta(hours=2)
                cursor += 1
            theme = f"Austin {requested_category.lower()} focus" if requested_category else f"Austin day {day_offset + 1}"
            days.append(ItineraryDayDraft(date=request.trip.start_date + timedelta(days=day_offset), day_theme=theme, activities=activities))
        summary = "A fixture-grounded Austin itinerary balanced around your selected interests."
        if requested_category:
            summary = f"Refined to prioritize {requested_category.lower()} places from the supplied local fixtures."
        return WorkerResponse(worker_name=self.worker_name, draft=WorkerItineraryDraft(days=days, short_trip_summary=summary))

    def _edit_existing(
        self,
        request: WorkerRequest,
        ranked_places,
        requested_category: str | None,
        requested_activity: str | None,
        *,
        wants_more: bool,
        wants_less: bool,
        maximum: int,
    ) -> WorkerItineraryDraft:
        existing = request.existing_itinerary.model_copy(deep=True)
        place_by_id = {item.place.place_id: item.place for item in ranked_places}
        used_ids = {
            activity.place_id
            for day in existing.days
            for activity in day.activities
        }
        for day in existing.days:
            if wants_less and day.activities:
                remove_index = next(
                    (
                        index
                        for index, activity in enumerate(day.activities)
                        if requested_category
                        and place_by_id.get(activity.place_id)
                        and place_by_id[activity.place_id].category == requested_category
                    ),
                    len(day.activities) - 1,
                )
                day.activities.pop(remove_index)
            if wants_more and len(day.activities) < maximum:
                addition = next(
                    (
                        item
                        for item in ranked_places
                        if item.place.place_id not in used_ids
                        and (
                            not requested_activity
                            or requested_activity in item.place.capabilities
                        )
                        and (not requested_category or item.place.category == requested_category)
                    ),
                    None,
                )
                if addition is None:
                    addition = next(
                        (item for item in ranked_places if item.place.place_id not in used_ids),
                        None,
                    )
                if addition:
                    last_start = (
                        datetime.strptime(day.activities[-1].start_time, "%H:%M")
                        if day.activities
                        else datetime(2000, 1, 1, 9)
                    )
                    start = last_start + (timedelta(hours=2) if day.activities else timedelta())
                    category = addition.place.category.lower()
                    match = requested_activity.replace("_", " ") if requested_activity else category
                    reason = f"Added by refinement for {match}: {addition.place.short_description}"
                    day.activities.append(
                        ItineraryItemDraft(
                            place_id=addition.place.place_id,
                            start_time=start.strftime("%H:%M"),
                            duration_minutes=90,
                            reason=reason,
                        )
                    )
                    used_ids.add(addition.place.place_id)
            action = "removed a stop from" if wants_less else "added a stop to"
            day.day_theme = f"Refined Austin day: {action} the plan"
        action_summary = "removed from" if wants_less else "added to"
        existing.short_trip_summary = (
            f"Refined the existing itinerary by keeping its structure and {action_summary} each day."
        )
        return existing
