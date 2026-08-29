# Antigravity Master Prompt — Priority Punch List

## Status check first
Confirmed already done and independently verified (control group FP rate now 17.09%
vs. 18.14% for drifting stations, correct direction; `requirements.txt` pins
`scikit-learn==1.9.0` and the model loads cleanly with that version): the Phase 21
control-group contamination fix and the scikit-learn version pin. Don't redo these.

One process note going forward: keep validation/checkpoint scripts in the repo (don't
delete them after a phase is confirmed working) -- they're what let completion claims
get independently re-checked later. If a script needs cleanup for a cleaner-looking
repo, move it to a `scripts/validation/` subfolder rather than deleting it.

Work through everything below in order. After each numbered item, run `git log
--oneline -1` and `git status`, paste both, and paste the actual output of whatever
that item's checkpoint asks for -- not a summary, the raw output. Don't report an item
done without that evidence. If a checkpoint fails, stop and report what failed rather
than moving on.

---

## P0b — Backend-authoritative vehicle state

**This is the highest-priority item in the whole project.** Right now the frontend
independently simulates manufacturing state instead of just displaying it, which
causes visible, undeniable inconsistencies (e.g. a vehicle's station-visit counter
exceeding the actual number of stations on its route). A judge hitting this in the
first few minutes of a demo is a worse outcome than any backend metric being mediocre.

**The bug, precisely:** in `frontend/js/twin_scene.js`, when a vehicle leaves a
station, the frontend independently picks its own next branch at line ~661:
```javascript
const chosen = nextEdges[Math.floor(Math.random() * nextEdges.length)];
```
and separately increments its own counter:
```javascript
veh.visit_history_len = (veh.visit_history_len || 1) + 1;
```
which gets reset to `1` at ST40. Meanwhile the backend simulator has its own,
independent vehicle state and its own station-traversal logic. A later sync function
tries to reconcile the two by partially overwriting the frontend's counter with the
backend's value when available:
```javascript
if (vBackend.visit_history_len) {
  veh.visit_history_len = vBackend.visit_history_len;
}
```
This is a race, not a fix: the frontend can choose a different physical branch than
the backend chose for the same vehicle (e.g. frontend takes ST03, backend took ST04),
so a single vehicle's visual location, genealogy, station count, defect history, and
downstream propagation can end up describing genuinely different physical journeys.

**Also:** the line has branch points (multiple valid outgoing edges from some
stations), so not every vehicle visits all 40 physical stations on its route -- the
maximum unique stations on any single route is fewer than 40 (verify the exact number
from `simulator/topology.py`'s actual edge list, don't assume a specific number).
Displaying "visited / 40" is therefore conceptually wrong even before the sync bug --
it should be "visited / route_length" where `route_length` is specific to that
vehicle's actual route.

**The fix, in order:**
1. Remove ALL manufacturing-state decision logic from `frontend/js/twin_scene.js` --
   the `Math.random()` branch selection, the independent `visit_history_len`
   increment, the reset-at-ST40 logic. The frontend's only remaining job for vehicle
   movement is to interpolate a visual position along the conveyor path between
   whatever station state the backend reports. It must never decide which branch a
   vehicle takes, never independently count stations visited, never independently
   reset any counter.
