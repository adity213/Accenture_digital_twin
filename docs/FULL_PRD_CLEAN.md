DigitalTwin.ai

Technical Prototype PRD — 1-Week Build Specification

Accenture Innovation Challenge 2026 · Round 2 · Problem Track 4

Team Twin Flow — Aditya Singh · Divyansh Singh Mertia · Harshada Rajhans (IIT Kanpur)

1. Scope & Objectives

1.1 In scope for the 1-week prototype

Full 40-station simulated topology across Body / Paint / Final Assembly, driving a live “replay” stream.

SPC/statistical anomaly baseline per station.

Virtual sensor inference + confidence scoring for low-instrumentation stations.

Gradient-boosted risk scoring model for bottleneck and defect likelihood, trained on simulator ground truth.

Graph-propagation layer producing downstream risk and time-to-impact.

Rule-based recommendation engine with expected-impact estimates.

Floor Supervisor live view (2.5D schematic + drill-down) and a lighter Plant Manager / Leadership summary view.

Public GitHub repo, README, and a 3-minute demo video.

1.2 Explicitly out of scope for v1

Real PLC/OT/MES integration — the simulator stands in for the live plant feed.

Real computer-vision defect detection — vision output is mocked as a labelled signal (defect_flag / defect_type), not a trained CV model.

Multi-plant / multi-line rollout, true closed-loop autonomous control, and continuous online retraining (a feedback-loop stub is included, full retraining is a stretch goal).

Authentication, RBAC enforcement, and production-grade security hardening (noted in the design, not built).

2. System Architecture

Layer | Responsibility | Tech

Layer

Responsibility

Tech

Simulator | Generates the synthetic line topology, live telemetry stream, and ground-truth anomaly labels | Python (numpy, pandas)

Simulator

Generates the synthetic line topology, live telemetry stream, and ground-truth anomaly labels

Python (numpy, pandas)

Ingestion / Store | Buffers the live stream; persists history for model training and the trend views | SQLite / DuckDB + in-memory ring buffer

Ingestion / Store

Buffers the live stream; persists history for model training and the trend views

SQLite / DuckDB + in-memory ring buffer

Processing Pipeline | SPC engine → virtual sensor inference → risk scoring → graph propagation → confidence aggregator → recommendation engine | Python (scikit-learn / LightGBM, networkx)

Processing Pipeline

SPC engine → virtual sensor inference → risk scoring → graph propagation → confidence aggregator → recommendation engine

Python (scikit-learn / LightGBM, networkx)

API | Exposes current + historical state, predictions, and recommendations; streams live updates | FastAPI (REST) + WebSocket

API

Exposes current + historical state, predictions, and recommendations; streams live updates

FastAPI (REST) + WebSocket

Frontend | Floor Supervisor schematic view; Plant Manager / Leadership summary view | React + TypeScript, react-three-fiber, Recharts

Frontend

Floor Supervisor schematic view; Plant Manager / Leadership summary view

React + TypeScript, react-three-fiber, Recharts

Data flows one direction, left to right, on every tick of the simulated clock: Simulator → Store → Processing Pipeline → API → Frontend. Each processing stage writes its output back to the store so the API layer only ever reads pre-computed state — this keeps the live view responsive regardless of model cost.

3. Line Topology & Data Model

3.1 Topology

40 stations total across 3 zones: Body Construction (14 stations), Paint (8 stations), Final Assembly (18 stations), connected as a directed graph with a small number of parallel/buffer paths (not a pure straight line) to make propagation interesting.

Each station has an explicit sensor_tier: “rich” (continuous PLC + vision telemetry) or “manual” (periodic checklist only) — roughly 80% rich / 20% manual, matching our stated assumption.

3.2 Station schema

station_id, zone, station_type, sensor_tier, target_cycle_time_s,

buffer_capacity_units, upstream_ids[], downstream_ids[]

3.3 Telemetry event schema

timestamp, station_id, cycle_time_s, buffer_level, vibration?, temperature?,

defect_flag, defect_type?, energy_kwh, vehicle_id

3.4 Vehicle / genealogy schema

vehicle_id, station_visit_log[{station_id, entry_time, exit_time}], defect_flags[]

