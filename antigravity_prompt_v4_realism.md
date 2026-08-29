# Antigravity Task Prompt v4 — Synthetic Data Realism Overhaul

## How to work
Same rules as prior prompts: work phases in order, don't start the next phase until the
current Validation Checkpoint passes with real pasted output, read a file before editing
it, and if something doesn't match what's described below, stop and report the mismatch
rather than guessing. This prompt touches the core of `simulator/generator.py`, which
everything else in the project (features, SPC, propagation, OOD report, financials) is
downstream of — go slower and check more here than you would on a UI phase.

**Do not skip Phase 22 (SPC recalibration) or Phase 23 (full re-validation).** Changing
the noise model without recalibrating what reads it, or without re-proving the model
still works, is worse than not doing this at all — it would leave the repo in a state
where the README's claims are quietly wrong.

---

## PHASE 17 — Shared latent "load state" (fixes autocorrelation + cross-signal correlation together)

**Problem being fixed:** currently every noise draw (`self.rng.gauss(...)` for cycle
time, vibration, temperature, power) is independent and redrawn fresh every tick, in
`simulator/generator.py`'s `step()`. Real telemetry has memory (thermal mass, sustained
load) and shared cause (vibration/temp/power all rise together under real load, not
independently).

Add, in `LineSimulator.__init__`, a per-station persistent state dict:
```python
self.load_state: Dict[str, float] = {sid: 0.0 for sid in self.stations}
```
Each tick, before computing telemetry for a station, update it with a mean-reverting
AR(1) process:
```python
rho = 0.90  # persistence -- higher = more autocorrelation/memory. Tune this; document whatever you land on.
innovation_sigma = 0.06
wear_influence = self.wear_state.get(sid, 0.0) * 0.4  # from Phase 21 -- if Phase 21 not done yet, use 0.0
target_load_mean = wear_influence
self.load_state[sid] = rho * self.load_state[sid] + (1 - rho) * target_load_mean + self.rng.gauss(0, innovation_sigma)
self.load_state[sid] = max(-1.0, min(2.0, self.load_state[sid]))  # soft bound, not a hard wall
```
Then have vibration, temperature, and power all read a shared multiplier derived from
this ONE state before adding their own small independent residual noise, e.g.:
```python
load_factor = 1.0 + 0.35 * self.load_state[sid]
vibration = max(0.1, base_vib * load_factor + self.rng.gauss(0, 0.04))
temperature = base_temp + (self.load_state[sid] * 3.0) + self.rng.gauss(0, 0.3)
power_kw = base_kw * (load_factor if base_kw is not None else 1.0) * 0.9 + self.rng.gauss(0, 0.15)
```
(These exact coefficients are starting points, not gospel — tune them so that under
NOMINAL operation, the resulting signal magnitudes are in a similar ballpark to what the
system currently produces, so you're adding correlation/memory without wildly changing
absolute scale yet. Scale changes come in Phase 18/19.)

Reduce the standalone noise `sigma`/`gauss` calls you're replacing accordingly — don't
just add this on top of the full old noise magnitude, or you'll double the variance.

### ✅ Validation Checkpoint 17
Run a station for 500 ticks under NOMINAL conditions (no anomalies injected) and compute,
in a short script: (a) lag-1 autocorrelation of the vibration series — should now be
clearly positive (e.g. >0.3), where before it would have been ~0 by construction; (b)
Pearson correlation between the vibration series and the temperature series over the
same window — should now be clearly positive, where before it would have been ~0. Paste
both numbers. If either is still near zero, the shared state isn't actually wired into
both signals — check before moving on.

---

## PHASE 18 — Lognormal cycle time (replaces hard-truncated Gaussian)

**Problem being fixed:** `actual_ct = self.rng.gauss(effective_target_ct, sigma)`
clipped to `[0.8x, 1.3x]` is symmetric and produces an unrealistic wall of density at the
clip boundary. Real cycle times are right-skewed: tight near target, with a longer,
smooth tail of occasional slow cycles.