2. Backend (`api/main.py` / `simulator/generator.py`) must emit, per vehicle, at
   minimum: `vin`, `current_station`, `previous_station`, `next_station`, `route_id`,
   `route_index` (this vehicle's position along its actual route), `route_length`
   (total stations on this vehicle's actual route, NOT a hardcoded 40),
   `visited_station_ids`. Verify which of these already exist and add what's missing.
3. Frontend renders `route_index / route_length` (e.g. "18 of 37 stations"), sourced
   entirely from the backend payload -- never a hardcoded `/ 40`.
4. Do NOT patch the visible symptom with something like `Math.min(count, 40)` -- that
   hides the divergence bug instead of fixing it. The fix must remove the frontend's
   independent decision-making, not cap its output.

### Validation Checkpoint P0b
Run a vehicle through a full route with the browser open. At 5+ points along the
route, query the backend API directly for that vehicle's `current_station` and
`visited_station_ids`, and compare against what's rendered in the browser. They must
match exactly at every checkpoint, not just usually. Also confirm the on-screen counter
never exceeds that specific vehicle's actual `route_length`.

---

## P0c — Applying a topology must not silently discard the trained model

In `api/main.py`, the apply-custom-topology and reset-topology endpoints (currently
around lines 916 and 949) each instantiate a fresh model directly:
```python
risk_model = RiskScoringModel()
```
This is an untrained model, and it silently replaces whatever trained model
`load_or_init_risk_model()` loaded at startup. Anyone who uses the topology editor
quietly downgrades the live system from the trained GBDT back to the untrained
heuristic fallback, with no indication anywhere in the UI that this happened.

**Fix:**
1. Change both call sites to call `load_or_init_risk_model()` (or equivalent) instead
   of instantiating `RiskScoringModel()` directly, so the trained artifact survives a
   topology change when the new topology is still compatible with it.
2. A topology change can genuinely change the feature space (different stations,
   different station types). Add an explicit compatibility check: if the new
   topology's station set materially differs from what the model was trained on,
   surface a visible status indicator in the UI (e.g. "Model status: retraining
   required") rather than silently falling back to the heuristic with no signal to the
   user.

### Validation Checkpoint P0c
Apply a custom topology via the editor, then immediately query the risk/predictions
endpoint and confirm the served scores still come from the trained GBDT (not the
untrained fallback) when the topology is compatible. Then apply a topology with a
materially different station set and confirm the visible status indicator appears.

---

## P1 — Highest score-improvement items (do after P0b/P0c)

**1. Make manual stations' sensor-poverty visibly real, not just modeled in the data.**
`pipeline/virtual_sensor.py`'s `VirtualSensorEngine` already estimates missing
telemetry from neighboring stations, shift baseline, and upstream flow, and computes a
disagreement score -- but check whether this is actually the primary, visible path a
manual station's UI card takes, or whether it's a secondary/fallback path that rarely
surfaces. For a manual station, the UI should show something like:
```
ST31
Sensor coverage: 35%
Estimated cycle time: 61.8s
Confidence: 71%
Missing: vibration, motor power, temperature
Why confidence is 71%: 3 upstream/downstream signals agree within 4.2%
```
If the UI currently just shows a "MANUAL" badge without this detail, build it out --
this makes the uneven-instrumentation story (which the data-generation layer already
models correctly, per the category-differentiated work done in earlier phases)
actually demonstrable on screen, not just present underneath.

**2. Build a prediction lead-time evaluation, using the simulator's own known ground
truth.** For every injected fault (scripted campaign or emergent wear-driven), record:
the tick it actually started (`actual_event_tick`, from the simulator's own ground-truth
anomaly log) and the tick of the model's first high-confidence prediction for that
station (`first_prediction_tick`). Compute `lead_time = actual_event_tick -
first_prediction_tick` for every such event, then report in aggregate: median lead
time, 90th-percentile lead time, false alarm rate, and miss rate. This is a stronger
validation claim than testing on another synthetic dataset generated from similar
assumptions, because it directly answers "does the model recover the simulator's own
known ground truth" rather than "does it generalize to more synthetic data" -- and it
reuses ground-truth anomaly logs that already exist from the OOD validation work.

**3. Reconcile every reported metric into one `docs/model_card.md`.** Numbers have
drifted across the README, `SCENARIO_VALIDATION_REPORT.md`, and various phase reports
over the course of this project. Before submission, produce one machine-readable model
card containing: dataset size, seed count, positive-event counts for both bottleneck
and defect targets, train/validation/test split sizes, full metrics for BOTH models
(ROC-AUC, PR-AUC, precision, recall, F1, Brier score -- never report only one model's
numbers), the full OOD regime table, and a calibration/reliability curve (a model
saying "80% risk" should correspond to roughly an 80% actual event frequency if that
number is meant to be read as a real probability). Point the README at this file
instead of quoting numbers inline that can drift out of sync again.

**4. Keep bottleneck and defect metrics separated everywhere**, not just in the OOD
script's latest table format -- audit every doc/endpoint that reports model
performance and make sure neither target's numbers are ever presented as if they
were the other's, or blended into one ambiguous number.

**5. Relabel feature-contribution output honestly.** `get_feature_contributions()`
compares an observed feature value against a hand-written baseline and a hand-written
weight -- it is a feature-deviation-based driver ranking, not SHAP, permutation
importance, counterfactual attribution, or genuine model-specific explanation. Don't
present it in the UI or docs as "AI explains the root cause." Relabel it "Risk
drivers" and describe it plainly as "feature-deviation based driver ranking" -- this
is more defensible under technical questioning and costs nothing to fix.

**6. Build a visible root-cause evidence chain, not just a ranked driver list.**
Currently the system surfaces individual elevated features (cycle time, vibration,
upstream starvation) ranked independently. A more convincing diagnostic presentation
chains them causally, e.g.:
```
ST17 vibration UP
  -> mechanical degradation suspected
    -> cycle time UP
      -> buffer depletion
        -> ST18 starvation predicted
```
with supporting evidence shown alongside (e.g. "Vibration: +42%, Cycle time: +18%,
Power: +11%, EWMA drift: 3.2 sigma, Upstream buffer: normal") and a stated likely cause
with confidence and a named alternative (e.g. "Likely cause: mechanical degradation
(86% confidence). Alternative: tool/process variation (9%)"). This moves the system
from "dashboard of numbers" to "diagnostic tool that constructs an argument," which is
a materially stronger demo moment.

---

## P2 — Enterprise-credibility items (only after P0/P1 are done)

**1. Add a thin OT-adapter abstraction layer**, even though there's no real PLC/OPC-UA
source to connect to. Structure it as:
```
simulator/  ->  ot_adapter/simulator_adapter.py  ->  digital twin ingestion
                 ot_adapter/opcua_adapter.py   (stub, clearly marked future work)
                 ot_adapter/mqtt_adapter.py    (stub, clearly marked future work)
```
The point isn't to build a working OPC-UA/MQTT integration -- it's to prove the
simulator is replaceable by a real physical data source, by making that seam an
explicit, named interface rather than the simulator feeding FastAPI directly with no
abstraction in between.

**2. Add a "prediction -> intervention -> measured outcome" demo sequence.** You
already have risk prediction, propagation, and recommendations -- close the loop and
make it visible: show a predicted value (e.g. "ST20 bottleneck in 7.4 min"), let the
user trigger a mitigating action, re-run the prediction, and show the measurable
result (e.g. "Avoided downtime: 6.7 min. Vehicles protected: 5."). This demonstrates
prediction coupled to a production-control decision with a measured outcome, not just
prediction displayed as a static card -- likely your strongest possible demo moment
given everything else already built.

**3. Fix the CSS scroll-container structure.** Currently multiple nested containers
set `overflow: hidden` (`body`, `.main-viewport`, `.workspace-floor`), with only one
inner `.schematic-viewport` set to `overflow: auto`, inside a schematic canvas
hardcoded to a fixed `2900px x 1280px`. This is reasonable for a desktop HMI at large
resolutions but breaks on a smaller laptop screen or at higher browser zoom -- there's
no way to reach content that overflows the fixed viewport.

Do NOT make the entire application freely scroll -- that would make it feel like a
generic website instead of a plant-control application. Instead: keep one fixed outer
HMI shell (header, nav, cockpit panels), but make exactly ONE scroll container
authoritative for the factory canvas itself:
```css
.workspace-floor,
.schematic-housing,
.schematic-viewport {
  min-height: 0;
}
```
applied wherever needed in the flex chain so nested `overflow: hidden` containers stop
swallowing the scroll context before it reaches the canvas. On smaller screens, switch
to a responsive layout where the cockpit becomes a drawer, the fault injector panel
becomes collapsible, and the factory canvas gets explicit scroll with no important
content living outside the scroll container. Test at 1366x768, 1440x900, 1920x1080,
and at 125%/150% browser zoom before calling this done -- don't assume it works at
sizes you haven't actually checked.

---

## P3 — Explicitly do not do yet
Do not touch general UI polish (animations, typography, tooltip positioning, card
density, micro-interactions, loading/error states) until everything above is done and
independently verified. The current visual design is already solid; further polish
has low marginal value compared to the internal-consistency issues above, and a judge
is far more likely to be swayed by "this system is internally truthful" than by
additional visual refinement.