4. Synthetic Data Simulator Design

The simulator is the foundation of the whole prototype: it must be realistic enough that the risk model has something genuine to learn, and it must retain ground-truth labels separately so the risk model is honestly evaluated as a prediction task, not a lookup.

4.1 Normal operation

Cycle time per station ∼ Normal(target_cycle_time, small σ), station-type dependent.

Buffer levels modelled with simple queueing dynamics between adjacent stations (inflow/outflow rate difference).

4.2 Injected anomaly types

Anomaly | Behaviour | Why it matters

Anomaly

Behaviour

Why it matters

Gradual equipment drift | Cycle time at a station rises slowly over hours, mimicking wear | Tests SPC trend detection and early warning

Gradual equipment drift

Cycle time at a station rises slowly over hours, mimicking wear

Tests SPC trend detection and early warning

Sudden stoppage | Station goes down for ~80–90 minutes before restart, per the Round 1 problem brief | Tests bottleneck propagation and time-to-impact

Sudden stoppage

Station goes down for ~80–90 minutes before restart, per the Round 1 problem brief

Tests bottleneck propagation and time-to-impact

Latent / late-surfacing defect | A defect is introduced upstream but only flagged N stations later at inspection | Tests root-cause tracing across the vehicle genealogy

Latent / late-surfacing defect

A defect is introduced upstream but only flagged N stations later at inspection

Tests root-cause tracing across the vehicle genealogy

Sensor blackout | Manual/low-tier stations only report at checklist intervals, never continuously | Tests virtual sensor inference and confidence scoring

Sensor blackout

Manual/low-tier stations only report at checklist intervals, never continuously

Tests virtual sensor inference and confidence scoring

Energy waste pattern | Idle-machine energy draw during starvation periods | Feeds the Energy output and leadership ROI view

Energy waste pattern

Idle-machine energy draw during starvation periods

Feeds the Energy output and leadership ROI view

Ground-truth labels (station_id, timestamp, true_anomaly_type) are stored separately and only used for model training/evaluation — never exposed to the live prediction pipeline.

5. Modeling Approach

5.1 SPC / anomaly baseline

Per-station EWMA / z-score on cycle time and buffer level against a rolling baseline. This does not make the final call alone — its output is a feature into the risk model — but it gives an explainable, always-on signal even before the ML model has enough data.

5.2 Virtual sensor inference & confidence

For manual/low-tier stations, we impute the expected state from: (i) correlated neighboring stations, (ii) historical pattern at the same point in shift, (iii) a lightweight regression across upstream/downstream signals. A confidence score (0–1) combines sensor tier, data recency, and agreement across the imputation methods:

confidence = w1·sensor_tier_score + w2·recency_score + w3·(1 − imputation_disagreement)

with weights normalized to sum to 1 and tuned against held-out simulator data so imputation error and reported confidence actually correlate.

5.3 Risk scoring model

A LightGBM (or scikit-learn GradientBoosting as a fallback) binary classifier per station predicts P(bottleneck within next 15 minutes) and P(defect associated with this station's output), using features: SPC z-scores, buffer trend, lagged upstream risk scores, cycle-time trend, sensor confidence, time-of-shift, and station type. Trained on simulator-labelled history; evaluated on precision/recall, lead-time-before-event, and calibration — not accuracy alone, since under-triage of a real bottleneck is far costlier than a false alarm.

5.4 Graph propagation layer

The line is represented as a DAG (networkx). Given a station's risk score, we propagate a decayed “downstream starvation risk” to descendant stations, weighted by inverse buffer capacity and graph distance, and estimate:

time_to_impact ≈ buffer_units_remaining / (inflow_rate − outflow_rate)

This is what turns “station 12 looks off” into “station 18 will starve in ~9 minutes if nothing changes” — the actionable, ripple-aware signal the brief specifically asks for.

5.5 Confidence aggregator

Combines data-confidence (5.2) with model-confidence (prediction probability spread / calibration) into a single 0–100 “Twin Confidence” shown per station, so floor staff can tell at a glance when to double-check a number themselves.

5.6 Recommendation engine

A rule table maps (risk_type × severity_tier × zone) to a concrete action, rationale, and an expected-impact estimate. Roughly 8–10 rules are enough to make the demo convincing, e.g.:

Note on the numbers below: the “Expected Impact” figures in this table are illustrative placeholders for what a rule's output should look like, not literal strings to hardcode. At runtime, expected impact must be computed from the actual current state (e.g., derived from the propagation layer's time-to-impact and buffer levels at the moment the rule fires) so it changes with the situation — a rule that always prints the same “~12 min” regardless of context is faking the mechanism, not implementing it.

