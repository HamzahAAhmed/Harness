# Journey Project Instructions

## 1. Mission

Journey is a harness-first 24-hour build challenge project.

The application domain is personalized trip-itinerary planning, but the primary deliverable is the reusable harness that governs the planning worker.

The harness must make these four pillars visibly and demonstrably separate from the worker:

1. Guardrails
2. Checkpoints
3. Material handling
4. Alarms

The Journey worker creates and refines itineraries. The harness controls what the worker receives, what actions are permitted, whether its output passes, when it may retry, and when execution must stop.

The requirements in:

* `docs/24-hour Build Challenge.pdf`
* `docs/Journey_Architecture_Defense.pdf`

are the project sources of truth.

When they conflict, the challenge requirements take priority.

## 2. Final demo scope

Journey must use deterministic local demo data only.

Do not implement or mention:

* Nominatim
* Overpass
* Google Places
* Live travel APIs
* External place providers
* Provider switching
* Network-based place retrieval

The only required external service is OpenAI for the OpenAI worker.

The application must also work without an OpenAI key through a deterministic worker.

Use one versioned demo destination dataset containing approximately 10–15 places. The destination must be stored in fixture data rather than hard-coded throughout the application.

The interface may support only the destination represented by the fixture data.

The application should support trips lasting one to three days.

## 3. Required technology

Use:

* Python 3.11 or newer
* Dash
* Flask through Dash
* Pydantic v2
* Official OpenAI Python SDK
* MapLibre GL JS
* Dash `dcc.Store`
* Pytest
* Ruff

Do not use:

* AWS
* Docker unless deployment absolutely requires it
* Kubernetes
* Redis
* Celery
* Authentication
* Cloud databases
* SQL databases
* Microservices
* Background workers
* Payment systems
* Direct booking
* Flight search
* Hotel search
* Review scraping
* Multiple AI agents
* Agent-to-agent delegation

Use one OpenAI planning worker and one deterministic worker.

## 4. Architectural principle

The worker performs the itinerary-planning task.

The harness owns:

* Input processing
* Material preparation
* Guardrail enforcement
* Tool execution
* Checkpoint evaluation
* Repair feedback
* Retry limits
* Human escalation
* Alarm creation
* Persistence
* Replay
* Observability

Do not place harness logic inside the OpenAI prompt.

Do not allow the worker to decide whether its own output is valid.

Do not let Dash callbacks contain business rules that belong to the harness.

## 5. Simplified project structure

Prefer this structure:

```text
app.py
AGENTS.md
HARNESS.md
IMPLEMENTATION_PLAN.md
README.md
requirements.txt
.env.example
.gitignore

journey/
  __init__.py
  config.py
  models.py

  harness/
    __init__.py
    controller.py
    materials.py
    guardrails.py
    checkpoints.py
    alarms.py
    persistence.py
    observability.py

  workers/
    __init__.py
    protocol.py
    openai_worker.py
    deterministic_worker.py

  tools/
    __init__.py
    demo_tools.py

  ui/
    __init__.py
    layout.py
    callbacks.py
    presenters.py

assets/
  journey-map.js
  journey.css

data/
  demo/
    destination.json
    places.json

tests/
  test_materials.py
  test_guardrails.py
  test_checkpoints.py
  test_alarms.py
  test_workers.py
  test_harness.py
  test_replay.py
```

Keep one module per required harness pillar.

Do not create extra abstraction layers unless they remove clear duplication.

## 6. Demo fixture data

Create one destination fixture:

```json
{
  "fixture_version": "1.0",
  "destination_id": "demo-destination-1",
  "name": "Austin, Texas",
  "latitude": 30.2672,
  "longitude": -97.7431,
  "source": "demo_fixture",
  "is_demo_data": true
}
```

Create approximately 10–15 place fixtures.

Each place must include:

```text
place_id
name
category
latitude
longitude
estimated_cost
demo_rating
demo_review_count
short_description
source
is_demo_data
fixture_version
```

Supported categories should remain limited to:

* Food
* History
* Art
* Nature
* Shopping
* Entertainment

All ratings, costs, and review counts must be clearly identified as simulated demonstration data.

Do not include long written reviews.

Do not imply that demonstration values are live, current, or retrieved from real providers.

## 7. Core Pydantic models

