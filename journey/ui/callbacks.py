from __future__ import annotations

from datetime import date

from dash import Input, Output, State, ctx, no_update
from pydantic import ValidationError

from journey.harness.controller import JourneyHarness
from journey.harness.persistence import restore_run, serialize_run
from journey.models import TripPreferences, TripRequest
from journey.ui.presenters import diagnostics_view, escalation_view, itinerary_view
from journey.workers.deterministic_worker import DeterministicJourneyWorker
from journey.workers.openai_worker import OpenAIJourneyWorker


def _worker(name: str):
    return OpenAIJourneyWorker() if name == "openai" else DeterministicJourneyWorker()


def register_callbacks(app):
    harness = JourneyHarness()

    @app.callback(Output("active-run-store", "data"), Output("active-itinerary-store", "data"), Output("map-data-store", "data"), Output("run-history-store", "data"), Output("form-error", "children"), Input("generate", "n_clicks"), Input("refine", "n_clicks"), Input("replay", "n_clicks"), State("destination", "value"), State("start-date", "date"), State("end-date", "date"), State("travelers", "value"), State("budget", "value"), State("interests", "value"), State("pace", "value"), State("worker-selector", "value"), State("scenario", "value"), State("refinement", "value"), State("replay-checkpoint", "value"), State("active-run-store", "data"), State("run-history-store", "data"), prevent_initial_call=True)
    def execute(generate_clicks, refine_clicks, replay_clicks, destination, start_date, end_date, travelers, budget, interests, pace, worker_name, scenario, refinement, replay_checkpoint, active_run, history):
        del generate_clicks, refine_clicks, replay_clicks
        try:
            worker = _worker(worker_name)
            if ctx.triggered_id == "generate":
                request = TripRequest(destination=destination, start_date=date.fromisoformat(start_date), end_date=date.fromisoformat(end_date), travelers=travelers, budget=budget, preferences=TripPreferences(interests=interests, pace=pace))
                result = harness.run(request, worker, scenario)
            else:
                record = restore_run(active_run)
                result = harness.refine(record, refinement or "", worker) if ctx.triggered_id == "refine" else harness.replay(record, replay_checkpoint, worker)
        except (ValidationError, ValueError, TypeError) as exc:
            return no_update, no_update, no_update, no_update, str(exc)
        record_data = serialize_run(result.run_record)
        updated_history = [*(history or []), record_data][-10:]
        itinerary_data = result.itinerary.model_dump(mode="json") if result.itinerary else None
        return record_data, itinerary_data, result.map_geojson, updated_history, ""

    @app.callback(Output("itinerary-output", "children"), Output("escalation-output", "children"), Output("diagnostics-output", "children"), Output("run-status", "children"), Output("worker-label", "children"), Output("refinement-feedback", "children"), Input("active-run-store", "data"), Input("active-itinerary-store", "data"))
    def render(run_data, itinerary_data):
        if not run_data:
            return itinerary_view(None), None, None, "Ready", "Worker: not selected", None
        from journey.models import HarnessRunResult, HumanEscalation, ValidatedItinerary
        record = restore_run(run_data)
        itinerary = ValidatedItinerary.model_validate(itinerary_data) if itinerary_data else None
        escalation = None
        if record.status == "needs_human":
            alarm = next(alarm for alarm in reversed(record.alarms) if alarm.requires_human)
            escalation = HumanEscalation(
                reason=str(alarm.context.get("reason", "Harness execution stopped.")),
                question="How should Journey continue?",
                available_options=[
                    "Change the trip fields on the left, then click Generate itinerary.",
                    "Open Demo controls, select Normal, then click Generate itinerary.",
                    "Click Start over to clear the current run and begin again.",
                ],
                blocking_checkpoint=record.current_stage,
                related_alarm_id=alarm.alarm_id,
            )
        result = HarnessRunResult(run_record=record, itinerary=itinerary, escalation=escalation)
        return itinerary_view(itinerary), escalation_view(result), diagnostics_view(result), record.status.replace("_", " ").title(), f"Worker: {record.worker_name}", record.user_message

    @app.callback(Output("accepted-trip-store", "data"), Output("active-run-store", "data", allow_duplicate=True), Output("save-message", "children"), Input("accept", "n_clicks"), State("active-run-store", "data"), State("active-itinerary-store", "data"), prevent_initial_call=True)
    def accept_trip(clicks, run_data, itinerary_data):
        del clicks
        if not run_data or not itinerary_data:
            return no_update, no_update, "Generate and validate an itinerary before saving."
        from journey.models import ValidatedItinerary
        record = restore_run(run_data)
        record, payload = harness.accept(record, ValidatedItinerary.model_validate(itinerary_data))
        return payload.model_dump(mode="json"), serialize_run(record), "Saved in this browser."

    @app.callback(Output("active-run-store", "clear_data"), Output("active-itinerary-store", "clear_data"), Output("map-data-store", "clear_data"), Input("start-over", "n_clicks"), prevent_initial_call=True)
    def start_over(clicks):
        del clicks
        return True, True, True

    app.clientside_callback("function(data){if(window.JourneyMap){window.JourneyMap.update(data);} return data ? data.features.length : 0;}", Output("map-update-sentinel", "children"), Input("map-data-store", "data"))
