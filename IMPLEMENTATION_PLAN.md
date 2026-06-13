# Journey Implementation Plan

## Scope

Journey is a harness-first itinerary application for the 24-hour Build Challenge. It uses one versioned 24-place Austin fixture dataset with activity capabilities, one deterministic worker, and one optional OpenAI worker. The harness owns all data loading, validation, control flow, repair, escalation, persistence, replay, hydration, and map-data generation.

No live place provider, booking flow, background job, database, authentication system, autonomous tool calling, or multi-agent behavior is in scope.

## 1. Simplified Architecture Diagram

```text
Dash UI / browser stores / MapLibre
                |
         JourneyHarness
     +----------+----------+
     |          |          |
 Materials  Guardrails  Checkpoints
     |          |          |
     +------ Alarms --------+
                |
      Harness-owned demo tools
                |
      JourneyWorker protocol
        /               \
 Deterministic       OpenAI
                |
      RunRecord + JSON traces
```

## 2. Material-Flow Diagram

```text
TripRequestMaterial
  -> ValidatedTripMaterial
  -> CandidatePlacesMaterial
  -> transformed CandidatePlacesMaterial (when over limit)
  -> RankedPlacesMaterial
  -> WorkerRequestMaterial
  -> DraftItineraryMaterial
  -> CheckpointFeedbackMaterial -> one repaired DraftItineraryMaterial
  -> ValidatedItineraryMaterial
  -> AcceptedTripMaterial
```

Every envelope is typed, versioned, hashed, size-limited, source-attributed, serializable, and stored in the run record.

## 3. Harness Pipeline

1. Validate the trip request and create its material.
2. Apply declared input guardrails and the input-integrity checkpoint.
3. Run fixture destination and candidate tools.
4. Normalize candidate material, apply the candidate-limit transform, and evaluate candidate quality.
5. Rank candidates deterministically and build the worker request.
6. Invoke the dependency-injected worker.
7. Evaluate schema, grounding, and schedule checkpoints.
8. On a repairable failure, create an alarm and feedback material, then invoke the same worker once more.
9. On repeated failure, create repair-exhausted and human-review alarms and stop.
10. On success, hydrate canonical place data, create validated itinerary/map data, persist the run record, and return diagnostics.

## 4. Guardrail Registry

| Stage | Guardrail | Failure action |
| --- | --- | --- |
| input | destination present and supported | block |
| input | valid dates and one-to-three-day duration | block |
| input | travelers 1-6 and positive budget | block |
| input | supported interests and pace | block |
| input | refinement length <= 500 | block |
| material | candidate count <= 12 | transform |
| material | worker context allowlist | block |
| material | text and payload size limits | transform/block |
| worker | selected worker registered | block |
| worker | attempts <= 2, refinements <= 3 | escalate |
| worker | session/token limits | escalate |
| worker | booking/payment/file/URL/code requests | block/escalate |
| security | API key remains server-side | block |

All declarations and results live in `journey/harness/guardrails.py` and appear in diagnostics.

## 5. Checkpoint Criteria

| Checkpoint | Pass criteria | Repairable |
| --- | --- | --- |
| Input Integrity | required fields, supported destination, dates/duration, traveler/budget bounds, supported interests/pace | no |
| Candidate Quality | non-empty, unique IDs, valid coordinates, fixture source/demo flags, within limit | no |
| Itinerary Schema | parses typed draft, correct day count, required day/activity fields | yes |
| Grounding | IDs belong to ranked candidates; no invented canonical fields; hydration succeeds | yes |
| Schedule | dates in range, parseable chronological non-overlapping times, positive duration, pace counts, justified repeats | yes |

## 6. Alarm Types

`INPUT_GUARDRAIL_BLOCKED`, `MATERIAL_VALIDATION_FAILED`, `CHECKPOINT_FAILED`, `GROUNDING_VIOLATION`, `REPAIR_REQUESTED`, `REPAIR_EXHAUSTED`, `WORKER_EXECUTION_FAILED`, `LIMIT_REACHED`, `HUMAN_REVIEW_REQUIRED`, and `BROWSER_PERSISTENCE_FAILED`.

Each alarm carries type, severity, stage, context, recommended action, human-review flag, timestamp, run ID, and alarm ID.

## 7. Worker Interface

```python
class JourneyWorker(Protocol):
    worker_name: str

    def execute(self, request: WorkerRequest) -> WorkerResponse:
        ...
```

`DeterministicJourneyWorker` and `OpenAIJourneyWorker` consume the same request model and return the same response model. Workers receive supplied place IDs and optional checkpoint feedback; they do not load fixtures, call tools, mutate records, validate themselves, or generate map data.

## 8. Feedback and Repair Flow

```text
checkpoint fail
  -> structured CheckpointResult
  -> typed alarm
  -> CheckpointFeedback(valid IDs, errors, required correction)
  -> CheckpointFeedbackMaterial
  -> same worker, repair attempt 1
  -> rerun output checkpoints
  -> pass OR repair exhausted
```

Exactly one repair attempt is permitted. The deterministic fail-once scenario changes output only after receiving real grounding feedback.

## 9. Human Escalation Flow

The harness stops and returns `HumanEscalation` when repair fails again, candidates are empty, unsupported booking/payment behavior is requested, a configured limit is reached, or constraints cannot be satisfied. The UI displays the reason, blocking control, related alarm, and choices without guessing a continuation.

## 10. Persistence and Replay Design

Dash stores active run/itinerary/map state in session storage and accepted trips/run history in local storage. Server callbacks revalidate every restored `RunRecord` with Pydantic before replay or acceptance.