Define all shared models in `journey/models.py`.

Required models include:

* `TripRequest`
* `TripPreferences`
* `Place`
* `RankedPlace`
* `ItineraryItemDraft`
* `ItineraryDayDraft`
* `WorkerItineraryDraft`
* `ValidatedItineraryItem`
* `ValidatedItineraryDay`
* `ValidatedItinerary`
* `WorkerRequest`
* `WorkerResponse`
* `CheckpointFeedback`
* `HumanEscalation`
* `MaterialEnvelope`
* `GuardrailDeclaration`
* `GuardrailResult`
* `CheckpointDeclaration`
* `CheckpointResult`
* `HarnessAlarm`
* `TraceEvent`
* `RunRecord`
* `HarnessRunResult`
* `SaveTripPayload`

Do not duplicate equivalent models across modules.

## 8. Material handling pillar

Material handling must be implemented in:

```text
journey/harness/materials.py
```

Define:

```python
class MaterialEnvelope(BaseModel):
    run_id: str
    material_id: str
    material_type: str
    stage: str
    schema_version: str
    created_at: datetime
    payload_hash: str
    payload: dict
    source: str
```

Use these material types:

1. `TripRequestMaterial`
2. `ValidatedTripMaterial`
3. `CandidatePlacesMaterial`
4. `RankedPlacesMaterial`
5. `WorkerRequestMaterial`
6. `DraftItineraryMaterial`
7. `CheckpointFeedbackMaterial`
8. `ValidatedItineraryMaterial`
9. `AcceptedTripMaterial`

The material handler must:

* Validate payloads
* Assign material IDs
* Record schema versions
* Hash payloads
* Normalize text
* Enforce payload-size limits
* Preserve source attribution
* Serialize materials
* Restore materials during replay
* Pass materials between harness stages

The worker must receive only a prepared `WorkerRequestMaterial`.

The worker must never:

* Read fixture files
* Access Dash stores
* Modify run records
* Decide which checkpoint runs
* Decide whether an alarm is raised

## 9. Guardrails pillar

Guardrails must be implemented in:

```text
journey/harness/guardrails.py
```

Guardrails must be declared in a registry.

Define:

```python
class GuardrailDeclaration(BaseModel):
    guardrail_id: str
    name: str
    stage: str
    description: str
    action_on_failure: Literal[
        "block",
        "transform",
        "retry",
        "escalate"
    ]
    severity: Literal[
        "info",
        "warning",
        "error",
        "critical"
    ]
```

Each execution returns:

```python
class GuardrailResult(BaseModel):
    guardrail_id: str
    passed: bool
    action: str
    reason: str | None
    input_material_id: str
    output_material_id: str | None
```

Required guardrails:

### Input guardrails

* Destination is present
* Destination matches the supported demo destination
* Start date is not after end date
* Trip duration is between one and three days
* Traveler count is between one and six
* Budget is positive
* Interests come from the supported category list
* Travel pace is `relaxed`, `balanced`, or `busy`
* Refinement text is no longer than 500 characters

### Material guardrails

* Candidate count does not exceed 12
* Worker context contains only required fields
* External or fixture text is length-limited
* Material payload size remains within configuration limits

### Worker guardrails

* Only the selected registered worker may execute
* Maximum worker attempts is two:

  * Initial attempt
  * One repair attempt
* Maximum refinement turns is three
* Maximum session duration is configurable
* Maximum token usage is configurable when token data is available
* OpenAI key remains server-side
* Unsupported booking, payment, file, URL, and code-execution requests are blocked

At least one guardrail must transform material.

Required transformation example:

* If more than 12 candidate places exist, retain only the top 12 and create a new transformed material envelope.

The worker must receive the transformed material, not the original oversized material.

Guardrail results must appear in diagnostics.

## 10. Checkpoints pillar

Checkpoints must be implemented in:

```text
journey/harness/checkpoints.py
```

Checkpoints must be declared with explicit pass/fail criteria.

Define:

```python
class CheckpointDeclaration(BaseModel):
    checkpoint_id: str
    name: str
    stage: str
    criteria: list[str]
    repairable: bool
```

Each checkpoint returns:

