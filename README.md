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
> 📘 **Full Industrial Standards & Mathematics Registry**: See the comprehensive [`REFERENCES.md`](file:///c:/Android%20Projects/accenture/digitaltwin-ai/REFERENCES.md) for full mathematical formulations, OEM citations, and code mapping.

| Simplified Parameter Name | Technical Name | Normal Operating Range | Warning Threshold (Amber) | Critical Threshold (Red) | Engineering Derivation & Physical Rationale |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Processing Time** | `cycle_time_s` | $50 - 65\text{ s}$ | $> 1.15 \times \text{Target}$ ($z > 2.0$) | $> 1.30 \times \text{Target}$ ($z > 3.0$) | Calibrated to plant takt time ($55-60\text{ JPH}$). Natural variation is $\pm 3\sigma$ ($\sigma \approx 4\%$). Progressive drift signals tip wear/motor friction; sudden surge signals stoppage. |
| **Waiting Line (Queue)** | `buffer_level` | $4 - 8\text{ units}$ ($40-70\%$) | $< 25\%$ or $> 80\%$ | $< 10\%$ (Starvation) or $100\%$ (Blockage) | Buffer capacity is $5-15\text{ cars}$. $<25\%$ fill gives downstream machines $<5\text{ mins}$ before running dry. $>80\%$ fill blocks upstream discharge. |
| **Machine Shaking** | `vibration` (RMS) | $0.4 - 1.2\text{ mm/s}$ | $2.8 - 4.5\text{ mm/s}$ (Zone C) | **$> 4.5\text{ mm/s}$** (Zone D Alarm) | Derived from **ISO 10816-3 / ISO 20816-1 Industrial Vibration Severity Standard**. $>4.5\text{ mm/s}$ signals imminent bearing/spindle seizure. |
| **Motor & Process Heat** | `temperature` | $24^\circ\text{C}$ (Ambient)<br>$55^\circ\text{C}$ (Pretreatment)<br>$190^\circ\text{C}$ (Oven) | $> 65^\circ\text{C}$ (Bath)<br>$> 205^\circ\text{C}$ (Oven) | $> 75^\circ\text{C}$ (Bath)<br>$> 220^\circ\text{C}$ (Oven) | **PPG/Axalta E-Coat Curing** ($180-200^\circ\text{C}$ crosslinking) & **Henkel Bath Guide** ($50-60^\circ\text{C}$). Overheating accelerates insulation breakdown & paint defects. |
| **Power Draw** | `power_kw` | $15 - 55\text{ kW}$ | $> 1.5 \times \text{Base}$ | $> 1.8 \times \text{Base}$ | Base active motor load ($28-32\text{ kW}$ Weld, $55\text{ kW}$ Oven, $15-50\text{ kW}$ Assembly). $>1.8\times$ draw while queue is empty indicates high idle energy waste. |
| **Sensor Trust Score** | `twin_confidence` | $90\% - 100\%$ | $65\% - 80\%$ | $< 65\%$ | Weighted by PRD Section 5.2 formula: $0.5 \cdot C_{\text{tier}} + 0.3 \cdot C_{\text{recency}} + 0.2 \cdot C_{\text{agreement}}$. Drops when sensors blackout or manual logs age. |
| **Stoppage Chance** | `composite_risk` | $< 15\%$ | $60\% - 80\%$ | $> 80\%$ | GBDT classifier output predicting probability of line bottleneck within the next 15 minutes. |
| **Starvation Countdown** | `time_to_impact` | $> 20\text{ mins}$ | $5 - 15\text{ mins}$ | $< 5\text{ mins}$ | $\text{time\_to\_impact} = \frac{\text{buffer\_units}}{\text{outflow} - \text{inflow}} \times T_{\text{target}}$. Time remaining before downstream station exhausts buffer. |
| **Cars Built Per Hour** | `jobs_per_hour` | $50 - 60\text{ JPH}$ | $35 - 50\text{ JPH}$ | $< 35\text{ JPH}$ | Actual count of completed vehicles traversing `ST01` through `ST40` per elapsed hour. |

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
