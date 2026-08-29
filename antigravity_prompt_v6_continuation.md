# Antigravity Task Prompt v6 — Phases 20-25 (Continuation)

## Confirmed current state (independently verified, not just self-reported)
Commit `e347c59` on `main`. Phases 17, 18, 19 are done and independently reproduced:
- Phase 17: shared `load_state` (AR(1)) drives vibration/temp/power — lag-1 autocorrelation
  0.63, vibration-temperature correlation 0.65+, confirmed real by rerunning
  `scripts/validate_phase17.py`.
- Phase 18: lognormal cycle time replacing hard-clipped Gaussian, coupled to `load_state`
  via `load_ct_mult` — confirmed by rerunning `scripts/validate_phase18.py`.
- Phase 19: three station categories (`automated_precision`/`automated_process`/`manual`)
  with differentiated CV (0.04/0.06/0.13) and defect-rate multipliers (0.6x/1.0x/2.8x) —
  confirmed by rerunning `scripts/validate_phase19.py`; manual-station skewness (0.475)
  clearly distinct from automated (0.040), with a real 1.9% tail beyond 1.3x target.

Same working rules as every prior prompt in this project: work phases in order, don't
start the next phase until the current Validation Checkpoint passes with real pasted
output, read a file before editing it, stop and report mismatches rather than guessing.

**New reference material for this round**: a related open-source project
(`jaehyeon-kim/oml-digital-twin-hotrolling`, a hot-strip-mill digital twin with online
concept-drift learning) contributed two design patterns folded into Phases 21 and 25
below — a no-drift "control group" subset for testing false-positive behavior, and a
residual-learning + shadow-mode-router architecture for the serving layer. Both are
referenced explicitly where they apply; you don't need to fetch that repo, the relevant
patterns are fully specified below.

---

## PHASE 20 — Anomaly-type-specific signal effect profiles

(Unchanged from the original spec — reproduced here for continuity since this is a new
file.)

Read `simulator/anomalies.py` first to see current effect fields, then define an
explicit per-type physical signature instead of the current blanket
`ct_multiplier > 1.2` check driving vibration for every anomaly type:

- `gradual_drift`: vibration rises, temperature rises modestly, power rises modestly —
  the one type where current coupled behavior is roughly right, keep it.
- `sudden_stoppage`: vibration drops toward ~0, power drops (verify existing
  `is_stopped` handling already does this correctly, don't rebuild if so).
- `latent_defect`: **should produce ~no telemetry signal at all** — physically correct
  (a latent defect isn't caught by real-time sensors, that's the whole point), and a
  genuine strength for your write-up. Remove any `cycle_time_multiplier` coupling this
  anomaly type currently has, if it has one.
- `sensor_blackout`: data-availability mechanism only, no change to underlying physics.
- `energy_waste`: power rises via `power_multiplier` (already exists), vibration/temp
  should NOT move — remove this type from whatever blanket vibration-bump condition
  currently sweeps it in.

### ✅ Validation Checkpoint 20
Inject each of the 5 anomaly types on a test station individually, run 30 ticks each,
report observed vibration/temperature/power delta from baseline per type. Confirm
`latent_defect` shows ~no change, `energy_waste` shows power change but ~no vibration
change, `gradual_drift`/`sudden_stoppage` behave as described. Paste actual numbers.

---

## PHASE 21 — Emergent wear/health model, with a no-drift control group and a strict no-leakage guarantee

**Wear state**, added alongside `load_state`:
```python
self.wear_state: Dict[str, float] = {
    sid: self.rng.uniform(0.0, 0.15) for sid in self.stations
}
```

**No-drift control group (new — borrowed from the hot-rolling reference project's
pattern of holding one product line at permanent zero wear velocity):** designate 3-4
stations, spread across your three categories (at least one `automated_precision`, one
`automated_process`, one `manual`), as permanent controls:
```python
NO_DRIFT_CONTROL_STATIONS = {"ST0X", "ST1X", "ST3X"}  # pick specific IDs, document which and why
```
For these stations, `wear_state` never increases — set their `base_wear_rate` to `0.0`
regardless of category. This is a deliberate scientific control, not an optimization: it
lets you later prove the model doesn't spuriously raise risk on equipment that's
genuinely fine, which is a distinct and important claim from "it catches real drift."

For all other stations, increase wear slowly each tick:
```python
base_wear_rate = {"automated_precision": 0.00015, "automated_process": 0.00020, "manual": 0.00025}[category]
shock = 0.02 if self.rng.random() < 0.0008 else 0.0
self.wear_state[sid] = min(1.2, self.wear_state[sid] + base_wear_rate * (1 + max(0, self.load_state[sid])) + shock)
```
Tune rate constants by running a long simulation and checking failure frequency lands
somewhere plausible (a handful of failures over several thousand ticks, not zero and not
constant) — iterate, don't just pick numbers and assume.

**Unscheduled failure trigger:** when `wear_state[sid] > 0.85` (never true for control
stations by construction), apply a per-tick probability of triggering a new ground-truth
anomaly category `"unscheduled_failure"` in `simulator/anomalies.py`, with its own
Phase-20-style signal profile (organic version of `gradual_drift`/`sudden_stoppage`,
your call), logged under the distinct `true_anomaly_type` so it's auditable separately
from scripted campaign events. Must emit through the same ground-truth logging mechanism
existing anomaly types use, so `scripts/generate_training_data.py`'s labeling pass (which
reads `is_stopped`/`ct_ratio`/`defect_flag`, not anomaly type) needs zero changes.