```python
class CheckpointResult(BaseModel):
    checkpoint_id: str
    checkpoint_name: str
    stage: str
    status: Literal["pass", "fail", "needs_human"]
    criteria: list[str]
    failures: list[str]
    feedback_for_worker: list[str]
    input_material_id: str
    output_material_id: str | None
    created_at: datetime
```

Implement exactly these five checkpoints.

### 1. Input Integrity Checkpoint

Pass criteria:

* All required trip fields exist
* Destination matches the demo fixture
* Dates are valid
* Trip duration is one to three days
* Traveler count and budget are valid
* Interests and pace use supported values

### 2. Candidate Quality Checkpoint

Pass criteria:

* Candidate collection is not empty
* Every place has a unique stable ID
* Every place has valid coordinates
* Every place identifies `demo_fixture` as its source
* Every place is marked as demo data
* Candidate count is within the configured limit

### 3. Itinerary Schema Checkpoint

Pass criteria:

* Worker output parses into the required Pydantic model
* The number of itinerary days matches the request
* Every day contains the required fields
* Every activity contains place ID, start time, duration, and reason

### 4. Grounding Checkpoint

Pass criteria:

* Every itinerary place ID exists in ranked candidate material
* No unsupported place was introduced
* Place names and coordinates are hydrated by the harness
* The worker did not invent ratings, prices, review counts, or source fields

### 5. Schedule Checkpoint

Pass criteria:

* Every date falls within the requested trip
* Start times are parseable
* Activities are chronological
* Activities do not overlap
* Durations are positive
* A place is not repeated without an explicit reason
* Activity count matches the selected pace

Use these approximate pace limits:

```text
Relaxed: 2–3 activities per day
Balanced: 3–4 activities per day
Busy: 4–5 activities per day
```

Checkpoints must not silently modify worker output.

They return pass/fail results to the harness.

## 11. Alarms pillar

Alarms must be implemented in:

```text
journey/harness/alarms.py
```

Define:

```python
class HarnessAlarm(BaseModel):
    alarm_id: str
    run_id: str
    alarm_type: str
    severity: Literal["info", "warning", "error", "critical"]
    stage: str
    context: dict
    recommended_action: str
    requires_human: bool
    created_at: datetime
```

Implement these alarm types:

* `INPUT_GUARDRAIL_BLOCKED`
* `MATERIAL_VALIDATION_FAILED`
* `CHECKPOINT_FAILED`
* `GROUNDING_VIOLATION`
* `REPAIR_REQUESTED`
* `REPAIR_EXHAUSTED`
* `WORKER_EXECUTION_FAILED`
* `LIMIT_REACHED`
* `HUMAN_REVIEW_REQUIRED`
* `BROWSER_PERSISTENCE_FAILED`

Every alarm must contain:

* Named alarm type
* Severity
* Stage
* Context
* Recommended action
* Whether human input is required

Alarms must be:

* Stored in the run record
* Added to structured logs
* Visible in the diagnostics interface
* Independently testable

Do not represent alarms as plain strings.

## 12. Worker interface

Workers must be implemented under:

```text
journey/workers/
```

Define one shared protocol:

```python
class JourneyWorker(Protocol):
    worker_name: str

    def execute(
        self,
        request: WorkerRequest,
    ) -> WorkerResponse:
        ...
```

The harness controller may depend only on this protocol.

Implement:

* `OpenAIJourneyWorker`
* `DeterministicJourneyWorker`

Both workers must receive the same `WorkerRequest`.

Both workers must return the same `WorkerResponse`.

Changing the worker must not require harness-code changes.

## 13. OpenAI worker

The OpenAI worker must:

* Use the official OpenAI Python SDK
* Keep the API key server-side
* Request structured output matching `WorkerItineraryDraft`
* Receive only prepared trip data, ranked places, existing itinerary, and checkpoint feedback
* Use only supplied place IDs
* Keep reasons concise
* Refine the existing itinerary when refinement text exists
* Correct output based on checkpoint feedback
* Never invent place data
* Never claim live pricing, ratings, opening hours, or availability

The worker should make one model request per attempt.

Do not implement autonomous tool calling inside the worker.

The harness calls tools before invoking the worker.

This keeps the worker portable and the harness visibly in control.

## 14. Deterministic worker

The deterministic worker proves portability and guarantees reliable demo scenarios.

It must support these modes:

