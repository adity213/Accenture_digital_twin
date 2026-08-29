# Antigravity Master Implementation Plan v8
## DigitalTwin.ai, P1/P2 Completion + Integrity Hardening

## Operating Rules

Before beginning:

1. Do **not** revisit the already-verified Phase 21 control-group contamination fix or scikit-learn pin unless a new regression is discovered.
2. Work strictly in the order below.
3. After **every numbered item**, run:
   ```bash
   git log --oneline -1
   git status --short
   ```
   and paste the raw output.
4. For every verification checkpoint, paste the actual command and raw output. Do not summarize.
5. If a checkpoint fails, **stop at that item** and report the failure. Do not continue.
6. Do not modify validation thresholds solely to make a checkpoint pass.
7. Do not delete validation/checkpoint scripts. Store persistent validation scripts under `scripts/validation/`.
8. Do not add general UI polish until all P0/P1 items and their checkpoints pass.
9. Preserve the existing 40-station topology and current simulator behavior unless a change is explicitly required below.

---

# P0.0: Establish the Current Baseline

## Objective

Before changing code, capture the current state so every subsequent change is auditable.

## Required checks

Run:

```bash
git log --oneline -5
git status --short
```

Then verify:

```bash
python --version
python -c "import sklearn; print(sklearn.__version__)"
```

Run the current available validation suite relevant to:

- model loading
- Phase 21 control-group integrity
- scenario/OOD validation
- Phase 25 routing/latency

Record the baseline results.

Also inspect and report:

- current HEAD SHA
- current model artifact path
- current requirements file
- which validation scripts currently exist
- current frontend asset cache versions

Do not modify anything during this step.

### Checkpoint

Paste the raw command output.

After the item:

```bash
git log --oneline -1
git status --short
```

---

# P0.1: Backend-Authoritative Vehicle State

## Objective

The backend simulator must be the **single source of truth for manufacturing state**.

The frontend must become a visualization/interpolation layer.

The current problem is that `frontend/js/twin_scene.js` still independently makes manufacturing-state decisions, including route progression and station transitions. The simulator backend performs its own queue-aware dynamic routing, so two independent state machines can diverge.

This must be eliminated.

## A. Backend Vehicle State

Verify and expose, for every active vehicle:

```text
vin
current_station
previous_station
next_station
route_id
route_index
visited_station_ids
route_length_estimate
route_length
```

Where useful, also expose:

```text
progress
state
```

## B. Actual Realized Route

Do **not** calculate a vehicle's final `route_length` by simply taking the graph-theoretic shortest path.

The simulator uses dynamic queue/load balancing.

Therefore maintain an ordered realized route for every vehicle, conceptually:

```python
route_station_ids = [...]
```

When the backend makes a routing decision at a branch, append the station that was actually selected.

Then:

```text
route_index = position in the vehicle's realized route
route_length = length of the realized route once that route is fully known
```

While the future route is not known, expose:

```text
route_length_estimate
```

rather than pretending a shortest-path number is the final route length.

## C. Canonical Backend Vehicle Serializer

Create one backend function, such as:

```python
serialize_vehicle_state(vdata)
```

All relevant endpoints and WebSocket payloads must use it.

Do not independently reconstruct route metadata in:

- `/api/stations`
- WebSocket payload construction
- `/api/vehicles/recent`
- genealogy-related responses where vehicle state is exposed

This prevents backend-side semantic drift.

## D. Frontend State Ownership

Remove **all manufacturing-state decision logic** from `frontend/js/twin_scene.js`.

In particular, remove from vehicle progression logic:

```javascript
Math.random()
```

or any other frontend branch choice.

Do not use:

```javascript
downstream_ids[0]
```

as an authoritative next-station decision.

Remove any frontend-generated manufacturing transition that changes:

```text
fromStation
toStation
state
```

because a visual dwell timer expired.

Remove:

```text
visit_history_len += 1
```

or equivalent independently maintained visit counters.

Remove reset-at-ST40 or equivalent frontend traversal reset logic.

The frontend may maintain temporary interpolation state needed to animate a vehicle between two backend-reported stations, but that state must never determine the next manufacturing state.

