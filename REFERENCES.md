# 📚 DigitalTwin.ai — Industrial Metrics & Standards Reference Sheet
**Accenture Innovation Challenge 2026 · Problem Track 4**  
*Team Twin Flow:* Aditya Singh · Divyansh Singh Mertia · Harshada Rajhans (IIT Kanpur)

---

## 📌 Executive Summary
This document serves as the authoritative, mathematical, and empirical reference registry for all parameters, operating thresholds, physical constants, algorithms, and business impact equations utilized within **DigitalTwin.ai**. Every metric is mapped to its underlying industrial standard, academic literature source, OEM manufacturing benchmark, and codebase implementation.

---

## 📑 Quick Navigation
1. [Line Operations & Takt Time Physics](#1-line-operations--takt-time-physics)
2. [Thermal & Thermodynamic Standards](#2-thermal--thermodynamic-standards)
3. [Vibration & Mechanical Health Standards (ISO 10816 / ISO 20816)](#3-vibration--mechanical-health-standards)
4. [Electrical Power & Energy Consumption](#4-electrical-power--energy-consumption)
5. [Statistical Process Control (SPC) & Quality Engineering](#5-statistical-process-control-spc--quality-engineering)
6. [Virtual Sensing & Confidence Scoring](#6-virtual-sensing--confidence-scoring)
7. [Predictive Risk Machine Learning & Graph Propagation](#7-predictive-risk-machine-learning--graph-propagation)
8. [Business Economics & Downtime Financial Modeling](#8-business-economics--downtime-financial-modeling)
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
- **Algorithms**: Histogram-Based Gradient Boosted Decision Tree (`HistGradientBoostingClassifier`) / LightGBM.
- **Predictive Horizons**:
  - $P(\text{Bottleneck within next 15 minutes})$
  - $P(\text{Defect associated with station output})$
- **Feature Vector ($D=11$, Strict Zero Data Leakage)**:
  1. `actual_processing_time / target_cycle_time_s` (Cycle Time Ratio)
  2. `buffer_level / buffer_capacity` (Buffer Utilization)
  3. `spc_drift_momentum` ($\{-1.0, 0.0, 1.0\}$)
  4. `spc_z_score` (Standardized deviation)
  5. `sensor_confidence` ($0.0 - 1.0$)
  6. `max_upstream_risk` ($0.0 - 1.0$)
  7. `mean_upstream_risk` ($0.0 - 1.0$)
  8. `shift_tick_sin` ($\sin(2\pi \cdot \text{tick} / 480)$ — 8-hour shift diurnal phase)
  9. `shift_tick_cos` ($\cos(2\pi \cdot \text{tick} / 480)$)
  10. `motor_heat_temperature` ($^\circ\text{C}$)
  11. `machine_shaking_vibration` ($\text{mm/s}$)
- **Chronological Validation**: Strict chronological 70% train / 30% test split without random temporal shuffling (preventing time-series data leakage).
- **Target Performance**: Area Under the ROC Curve ($\text{AUC} \ge 0.85$), Lead time advance warning $\ge 12\text{ minutes}$.
- **Exact Source**:
  - Ke, G., Meng, Q., Finley, T., et al. (2017). *LightGBM: A highly efficient gradient boosting decision tree*. Advances in Neural Information Processing Systems (NeurIPS 30).
  - *Technical PRD Section 5.3 & Acceptance Criteria*.
- **Code Implementation**: [`pipeline/risk_model.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/pipeline/risk_model.py), [`tests/test_pipeline.py`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/tests/test_pipeline.py#L35-L75).

### 7.2 Downstream Starvation Countdown Equation
Models bottleneck starvation wave propagation across the line DAG topology:

$$\text{time\_to\_impact}_{u \rightarrow v} = \frac{\text{BufferUnitsRemaining}_v}{\max\left(0.10, \text{OutflowRate}_v - \text{InflowRate}_u\right)} \times T_{\text{target}, v}$$

Where:
- Graph traversal tracks all reachable topological descendants in directed acyclic order.
- Decayed risk propagation applies structural damping:
  $$\text{Risk}_{\text{propagated}}(v) = \text{Risk}(u) \cdot \gamma^{\text{dist}(u,v)} \cdot \left(1.0 - \frac{\text{BufferLevel}_v}{\text{BufferCap}_v}\right)$$
  ($\gamma = 0.85$ decay factor).
- **Exact Source**:
  - *Technical PRD Section 5.4 (Graph Propagation Layer)*.
  - NetworkX Graph Algorithms Library (Hagberg et al., 2008).
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

---

## 9. Summary Traceability Matrix

| Parameter / Metric | Nominal Baseline | Warning Limit | Critical Alarm | Standard / Scientific Source | Code File & Line |
| :--- | :---: | :---: | :---: | :--- | :--- |
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

---
*Maintained by Team Twin Flow · Indian Institute of Technology Kanpur (IITK)*