```text
normal
fail_once_then_repair
fail_twice
```

### Normal

Returns a valid itinerary.

### Fail once then repair

On the first attempt:

* Returns one unknown place ID

After receiving grounding-checkpoint feedback:

* Removes the unknown ID
* Uses one of the supplied valid IDs
* Returns a corrected response

### Fail twice

* Returns an unknown place ID initially
* Receives checkpoint feedback
* Returns another invalid response
* Causes the harness to raise `REPAIR_EXHAUSTED`
* Causes human escalation

The deterministic worker must react to the actual checkpoint-feedback material.

Do not hard-code the correction inside the harness.

## 15. Demo tools

Tools must be implemented in:

```text
journey/tools/demo_tools.py
```

Implement four typed tools:

### `locate_destination`

* Loads the single destination fixture
* Confirms the requested destination matches it
* Returns typed destination data

### `find_nearby_places`

* Loads candidate places from local fixture data
* Filters by selected interests
* Returns typed place data
* Performs no network calls

### `rank_places`

Ranks places deterministically using:

* Interest match
* Budget fit
* Distance from destination center
* Demo rating confidence
* Category diversity

Return:

* Place ID
* Total score
* Score components
* Brief deterministic explanation

Use stable tie-breaking.

### `save_trip`

* Validates the accepted itinerary
* Returns a typed `SaveTripPayload`
* Does not directly access browser storage

The Dash client-side layer writes the payload to local storage.

Tools do not create itineraries.

Tools do not call OpenAI.

Workers do not call tools directly.

The harness controls tool execution.

## 16. Harness controller

Implement the central controller in:

```text
journey/harness/controller.py
```

Expose:

```python
class JourneyHarness:
    def run(
        self,
        trip_request: TripRequest,
        worker: JourneyWorker,
    ) -> HarnessRunResult:
        ...

    def refine(
        self,
        run_record: RunRecord,
        refinement: str,
        worker: JourneyWorker,
    ) -> HarnessRunResult:
        ...

    def replay(
        self,
        run_record: RunRecord,
        checkpoint_id: str,
        worker: JourneyWorker,
    ) -> HarnessRunResult:
        ...
```

The controller executes this pipeline:

1. Receive trip request
2. Create trip-request material
3. Apply input guardrails
4. Run input checkpoint
5. Run `locate_destination`
6. Run `find_nearby_places`
7. Normalize candidate material
8. Apply candidate-limit guardrail
9. Run candidate-quality checkpoint
10. Run `rank_places`
11. Build worker-request material
12. Invoke selected worker
13. Store draft-itinerary material
14. Run schema checkpoint
15. Run grounding checkpoint
16. Run schedule checkpoint
17. If repairable failure occurs:

    * Persist the failure
    * Create an alarm
    * Create checkpoint-feedback material
    * Invoke the worker one more time
    * Run the same checkpoints again
18. If the second attempt fails:

    * Raise `REPAIR_EXHAUSTED`
    * Raise `HUMAN_REVIEW_REQUIRED`
    * Stop execution
19. Hydrate canonical place fields
20. Store validated-itinerary material
21. Persist the run record
22. Return itinerary and diagnostics

The selected worker must not control pipeline stages.

## 17. Checkpoint feedback and repair

When a repairable checkpoint fails, create:

```python
class CheckpointFeedback(BaseModel):
    failed_checkpoint_id: str
    failed_criteria: list[str]
    validation_errors: list[str]
    valid_place_ids: list[str]
    required_correction: str
    repair_attempt: int
```

Send this feedback to the selected worker.

Example:

```text
Failed checkpoint:
grounding_checkpoint

Error:
Unknown place ID "unknown-999"

Valid IDs:
["demo-001", "demo-002", "demo-003"]

Required correction:
Replace the unknown place using one valid supplied place ID.
Preserve all valid itinerary items.
```

One repair attempt is allowed.

Do not loop indefinitely.

## 18. Human-in-the-loop escalation

Define:

```python
class HumanEscalation(BaseModel):
    reason: str
    question: str
    available_options: list[str]
    blocking_checkpoint: str | None
    related_alarm_id: str
```

The harness must stop and request human input when:

* Repair fails a second time
* No candidate places match the request
* The user requests unsupported booking or payment behavior
* The session reaches a configured limit
* The worker cannot satisfy conflicting constraints

