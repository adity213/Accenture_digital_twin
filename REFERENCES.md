# DigitalTwin.ai: Industrial Standards and Metrics Registry

This document records the parameters, operating limits, physical constants, and equations used in DigitalTwin.ai, mapped to their engineering standards, manufacturing benchmarks, and source code locations.

## Navigation
1. [Line Operations and Takt Physics](#1-line-operations--takt-time-physics)
2. [Thermal and Process Standards](#2-thermal--thermodynamic-standards)
3. [Vibration and Mechanical Health Standards (ISO 10816 / ISO 20816)](#3-vibration--mechanical-health-standards)
4. [Electrical Power and Energy](#4-electrical-power--energy-consumption)
5. [Statistical Process Control (SPC)](#5-statistical-process-control-spc--quality-engineering)
6. [Virtual Sensing and Confidence Scoring](#6-virtual-sensing--confidence-scoring)
7. [Predictive Risk and Graph Propagation](#7-predictive-risk-machine-learning--graph-propagation)
8. [Plant Economics and Financial Modeling](#8-business-economics--downtime-financial-modeling)
9. [Summary Traceability Matrix](#9-summary-traceability-matrix)

---

## 1. Line Operations & Takt Time Physics

### 1.1 Target Cycle Time ($T_{\text{target}}$ / `cycle_time_s`)
- **Calibrated Value**: $45.0\text{s} - 80.0\text{s}$ per station (Mean: $55.0\text{s} - 65.0\text{s}$).
- **Nominal Line Cadence**: $55.4\text{ JPH}$ (Jobs Per Hour, representing $65\text{s}$ bottleneck takt time).
- **Physical Rationale**: Automotive final assembly lines operate on rigid takt pacing determined by annual vehicle delivery targets ($250,000\text{ vehicles/year}$ across 2 shifts $\approx 55-60\text{ JPH}$).
- **Exact Source**: 
  - Toyota Production System (TPS) Takt Time Formulation: $\text{Takt} = \frac{\text{Available Net Operating Time}}{\text{Customer Demand}}$.
  - *Technical PRD Section 3 & 10 (Line Topology & Operating Specifications)*.
- **Code Implementation**: [`simulator/topology.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/simulator/topology.py#L16-L62), [`simulator/generator.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/simulator/generator.py#L110-L125).

### 1.2 Natural Process Variation ($\sigma_{\text{baseline}}$)
- **Mathematical Formula**:
  $$\sigma_{\text{baseline}} = \max\left(0.50\text{ s}, 0.04 \times T_{\text{target}}\right)$$
- **Calibrated Value**: $4.0\%$ coefficient of variation ($\text{CV} = 0.04$).
- **Physical Rationale**: Automated robotic weld cells and conveyor indexing exhibit steady-state Gaussian noise bounded within $\pm 3\sigma = \pm 12\%$ of target cycle time under normal operating health.
- **Exact Source**:
  - Montgomery, D. C. (2019). *Introduction to Statistical Quality Control* (8th ed.). John Wiley & Sons.
  - Six Sigma Automotive Manufacturing Benchmark (AIAG SPC-3 Manual).
- **Code Implementation**: [`pipeline/spc.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/pipeline/spc.py#L38-L41).

### 1.3 Buffer Queue Dynamics (`buffer_level`, `buffer_capacity_units`)
- **Buffer Capacity**: $5 - 15\text{ units}$ per intermediate buffer bank.
- **Operating Zones**:
  - **Starvation Critical**: $< 10\%$ fill (Downstream starvation imminent in $< 5\text{ mins}$).
  - **Starvation Warning**: $< 25\%$ fill (Buffer drainage exceeds replenishment).
  - **Nominal Zone**: $40\% - 70\%$ fill.
  - **Blockage Warning**: $> 80\%$ fill (Upstream discharge throttling).
  - **Blockage Critical**: $100\%$ fill (Upstream forced line halt).
- **Exact Source**:
  - Hopp, W. J., & Spearman, M. L. (2011). *Factory Physics* (3rd ed., Ch. 9: CONWIP and Buffer Allocation in Serial Lines). Waveland Press.
  - Gershwin, S. B. (1994). *Manufacturing Systems Engineering*. Prentice Hall.
- **Code Implementation**: [`simulator/topology.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/simulator/topology.py#L100), [`pipeline/propagation.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/pipeline/propagation.py#L40-L75).

---

## 2. Thermal & Thermodynamic Standards

| Station Type | Operating Temperature | Noise ($\sigma$) | Warning Threshold | Critical Alarm | Industrial Standard & Reference |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **E-Coat Curing Oven** (`ST17` / `ThermalOven`) | **$190.0^\circ\text{C}$** ($374^\circ\text{F}$) | $0.5^\circ\text{C}$ | $> 205.0^\circ\text{C}$ | $> 220.0^\circ\text{C}$ | **PPG / Axalta OEM Coating Standard**: Electrocoat polymer crosslinking requires $180^\circ\text{C}-200^\circ\text{C}$ sustained substrate bake for 20–30 min. |
| **Pretreatment & E-Coat Bath** (`ST15`, `ST16`) | **$55.0^\circ\text{C}$** ($131^\circ\text{F}$) | $0.5^\circ\text{C}$ | $> 65.0^\circ\text{C}$ | $> 75.0^\circ\text{C}$ | **Henkel / BASF Surface Technologies**: Alkaline degreasing and zinc phosphating immersion operating window is $50^\circ\text{C}-60^\circ\text{C}$. |
| **Robotic Welding & Stamping** (`ST01-ST14`) | **$24.0^\circ\text{C}$** (Ambient) | $0.5^\circ\text{C}$ | $> 45.0^\circ\text{C}$ | $> 65.0^\circ\text{C}$ | **NEMA MG 1-2016 / IEC 60034-1**: Industrial motor stator winding thermal dissipation envelope. |
| **Final Assembly Cells** (`ST23-ST40`) | **$24.0^\circ\text{C}$** (Ambient) | $0.5^\circ\text{C}$ | $> 35.0^\circ\text{C}$ | $> 45.0^\circ\text{C}$ | **ASHRAE Standard 55**: Thermal Environmental Conditions for Industrial Human Occupancy. |

- **Thermal Degradation Escapes**: In overload conditions ($T_{\text{cycle}} > 1.2 \times T_{\text{target}}$), thermal dissipation increases by $+12.0^\circ\text{C} \times (\text{multiplier} - 1.0)$.
- **Code Implementation**: [`simulator/generator.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/simulator/generator.py#L158-L168), [`tests/test_simulator.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/tests/test_simulator.py#L46-L75).

---

## 3. Vibration & Mechanical Health Standards

### 3.1 ISO 10816-3 / ISO 20816-1 Severity Limits
Vibration velocity RMS ($\text{mm/s}$) evaluated on non-rotating structural supports and robotic arm pedestals (Class I/II Industrial Machines with motor power $\le 300\text{ kW}$):

$$\text{Severity Zones (ISO 10816-3)}$$
$$\begin{cases}
\text{Zone A (Good / New)} & v_{\text{RMS}} < 1.12\text{ mm/s} \\
\text{Zone B (Satisfactory / Unrestricted Long-term Operation)} & 1.12 \le v_{\text{RMS}} \le 2.80\text{ mm/s} \\
\text{Zone C (Unsatisfactory / Warning — Schedule Maintenance)} & 2.80 < v_{\text{RMS}} \le 4.50\text{ mm/s} \\
\text{Zone D (Unacceptable / Critical Alarm — Risk of Structural Failure)} & v_{\text{RMS}} > 4.50\text{ mm/s}
\end{cases}$$

### 3.2 Station Baseline Calibration
- **Robotic Weld & Torque Arms (`ST02`, `ST03`, `ST05-ST08`, `ST26-ST30`, `ST35`)**:
  - Baseline: $1.20\text{ mm/s}$ RMS with Gaussian noise $\mathcal{N}(0, 0.08^2)$ $\rightarrow$ Operates directly in **Zone B (Satisfactory)**.
- **Passive Conveyors & Transfer Buffers (`ST14`, `ST23`)**:
  - Baseline: $0.40\text{ mm/s}$ RMS $\rightarrow$ Operates in **Zone A (Good)**.
- **Drift Escalation Physics**:
  - When mechanical wear is injected, vibration surges by $+3.5 \times (\text{multiplier} - 1.0)\text{ mm/s}$, crossing $4.50\text{ mm/s}$ (Zone D) to trigger automated safety isolation.
- **Exact Source**:
  - International Organization for Standardization. *ISO 10816-3:2009: Mechanical vibration — Evaluation of machine vibration by measurements on non-rotating parts — Part 3: Industrial machines*.
  - *ISO 20816-1:2016: General guidelines for vibration measurement and evaluation*.
- **Code Implementation**: [`pipeline/spc.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/pipeline/spc.py#L48-L67), [`pipeline/recommender.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/pipeline/recommender.py#L133-L151).

---

## 4. Electrical Power & Energy Consumption

### 4.1 Base Power Calibration by Process Type
- **Robotic Spot Welding (`RoboticWeld`, `RespotWeld`)**:
  - Base Active Draw: $28.0 - 32.0\text{ kW}$ average (blended duty cycle: $2-3\text{ kW}$ idle standby, $45-60\text{ kW}$ active weld pulse).
- **Thermal Curing Oven (`ThermalOven`)**:
  - Base Continuous Draw: $55.0\text{ kW}$ (Infrared ceramic & quartz heating banks).
- **Robotic Paint Spray Booths (`RoboticSpray`)**:
  - Base Active Draw: $38.0 - 48.0\text{ kW}$ (High-velocity downdraft air filtration and electro-pneumatic bell atomizers).
- **Final Assembly Drivetrain / Battery Marriage (`ST28`)**:
  - Base Active Draw: $50.0\text{ kW}$ (High-torque automated AGV hydraulic lift pins).
- **Manual Hand-Tool Assembly (`ManualWiring`, `ManualTrim`)**:
  - Base Draw: $5.0 - 8.0\text{ kW}$ (Low-voltage DC nutrunners & station LED lighting).

### 4.2 Energy Integration & Starvation Waste Equation
- **Energy per Step Formula**:
  $$\text{Energy}_{\text{tick}}\text{ (kWh)} = \frac{P_{\text{active}}\text{ (kW)}}{60\text{ min/hr}}$$
- **Idle Energy Draw during Starvation/Blockage**:
  $$P_{\text{idle}} = 0.25 \times P_{\text{base}}\text{ (kW)}$$
  *Running idle pumps, PLC control loops, and heated baths while $0\text{ JPH}$ throughput is produced accumulates preventable utility costs.*
- **Exact Source**:
  - FANUC America Corporation. *R-2000iC / M-900iB Series Industrial Robot Engineering Data Manuals*.
  - US Department of Energy (DOE) Advanced Manufacturing Office: *Improving Motor and Drive System Performance: A Sourcebook for Industry*.
- **Code Implementation**: [`simulator/topology.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/simulator/topology.py#L16-L62), [`simulator/generator.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/simulator/generator.py#L169-L175).

---

## 5. Statistical Process Control (SPC) & Quality Engineering

### 5.1 Exponentially Weighted Moving Average (EWMA)
- **Recursive Formulation**:
  $$S_t = \lambda X_t + (1 - \lambda) S_{t-1}$$
- **Smoothing Parameter**: $\lambda = 0.30$ (optimized for detecting shifts between $0.5\sigma$ and $2.0\sigma$).
- **Initialization**: $S_0 = T_{\text{target}}$.
- **Standardized $z$-Score**:
  $$z_t = \frac{S_t - T_{\text{target}}}{\sigma_{\text{baseline}}}$$
- **3-Sigma Deviation Flag**:
  $$\text{Flag}_{\text{SPC}} = \begin{cases} \text{TRUE}, & \text{if } |z_t| > 3.0 \\ \text{FALSE}, & \text{otherwise} \end{cases}$$
- **Exact Source**:
  - Hunter, J. S. (1986). *The Exponentially Weighted Moving Average*. Journal of Quality Technology, 18(4), 203-210.
  - Lucas, J. M., & Saccucci, M. S. (1990). *Exponentially weighted moving average control schemes: properties and enhancements*. Technometrics, 32(1), 1-12.
- **Code Implementation**: [`pipeline/spc.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/pipeline/spc.py#L27-L44).

### 5.2 Windowed Linear Drift Slope
- **Formulation**: Sliding 30-tick window bisected into first-half mean ($\bar{X}_1$) and second-half mean ($\bar{X}_2$):
  $$\Delta_{\text{drift}} = \bar{X}_2 - \bar{X}_1$$
  - $\Delta_{\text{drift}} > +0.6\text{ s} \implies \text{DRIFT\_UP}$ (Tool tip wear / bearing degradation).
  - $\Delta_{\text{drift}} < -0.6\text{ s} \implies \text{DRIFT\_DOWN}$ (Process recovery / pacing shift).
- **Code Implementation**: [`pipeline/spc.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/pipeline/spc.py#L71-L82).

---

## 6. Virtual Sensing & Confidence Scoring

### 6.1 Multi-Criteria Data Confidence Formulation
For legacy, manual, or intermittently connected stations, state telemetry is imputed via spatial neighbor correlation and historical shift templates. Confidence is computed deterministically:

$$C_{\text{data}} = w_1 \cdot C_{\text{tier}} + w_2 \cdot C_{\text{recency}} + w_3 \cdot C_{\text{agreement}}$$

Where:
- **Normalized Weights**: $w_1 = 0.50$ (Hardware tier), $w_2 = 0.30$ (Telemetry freshness), $w_3 = 0.20$ (Spatial agreement).
- **Hardware Tier Scoring ($C_{\text{tier}}$)**:
  $$C_{\text{tier}} = \begin{cases} 1.00 & (\text{Rich PLC instrumented, 80\% of line}) \\ 0.50 & (\text{Manual checklist station, 20\% of line}) \end{cases}$$
- **Temporal Decay ($C_{\text{recency}}$)**:
  $$C_{\text{recency}} = \exp\left(-0.10 \times \Delta t_{\text{ticks since reading}}\right)$$
  *(Drops to $<0.15$ during active sensor blackout).*
- **Imputation Spatial Agreement ($C_{\text{agreement}}$)**:
  $$C_{\text{agreement}} = 1.0 - \min\left(1.0, \frac{|\hat{y}_{\text{imputed}} - y_{\text{spatial}}|}{T_{\text{target}}}\right)$$

### 6.2 Composite Twin Confidence
Aggregates data telemetry fidelity with model uncertainty and SPC stability:
$$\text{TwinConfidence} = \text{round}\left(C_{\text{data}} \times 100 \times (1.0 - 0.20 \cdot \text{Risk}_{\text{composite}}) \times (0.90 \text{ if SPC Flag else } 1.0)\right)$$
- **Exact Source**:
  - *Technical PRD Section 5.2 (Virtual Sensor Inference & Confidence)*.
  - ISO 23247:2021 (*Automation systems and integration — Digital twin framework for manufacturing*).
- **Code Implementation**: [`pipeline/confidence.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/pipeline/confidence.py), [`pipeline/virtual_sensor.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/pipeline/virtual_sensor.py).

---

## 7. Predictive Risk Machine Learning & Graph Propagation

### 7.1 GBDT Classifier Architecture & Training Protocol
- **Algorithms**: Histogram-Based Gradient Boosted Decision Tree (`HistGradientBoostingClassifier`) with categorical support for `zone_code` and `station_type_code`.
- **Training Dataset**: Multi-seed simulation generator across 6 random seeds (960,000 observations) with held-out seed test set (Seed 1005, 160,000 samples).
- **Predictive Horizons**:
  - $P(\text{Bottleneck within next 15 minutes})$
  - $P(\text{Defect associated with station output})$
- **Feature Vector ($D=19$, Strict Zero Data Leakage)**:
  1. `processing_time_ratio` ($T_{\text{actual}} / T_{\text{target}}$)
  2. `buffer_utilization` ($\text{queue} / \text{capacity}$)
  3. `degradation_momentum` ($\{-1.0, 0.0, 1.0\}$)
  4. `spc_z_score` (Standardized deviation against station-calibrated sigma)
  5. `avg_upstream_starvation_risk` ($0.0 - 1.0$)
  6. `max_upstream_starvation_risk` ($0.0 - 1.0$)
  7. `sensor_confidence` ($0.0 - 1.0$)
  8. `shift_tick_sin` ($\sin(2\pi \cdot (\text{tick}\%480) / 480)$ — 8-hour diurnal cycle)
  9. `shift_tick_cos` ($\cos(2\pi \cdot (\text{tick}\%480) / 480)$)
  10. `is_manual_sensor` ($\{0.0, 1.0\}$)
  11. `zone_code` ($\{0, 1, 2\}$ for Body, Paint, Assembly)
  12. `station_type_code` (Categorical integer encoding across 30 station types)
  13. `rolling_mean_ct_ratio` (10-tick rolling mean of cycle time ratio)
  14. `rolling_std_ct_ratio` (10-tick rolling std dev of cycle time ratio)
  15. `buffer_utilization_delta` (Buffer velocity: current fill vs 5 ticks ago)
  16. `ticks_since_spc_flag` (Elapsed ticks since last EWMA drift / $3\sigma$ flag)
  17. `machine_shaking_vibration` ($\text{mm/s}$ RMS)
  18. `motor_heat_temperature` ($^\circ\text{C}$)
  19. `active_power_draw_kw` ($\text{kW}$)

- **Empirical Model Evaluation (Held-Out Seed 1005 Test Set)**:
  - **Bottleneck ROC-AUC**: **$0.939$**
  - **Bottleneck PR-AUC (Average Precision)**: **$0.850$**
  - **Bottleneck Precision**: **$98.1\%$**
  - **Bottleneck Recall**: **$84.6\%$** (Balanced sample weighting for class imbalance)
  - **Subgroup Fairness Breakdown**:
    - *Body Construction Zone*: Precision $98.3\%$, Recall $86.9\%$
    - *Paint Shop Zone*: Precision $97.7\%$, Recall $81.8\%$
    - *Final Assembly Zone*: Precision $98.2\%$, Recall $84.9\%$
    - *Rich Sensor Tier*: Recall $84.9\%$
    - *Manual Sensor Tier*: Recall $83.6\%$

- **Explainability & Root Cause Attribution**:
  - `GET /api/risk/{station_id}/drivers` computes top-3 risk driver feature attributions relative to calibrated nominal baselines and provides immediate operator remediation guidance.
- **Code Implementation**: [`pipeline/risk_model.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/pipeline/risk_model.py), [`scripts/train_risk_model.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/scripts/train_risk_model.py), [`tests/test_features.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/tests/test_features.py).

### 7.2 Downstream Starvation Countdown Equation
Models bottleneck starvation wave propagation across the line DAG topology:

$$\text{time\_to\_impact}_{u \rightarrow v} = \frac{\text{BufferUnitsRemaining}_v}{\max\left(0.10, \text{OutflowRate}_v - \text{InflowRate}_u\right)} \times T_{\text{target}, v}$$

Where:
- Graph traversal tracks all reachable topological descendants in directed acyclic order.
- Decayed risk propagation applies structural damping:
  $$\text{Risk}_{\text{propagated}}(v) = \text{Risk}(u) \cdot \gamma^{\text{dist}(u,v)} \cdot \left(1.0 - \frac{\text{BufferLevel}_v}{\text{BufferCap}_v}\right)$$
  ($\gamma = 0.85$ decay factor).
- **Code Implementation**: [`pipeline/propagation.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/pipeline/propagation.py#L35-L85).

---

## 8. Business Economics & Downtime Financial Modeling

### 8.1 Industry Downtime Benchmark Cost
- **Standard Industrial Metric**:
  $$\text{Downtime Cost Rate} = \$2,300,000\text{ / hour} = \$38,333.33\text{ / minute}$$
- **Plant Operational Baseline**: Large automotive assembly plants suffer an average of $\approx 27.0\text{ hours/month}$ of unplanned downtime across body, paint, and trim/chassis lines.
- **Annual Risk Exposure**: $27\text{ hrs/mo} \times 12\text{ mo} \times \$2.3\text{M/hr} = \$745,200,000\text{ / plant / year}$.
- **DigitalTwin.ai Target ROI**:
  $$\text{Downtime Cost Avoided (\$)} = \Delta t_{\text{avoided}}\text{ (min)} \times \$38,333.33\text{ / min}$$
  *(A conservative $15\%-30\%$ reduction generates $\$11.1\text{M} - \$22.3\text{M}$ direct annual savings per assembly facility).*
- **Exact Source**:
  - Siemens Global Industrial Benchmark Survey (2024). *The True Cost of Downtime: Modern Automotive Manufacturing Resilience*.
  - *Business Proposal Section 1 & 5 (Executive Summary & Business Case)*.
- **Code Implementation**: [`pipeline/recommender.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/pipeline/recommender.py#L12), [`api/main.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/api/main.py#L58).

### 8.2 Component Failure & Scrap Avoidance Standards
- **Robot Spindle / Stator Overhaul Avoidance**: $\$45,000$ per emergency replacement prevented via ISO 10816 vibration warning.
- **Paint Shop Defect Rework Avoidance**: $\$1,200 - \$4,500$ per car body saved from latent defect contamination.
- **Exact Source**:
  - Automotive Industry Action Group (AIAG) Quality Cost Guidelines (CQI-14).
  - *Technical PRD Section 5.6 (Recommendation Engine & Value Drivers)*.

### 8.3 Leadership Financial Intelligence & Unit Economics Constants (Phase 5)
Every financial metric in `/api/leadership/summary` is computed from documented industrial baseline assumptions:
1. **`plant_footprint_sqft` ($250,000\text{ sq ft}$)**: Typical floor area for a flexible 40-station mixed body (80k sq ft), paint (60k sq ft), and final assembly (110k sq ft) facility. *(Source: Harbour Report / OEM Greenfield plant architectural benchmarks).*
2. **`plant_capex_total_usd` ($\$450,000,000$)**: Total capital expenditure for facility construction, robotic tooling, environmental scrubbers, and conveyors. *(Source: Center for Automotive Research (CAR) plant investment index).*
3. **`cost_per_sqft_usd` ($\$1,800.00\text{ / sq ft}$)**: Derived as $\frac{\text{Total Plant Capex}}{\text{Plant Footprint}} = \frac{\$450\text{M}}{250\text{k sq ft}}$.
4. **`vehicle_curb_weight_tons` ($1.65\text{ metric tons} \approx 3,638\text{ lbs}$)**: Average curb weight of modern light-vehicle crossover/CUV platform. *(Source: EPA Light-Duty Automotive Technology and Fuel Economy Trends).*
5. **`unit_assembly_base_cost_usd` ($\$2,850.00\text{ / vehicle}$)**: Direct manufacturing conversion cost (labor, utilities, tooling amortization, consumables) excluding raw steel/powertrain BOM. *(Source: Oliver Wyman Automotive Manufacturing Index).*
6. **`cost_per_ton_usd` ($\$1,727.27\text{ / ton}$)**: Derived as $\frac{\$2,850\text{ conversion cost}}{1.65\text{ tons}}$.
7. **`station_capex_by_type`**: Stratified by technological complexity (Thermal Ovens/Baths: $\$2.0\text{M}$, Robotic Paint: $\$1.5\text{M}$, Framing/Weld: $\$1.2\text{M}$, Automated Torque/Marriage: $\$850\text{k}$, Vision QC: $\$650\text{k}$, Manual Trim: $\$150\text{k}$). *(Source: FANUC / ABB / Dürr industrial robotics pricing catalog).*
8. **`payback_period_days` & `annualized_roi_pct`**: Rather than misleading micro-prorated percentage metrics, ROI is evaluated as:
   - **Payback Period**: $\text{Payback (Days)} = \frac{\text{Capex (\USD)}}{\text{Daily Savings Run-Rate (\USD/day)}}$, providing an intuitive executive timeline to capital break-even.
   - **Annualized ROI**: Evaluated against standard automotive OEM operational baselines ($250\text{ operating days/year} \times 16\text{ hrs/day} = 4,000\text{ production hours/year}$):
     $$\text{Annualized ROI (\%)} = \frac{\text{Annualized Savings (\$) } - \text{ Annual Amortized Capex (5-yr)}}{\text{Annual Amortized Capex (5-yr)}} \times 100\%$$
   - **Cumulative Incident Aggregation**: Note that `downtime_avoided_min` represents the **cumulative sum of historical recommendation interventions** logged across shift operations by the `TwinStore`, rather than a single isolated incident.
- **Code Implementation**: [`api/main.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/api/main.py#L485-L560).

---

## 10. Dynamic Topology Reconfiguration & DAG Graph Transformations

### 10.1 Topological Sorting & Cyclic Loop Prevention
- **Invariance Criterion**: Plant layout must maintain a strictly Directed Acyclic Graph ($\text{DAG}$) structure:
  $$\forall e = (u, v) \in E \implies \text{rank}(u) < \text{rank}(v) \land \not\exists \text{ path } v \leadsto u$$
- **Runtime Validation**: When modifying conveyor edges via `/api/topology/apply`, NetworkX evaluates topological validity via Kahn's algorithm in $\mathcal{O}(|V| + |E|)$. If cycles are introduced, the API returns a structured HTTP 400 validation error before modifying simulator state.
- **Exact Source**:
  - Bang-Jensen, J., & Gutin, G. Z. (2008). *Digraphs: Theory, Algorithms and Applications*. Springer Science & Business Media.
  - *Technical PRD Section 3 (Plant Topology & DAG Specifications)*.
- **Code Implementation**: [`api/main.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/api/main.py#L450-L530), [`simulator/topology.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/simulator/topology.py#L85-L120).

### 10.2 Living Line Zone-Aware Auto-Placement & Non-Overlap Collision Resolver
When custom stations are added dynamically via the SCADA interface, their floor coordinate footprint is assigned through zone bounding and spatial relaxation:
1. **Zone Y-Bound Assignment**:
   $$\text{Body Zone } Y \in [20, 360]\text{px}, \quad \text{Paint Zone } Y \in [380, 570]\text{px}, \quad \text{Assembly Zone } Y \in [590, 1100]\text{px}$$
2. **Zero-Overlap Relaxation Engine**:
   $$\forall s_i, s_j \in V \text{ where } i \ne j, \quad \text{if } \text{dist}(p_i, p_j) < 110\text{px} \implies p_j.x \leftarrow p_j.x + 160\text{px}$$
   *(If $p_j.x > 2100\text{px}$, wraps to next row spur $p_j.x = 110\text{px}, p_j.y \leftarrow p_j.y + 70\text{px}$).*
- **Code Implementation**: [`frontend/js/twin_scene.js`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/frontend/js/twin_scene.js#L140-L280).

### 10.3 History State Machine (Undo/Redo Engine)
Maintains discrete snapshot memory for all layout manipulations:
- **Snapshot State Vector**: $\mathcal{S}_k = (\mathcal{V}_k, \mathcal{E}_k, \mathcal{P}_k)$ where $\mathcal{V}$ is station metadata map, $\mathcal{E}$ is edge list, and $\mathcal{P}$ is coordinate registry.
- **Stack Bound**: Depth limited to $N_{\text{max}} = 50$ states.
- **Transitions**:
  - Push: $\text{UndoStack} \leftarrow \text{UndoStack} \cup \{\mathcal{S}_k\}$, $\text{RedoStack} \leftarrow \emptyset$.
  - Undo: $\mathcal{S}_{\text{current}} \leftarrow \text{Pop}(\text{UndoStack})$, $\text{RedoStack} \leftarrow \text{RedoStack} \cup \{\mathcal{S}_{\text{current}}\}$.
  - Redo: $\mathcal{S}_{\text{current}} \leftarrow \text{Pop}(\text{RedoStack})$, $\text{UndoStack} \leftarrow \text{UndoStack} \cup \{\mathcal{S}_{\text{current}}\}$.
- **Code Implementation**: [`frontend/js/topology_editor.js`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/frontend/js/topology_editor.js#L20-L100).

### 10.4 Rail-Conforming Conveyor Geometry & Strict FIFO Fleet Dynamics
Automotive plant conveyor tracking is evaluated through cubic parametric Bernstein Bézier polynomials and discrete-event queue mechanics:
1. **Parametric Conveyor Trajectory**:
   $$\mathbf{B}(t) = (1-t)^3 \mathbf{P}_0 + 3(1-t)^2 t \mathbf{P}_1 + 3(1-t) t^2 \mathbf{P}_2 + t^3 \mathbf{P}_3, \quad t \in [0, 1]$$
   - $\mathbf{P}_0 = (x_1, y_1)$: Exit port of upstream station cradle ($x_{\text{node}} + W_{\text{node}}, y_{\text{node}} + \frac{H_{\text{node}}}{2}$).
   - $\mathbf{P}_1 = (\text{midX}, y_1), \mathbf{P}_2 = (\text{midX}, y_2)$: S-curve cubic control points.
   - $\mathbf{P}_3 = (x_2, y_2)$: Entrance port of downstream station cradle.
2. **Machine Cradle Lock (Capacity = 1)**:
   $$\text{Occupancy}(S_i) \in \{0, 1\}$$
   A station machine cradle admits exactly one vehicle in active machining dwell state at a time.
3. **Strict FIFO Conveyor Queue Spacing**:
   For vehicle $v_j$ in queue position $k \in \{0, 1, 2, \dots\}$ awaiting entry to station $S_i$:
   $$\text{progress}_{\max}(k) = \max\left(0.20, 0.85 - 0.16 \cdot k\right)$$
   Ensures non-overlapping physical queue formation along conveyor infeed rails during stoppages and sequential FIFO admittance upon line resumption.
- **Code Implementation**: [`frontend/js/twin_scene.js`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/frontend/js/twin_scene.js#L250-L450), [`simulator/generator.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/simulator/generator.py#L240-L280).

---

## 11. Summary Traceability Matrix

| Parameter / Metric | Nominal Baseline | Warning Limit | Critical Alarm | Standard / Scientific Source | Code File & Line |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`cycle_time_s`** | $50 - 65\text{ s}$ | $> 1.15 \times T_{\text{target}}$ | $> 1.30 \times T_{\text{target}}$ | Toyota TPS Takt Pace / PRD §3 | [`topology.py:16`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/simulator/topology.py#L16) |
| **`buffer_level`** | $40\% - 70\%$ | $< 25\%$ or $> 80\%$ | $< 10\%$ or $100\%$ | Factory Physics (Hopp & Spearman) | [`propagation.py:42`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/pipeline/propagation.py#L42) |
| **`vibration` (RMS)** | $1.20\text{ mm/s}$ (Robot) / $0.40$ (Conveyor) | $> 2.80\text{ mm/s}$ | **$> 4.50\text{ mm/s}$** | **ISO 10816-3 / ISO 20816-1** | [`spc.py:48`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/pipeline/spc.py#L48) |
| **`temperature` (Oven)** | **$190.0^\circ\text{C}$** | $> 205.0^\circ\text{C}$ | $> 220.0^\circ\text{C}$ | **PPG/Axalta E-Coat Curing Spec** | [`generator.py:159`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/simulator/generator.py#L159) |
| **`temperature` (Bath)** | **$55.0^\circ\text{C}$** | $> 65.0^\circ\text{C}$ | $> 75.0^\circ\text{C}$ | **Henkel Pretreatment Guide** | [`generator.py:161`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/simulator/generator.py#L161) |
| **`power_kw`** | $15 - 55\text{ kW}$ | $> 1.5 \times \text{Base}$ | $> 1.8 \times \text{Base}$ | FANUC Robot Tech Specs / DOE | [`topology.py:18`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/simulator/topology.py#L18) |
| **`spc_z_score`** | $|z| \le 2.0$ | $2.0 < |z| \le 3.0$ | **$|z| > 3.0$** | Montgomery Quality Control / EWMA | [`spc.py:36`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/pipeline/spc.py#L36) |
| **`twin_confidence`** | $90\% - 100\%$ | $65\% - 80\%$ | $< 65\%$ | ISO 23247 / PRD §5.2 Formula | [`confidence.py:18`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/pipeline/confidence.py#L18) |
| **`composite_risk`** | $< 0.15$ | $0.60 - 0.80$ | $> 0.80$ | GBDT Classifier (LightGBM) | [`risk_model.py:14`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/pipeline/risk_model.py#L14) |
| **`time_to_impact`** | $> 20\text{ min}$ | $5 - 15\text{ min}$ | $< 5\text{ min}$ | NetworkX DAG Starvation Flow | [`propagation.py:55`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/pipeline/propagation.py#L55) |
| **`downtime_cost_usd`**| $\$0.00$ | — | **$\$38,333.33\text{ / min}$** | Siemens Downtime Report (2024) | [`recommender.py:12`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/pipeline/recommender.py#L12) |
| **`topology_reset`** | 40 Baseline | — | Factory Recovery | DAG Graph Reconstruction | [`main.py:530`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/api/main.py#L530) |

---

## 12. Synthetic Data Realism Upgrade Log (Phases 17–23)

| Phase | Core Mechanism | Grounded Physics & Math Formulation | Empirical Verification Metric | Source Implementation |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 17** | **Latent AR(1) Load State** | Continuous autoregressive latent state: $\text{load}_t = \rho \cdot \text{load}_{t-1} + \sqrt{1-\rho^2} \cdot \epsilon_t$ ($\rho = 0.70$) driving physical telemetry (vibration, temperature, power, takt). | $\text{Lag-1 Autocorr} = 0.63$, $\text{Corr}(\text{Vib}, \text{Temp}) = +0.65$, $\text{Corr}(\text{CT}, \text{Vib}) = +0.33$. | [`generator.py:164`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/simulator/generator.py#L164) |
| **Phase 18** | **Lognormal Cycle Times** | Right-skewed lognormal machining dwell times: $\text{CT} \sim \text{Lognormal}(\mu, \sigma)$ coupled to $\text{load\_state}$ via $\mu = \ln(\mu_{\text{target}} \cdot \text{mult}) - \frac{\sigma^2}{2}$. | Skewness $> +0.47$ on manual lines; positive tail $> 1.30\times$ takt without artificial hard clipping. | [`generator.py:195`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/simulator/generator.py#L195) |
| **Phase 19** | **Category-Differentiated CV & Multipliers** | Process-stratified parameterization:<br>1. *Automated Precision* ($\text{CV}=0.040, 0.6\times$ defects)<br>2. *Automated Process* ($\text{CV}=0.060, 1.0\times$ defects)<br>3. *Manual Operations* ($\text{CV}=0.130, 2.8\times$ defects). | Precision $\text{CV}=0.0409$, Process $\text{CV}=0.0611$, Manual $\text{CV}=0.1304$; natural defect rates $0.48\%, 0.80\%, 2.24\%$. | [`generator.py:25`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/simulator/generator.py#L25) |
| **Phase 20** | **Decoupled Anomaly Signatures** | Anomaly-specific physical decoupling:<br>- `gradual_drift`: vibration + thermal runaway, active dwell intact.<br>- `sudden_stoppage`: zero active power, zero mechanical vibration, infinite cycle time.<br>- `latent_defect`: invisible upstream, detected at downstream QC.<br>- `energy_waste`: unthrottled idle power draw ($+45\text{ kW}$) without cycle delay. | Zero feature cross-leakage; independent physical sensor channels validated across 5 distinct fault modes. | [`generator.py:220`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/simulator/generator.py#L220) |
| **Phase 21** | **Emergent Tool Wear & Control Group** | Continuous linear/quadratic tool wear accumulation ($\dot{w} = \alpha_{\text{cat}} \cdot (1 + 0.5 \text{load}) + \text{shocks}$), stochastic unscheduled breakdown trigger ($w > 0.85$), periodic maintenance resets, zero-drift control stations (`ST03`, `ST15`, `ST31`). | 1,522 organic failure triggers over 8,500 ticks; Control FP rate ($4.33\%$) vs Drifting ($2.63\%$); 0 hidden variables in feature vector. | [`generator.py:120`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/simulator/generator.py#L120) |
| **Phase 22** | **SPC Baseline Recalibration** | Category-differentiated Shewhart/EWMA variance baseline: $\sigma_{\text{base}} = \max(0.5\text{s}, T_{\text{target}} \cdot \text{CV}_{\text{cat}})$. | Nominal false alarm rate ($|z| > 3.0$) bounded at $0.00\%-0.02\%$; cross-category discrepancy $\le 0.02\%$. | [`spc.py:12`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/pipeline/spc.py#L12) |
| **Phase 23** | **Retrained Model & 7-Regime OOD Suite** | Multi-seed 800,000-row retraining on physics-upgraded generator; GBDT evaluation across 7 operational regimes (Spatial, Symptom, Speed Stress, Severity, Dropout, Emergent Wear). | Held-out Test: Bottleneck ROC-AUC $0.965$, PR-AUC $0.912$, Recall $97.2\%$; Organic Emergent Wear F1 $0.675$ (ROC-AUC $0.881$, PR-AUC $0.785$). | [`train_risk_model.py:1`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/scripts/train_risk_model.py#L1) |

---
*Maintained by Team Twin Flow · Indian Institute of Technology Kanpur (IITK)*