Replay creates a new run ID and sets `parent_run_id` to the original run. It selects persisted successful candidate/ranking materials for the chosen checkpoint, avoids fixture reload/reranking when those materials already exist, records a replay trace, and runs all downstream controls normally.

## 11. UI Component List

- Trip form: destination, dates, travelers, budget, interests, pace
- Worker selector and generate button
- Itinerary cards and refinement controls
- Accept/save and start-over actions
- Human-escalation panel
- Collapsible demo controls: deterministic scenario, replay checkpoint, replay action
- Collapsible diagnostics with materials, guardrails, checkpoints, alarms, worker activity, replay, and trace metrics
- Visible fixture/simulated-data/worker/status labels
- MapLibre container fed only validated server-generated GeoJSON
- Session/local `dcc.Store` components required by `AGENTS.md`

## 12. Test Matrix

| Area | Happy path | Failure/boundary | Integration proof |
| --- | --- | --- | --- |
| Models/materials | typed round-trip | invalid payload/size | replay restoration |
| Guardrails | valid request | invalid input and candidate transform | transformed candidates reach worker |
| Checkpoints | valid draft | schema, unknown ID, overlap, invented field | full output checkpoint chain |
| Alarms | structured alarm | all required metadata | persisted and traced alarm |
| Workers | normal output | fail once/fail twice/OpenAI error | same harness protocol |
| Feedback | corrected repair | exhausted repair | feedback reaches and changes worker |
| Replay | downstream rerun | tampered browser record | candidate/ranking materials reused |
| Security | deterministic no-key | no key/client payload/network | mocked OpenAI only |
| UI/map | cards and validated GeoJSON | escalation/empty state | Dash callback and browser smoke test |

## 13. Five-Minute Demo Sequence

1. Show the four modules and worker protocol in code/diagnostics.
2. Enter a real Austin trip request and run deterministic `normal`; show all controls pass, itinerary cards, and map.
3. Run `fail_once_then_repair`; show the unknown ID, grounding failure, alarm, feedback valid IDs, changed worker response, and successful repair.
4. Run `fail_twice`; show bounded retry, `REPAIR_EXHAUSTED`, `HUMAN_REVIEW_REQUIRED`, stopped status, and question.
5. Replay the successful run from grounding/schedule using persisted candidate/ranking materials; show new run/parent IDs.
6. Swap worker selector to OpenAI when a server key is available, or explain deterministic no-key portability.

## 14. Requirement-to-File Mapping

| Requirement | Primary files |
| --- | --- |
| shared typed contracts | `journey/models.py` |
| material handling | `journey/harness/materials.py` |
| declared guardrails | `journey/harness/guardrails.py` |
| explicit checkpoints | `journey/harness/checkpoints.py` |
| structured alarms | `journey/harness/alarms.py` |
| persistence/revalidation | `journey/harness/persistence.py`, `journey/ui/callbacks.py` |
| observability | `journey/harness/observability.py` |
| worker portability | `journey/workers/protocol.py`, both worker modules |
| fixture-only tools | `journey/tools/demo_tools.py`, `data/demo/*.json` |
| controlled pipeline/repair/escalation/replay | `journey/harness/controller.py` |
| one-page UI/diagnostics | `journey/ui/*.py`, `app.py` |
| validated map | `journey/ui/presenters.py`, `assets/journey-map.js` |
| architecture/demo docs | `HARNESS.md`, `README.md` |

## 15. Requirement-to-Test Mapping

| Requirement | Tests |
| --- | --- |
| typed materials, hashes, source, restore | `tests/test_materials.py` |
| declared guardrails, blocking, transformation, finite limits | `tests/test_guardrails.py` |
| five explicit checkpoints and failure modes | `tests/test_checkpoints.py` |
| structured alarm types and metadata | `tests/test_alarms.py` |
| common protocol and deterministic behavior | `tests/test_workers.py` |
| real pipeline, no worker on invalid input, repair/escalation | `tests/test_harness.py` |
| persisted replay and browser revalidation | `tests/test_replay.py` |
| API-key/client/network boundaries | `tests/test_security.py` |
| UI stores, callbacks, validated map GeoJSON | `tests/test_ui.py` |

## Build and Verification Order

Implementation follows the exact 20-step order in `AGENTS.md`: models; materials; guardrails; checkpoints; alarms; persistence; protocol; deterministic worker; fixtures/tools; controller; feedback/repair; escalation; replay; harness tests; OpenAI worker; Dash; diagnostics; MapLibre; documentation; final verification.

After each backend phase, run focused Pytest tests and `ruff check .`. Keep `python app.py` runnable after application scaffolding exists. Final verification includes the complete test suite, Ruff, all three deterministic scenarios, replay, worker switching, persistence revalidation, browser/MapLibre behavior, no-key startup, no client-side key, and no live network calls in tests.

## Verification Progress

- Core models, materials, guardrails, checkpoints, alarms, persistence: implemented; focused tests and Ruff pass.
- Worker protocol, deterministic scenarios, fixture tools, controller, feedback, escalation, replay: implemented; harness integration tests pass.
- OpenAI structured worker: implemented with an injected mocked client test and no live test network calls.
- Dash, diagnostics, browser stores, and MapLibre adapter: implemented; app import and required-store tests pass.
- Documentation and deployment verification: complete.
- Final automated result: 21 Pytest tests pass; `ruff check .`, `compileall`, and `git diff --check` pass.
- Manual scenario result: normal completes; fail-once repairs and completes; fail-twice creates `REPAIR_EXHAUSTED` plus `HUMAN_REVIEW_REQUIRED`; replay links its parent and reuses ranked material.
- Deployment result: Gunicorn serves HTTP 200 and vendored MapLibre assets; no external runtime asset URLs are present in the page.
- Browser screenshot verification: not run because no browser automation executable is installed in this environment.
