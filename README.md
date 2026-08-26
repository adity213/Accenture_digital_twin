# DigitalTwin.ai — Predictive Automotive Assembly Intelligence Engine
**Accenture Innovation Challenge 2026 · Round 2 · Problem Track 4**  
*Team Twin Flow:* Aditya Singh · Divyansh Singh Mertia · Harshada Rajhans (IIT Kanpur)

---

## 🚀 Overview
DigitalTwin.ai is an end-to-end predictive digital twin prototype for automotive manufacturing lines. It addresses the core failure modes of modern high-speed automotive plants (unplanned line stoppages costing up to $2.3M/hour) by moving from reactive alarms to **predictive risk forecasting, virtual sensing, and graph-propagated decision intelligence**.

```
  Synthetic Simulator (40 Stations)
                │
                ▼
  SQLite & In-Memory Ring Buffer
                │
                ▼
  SPC & Virtual Sensor Engine (80/20 Tier Split)
                │
                ▼
  LightGBM / GBDT Predictive Risk Model (Chronological 70/30 Split)
                │
                ▼
  NetworkX Graph Propagation Layer (Starvation Countdowns)
                │
                ▼
  Actionable Recommendation Engine (Dynamic Cost & Downtime Impact)
                │
                ▼
  FastAPI REST + Real-Time WebSocket Streaming
                │
                ▼
  Dual Persona UI: Floor Supervisor (2.5D Schematic) & Plant Leadership
```

---

## 📊 Core Parameters & Operating Threshold Derivation

| Simplified Parameter Name | Technical Name | Normal Operating Range | Warning Threshold (Amber) | Critical Threshold (Red) | Engineering Derivation & Physical Rationale |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Processing Time** | `cycle_time_s` | $50 - 65	ext{ s}$ | $> 1.15	imes 	ext{ Target}$ ($z > 2.0$) | $> 1.30	imes 	ext{ Target}$ ($z > 3.0$) | Calibrated to plant takt time ($55-60	ext{ JPH}$). Natural variation is $\pm 3\sigma$ ($\sigma pprox 4\%$). Progressive drift signals tip wear/motor friction; sudden $10	imes$ surge signals stoppage. |
| **Waiting Line (Queue)** | `buffer_level` | $4 - 8	ext{ units}$ ($40-70\%$) | $< 25\%$ or $> 80\%$ | $< 10\%$ (Starvation) or $100\%$ (Blockage) | Buffer capacity is $5-15	ext{ cars}$. $<25\%$ fill gives downstream machines $<5	ext{ mins}$ before running dry. $>80\%$ fill blocks upstream discharge. |
| **Machine Shaking** | `vibration` (RMS) | $0.6 - 1.2	ext{ mm/s}$ | $1.2 - 2.0	ext{ mm/s}$ | $> 2.0	ext{ mm/s}$ | Derived from **ISO 10816-3 Industrial Vibration Severity Standard**. $>2.0	ext{ mm/s}$ indicates severe bearing fatigue or loose robot joints. |
| **Motor Heat** | `temperature` | $20^\circ	ext{C} - 35^\circ	ext{C}$ | $> 45^\circ	ext{C}$ | $> 65^\circ	ext{C}$ | Thermal dissipation of servomotors and paint ovens. Overheating accelerates insulation breakdown and mechanical seizure. |
| **Power Draw** | `power_kw` | $15 - 40	ext{ kW}$ | $> 1.5	imes 	ext{ Base}$ | $> 1.8	imes 	ext{ Base}$ | Base active motor load ($20	ext{ kW}$ Body, $60	ext{ kW}$ Paint, $15	ext{ kW}$ Assembly). $>1.8	imes$ draw while queue is empty indicates high idle energy waste. |
| **Sensor Trust Score** | `twin_confidence` | $90\% - 100\%$ | $65\% - 80\%$ | $< 65\%$ | Weighted by PRD Section 5.2 formula: $0.5 \cdot C_{	ext{tier}} + 0.3 \cdot C_{	ext{recency}} + 0.2 \cdot C_{	ext{agreement}}$. Drops when sensors blackout or manual logs age. |
| **Stoppage Chance** | `composite_risk` | $< 15\%$ | $60\% - 80\%$ | $> 80\%$ | GBDT classifier output predicting probability of line bottleneck within the next 15 minutes. |
| **Starvation Countdown** | `time_to_impact` | $> 20	ext{ mins}$ | $5 - 15	ext{ mins}$ | $< 5	ext{ mins}$ | $	ext{time\_to\_impact} = rac{	ext{buffer\_units}}{	ext{outflow} - 	ext{inflow}} 	imes T_{	ext{target}}$. Time remaining before downstream station exhausts buffer. |
| **Cars Built Per Hour** | `jobs_per_hour` | $50 - 60	ext{ JPH}$ | $35 - 50	ext{ JPH}$ | $< 35	ext{ JPH}$ | Actual count of completed vehicles traversing `ST01` through `ST40` per elapsed hour. |

---

## 🌟 Key Features
1. **40-Station Line Topology (DAG with Parallel Paths)**:
   - Body Construction (14 stations), Paint Shop (8 stations), Final Assembly (18 stations).
   - 80% Rich PLC-instrumented / 20% Manual checklist stations.
2. **Synthetic Data Simulator with 5 Ground-Truth Anomaly Types**:
   - Gradual Equipment Drift, 85-min Sudden Stoppage, Latent Defect Genealogy, Sensor Blackout, Energy Surge.
3. **Statistical Process Control (SPC) & Virtual Sensing**:
   - EWMA ($\lambda=0.3$) and rolling $z$-scores ($|z|>3.0$ detection).
   - Multi-source virtual sensor imputation with Twin Confidence scoring ($0-100\%$).
4. **Predictive Risk Model**:
   - Predicts $P(	ext{bottleneck in 15 mins})$ and $P(	ext{defect})$.
   - Evaluated on precision/recall/AUC with zero ground-truth data leakage.
5. **Graph-Based Ripple Propagation**:
   - Computes dynamic downstream starvation countdown:
     $$	ext{time\_to\_impact} = rac{	ext{buffer\_units}}{	ext{outflow} - 	ext{inflow}} 	imes 60	ext{ s}$$
6. **Dual Persona Dashboard**:
   - **Floor Supervisor View**: Interactive 2.5D schematic, drill-down dials, and 1-click anomaly injection.
   - **Leadership View**: Downtime avoided ($3.4M savings), processing time heatmaps, and genealogy traceability.

---

## 🛠️ Quick Start & Running Tests

```bash
# 1. Navigate to directory
cd "c:/Android Projects/accenture/digitaltwin-ai"

# 2. Run test suite to verify all phase gates
python run_direct_tests.py

# 3. Launch FastAPI Server & Frontend
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser at: `http://localhost:8000`