## E. Backend-Driven Visual Transitions

When the backend reports:

```text
ST20 -> ST21
```

the frontend should animate:

```text
ST20 -> ST21
```

It must not first decide:

```text
ST20 -> some locally chosen station
```

and then wait for backend correction.

Backend state drives the transition.

## P0.1 Validation Checkpoint

Run a controlled vehicle through a full route with the browser open.

Test every actual branch point in the topology.

At a minimum, include 10 checkpoints covering:

- normal linear transition
- branch decision
- branch exit
- manual station
- stalled station
- queued vehicle behind occupied station
- defect-bearing vehicle
- near-terminal vehicle
- terminal completion
- new vehicle spawn

At every checkpoint compare:

```text
Backend current_station
Frontend displayed current station

Backend visited_station_ids
Frontend displayed route/genealogy information

Backend route_index
Frontend displayed route index
```

They must match exactly.

Also deliberately create at least two branch situations in which queue lengths differ so that the backend selects different downstream branches. Confirm the frontend follows the backend-selected branch.

Confirm the displayed traversal count never exceeds the vehicle's actual realized route length.

Do not accept "usually matches." The frontend must deterministically reflect backend state.

After the item:

```bash
git log --oneline -1
git status --short
```

---

# P0.2: Topology Changes Must Not Silently Discard the Trained Model

## Objective

Changing the topology must never silently replace the trained model with an untrained model or serve an incompatible model without warning.

The current implementation has already moved toward using `load_or_init_risk_model()`, but station-ID equality by itself is insufficient for model compatibility.

## A. Preserve the Trained Artifact

Both topology apply and topology reset must load/preserve the trained model artifact rather than directly instantiating a blank:

```python
RiskScoringModel()
```

unless an explicit compatibility failure requires a fallback.

## B. Model Compatibility Fingerprint

Create a compatibility descriptor containing at least:

```text
model version
feature schema/version
station IDs
station types
sensor tiers
zone assignments
relevant topology/schema version
```

Store this metadata with the trained model or in a companion artifact.

Do not assume:

```text
same station IDs = same feature semantics
```

A topology can retain station IDs while changing station types, zones, sensor tiers, targets, or other feature semantics.

## C. Explicit Serving State

Expose model state consistently through the backend/UI, such as:

```text
MODEL ACTIVE
MODEL FALLBACK
RETRAINING REQUIRED
```

Also expose the serving mode where appropriate.

If topology compatibility fails, visibly report:

```text
Model status: retraining required
```

Never silently downgrade to a heuristic path.

## D. Topology Validation

Before applying a topology, validate at minimum:

```text
valid station identifiers
valid edges
no cycles
no orphan/unreachable stations
valid entry node(s)
valid terminal node(s)
```

For branch points, where practical, also calculate:

```text
nominal downstream path processing time
branch bottleneck capacity
```

Do not block this P0 item on sophisticated optimization.

## P0.2 Validation Checkpoint

1. Apply a topology compatible with the trained model.
2. Query the model/risk endpoint.
3. Confirm the response indicates trained-model serving.
4. Apply a topology with a materially different station set and/or incompatible feature semantics.
5. Confirm a visible `retraining required` state.
6. Confirm the system does not silently present heuristic fallback results as trained GBDT results.

After the item:

```bash
git log --oneline -1
git status --short
```

---

# P1.1: Make Manual-Station Sensor Poverty Real and Visible

## Objective

Make the uneven instrumentation requirement visibly demonstrable in the actual operating path, not merely present in the synthetic data.

The existing `VirtualSensorEngine` estimates missing telemetry using:

- neighboring stations
- shift baseline
- upstream/downstream flow
- disagreement between estimates

Use that actual engine output.

## Required UI Behavior

For a genuine manual station, show information such as:

```text
ST31

Sensor coverage
35%

Cycle time
61.8 s (estimated)

Confidence
71%

Missing telemetry
Vibration
Motor power
Temperature

Inference basis
Neighbor agreement: 3 signals
Disagreement: 4.2%
```

