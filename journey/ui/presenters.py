from __future__ import annotations

from dash import html

from journey.models import HarnessRunResult, ValidatedItinerary


def itinerary_view(itinerary: ValidatedItinerary | None):
    if not itinerary:
        return html.Div([html.H3("No itinerary yet"), html.P("Submit a supported Austin trip to run the harness.")], className="empty-state")
    return html.Div([html.P(itinerary.short_trip_summary, className="summary"), *[html.Section([html.Div([html.P(day.date.strftime("%A, %B %d"), className="eyebrow"), html.H3(day.day_theme)]), html.Div([html.Article([html.Span(item.start_time, className="time"), html.Div([html.H4(item.name), html.P(f"{item.category} · {item.duration_minutes} min · simulated ${item.estimated_cost:.0f}"), html.P(f"Simulated rating {item.demo_rating:.1f}/5 from {item.demo_review_count:,} demo reviews", className="fixture-meta"), html.P("Activities: " + ", ".join(capability.replace("_", " ") for capability in item.capabilities), className="capabilities") if item.capabilities else None, html.P(item.short_description), html.P(item.reason, className="reason")])], className="activity", style={"--delay": f"{index * 70}ms"}) for index, item in enumerate(day.activities)], className="activity-list")], className="itinerary-day") for day in itinerary.days]])


def escalation_view(result: HarnessRunResult):
    if not result.escalation:
        return None
    escalation = result.escalation
    return html.Section([html.P("Human review required", className="eyebrow danger"), html.H3(escalation.question), html.P(escalation.reason), html.Ul([html.Li(option) for option in escalation.available_options])], className="escalation")


def diagnostics_view(result: HarnessRunResult):
    record = result.run_record
    groups = [
        ("Materials", [{"type": item.material_type, "stage": item.stage, "id": item.material_id, "source": item.source} for item in record.materials]),
        ("Guardrails", [item.model_dump(mode="json") for item in record.guardrail_results]),
        ("Checkpoints", [item.model_dump(mode="json") for item in record.checkpoint_results]),
        ("Alarms", [item.model_dump(mode="json") for item in record.alarms]),
        ("Worker activity", {"worker": record.worker_name, "repairs": record.repair_attempts, "refinements": record.refinement_turns}),
        ("Replay", {"run_id": record.run_id, "parent_run_id": record.parent_run_id, "checkpoint": record.replay_checkpoint_id}),
        ("Trace metrics", [item.model_dump(mode="json") for item in record.trace_events]),
    ]
    return html.Div([html.Details([html.Summary(title), html.Pre(__import__("json").dumps(payload, indent=2))], open=title in {"Checkpoints", "Alarms"}) for title, payload in groups], className="diagnostic-groups")
