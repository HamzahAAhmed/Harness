from datetime import date, timedelta

from dash import dcc, html

from journey.config import SUPPORTED_CATEGORIES


def build_layout():
    start = date.today() + timedelta(days=14)
    return html.Main([
        dcc.Store(id="active-run-store", storage_type="session"),
        dcc.Store(id="active-itinerary-store", storage_type="session"),
        dcc.Store(id="accepted-trip-store", storage_type="local"),
        dcc.Store(id="run-history-store", storage_type="local", data=[]),
        dcc.Store(id="map-data-store", storage_type="session"),
        html.Header([html.Div([html.P("HARNESS-FIRST TRAVEL PLANNING", className="kicker"), html.H1("Journey"), html.P("A bounded itinerary worker, governed in plain sight.", className="lede")]), html.Div([html.Span("Local fixture data"), html.Span("Simulated ratings + costs"), html.Span(id="run-status", children="Ready")], className="status-rail")], className="masthead"),
        html.Div([
            html.Aside([html.H2("Shape the trip"), html.Label(["Destination", dcc.Dropdown(id="destination", options=["Austin, Texas"], value="Austin, Texas", clearable=False)]), html.Div([html.Label(["Start", dcc.DatePickerSingle(id="start-date", date=start)]), html.Label(["End", dcc.DatePickerSingle(id="end-date", date=start)])], className="field-pair"), html.Div([html.Label(["Travelers", dcc.Input(id="travelers", type="number", min=1, max=6, value=2)]), html.Label(["Budget", dcc.Input(id="budget", type="number", min=1, value=450, placeholder="USD")])], className="field-pair"), html.Label(["Interests", dcc.Checklist(id="interests", options=list(SUPPORTED_CATEGORIES), value=list(SUPPORTED_CATEGORIES), className="check-grid")]), html.Label(["Pace", dcc.RadioItems(id="pace", options=[{"label": item.title(), "value": item} for item in ("relaxed", "balanced", "busy")], value="balanced", inline=True)]), html.Label(["Worker", dcc.Dropdown(id="worker-selector", options=[{"label": "Deterministic Journey Worker", "value": "deterministic"}, {"label": "OpenAI Journey Worker", "value": "openai"}], value="deterministic", clearable=False)]), html.Button("Generate itinerary", id="generate", className="primary"), html.P(id="form-error", className="error")], className="control-panel"),
            html.Section([html.Div([html.Div([html.P("VALIDATED PLAN", className="eyebrow"), html.H2("Your Austin rhythm")]), html.Div(id="worker-label", children="Worker: Deterministic Journey Worker", className="worker-chip")], className="section-heading"), html.Div([html.Div(id="itinerary-output", className="itinerary"), html.Div([html.P("Numbered stops follow itinerary order. Select a marker for full fixture details.", className="map-hint"), html.Div(id="journey-map", className="map"), html.Div(id="map-update-sentinel")], className="map-shell")], className="workspace-grid"), html.Div(id="escalation-output"), html.Div(id="refinement-feedback", className="refinement-feedback"), html.Div([html.Label(["Refinement request", dcc.Input(id="refinement", placeholder="Try: Add swimming, hiking, kayaking, brunch, music, or a museum", maxLength=500)], className="refinement-input"), html.Button("Refine", id="refine"), html.Button("Accept & save", id="accept"), html.Button("Start over", id="start-over", className="quiet")], className="refinement-bar"), html.Div(id="save-message")], className="workspace")
        ], className="app-grid"),
        html.Section([html.Details([html.Summary("Demo controls"), html.Div([html.Label(["Deterministic scenario", dcc.Dropdown(id="scenario", options=[{"label": "Normal", "value": "normal"}, {"label": "Fail once, then repair", "value": "fail_once_then_repair"}, {"label": "Fail twice and escalate", "value": "fail_twice"}], value="normal", clearable=False)]), html.Label(["Replay checkpoint", dcc.Dropdown(id="replay-checkpoint", options=["itinerary_schema", "grounding", "schedule"], value="grounding", clearable=False)]), html.Button("Replay", id="replay")], className="demo-controls")]), html.Details([html.Summary("Harness diagnostics"), html.Div(id="diagnostics-output")])], className="lower-deck"),
        html.Footer("Place data: local demonstration fixtures. Ratings, review counts, and costs are simulated.")
    ])