Clearly distinguish:

```text
Measured
```

from:

```text
Estimated
```

Do not represent imputed values as physical measurements.

## Backend-to-UI Integrity

Verify the displayed estimate and confidence come from the backend's actual `VirtualSensorEngine` output.

Do not create a duplicate frontend-only virtual sensor calculation.

## P1.1 Validation Checkpoint

For a manual station:

1. Capture the backend telemetry payload.
2. Confirm physical sensor fields are missing where expected.
3. Confirm `VirtualSensorEngine` output exists.
4. Confirm the UI displays the same estimate/confidence.
5. Perturb an upstream input used by the virtual sensor.
6. Confirm the inferred value changes.
7. Confirm estimated and measured fields remain visually distinguishable.

After the item:

```bash
git log --oneline -1
git status --short
```

---

# P1.2: Build a Real Prediction Lead-Time Evaluation

## Objective

Measure whether the **actual served system** predicts simulator events early.

Do not evaluate only raw GBDT probability.

The serving path includes:

```text
ML model
+
deterministic baseline
+
sensor confidence
+
model/baseline divergence
+
fallback routing
```

Therefore evaluate the same serving decision logic used by the application.

## Required Validation Script

Create:

```text
scripts/validation/evaluate_lead_time.py
```

For every scripted or emergent event, record:

```text
anomaly_type
station_id
actual_event_tick
first_prediction_tick
serving_mode
served_risk
raw_ml_risk
sensor_confidence
divergence
threshold
```

## Prediction Definition

Do not count a one-tick probability spike as a meaningful prediction.

Use an explicit alert condition, for example:

```text
served risk >= alert threshold
for K consecutive ticks
```

Choose and document `K`.

Alternatively, use the system's actual alert-state transition if that is the true production logic.

## Metrics

Report:

```text
median lead time
P90 lead time
miss rate
false alarm rate
```

Break down by anomaly type:

```text
gradual drift
sudden stoppage
emergent wear
latent defect
energy anomaly
```

Also report:

```text
overall
```

Where useful, distinguish:

```text
raw ML lead time
served-system lead time
```

The latter is the one that matters operationally.

## P1.2 Validation Checkpoint

The script must produce raw output containing:

```text
number of events
number detected
number missed
median lead time
P90 lead time
false alarm rate
per-anomaly-type results
```

The script must use the same decision/routing semantics as the actual application.

Do not change thresholds merely to improve reported lead time.

After the item:

```bash
git log --oneline -1
git status --short
```

---

# P1.3: Investigate the Defect Model's Spatial-OOD Failure

## Objective

The previous benchmark indicated a major difference between the bottleneck and defect models.

The earlier reported spatial-OOD result included approximately:

```text
Defect IID ROC-AUC:       0.776
Defect Spatial ROC-AUC:   0.483
Defect Spatial Recall:    0%
```

This must not be ignored.

Do not remove or weaken the spatial-OOD benchmark.

## Required Investigation

Compare train versus spatial-OOD distributions for:

```text
all features
station type
zone
sensor tier
station identifier encoding
defect prevalence
defect mechanism
inspection station
```

Investigate potential station-specific confounding or leakage through:

```text
station ID
zone code
station type
sensor tier
defect-generation mechanism
inspection placement
```

Determine whether the failure is:

```text
true spatial generalization failure
label-generation artifact
feature leakage
target/base-rate structure
feature distribution shift
```

or a combination.

## Required Output

First produce a written diagnosis.

Only then implement a fix if one is scientifically defensible.

Preferred fixes should improve station-invariant physical/process generalization rather than simply making the held-out test easier.

Do not solve the problem by training on the spatial test stations.

## P1.3 Validation Checkpoint

Report:

```text
before
after
reason for change
```

for at least:

```text
ROC-AUC
PR-AUC
recall
```

for both IID and spatial-OOD defect evaluation.

Explicitly state whether spatial generalization improved.

After the item:

```bash
git log --oneline -1
git status --short
```

---

# P1.4: Audit and Define False-Positive Measurement

## Objective

Lock down exactly what the reported false-positive rate means.