Condition | Recommended Action | Expected Impact

Condition

Recommended Action

Expected Impact

Bottleneck risk > 70%, Final Assembly, buffer < 20% | Reroute next 3 vehicles to parallel path / reassign 1 operator | ~12 min downtime avoided

Bottleneck risk > 70%, Final Assembly, buffer < 20%

Reroute next 3 vehicles to parallel path / reassign 1 operator

~12 min downtime avoided

Gradual drift flagged, Body zone, confidence > 80% | Schedule inspection at next maintenance window | Prevents escalation to full stoppage

Gradual drift flagged, Body zone, confidence > 80%

Schedule inspection at next maintenance window

Prevents escalation to full stoppage

Latent defect risk > 60%, low confidence station | Flag vehicle batch for manual QC hold | Avoids downstream rework across N vehicles

Latent defect risk > 60%, low confidence station

Flag vehicle batch for manual QC hold

Avoids downstream rework across N vehicles

6. API Design

Endpoint | Method | Purpose

Endpoint

Method

Purpose

/stations | GET | List all stations with static topology + current sensor tier

/stations

GET

List all stations with static topology + current sensor tier

/stations/{id}/history | GET | Time-series history for a station (cycle time, buffer, energy)

/stations/{id}/history

GET

Time-series history for a station (cycle time, buffer, energy)

/risk/current | GET | Current risk scores + confidence for every station

/risk/current

GET

Current risk scores + confidence for every station

/risk/{station_id}/propagation | GET | Downstream propagation and time-to-impact for a station

/risk/{station_id}/propagation

GET

Downstream propagation and time-to-impact for a station

/recommendations | GET | Current ranked recommendations with expected impact

/recommendations

GET

Current ranked recommendations with expected impact

/recommendations/{id}/override | POST | Log a supervisor accept/override decision

/recommendations/{id}/override

POST

Log a supervisor accept/override decision

/stream/live | WS | Live push of telemetry + updated risk/confidence as the simulator ticks

/stream/live

WS

Live push of telemetry + updated risk/confidence as the simulator ticks

7. Frontend / UX Design

7.1 Floor Supervisor view (primary, deep)

A 2.5D schematic (react-three-fiber) with stations arranged along the 3 zones as simple extruded blocks, color-coded green / amber / red by combined current + predicted risk.

Clicking a station opens a side panel: live metrics, Twin Confidence, contributing factors, and the top recommended action with an accept/override control.

Live WebSocket updates so risk color and time-to-impact move in real time as the simulator plays.

7.2 Plant Manager / Leadership view (lighter, secondary tab)

Weekly bottleneck heat-map (station × time).

Downtime-avoided counter and energy-waste chart (Recharts, periodic refresh rather than live).

Top recurring root causes, to support the business-case narrative in the demo video.

This view was intentionally scoped lighter, per our prioritisation: the Floor Supervisor view and the prediction/recommendation engine are the hero mechanism this week; the leadership view exists to prove the same twin serves multiple personas, not to be pixel-polished.

8. Tech Stack

Component | Choice

Component

Choice

Simulator & pipeline | Python 3.11, pandas, numpy, scikit-learn / LightGBM, networkx

Simulator & pipeline

Python 3.11, pandas, numpy, scikit-learn / LightGBM, networkx

Storage | SQLite or DuckDB for history; in-memory buffer for the live tick

Storage

SQLite or DuckDB for history; in-memory buffer for the live tick

API | FastAPI (REST + WebSocket)

API

FastAPI (REST + WebSocket)

Frontend | React + TypeScript, react-three-fiber / Three.js for the schematic, Recharts for trend panels

Frontend

React + TypeScript, react-three-fiber / Three.js for the schematic, Recharts for trend panels

Packaging | Docker Compose (optional, nice-to-have for the repo)

