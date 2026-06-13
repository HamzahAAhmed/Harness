# Journey Harness

## Purpose

Journey is a reusable harness that governs an itinerary-planning worker. The worker proposes an itinerary from supplied place IDs; the harness controls every input, material, tool, validation, retry, escalation, persistence, replay, hydration, and map-rendering decision around it.

```text
Trip Input
    |
Material Handler
    |
Guardrails
    |
Demo Tools
    |
Candidate Checkpoint
    |
Worker
    |
Output Checkpoints
    |
    +-- pass --> Hydrated Validated Itinerary --> MapLibre
    |
    +-- fail --> Alarm --> Feedback --> One Repair
                                    |
                                    +-- fail --> Human Escalation
```

## Worker Responsibility

The worker creates or refines itinerary days using only supplied place IDs, dates, start times, durations, concise reasons, day themes, and a short summary. Both workers implement `JourneyWorker.execute(WorkerRequest) -> WorkerResponse`.

The worker does not load fixtures, call tools, access Dash stores, create alarms, select checkpoints, enforce retries, persist records, hydrate place data, or create GeoJSON.

## Four Pillars

### Material Handling

`journey/harness/materials.py` creates versioned `MaterialEnvelope` objects with IDs, stages, schema versions, UTC timestamps, normalized payloads, SHA-256 hashes, size limits, and source attribution. The flow is trip request, validated input, candidates, ranked candidates, worker request, draft, optional feedback, validated itinerary, and accepted trip. Fixture places also carry activity capabilities such as swimming, hiking, kayaking, brunch, live music, and family-friendly use.

### Guardrails

`journey/harness/guardrails.py` contains declared input, material, worker, and security controls. Results identify the declaration, pass state, action, reason, and input/output material IDs. Candidate count is a demonstrated transform: oversized material becomes a new capped material, and downstream stages receive the transformed envelope.

### Checkpoints

`journey/harness/checkpoints.py` declares exactly five checkpoints:

1. Input integrity: supported destination, complete fields, valid dates/duration, travelers, budget, interests, and pace.
2. Candidate quality: non-empty candidates, unique IDs, valid fixture source/demo flags, coordinates, and count.
3. Itinerary schema: typed draft, matching day count, and required activity fields.
4. Grounding: every place ID belongs to ranked material; canonical fields come from harness hydration.
5. Schedule: dates, parseable chronological non-overlapping times, positive durations, pace counts, and justified repeats.

Checkpoints return explicit pass/fail results and never edit worker output.

### Alarms

`journey/harness/alarms.py` creates typed alarms containing ID, run ID, type, severity, stage, context, recommended action, human flag, and timestamp. Supported types are `INPUT_GUARDRAIL_BLOCKED`, `MATERIAL_VALIDATION_FAILED`, `CHECKPOINT_FAILED`, `GROUNDING_VIOLATION`, `REPAIR_REQUESTED`, `REPAIR_EXHAUSTED`, `WORKER_EXECUTION_FAILED`, `LIMIT_REACHED`, `HUMAN_REVIEW_REQUIRED`, and `BROWSER_PERSISTENCE_FAILED`.

## Feedback and Repair

A repairable failure produces `CheckpointFeedback` with the failed criteria, validation errors, valid place IDs, required correction, and repair number. The harness packages it as material and invokes the same worker one more time. The deterministic fail-once scenario proves that the worker changes its second response only after receiving this feedback. A second failure creates `REPAIR_EXHAUSTED` and `HUMAN_REVIEW_REQUIRED` and stops.

## Human Escalation

The harness stops for repeated repair failure, missing candidates, unsupported actions, configured limits, or unsatisfied constraints. It returns a reason, question, options, blocking checkpoint, and related alarm. The UI displays that question rather than guessing.

## Persistence and Replay

Dash uses session stores for the active run, itinerary, and map, plus local stores for accepted trips and run history. Browser data is revalidated into a typed `RunRecord` before refinement, replay, or acceptance.

Replay creates a new run ID, links `parent_run_id`, records the selected checkpoint, reuses persisted ranked material, and executes downstream worker/checkpoint stages normally. It does not reload candidate fixtures when ranked material exists.

## Observability

`journey/harness/observability.py` emits JSON trace events to stdout for run, worker, repair, replay, and completion activity. Diagnostics separate materials, guardrails, checkpoints, alarms, worker activity, replay, and trace metrics. API keys, full prompts, and entire browser payloads are not logged.

## Demo Data

All destination and place data is bundled in `data/demo`. Ratings, costs, and review counts are simulated and visibly labeled. Journey does not use live place or travel providers.

## Swapping Workers

Choose the worker in the Dash selector or inject either class into `JourneyHarness.run`. The controller depends only on `JourneyWorker`; no harness modification is needed. OpenAI requires a server-side `OPENAI_API_KEY`. Deterministic mode starts and runs without one.

## Five-Minute Demo

1. Show the four pillar modules and common protocol.
2. Generate a normal Austin request; show passing controls, hydrated cards, and validated map.
3. Select fail-once; show grounding failure, alarm, feedback valid IDs, changed second response, and pass.
4. Select fail-twice; show one bounded repair and human escalation.
5. Replay from grounding; show new and parent run IDs and reused ranked material.
6. Switch the worker selector to demonstrate portability.

## Known Limitations

- One Austin fixture destination and twenty-four places, with at most twelve supplied to a worker per attempt.
- Deterministic natural-language matching is intentionally bounded to declared activity terms; unmatched refinements preserve the plan and display an explanation.
- One-to-three-day itineraries with approximate pace counts.
- One repair and three refinements.
- Browser-local persistence only; clearing browser storage removes history.
- OpenAI mode requires network access and a server-side key; deterministic mode is the reliable demo fallback.
- The MapLibre library is vendored and uses a local no-tile style; place data remains local and validated.