The independently observed Phase 21 result is approximately:

```text
Control FPR: 17.09%
Drifting FPR: 18.14%
```

Do not optimize this number before defining its measurement unit.

## Required Analysis

State explicitly whether FPR is measured at the level of:

```text
prediction tick
station episode
alert
vehicle event
anomaly window
```

For the final product narrative, prefer an operational alert/episode-level definition over raw per-tick counting where appropriate.

Report:

```text
TP
FP
TN
FN
positive prevalence
FPR
precision
recall
```

Break down by station category:

```text
automated precision
automated process
manual
```

Investigate whether:

```text
sensor confidence
manual variance
station category
SPC behavior
```

are systematically driving false positives.

Do not blindly lower the prediction threshold.

## P1.4 Validation Checkpoint

Provide the raw calculation and denominator definition.

Show category-level confusion statistics and score distributions.

After the item:

```bash
git log --oneline -1
git status --short
```

---

# P1.5: Create a Single Canonical Model Card

## Objective

Create one canonical source of model-validation numbers.

Create:

```text
data/model_card.json
docs/model_card.md
```

`model_card.json` is the canonical numerical source.

`model_card.md` is the human-readable presentation.

## Required Contents

Include:

```text
dataset size
seed count
positive-event counts for bottleneck target
positive-event counts for defect target
train/validation/test split sizes
```

For the **Bottleneck** model:

```text
ROC-AUC
PR-AUC
precision
recall
F1
Brier score
```

For the **Defect** model:

```text
ROC-AUC
PR-AUC
precision
recall
F1
Brier score
```

Also include:

```text
full OOD regime table
FPR definition
calibration/reliability information
model version
feature schema version
```

Generate calibration/reliability information from held-out predictions rather than manually transcribing summary numbers.

A reported risk of "80%" should only be described as a probability if calibration supports interpreting it that way.

README should point to the model card instead of duplicating mutable metrics.

## P1.5 Validation Checkpoint

Verify that:

```text
data/model_card.json
docs/model_card.md
```

agree on every reported metric.

Verify both bottleneck and defect targets are explicitly represented.

After the item:

```bash
git log --oneline -1
git status --short
```

---

# P1.6: Rename Risk Explanations Honestly

## Objective

Make the current feature contribution presentation technically defensible.

Rename:

```text
AI Root Cause
```

to:

```text
Risk Drivers
```

Describe the method as:

```text
feature-deviation based driver ranking
```

Do not describe it as:

```text
SHAP
permutation importance
counterfactual attribution
causal explanation
confirmed root cause
```

unless a genuine method supporting those claims is implemented.

The current implementation compares features against hand-written baselines and weights, so it should be represented accordingly.

## P1.6 Validation Checkpoint

Audit all UI and documentation references to the existing root-cause wording.

Confirm terminology is consistent across:

- station detail UI
- recommendation UI
- API field descriptions
- README
- technical documentation

After the item:

```bash
git log --oneline -1
git status --short
```

---

# P1.7: Build a Diagnostic Evidence Chain

## Objective

Upgrade the current flat driver list into a structured diagnostic argument without falsely claiming causal proof.

Use a presentation such as:

```text
Vibration ↑
    ↓
Mechanical degradation suspected
    ↓
Cycle time ↑
    ↓
Buffer depletion
    ↓
Downstream starvation predicted
```

Surface supporting evidence such as:

```text
Vibration
Cycle time
Power
SPC/EWMA
Buffer level
Upstream risk
```

Then present:

```text
Likely mechanism
Confidence
Alternative explanation
```

Use terms such as:

```text
Likely mechanism
Diagnostic evidence
```

rather than:

```text
Confirmed root cause
```

unless the evidence truly supports that statement.

## P1.7 Validation Checkpoint

Verify that every displayed value in the evidence chain comes from actual backend state/model outputs.

Do not hardcode example percentages as if they were live calculations.

After the item:

```bash
git log --oneline -1
git status --short
```

---

# INTERMEDIATE GATE: Economics and Unit-Consistency Audit

## Objective

Before implementing the intervention demo, audit every existing economic and downtime quantity.