The Dash UI must display:

* Why execution stopped
* Which checkpoint or guardrail caused it
* Available user choices

The harness must not guess past an escalation condition.

## 19. Persistence and replay

Implement persistence in:

```text
journey/harness/persistence.py
```

Use browser-local storage through Dash `dcc.Store(storage_type="local")`.

Persist a typed `RunRecord` containing:

```python
class RunRecord(BaseModel):
    run_id: str
    parent_run_id: str | None
    worker_name: str
    current_stage: str
    materials: list[MaterialEnvelope]
    guardrail_results: list[GuardrailResult]
    checkpoint_results: list[CheckpointResult]
    alarms: list[HarnessAlarm]
    trace_events: list[TraceEvent]
    repair_attempts: int
    refinement_turns: int
    status: str
```

Never trust browser data automatically.

Revalidate restored run records before replay or acceptance.

Replay must:

* Start from a selected persisted checkpoint
* Reuse prior successful materials
* Avoid reloading fixture data when candidate material is already stored
* Create a new run ID
* Link the replay to the original run
* Record the replay checkpoint
* Run all later guardrails and checkpoints normally

A simple replay dropdown is sufficient.

## 20. Observability

Implement observability in:

```text
journey/harness/observability.py
```

Record structured events for:

* Run started
* Guardrail evaluated
* Tool started
* Tool completed
* Worker started
* Worker completed
* Checkpoint passed
* Checkpoint failed
* Repair requested
* Alarm created
* Human escalation created
* Replay started
* Plan accepted
* Run completed

Track when available:

* Stage duration
* Total run duration
* Worker latency
* Token usage
* Estimated cost
* Repair count
* Refinement count
* Selected worker
* Final status

Use JSON logs to stdout.

Do not add external observability platforms.

Do not log:

* API keys
* Full OpenAI prompts
* Entire browser-storage payloads
* Sensitive user information

Observability does not replace alarms.

## 21. Dash interface

Create a single-page interface.

Required controls:

* Supported destination
* Start date
* End date
* Travelers
* Budget
* Interest selection
* Travel pace
* Worker selector
* Generate button
* Refinement text
* Refine button
* Accept and save button
* Start over button

Add a collapsed “Demo controls” section containing:

* Deterministic worker scenario selector
* Replay checkpoint selector
* Replay button

Required output areas:

* Itinerary cards
* MapLibre map
* Conversation/refinement history
* Human-escalation panel
* Data disclaimer
* Harness diagnostics

Diagnostics must show separate sections for:

1. Materials
2. Guardrails
3. Checkpoints
4. Alarms
5. Worker activity
6. Replay information
7. Trace metrics

Display visibly:

```text
Place data: Local demonstration fixtures
Ratings and costs: Simulated
Worker: OpenAI Journey Worker
```

or:

```text
Worker: Deterministic Journey Worker
```

## 22. MapLibre

Use MapLibre GL JS only for rendering validated itinerary data.

Create:

* `assets/journey-map.js`
* `assets/journey.css`
* A Dash map container
* A client-side callback or JavaScript update function

Display:

* Numbered activity markers
* Popups with time, name, category, and reason
* A line connecting activities in schedule order
* Fit-to-bounds behavior
* Clear demo-data attribution

The server must create GeoJSON only from validated and hydrated itinerary material.

The worker must not generate GeoJSON.

Escape all popup content.

Initialize the map once and update its source after refinements.

## 23. Browser state

Use separate Dash stores:

```text
active-run-store: session
active-itinerary-store: session
accepted-trip-store: local
run-history-store: local
map-data-store: session
```

Do not use process-global dictionaries for session state.

Do not store API keys in any Dash store.

## 24. Required tests

Write tests proving:

### Materials

* Materials receive IDs and hashes
* Materials serialize and restore
* Invalid material is rejected
* Source attribution is preserved

### Guardrails

* Guardrails are declared in a registry
* Invalid input is blocked
* Candidate material is transformed to the limit
* Transformed material reaches the worker
* Limits are finite

### Checkpoints

* Checkpoint criteria are explicit
* Valid output passes
* Unknown place ID fails grounding
* Overlapping activities fail schedule
* Invalid schema fails schema checkpoint
* Unsupported worker claims fail grounding or schema validation