**Maintenance windows:** per your problem statement's reference parameter, add a
periodic maintenance event (e.g. once per simulated week — pick and document the
mapping) that resets `wear_state` for stations above some threshold back toward a low
value (partial service is realistic, doesn't need to be a hard reset to 0).

**Strict no-leakage guarantee (new — explicit checkpoint, not just an assumption):**
`wear_state` and `load_state` must NEVER appear directly in
`pipeline/risk_model.py`'s feature list. The model should only ever see their *physical
symptoms* (vibration, cycle time, temperature, defect flags) — never the ground-truth
latent state itself. This mirrors the reference project's explicit design principle
("hidden state variables are strictly excluded... so the algorithm cannot cheat").

**Do not let this overwhelm the balanced campaign coverage** from
`simulator/anomaly_campaign.py` — campaigns remain the primary, guaranteed-coverage
mechanism; emergent wear failures are additive, lower-frequency, organic texture on top.

**New OOD regime:** add "Emergent Wear-Driven Failures" as a 7th scenario to
`scripts/generate_scenario_datasets.py` / `scripts/evaluate_scenario_validation.py` —
disable/minimize the scripted campaign, rely on the wear model, and test whether a model
trained mostly on scripted patterns generalizes to organically-emerging ones (which ramp
up more gradually and unpredictably than a scripted injection with crisp edges).

### ✅ Validation Checkpoint 21
1. Run ~8000+ ticks with both campaign and emergent wear active. Report: how many
   `unscheduled_failure` events occurred, across how many distinct stations, and how many
   maintenance resets fired.
2. **Negative checkpoint (must explicitly pass, not just be assumed):** run
   `grep -n "wear_state\|load_state" pipeline/risk_model.py` and confirm neither appears
   in the feature extraction / `FEATURE_NAMES` list. If either does, this is a leakage
   bug — fix before continuing.
3. **Control-group false-positive check:** using a freshly retrained model (or the
   existing one if Phase 23 hasn't rerun yet), measure the bottleneck/defect false-
   positive rate specifically on ticks belonging to the `NO_DRIFT_CONTROL_STATIONS`, and
   compare it to the false-positive rate on regular (drifting) stations over the same
   window. The control group's rate should be low and should NOT be meaningfully higher
   than normal — if the model is flagging risk on stations that never actually degrade,
   that's a real problem worth reporting, not glossing over.
4. Re-run the Phase 1-style bias audit and confirm no subgroup's coverage collapsed.
5. Run the new OOD regime, report its metrics alongside the other 6 in
   `docs/SCENARIO_VALIDATION_REPORT.md`.

---

## PHASE 22 — SPC recalibration (do not skip)

`pipeline/spc.py`'s flat "4% of target" control limit is now actively wrong given Phase
19's category-differentiated variance. Measure empirical nominal-operation cycle-time
std per category (using a no-anomaly simulation run), update `spc.py`'s baseline sigma
to be category-specific, and document the new values + empirical source in
`docs/PHYSICS_GROUNDING_AUDIT.md`.

### ✅ Validation Checkpoint 22
Report nominal-operation SPC false-positive flag rates per category, before and after
recalibration — "after" should be low and comparable across categories.

---

## PHASE 23 — Full regenerate, retrain, and re-validate (mandatory)

1. Regenerate the full multi-seed training dataset with the Phase 17-22 generator.
2. Re-run the defect-concentration bias audit (`scripts/audit_defect_rate_concentration.py`),
   update `data/DATA_SANITY_NOTES.md`.
3. Retrain (`scripts/train_risk_model.py`), report full metrics side-by-side against the
   last known-good numbers (bottleneck: 0.932 AUC / 83.2% recall; defect: 0.601 AUC /
   0.289 PR-AUC, or Phase 11's uplifted numbers if that work was done). **A metrics drop
   is not necessarily a regression** — more realistic, less artificially-clean data is
   genuinely harder to predict from. Say this explicitly in `data/DATA_SANITY_NOTES.md`.
4. Re-run the full OOD suite (all 7 regimes now), compare against the last report.
5. Fold in Phase 21's control-group false-positive numbers as part of this consolidated
   report — it belongs alongside the OOD table as another generalization/robustness
   data point.
6. Update `REFERENCES.md` with a consolidated "Synthetic Data Realism Upgrade Log" table:
   what changed, before/after key statistics, why each change is more representative of
   a real assembly line.

### ✅ Validation Checkpoint 23
Paste the full retrain metrics table (before/after), the full 7-regime OOD table, the
control-group false-positive comparison, and confirm Phases 17-22's individual
checkpoints still hold on a final integration run.

---

## PHASE 24 — Shift-based productivity and fatigue model

(Only start after Phase 23's checkpoint passes.)

`pipeline/risk_model.py` already computes `shift_tick_sin`/`shift_tick_cos` from
`shift_tick % 480`, but confirm (grep `simulator/generator.py` for `shift`) that nothing
yet varies telemetry by this cycle — if Phase 17-23 introduced something already, adapt
rather than duplicate.

1. Define 3 shifts (Day 06:00-14:00, Evening 14:00-22:00, Night 22:00-06:00) using the
   existing 480-tick period. Verify alignment with `self.start_time`.
2. Shift multiplier table extending Phase 19's category system — large effect on manual
   stations (Night: ~1.35x CV, ~1.6-1.8x defect rate vs. Day), near-flat for automated
   categories (Night: ~1.02-1.1x, reflecting thinner support staffing, not machine
   fatigue). Document reasoning in `REFERENCES.md`.
3. Category-agnostic handover-window effect (~20-30 min at shift boundaries, ~1.1-1.15x
   CV for everyone).
4. Feed fatigue into Phase 17's `load_state` as a rising-through-the-shift target mean
   for manual stations, resetting at shift change — reuse the mechanism, don't add a
   parallel one.
5. Add explicit `shift_name` (categorical) and `is_night_shift` (binary) features
   alongside the existing sin/cos ones — update `FEATURE_NAMES` in both
   `pipeline/risk_model.py` and `scripts/generate_training_data.py`, check both, this
   project has had feature-list drift between them before.

### ✅ Validation Checkpoint 24
1. Run a 3-day (4320-tick) simulation, bucketed by shift, report mean cycle time /
   cycle-time CV / defect rate for manual vs. automated stations separately. Confirm
   Night > Evening > Day for manual on all three; confirm automated stays close to flat
   (report the actual ratio for both, to make the contrast explicit).
2. Trace `load_state` for one manual station across a single Night shift — confirm
   visible upward trend through the shift, reset at the boundary.
3. Regenerate a small dataset, confirm `shift_tick_sin`/`shift_tick_cos` now show
   non-trivial correlation with the labels (point-biserial or group-mean-by-phase check)
   — should move from ~0 (their state before this phase) to something real.
4. Re-run the full regenerate → retrain → bias-audit sequence, report metrics alongside
   Phase 23's for a three-way comparison (original → realism pass → +shift model).

---

## PHASE 25 — Residual learning + Shadow Mode Router for the risk model (new architecture, not just data)

**Motivation:** currently the GBDT risk score stands alone as the model's output. A more
defensible, physics-grounded architecture (borrowed from the hot-rolling reference
project's `Final Force = Physics Baseline + ML Residual`, routed through a guardrail
that falls back to the deterministic baseline if the ML output looks untrustworthy)
gives you a real, concrete answer to "how do you prevent the model from being
confidently wrong" — which a technical judge is likely to ask.

**1. Formalize the deterministic baseline.** `pipeline/risk_model.py`'s current
untrained-fallback heuristic (threshold logic on `processing_time_ratio`/`vibration`) is
already a deterministic, physics-adjacent risk estimate. Promote it to a first-class
function, `compute_baseline_risk(features_or_telemetry) -> float`, computed
**always**, not just when the GBDT is untrained — this becomes the "physics baseline"
half of the architecture, alongside SPC signals where relevant.

**2. Try residual framing as an experiment, don't mandate replacing the current
approach blindly.** Train an alternate version of the model where the GBDT target is
`(actual_risk_proxy - baseline_risk)` instead of the raw label, and the final prediction
is reconstructed as `baseline_risk + gbdt_residual_prediction`. Compare this against the
current direct-prediction approach on the same held-out test set (AUC/PR-AUC/recall).
Keep whichever performs better and is more stable across the OOD regimes — report both,
don't assume the fancier approach wins without checking.

**3. Build the Shadow Mode Router.** In `pipeline/risk_model.py` or a new
`pipeline/risk_router.py`:
```python
def route_risk_prediction(gbdt_risk: float, baseline_risk: float, divergence_threshold: float) -> dict:
    divergence = abs(gbdt_risk - baseline_risk)
    if divergence > divergence_threshold:
        return {"served_risk": baseline_risk, "shadow_risk": gbdt_risk, "routed": True, "divergence": divergence}
    return {"served_risk": gbdt_risk, "shadow_risk": gbdt_risk, "routed": False, "divergence": divergence}
```
Calibrate `divergence_threshold` empirically from a validation set (e.g. some high
percentile of normal GBDT-vs-baseline divergence under nominal conditions), not an
arbitrary guess — measure it, then pick.

**4. Wire into `api/main.py`'s live risk computation.** Serve `served_risk` to the
frontend by default. Log `shadow_risk` and `routed`/`divergence` for every tick (doesn't
need to be shown by default, but should be available) — this is genuinely good demo
material: "the AI wanted to flag X, but was routed to the safer physics-based estimate
because it diverged too far from what the deterministic model expects" is a strong,
honest answer to a judge's reliability question. Consider surfacing this in the same
transparency spirit as the "AI-enhanced" vs. "Standard" badge from the GenAI phase — this
is the same fallback-first philosophy, one layer earlier in the pipeline.

### ✅ Validation Checkpoint 25
1. Report the residual-vs-direct comparison table (both approaches' AUC/PR-AUC/recall on
   the same test set) and which one you kept, with reasoning.
2. Report how the `divergence_threshold` was calibrated (the actual percentile/value
   used and why).
3. Run the router over the full OOD suite (all 7 regimes) and report, per regime: what
   fraction of predictions got routed to the baseline instead of the GBDT. **This should
   be higher during harder/more out-of-distribution regimes (especially the Sensor
   Degradation Stress regime, which already showed the weakest raw GBDT performance) than
   during baseline I.I.D.** — if it's not, the guardrail isn't actually doing its job of
   catching the cases where the GBDT is least trustworthy. If it is, that's a genuinely
   good, reportable result.
4. Confirm overall served-prediction recall/precision doesn't collapse when the router is
   active — it should trade a small amount of raw GBDT performance for meaningfully safer
   behavior in the regimes where the GBDT is weak, not tank performance everywhere.