Trace:

```text
downtime_avoided_min
downtime_avoided_hours
cost_savings_usd
cumulative_downtime_avoided_min
jobs_per_hour
```

through:

```text
recommendation generation
aggregation
API payload
frontend display
```

Check every conversion between:

```text
seconds
minutes
hours
```

and verify units algebraically.

Do not build the intervention demo on top of an incorrect economic KPI.

## Required Validation

Create a deterministic unit test or equivalent validation case with known inputs:

```text
known recommendation
known avoided minutes
expected avoided hours
expected dollar savings
```

Verify the API and UI reflect the same values.

After the gate:

```bash
git log --oneline -1
git status --short
```

---

# P2.1: Prediction → Operational Intervention → Measured Outcome

## Objective

Close the loop between prediction and action without artificially forcing the risk score downward.

## Critical Constraint

Do **not** implement:

```text
click intervention
→ directly reduce risk score
```

Do not clear or modify a state solely because that makes the risk number look better.

The intervention must modify an operational simulator variable and allow the twin to observe the resulting consequences naturally.

## Valid Intervention Examples

### Maintenance

```text
schedule maintenance
→ wear state changes after maintenance
→ cycle time improves
→ risk changes naturally
```

### Release-Rate Control

```text
reduce upstream release rate
→ inflow changes
→ buffer depletion changes
→ starvation forecast changes
```

### Branch Rebalancing

```text
reroute/rebalance flow
→ queue distribution changes
→ downstream risk changes
```

## Counterfactual Requirement

For any intervention demo, maintain two scenarios:

```text
WORLD A
No intervention
→ resulting trajectory
→ resulting downtime/event

WORLD B
Intervention
→ resulting trajectory
→ resulting downtime/event
```

Then derive:

```text
estimated avoided downtime
vehicles protected
```

from the actual difference.

Do not claim "avoided downtime" without a counterfactual baseline.

## P2.1 Validation Checkpoint

Demonstrate one complete scenario:

```text
prediction
→ recommended action
→ operator triggers action
→ simulator state changes
→ telemetry changes
→ prediction changes
→ measurable outcome
```

The post-intervention improvement must arise from the simulator's changed operational state, not from directly editing the risk number.

After the item:

```bash
git log --oneline -1
git status --short
```

---

# P2.2: Intervention Audit Trail

## Objective

Make the intervention itself traceable.

Every intervention should receive a unique ID and log at least:

```text
intervention_id
station_id
trigger risk
action
operator
before state
after state
predicted impact
observed simulated outcome
timestamp
```

Reuse existing recommendation/override infrastructure where practical.

The UI should be able to show:

```text
Prediction
→ Action
→ Outcome
```

rather than only:

```text
Recommendation
→ green number
```

## P2.2 Validation Checkpoint

Verify that a triggered intervention produces a persistent, queryable record.

Verify before/after simulator state is recorded.

Verify predicted versus observed outcome can be compared.

After the item:

```bash
git log --oneline -1
git status --short
```

---

# P2.3: Thin Telemetry-Source Abstraction

## Objective

Demonstrate that the simulator can eventually be replaced by a physical data source without pretending that a real PLC/MQTT/OPC-UA integration has been built.

Keep this abstraction thin.

A suitable structure is conceptually:

```text
telemetry_source/
    simulator_source.py
    opcua_source.py
    mqtt_source.py
```

or an equivalent interface.

The simulator source should be the only fully working implementation.

OPC-UA and MQTT should be clearly documented stubs/future work.

The important seam is:

```text
TelemetrySource
    ↓
Twin ingestion
```

rather than:

```text
API directly coupled to simulator internals
```

Do not create a huge abstraction layer that merely mirrors dozens of simulator methods.

## P2.3 Validation Checkpoint

Start the application using the simulator source.

Verify the twin produces the same essential telemetry/prediction behavior through the abstraction layer.

Verify the API no longer depends on simulator implementation details where the new abstraction is intended to sit.

After the item:

```bash
git log --oneline -1
git status --short
```

---

# P2.4: Fix the Scroll-Container Architecture