Replace with a lognormal draw parametrized so its MEAN equals `effective_target_ct`:
```python
import math

def lognormal_cycle_time(rng, mean_ct: float, cv: float) -> float:
    # cv = coefficient of variation (std/mean), station-category-specific -- see Phase 19
    sigma_ln = math.sqrt(math.log(1 + cv**2))
    mu_ln = math.log(mean_ct) - 0.5 * sigma_ln**2
    val = rng.lognormvariate(mu_ln, sigma_ln)
    return min(val, mean_ct * 2.5)  # soft cap on extreme outliers, not a hard truncation near the mean
```
Wire the existing `load_state` from Phase 17 in as a mild multiplier on `mean_ct` before
this draw (a station currently running "hot" per its load state should trend toward
slightly longer cycles too), rather than treating cycle time as fully independent of the
same latent state driving vibration/temp/power.

### ✅ Validation Checkpoint 18
Generate 2000 nominal-condition cycle-time samples for one station, plot or numerically
report: mean (should be close to target), skewness (should now be positive/right-
skewed, not ~0), and confirm no hard wall of density exactly at any clip boundary (check
the histogram bin counts near 1.3x target specifically — there should be a smooth
taper, not a spike).

---

## PHASE 19 — Station-category-differentiated variance and defect-rate multipliers

Define three categories (extend the existing `robotic_types` list logic, don't
duplicate it):
- `automated_precision` (existing `robotic_types` list)
- `automated_process` (ovens, chemical baths, transfer buffers, scanners — automated but
  not robotic-mechanical)
- `manual` (existing manual/`is_manual_sensor` stations)