Packaging

Docker Compose (optional, nice-to-have for the repo)

9. Repository Structure

digitaltwin-ai/

simulator/        topology.py, generator.py, anomalies.py

pipeline/         spc.py, virtual_sensor.py, risk_model.py,

propagation.py, confidence.py, recommender.py

api/              main.py (FastAPI), schemas.py, ws.py

frontend/         floor-view/, leadership-view/, shared components

notebooks/        model training + evaluation

data/             generated topology.json, historical telemetry

README.md, demo/ (video + script)

10. 7-Day Build Plan

Day | Focus

Day

Focus

1 | Finalize 40-station topology; build the simulator (normal operation + all 5 anomaly types)

1

Finalize 40-station topology; build the simulator (normal operation + all 5 anomaly types)

2 | SPC baseline; virtual sensor inference + confidence scoring

2

SPC baseline; virtual sensor inference + confidence scoring

3 | Train and evaluate the risk scoring model; build the graph propagation layer

3

Train and evaluate the risk scoring model; build the graph propagation layer

4 | Recommendation engine; FastAPI backend + WebSocket streaming; wire pipeline end-to-end

4

Recommendation engine; FastAPI backend + WebSocket streaming; wire pipeline end-to-end

5 | Floor Supervisor schematic view + station drill-down panel, connected live

5

Floor Supervisor schematic view + station drill-down panel, connected live

6 | Plant Manager / Leadership view; end-to-end integration and polish

6

Plant Manager / Leadership view; end-to-end integration and polish

7 | Buffer day: bug fixes, demo video recording, README, GitHub repo, rehearse the pitch

7

Buffer day: bug fixes, demo video recording, README, GitHub repo, rehearse the pitch

11. Prototype Acceptance Checklist

Full 40-station simulation runs end-to-end and drives the live views.

At least one gradual-degradation, one sudden-stoppage, and one latent/late-surfacing defect scenario are demonstrably detected.

At least one manual/low-sensor station visibly shows virtual-sensor inference with a lower confidence score than a rich-sensor station.

At least 3 recommendations fire during the demo, each with a stated expected impact.

Both the Floor Supervisor and Plant Manager/Leadership views are functional and reachable from one app.

A supervisor override is logged and visible somewhere in the system (even if not yet used to retrain).

12. Demo Script Outline (≤ 3 minutes)

0:00–0:25 — The problem, in the plant's own numbers (27 hrs/month, $2.3M/hour, reactive monitoring).

0:25–1:00 — Open the live twin: show the schematic, a station going amber then red as a stoppage is injected.

1:00–1:40 — Click into the flagged station: show Twin Confidence, contributing factors, and the downstream time-to-impact from the propagation layer.

1:40–2:10 — Show the recommendation firing, accept it, and show the manual/low-sensor station case with its lower confidence score.

2:10–2:40 — Switch to the Plant Manager / Leadership view: weekly heat-map and downtime-avoided counter.

2:40–3:00 — Close on the roadmap: shadow-mode pilot → closed loop → multi-plant.

13. Stretch Goals (if ahead of schedule)

Feedback-loop stub: a supervisor override nudges the risk model's feature weights, demonstrating the learning loop conceptually.

Low-cost sensing retrofit recommender: rank manual stations by how much they'd improve twin accuracy if instrumented.

A second simulated line to show the topology-as-config approach genuinely generalizes.

14. Known Limitations / Non-Goals (v1)

No real PLC/OT/MES connection — the simulator is an explicit stand-in, clearly labelled as such in the demo.

Computer-vision defect detection is mocked as a labelled signal, not a trained model, given the one-week timeline.

No authentication/RBAC enforcement or production security hardening — called out as Phase 1 work in the Business Proposal.

Continuous online retraining is a stretch goal, not a v1 guarantee.

15. Default Parameters — Ambiguity Resolution

Antigravity (or any coding agent) works better with a concrete default than an open judgment call. Every number below is a starting default, not a suggestion to re-derive from scratch — change it only if a gate in Section 16 explicitly tells you to.

Parameter | Default Value

Parameter

Default Value

Station count / zone split | 40 total — Body 14, Paint 8, Final Assembly 18. Fixed; do not change without updating every downstream test and gate.