## Objective

Keep the application feeling like an industrial HMI while making the actual factory canvas usable at smaller screen sizes and higher browser zoom.

Do **not** turn the entire application into a generic vertically scrolling webpage.

## Required Structure

Keep the outer HMI shell fixed.

Make exactly one authoritative scroll container for the factory canvas.

Audit the interaction among:

```text
body
.app-layout
.main-viewport
.view-panel
.workspace-floor
.schematic-housing
.schematic-viewport
living-line-stage
```

Ensure flex parents allow the intended scroll container to shrink, using `min-height: 0` where required.

On smaller viewports:

```text
cockpit → drawer
fault injector → collapsible section
factory canvas → explicit horizontal/vertical scroll
```

No important content should live outside a reachable scroll context.

## Validation Checkpoint

Test at:

```text
1366 × 768
1440 × 900
1920 × 1080
```

and at:

```text
100% browser zoom
125% browser zoom
150% browser zoom
```

Verify:

- factory canvas is reachable
- cockpit controls are reachable
- station details are reachable
- no critical content is clipped
- no accidental page-level horizontal overflow
- no nested scroll trap prevents reaching content
- the HMI shell remains visually stable

After the item:

```bash
git log --oneline -1
git status --short
```

---

# P3: Explicitly Defer General UI Polish

Do **not** work on these until all P0/P1 items and checkpoints pass:

```text
general animation polish
typography redesign
new decorative gradients
micro-interactions
extra dashboards
card density refinements
tooltip cosmetics
loading/error visual polish
```

The current visual system is already strong enough for the competition prototype.

The priority is internal truthfulness and technical credibility.

---

# Final Submission Acceptance Criteria

Before declaring the submission ready, verify all of the following.

## Vehicle Truth

```text
Backend selects route
        ↓
Backend state is streamed
        ↓
Frontend visualizes/interpolates route
```

There must be:

- no frontend branch selection
- no frontend genealogy
- no impossible traversal counters
- no backend/frontend vehicle-state contradiction

## Model Truth

```text
Bottleneck metrics separate
Defect metrics separate
Spatial-OOD retained
FPR definition explicit
Model card canonical
```

## Sensor Truth

```text
Measured ≠ Estimated
```

Manual stations must visibly use virtual sensing.

## Prediction Truth

```text
Prediction
    ↓
Actual event
    ↓
Measured lead time
```

Lead-time methodology must use the served system's decision logic.

## Intervention Truth

```text
Prediction
    ↓
Operational action
    ↓
Simulator state changes
    ↓
Measured consequence
```

No artificial reduction of risk scores.

## Topology Truth

```text
Topology change
    ↓
Compatibility check
    ↓
Trained model preserved
OR
Retraining required clearly shown
```

## UI Truth

```text
No 53/40
No backend/frontend state divergence
No clipped critical information
```

---

# Final Execution Order

Execute exactly in this order:

```text
P0.0  Baseline
  ↓
P0.1  Backend-authoritative vehicles
  ↓
P0.2  Topology/model compatibility
  ↓
P1.1  Manual virtual sensing UI
  ↓
P1.2  Prediction lead-time evaluation
  ↓
P1.3  Defect spatial-OOD investigation
  ↓
P1.4  False-positive measurement audit
  ↓
P1.5  Canonical model card
  ↓
P1.6  Risk-driver relabel
  ↓
P1.7  Diagnostic evidence chain
  ↓
Economics / unit-consistency audit
  ↓
P2.1  Prediction → intervention → outcome
  ↓
P2.2  Intervention audit trail
  ↓
P2.3  Telemetry-source abstraction
  ↓
P2.4  Scroll/responsive behavior
  ↓
Final end-to-end demo validation
```

## Final Principle

Throughout implementation, preserve these three rules:

```text
1. Do not fake causality.
2. Do not fake counterfactual outcomes.
3. Do not evaluate raw model output when the actual product serves a routed/fallback decision.
```

The goal is not merely to make the dashboard look convincing.

The goal is to make the **digital twin internally truthful, auditable, and demonstrably useful**.