### Feedback

* Failed checkpoint produces feedback
* Feedback is sent to the worker
* Worker changes its second response
* Corrected response passes

### Alarms

* Every alarm includes type, severity, context, and recommended action
* Grounding failure raises the expected alarm
* Repeated failure raises `REPAIR_EXHAUSTED`
* Human escalation raises `HUMAN_REVIEW_REQUIRED`

### Workers

* Both workers implement the same protocol
* Both workers run through the same harness
* Switching workers requires no harness changes
* Deterministic scenarios behave as documented

### Replay

* Run records restore correctly
* Replay starts at the selected checkpoint
* Replay reuses earlier materials
* Replay does not reload fixture data unnecessarily

### Security

* API keys do not appear in client payloads
* Browser-restored records are revalidated
* Tests make no live network calls

Mock all OpenAI calls in automated tests.

## 25. Documentation

Create a root-level `HARNESS.md`.

It must include:

1. Harness purpose
2. Worker responsibility
3. Worker non-responsibilities
4. Four-pillar architecture
5. Guardrail declarations
6. Checkpoint pass/fail criteria
7. Material flow
8. Alarm schema and alarm types
9. Worker protocol
10. Feedback and repair flow
11. Human escalation
12. Persistence
13. Replay
14. Observability
15. Demo-data disclaimer
16. Worker-swap instructions
17. Five-minute demo flow
18. Known limitations

Include a diagram similar to:

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
    +-- pass --> Validated Itinerary
    |
    +-- fail --> Alarm --> Feedback --> One Repair
                                    |
                                    +-- fail --> Human Escalation
```

## 26. Required commands

The repository must support:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
pytest
ruff check .
```

Expose:

```python
server = app.server
```

for deployment.

## 27. Environment variables

Use only necessary variables:

```env
OPENAI_API_KEY=
OPENAI_MODEL=
JOURNEY_WORKER=deterministic
MAX_REPAIR_ATTEMPTS=1
MAX_REFINEMENT_TURNS=3
MAX_CANDIDATE_PLACES=12
MAX_TRIP_DAYS=3
```

The app must start without an OpenAI key when the deterministic worker is selected.

## 28. Implementation order

Implement in this order:

1. Shared Pydantic models
2. Material handling
3. Guardrail registry and engine
4. Checkpoint registry and engine
5. Alarm manager
6. Run-record persistence
7. Worker protocol
8. Deterministic worker
9. Demo fixtures and tools
10. Harness controller
11. Feedback and repair
12. Human escalation
13. Replay
14. Harness tests
15. OpenAI worker
16. Dash interface
17. Diagnostics interface
18. MapLibre
19. Documentation
20. Final verification

Do not begin UI polish before the harness tests pass.

## 29. Working method

Before coding:

1. Inspect the repository.
2. Read this file.
3. Read both source PDFs.
4. Create `IMPLEMENTATION_PLAN.md`.
5. Map every challenge requirement to:

   * Source file
   * Test
   * Demo step

During implementation:

* Work in vertical slices
* Keep the application runnable
* Run focused tests after each phase
* Keep code straightforward
* Avoid premature abstractions
* Do not expand scope
* Update the implementation plan

Before declaring completion:

* Run all tests
* Run Ruff
* Run the deterministic normal scenario
* Run fail-once-and-repair
* Run fail-twice-and-escalate
* Run OpenAI mode when a key is available
* Test replay
* Test worker switching
* Verify local persistence
* Verify MapLibre
* Verify that no key reaches the browser

## 30. Definition of done

Journey is complete only when:

1. Guardrails, checkpoints, materials, and alarms are separate modules.
2. The worker is separate from all four pillars.
3. Guardrails are declared.
4. Checkpoints have explicit pass/fail criteria.
5. Alarms are structured.
6. Material movement is typed and visible.
7. A checkpoint failure changes the worker’s next response.
8. A corrected response can pass.
9. A repeated failure stops and requests human input.
10. Run data can be persisted and replayed.
11. Both workers use the same harness.
12. A real user trip request can be entered.
13. Demo data is clearly labeled.
14. MapLibre shows only validated places.
15. `HARNESS.md` is complete.
16. Tests make no live network calls.
17. The deployed demo can be explained in five minutes.