Station count / zone split

40 total — Body 14, Paint 8, Final Assembly 18. Fixed; do not change without updating every downstream test and gate.

Sensor tier split | 80% rich / 20% manual, fixed random seed = 42 for reproducibility.

Sensor tier split

80% rich / 20% manual, fixed random seed = 42 for reproducibility.

Buffer capacity per station | Uniform random 5–15 units, same seed = 42.

Buffer capacity per station

Uniform random 5–15 units, same seed = 42.

Simulation tick size | 1 simulated minute per tick.

Simulation tick size

1 simulated minute per tick.

Live replay speed | 1 simulated hour ≈ 20 real seconds during demo playback.

Live replay speed

1 simulated hour ≈ 20 real seconds during demo playback.

SPC threshold | z-score > 3.0 flags a deviation. Only drop to 2.5 if Day 2's gate shows drift anomalies aren't caught early enough.

SPC threshold

z-score > 3.0 flags a deviation. Only drop to 2.5 if Day 2's gate shows drift anomalies aren't caught early enough.

EWMA smoothing factor (λ) | 0.3

EWMA smoothing factor (λ)

0.3

Confidence formula weights | w1 (sensor tier) = 0.5, w2 (recency) = 0.3, w3 (imputation agreement) = 0.2 (Section 5.2).

Confidence formula weights

w1 (sensor tier) = 0.5, w2 (recency) = 0.3, w3 (imputation agreement) = 0.2 (Section 5.2).

Risk alert thresholds | P(risk) > 0.6 → amber, P(risk) > 0.8 → red.

Risk alert thresholds

P(risk) > 0.6 → amber, P(risk) > 0.8 → red.

Risk model hyperparameters | LightGBM: num_leaves=31, learning_rate=0.05, n_estimators=200, early stopping on validation AUC.

Risk model hyperparameters

LightGBM: num_leaves=31, learning_rate=0.05, n_estimators=200, early stopping on validation AUC.

Train/test split | Chronological — first 70% of simulated time for training, last 30% held out. Never a random row shuffle.

Train/test split

Chronological — first 70% of simulated time for training, last 30% held out. Never a random row shuffle.

WebSocket push cadence | One push per simulated tick; target end-to-end UI latency < 2 seconds.

WebSocket push cadence

One push per simulated tick; target end-to-end UI latency < 2 seconds.

16. Phase-Gate Validation Framework

Each day in Section 10 ends with a gate: a concrete, mostly-automatable check that must pass before the next day's work begins. Treat a failed gate as a stop condition, not a note for later — errors compound silently in a pipeline like this, and a broken Day 1 simulator invalidates every metric computed on Day 3.

Important — these gates check the mechanism, not a score: no number below is a guaranteed or externally validated result — they are internal sanity bars, calibrated against your own simulator. Where a gate mentions a specific figure, treat it as a starting default to tune, not a target to force. If a number won't move honestly, the fix is to correct the underlying mechanism (the model, the feature set, the confidence formula), never to hardcode a value, fabricate a baseline, or adjust the simulator until the gate happens to pass. A gate that passes because the result was faked is worse than a gate that fails honestly — it hides exactly the bug the gate was built to catch.

Day 1 Gate — Simulator & Topology

Validation Check | Pass Criteria

Validation Check

Pass Criteria

Topology structure | 40 stations total; zone counts exactly 14 / 8 / 18; graph is a valid DAG (networkx.is_directed_acyclic_graph == True).

Topology structure

40 stations total; zone counts exactly 14 / 8 / 18; graph is a valid DAG (networkx.is_directed_acyclic_graph == True).

Normal-operation sanity | With all anomalies OFF, ≥99% of cycle-time readings per station fall within ±3σ of that station's target.

Normal-operation sanity

With all anomalies OFF, ≥99% of cycle-time readings per station fall within ±3σ of that station's target.

All 5 anomaly types triggerable | Each of drift, stoppage, latent defect, sensor blackout, and energy waste can be independently invoked and produces a measurable deviation in the raw signal.

All 5 anomaly types triggerable

Each of drift, stoppage, latent defect, sensor blackout, and energy waste can be independently invoked and produces a measurable deviation in the raw signal.