Assign relative multipliers (these are assumptions — document the reasoning in
`REFERENCES.md`, same standard as the Phase 5 financial constants):
- Cycle-time CV: `automated_precision` ≈ 0.04, `automated_process` ≈ 0.06, `manual` ≈
  0.12-0.15 (human variability is genuinely higher than servo-controlled repeatability —
  don't make this a token difference, make it real).
- Natural (non-anomalous) defect rate multiplier on the current flat 0.8% base:
  `automated_precision` ≈ 0.6x, `automated_process` ≈ 1.0x, `manual` ≈ 2.5-3x.

Report the new resulting OVERALL average defect rate across all 40 stations after this
change (it will no longer be exactly 0.8% — that's expected and fine, just report the
new number, don't silently let it drift without noting it).

### ✅ Validation Checkpoint 19
Run a 2000-tick nominal simulation and report, per category: realized cycle-time CV and
realized defect rate, compared against the assumed targets above. They should be close
(within reasonable sampling noise) — if a category's realized numbers don't match what
you configured, find the bug before moving on.

---

## PHASE 20 — Anomaly-type-specific signal effect profiles (decouple vibration from blanket ct_multiplier)

**Problem being fixed:** currently, ANY anomaly pushing `ct_multiplier > 1.2` forces
vibration and temperature up by the same formula, regardless of anomaly type. This makes
vibration nearly redundant with processing-time-ratio during anomalies, and is
physically wrong for some anomaly types.

Read `simulator/anomalies.py` first to see the exact effect fields currently available
per anomaly type, then define an explicit per-type physical signature (add new fields to
the anomaly effect dict only if genuinely needed, don't duplicate existing ones):

- `gradual_drift`: vibration rises (mechanical wear signature), temperature rises
  modestly, power rises modestly — this is the one type where the current coupled
  behavior is roughly right, keep it.
- `sudden_stoppage`: vibration drops toward ~0, power drops (already correctly handled
  via `is_stopped` — verify, don't rebuild).
- `latent_defect`: **should produce little to no telemetry signal at all** — this is the
  physically correct behavior and a genuine strength for your write-up: a latent defect
  is by definition not something real-time sensors catch, which is exactly why the
  genealogy/QC mechanism exists. Confirm `latent_defect`'s effect dict doesn't set a
  meaningful `cycle_time_multiplier`, and if it currently does, remove that coupling.
- `sensor_blackout`: affects data availability only (already a separate mechanism), no
  change needed to underlying physical signal generation.
- `energy_waste`: power/energy rise via `power_multiplier` (already exists) but should
  NOT trigger the vibration/temperature bump — an inefficient/miscalibrated energy draw
  doesn't necessarily mean mechanical stress. Remove this type from whatever generic
  `ct_multiplier > 1.2` vibration-bump condition currently exists, if it's currently
  swept in by that blanket check.

Implement this as an explicit lookup (anomaly type → which channels it affects and how),
not a single shared formula gated only by `ct_multiplier`.

### ✅ Validation Checkpoint 20
Inject each of the 5 anomaly types on a test station one at a time, run 30 ticks each,
and report the observed vibration/temperature/power delta from baseline for each type.
Confirm `latent_defect` shows ~no telemetry change, `energy_waste` shows a power change
but ~no vibration change, and `gradual_drift`/`sudden_stoppage` behave as described
above. Paste the actual numbers, not just "looks right."

---

## PHASE 21 — Emergent per-station wear/health model + unscheduled failures + maintenance resets

This is the most ambitious phase — go carefully, and don't let it destabilize the
balanced coverage your training pipeline depends on (see the checkpoint below).

**Wear state**, added alongside `load_state` in `LineSimulator.__init__`:
```python
self.wear_state: Dict[str, float] = {
    sid: self.rng.uniform(0.0, 0.15) for sid in self.stations  # slight age variety at start, not all zero
}
```
Each tick, increase it slowly:
```python
base_wear_rate = {"automated_precision": 0.00015, "automated_process": 0.00020, "manual": 0.00025}[category]
shock = 0.02 if self.rng.random() < 0.0008 else 0.0  # rare larger jumps -- bad batch of parts, mishandling
self.wear_state[sid] = min(1.2, self.wear_state[sid] + base_wear_rate * (1 + max(0, self.load_state[sid])) + shock)
```
(Tune the rate constants so that, over a realistic multi-thousand-tick run, stations
plausibly cross the failure threshold a handful of times, not never and not constantly —
you'll need to iterate on this by running a long simulation and checking the failure
frequency, don't just pick numbers and assume they're right.)

**Unscheduled failure trigger:** when `wear_state[sid] > 0.85`, apply a per-tick
probability of triggering a new ground-truth anomaly category, `"unscheduled_failure"`
(add this as a genuinely new type in `simulator/anomalies.py`'s effect/logging path, with
its own realistic signal profile per Phase 20's pattern — e.g. it should look like an
organic version of `gradual_drift` or `sudden_stoppage`, your call, but log it under the
distinct `true_anomaly_type: "unscheduled_failure"` so it's auditable separately from
scripted campaign events). This must emit ground-truth log entries through the SAME
mechanism your existing anomaly types use, so `scripts/generate_training_data.py`'s
labeling pass (which reads `is_stopped`/`ct_ratio`/`defect_flag`, not anomaly type
specifically) picks it up with zero changes to the labeling logic itself.

**Maintenance windows:** per your problem statement's reference parameter ("production
can only be paused for instrumentation changes during a small number of scheduled
maintenance windows per year"), add a periodic maintenance event — e.g. every
`N` ticks (pick something that maps sensibly onto your simulated timescale; document the
mapping, e.g. "1 maintenance window per simulated week"), reset `wear_state` for stations
above some threshold back toward a low value (not necessarily exactly 0 — partial
service is realistic too), simulating real preventive maintenance cadence.

**Do not let this replace or overwhelm the balanced campaign coverage from
`simulator/anomaly_campaign.py`.** Keep campaign-driven injections as the primary,
guaranteed-coverage mechanism for training data; the emergent wear model runs
simultaneously as an additive, lower-frequency, more organic source. This is
deliberate — campaigns guarantee every station/zone/type gets adequate positive-label
coverage (which the Phase 1 bias audit checks), while emergent failures add realistic,
unscripted texture on top.

**New OOD regime:** add a 7th scenario to `scripts/generate_scenario_datasets.py` /
`scripts/evaluate_scenario_validation.py`: **"Emergent Wear-Driven Failures"** — generate
a test dataset with the scripted campaign disabled or minimized, relying primarily on the
wear model to produce anomalies. This tests whether a model trained mostly on
scripted-campaign patterns (which have crisp, deliberate start/duration edges) can
generalize to organically-emerging failures, which ramp up more gradually and
unpredictably. This is genuinely the most scientifically interesting OOD test in the
suite so far — a meaningful generalization gap here would be a legitimate, reportable
finding, not a failure.

### ✅ Validation Checkpoint 21
1. Run a long simulation (~8000+ ticks) with both campaign and emergent wear active.
   Report: how many `unscheduled_failure` events occurred, spread across how many
   distinct stations, and how many maintenance reset events fired.
2. Re-run the Phase 1-style bias audit (by zone / station_type / sensor_tier) on a freshly
   generated training dataset with this enabled, and confirm no subgroup's coverage
   collapsed relative to what it was before this phase — emergent failures are stochastic
   and could, by bad luck, cluster unevenly; check for this explicitly rather than
   assuming balance held.
3. Run the new OOD regime and report its ROC-AUC / PR-AUC / generalization gap alongside
   the other 6 regimes already in `docs/SCENARIO_VALIDATION_REPORT.md`.

---

## PHASE 22 — SPC recalibration (do not skip this)

`pipeline/spc.py` currently uses a flat `sigma = 4% of target` control limit for every
station, which was already a known simplification even before this overhaul (see
`docs/PHYSICS_GROUNDING_AUDIT.md`). Now that Phase 19 has made process variance
genuinely different across `automated_precision` / `automated_process` / `manual`
categories, a flat 4% limit is actively wrong: too tight for manual stations (constant
false-positive control violations at nominal operation) and too loose for precision
robotic stations (under-sensitive to real drift).

1. Run a nominal-operation-only simulation (no anomalies) for each category, measure the
   empirical cycle-time standard deviation actually produced by Phase 18/19's changes.
2. Update `pipeline/spc.py`'s baseline sigma calculation to use category-specific values
   derived from step 1, instead of the flat 4% constant. Document the new values and
   their empirical source in `docs/PHYSICS_GROUNDING_AUDIT.md`.
3. Re-check the false-positive rate: run each category under nominal conditions and
   confirm the SPC engine's flag rate is low and roughly similar across categories after
   recalibration (it should NOT still be higher for manual stations purely due to
   miscalibration — some difference is fine if it reflects genuine signal, but it
   shouldn't be an artifact of the stale flat constant).

### ✅ Validation Checkpoint 22
Report nominal-operation false-positive SPC flag rates per category, before and after
recalibration. The "after" numbers should be low and comparable across categories; if
they're not, the recalibration didn't actually fix the mismatch.

---

## PHASE 23 — Full regenerate, retrain, and re-validate (mandatory, not optional)

This is the same discipline as the original data-sanctity pass, applied to the new
generator. Do not report this project as "upgraded" until this phase's checkpoint passes.

1. Regenerate the full multi-seed training dataset with the new generator
   (`scripts/generate_training_data.py`, same seed count/scale as your last full run).
2. Re-run the Phase 1-style defect-concentration bias audit
   (`scripts/audit_defect_rate_concentration.py`) — confirm the inspection-station
   defect-surfacing pattern still makes physical sense under the new
   category-differentiated defect rates, and update `data/DATA_SANITY_NOTES.md` with any
   changed numbers.
3. Retrain the risk model (`scripts/train_risk_model.py`) and report full metrics
   side-by-side against the last known-good numbers (bottleneck: 0.932 AUC / 83.2%
   recall; defect: 0.601 AUC / 0.289 PR-AUC, or whatever Phase 11's uplift work landed
   on if that was completed first). **If metrics come out lower than before, that is not
   necessarily a regression** — the new data is more realistic and therefore likely
   genuinely harder to predict from than the old symmetric-noise, decoupled-signal data.
   Say this explicitly in your report and in `data/DATA_SANITY_NOTES.md` so a judge
   doesn't misread an honest metric drop as things getting worse.
4. Re-run the full OOD suite (all 7 regimes now, including Phase 21's new one) and
   compare against the last report.
5. Update `REFERENCES.md` with a consolidated "Synthetic Data Realism Upgrade Log"
   section summarizing, in one table: what changed (noise model, cycle-time
   distribution, category differentiation, anomaly-effect decoupling, emergent wear
   model, SPC recalibration), the before/after key statistics for each, and why each
   change makes the data more representative of a real assembly line — this table is
   genuinely good material for your written proposal, not just internal documentation.

### ✅ Validation Checkpoint 23
Paste: the full retrain metrics table (before/after), the full 7-regime OOD table
(before/after where applicable), and confirm every one of Phases 17-22's checkpoints
still holds on a final end-to-end run (don't just trust that they held when you did them
individually — integration can break things that worked in isolation).