Ground-truth labels populated | The separate ground-truth label table has a non-zero row count for every one of the 5 anomaly types after a full simulated run.

Ground-truth labels populated

The separate ground-truth label table has a non-zero row count for every one of the 5 anomaly types after a full simulated run.

If this gate fails: do not start Day 2. A broken simulator invalidates every metric computed downstream — fix the topology or anomaly generator first.

Day 2 Gate — SPC & Virtual Sensor Confidence

Validation Check | Pass Criteria

Validation Check

Pass Criteria

SPC false-positive rate | Low enough that a floor supervisor wouldn't drown in false alarms on the anomaly-free run — start near 5% as a working default, then tune the z-score threshold against your own run rather than treating 5% as a fixed target.

SPC false-positive rate

Low enough that a floor supervisor wouldn't drown in false alarms on the anomaly-free run — start near 5% as a working default, then tune the z-score threshold against your own run rather than treating 5% as a fixed target.

SPC catches drift early | An injected gradual-drift window is flagged meaningfully before it reaches full magnitude — report the actual point of detection rather than asserting a fixed 50% mark.

SPC catches drift early

An injected gradual-drift window is flagged meaningfully before it reaches full magnitude — report the actual point of detection rather than asserting a fixed 50% mark.

Confidence differentiation | Average confidence for manual-tier stations is consistently and visibly lower than rich-tier stations across a full run. There is no fixed point gap to hit — the actual gap will depend on your simulator's noise; the failure condition is manual-tier confidence being roughly equal to or higher than rich-tier confidence, which would mean the formula isn't using sensor tier at all.

Confidence differentiation

Average confidence for manual-tier stations is consistently and visibly lower than rich-tier stations across a full run. There is no fixed point gap to hit — the actual gap will depend on your simulator's noise; the failure condition is manual-tier confidence being roughly equal to or higher than rich-tier confidence, which would mean the formula isn't using sensor tier at all.

Imputation error check | Virtual-sensor imputation error, checked dev-only against the simulator's hidden true values, is measurably higher for manual stations than rich stations — report the actual numbers achieved, don't pre-decide them.

Imputation error check

Virtual-sensor imputation error, checked dev-only against the simulator's hidden true values, is measurably higher for manual stations than rich stations — report the actual numbers achieved, don't pre-decide them.

If this gate fails: do not proceed to model training on top of an SPC/confidence layer that isn't differentiating — the risk model will inherit and hide the bug.

Day 3 Gate — Risk Model & Propagation

Validation Check | Pass Criteria

Validation Check

Pass Criteria

No data leakage | The inference-time feature matrix excludes every ground-truth/anomaly label column — assert this by column-name check in code, not by eye.

No data leakage

The inference-time feature matrix excludes every ground-truth/anomaly label column — assert this by column-name check in code, not by eye.

Chronological split enforced | Train/test split is by simulated time (first 70% / last 30%), never a random row shuffle.

Chronological split enforced

Train/test split is by simulated time (first 70% / last 30%), never a random row shuffle.

Model quality vs. baseline | The trained model must beat two baselines you compute yourself on the same held-out window: (a) a majority-class / always-normal predictor, and (b) the Day 2 SPC-only score. Report the actual AUC, precision, and recall achieved — there is no fixed external target number to hit; the requirement is a real, measured improvement over your own baselines, not a specific score.

Model quality vs. baseline

The trained model must beat two baselines you compute yourself on the same held-out window: (a) a majority-class / always-normal predictor, and (b) the Day 2 SPC-only score. Report the actual AUC, precision, and recall achieved — there is no fixed external target number to hit; the requirement is a real, measured improvement over your own baselines, not a specific score.

Positive lead time | The average gap between alert-crossing time and actual event time shows the alert firing before the event — report this number explicitly, not just accuracy. If it's negative (detects only after the fact), that's an honest finding to fix, not to paper over.

Positive lead time

The average gap between alert-crossing time and actual event time shows the alert firing before the event — report this number explicitly, not just accuracy. If it's negative (detects only after the fact), that's an honest finding to fix, not to paper over.

Propagation countdown behaves correctly | For a known synthetic stoppage, downstream stations' time-to-impact decreases monotonically as the simulated clock advances toward the actual impact.

Propagation countdown behaves correctly

For a known synthetic stoppage, downstream stations' time-to-impact decreases monotonically as the simulated clock advances toward the actual impact.

If this gate fails: if the AUC/recall bar isn't met, don't hide it — fall back to a documented SPC-only risk score for that anomaly type and note it as a limitation, rather than shipping a model that doesn't actually predict anything.

Day 4 Gate — Recommendation Engine & API

Validation Check | Pass Criteria

Validation Check

Pass Criteria

API smoke tests | Every REST endpoint (Section 6) returns HTTP 200 with the documented JSON keys present, via a scripted smoke test.

API smoke tests

Every REST endpoint (Section 6) returns HTTP 200 with the documented JSON keys present, via a scripted smoke test.

WebSocket stream health | A test client receives at least N messages in T seconds with strictly increasing timestamps — no stalls, no out-of-order replay.

WebSocket stream health

A test client receives at least N messages in T seconds with strictly increasing timestamps — no stalls, no out-of-order replay.

Recommendation rules unit-tested | Each of the ~8–10 rules (Section 5.6) has a unit test that constructs the triggering state and asserts the expected action fires.

Recommendation rules unit-tested

Each of the ~8–10 rules (Section 5.6) has a unit test that constructs the triggering state and asserts the expected action fires.

Every recommendation carries required fields | condition matched, action, expected impact, and confidence are all non-empty on every recommendation returned.

Every recommendation carries required fields

condition matched, action, expected impact, and confidence are all non-empty on every recommendation returned.

If this gate fails: fix the contract before building the frontend against it — a shaky API on Day 4 becomes a far more expensive fix once the UI depends on its exact shape.

Day 5 Gate — Floor Supervisor View

Validation Check | Pass Criteria

Validation Check

Pass Criteria

Live color-change latency | Injecting a stoppage changes the affected station's color within 2 seconds, end to end.

Live color-change latency

Injecting a stoppage changes the affected station's color within 2 seconds, end to end.

Confidence visibly differs in UI | Clicking a rich-tier and a manual-tier station shows visibly different confidence values, consistent with the Day 2 gate.

Confidence visibly differs in UI

Clicking a rich-tier and a manual-tier station shows visibly different confidence values, consistent with the Day 2 gate.

No console errors over a full run | A full simulated hour of playback produces zero uncaught frontend errors.

No console errors over a full run

A full simulated hour of playback produces zero uncaught frontend errors.

If this gate fails: a laggy or visually-uniform demo undercuts the two things judges are meant to notice — live prediction and confidence-aware sensing — so this gate is worth protecting even at the cost of UI polish elsewhere.

Day 6 Gate — Leadership View & Integration

Validation Check | Pass Criteria

Validation Check

Pass Criteria

Cross-view consistency | Floor view and leadership view never disagree on the same underlying numbers during a full run.

Cross-view consistency

Floor view and leadership view never disagree on the same underlying numbers during a full run.

Numbers reconcile exactly | Leadership-view aggregates (e.g., downtime avoided) equal a fresh recomputation from stored logs, not a separately drifting counter.

Numbers reconcile exactly

Leadership-view aggregates (e.g., downtime avoided) equal a fresh recomputation from stored logs, not a separately drifting counter.

If this gate fails: do not paper over a reconciliation mismatch with a rounding excuse — it usually means one view is reading stale or duplicated data.

Day 7 Gate — Final Demo Readiness

Validation Check | Pass Criteria

Validation Check

Pass Criteria

Clean-environment install | A fresh clone, following only the README, installs and runs successfully with no undocumented manual steps.

Clean-environment install

A fresh clone, following only the README, installs and runs successfully with no undocumented manual steps.

Acceptance checklist complete | Every item in Section 11 is checked off with a specific timestamp/scene in the demo video it corresponds to.

Acceptance checklist complete

Every item in Section 11 is checked off with a specific timestamp/scene in the demo video it corresponds to.

Demo runtime | The recorded video is at or under 3 minutes.

Demo runtime

The recorded video is at or under 3 minutes.

If this gate fails: this is the one gate with no time left to recover from on submission day — treat Day 6 evening as the real deadline for everything above, and hold Day 7 for this checklist only.

17. Build Guardrails — Explicit Do's and Don'ts

Antigravity will make faster, more consistent decisions with hard constraints stated up front rather than discovered mid-build. Treat the following as non-negotiable unless a gate in Section 16 explicitly forces a documented deviation.

Don't | Do instead

Don't

Do instead

Shuffle rows randomly for the train/test split | Split chronologically — train on the first 70% of simulated time, test on the last 30% (Section 15)

Shuffle rows randomly for the train/test split

Split chronologically — train on the first 70% of simulated time, test on the last 30% (Section 15)

Include any ground-truth anomaly/label column in the live feature set | Keep ground-truth labels in a separate table used only for offline training and evaluation

Include any ground-truth anomaly/label column in the live feature set

Keep ground-truth labels in a separate table used only for offline training and evaluation

Hardcode a flat confidence value per sensor tier | Compute confidence from the formula in Section 5.2 so it moves with data recency and imputation agreement

Hardcode a flat confidence value per sensor tier

Compute confidence from the formula in Section 5.2 so it moves with data recency and imputation agreement

Simplify the 40-station line into a single straight chain “to make it easier” | Keep the parallel/buffer paths from Section 3.1 — they're what makes graph propagation, the core differentiator, meaningful

Simplify the 40-station line into a single straight chain “to make it easier”

Keep the parallel/buffer paths from Section 3.1 — they're what makes graph propagation, the core differentiator, meaningful

Implement “live” updates as frontend polling every second | Use genuine WebSocket push per Section 6 — “live” is part of what's being demonstrated

Implement “live” updates as frontend polling every second

Use genuine WebSocket push per Section 6 — “live” is part of what's being demonstrated

Let the recommendation engine generate actions freeform at runtime | Keep the rule table in Section 5.6 explicit and inspectable in code/config, so any firing rule can be pointed to and explained live

Let the recommendation engine generate actions freeform at runtime

Keep the rule table in Section 5.6 explicit and inspectable in code/config, so any firing rule can be pointed to and explained live

Silently change the 80/20 sensor ratio or the 40-station topology mid-build | Treat these as fixed parameters (Section 15); any change must be reflected back into every threshold and gate that depends on it

Silently change the 80/20 sensor ratio or the 40-station topology mid-build

Treat these as fixed parameters (Section 15); any change must be reflected back into every threshold and gate that depends on it

Move on to the next day's work when a gate fails | Fix the gate, or explicitly descope with a note in the README's Known Limitations — don't let a silent failure compound

Move on to the next day's work when a gate fails

Fix the gate, or explicitly descope with a note in the README's Known Limitations — don't let a silent failure compound

Introduce a new library/framework outside Section 8 without checking it installs cleanly first | Stick to the Section 8 stack; verify installation before writing code against a substitution

Introduce a new library/framework outside Section 8 without checking it installs cleanly first

Stick to the Section 8 stack; verify installation before writing code against a substitution

Report only overall accuracy for the risk model | Report precision/recall/AUC and lead-time-before-event (Section 16, Day 3) — accuracy alone hides whether the model detects anything before it happens

Report only overall accuracy for the risk model

Report precision/recall/AUC and lead-time-before-event (Section 16, Day 3) — accuracy alone hides whether the model detects anything before it happens

Hardcode a metric, confidence value, or expected-impact figure to make a gate in Section 16 pass | Compute and report the real number, even if it's unimpressive — a failing gate is information about a real bug; a faked gate hides that bug and undermines the whole prototype's credibility

Hardcode a metric, confidence value, or expected-impact figure to make a gate in Section 16 pass

Compute and report the real number, even if it's unimpressive — a failing gate is information about a real bug; a faked gate hides that bug and undermines the whole prototype's credibility

Tune the simulator itself until a model gate happens to pass | Fix the model/pipeline to genuinely perform better on the existing simulator; the simulator's job is to be a fair, fixed test bed, not a dial to adjust toward a target score

Tune the simulator itself until a model gate happens to pass

Fix the model/pipeline to genuinely perform better on the existing simulator; the simulator's job is to be a fair, fixed test bed, not a dial to adjust toward a target score