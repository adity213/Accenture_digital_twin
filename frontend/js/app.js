/**
 * DigitalTwin.ai — TwinSphere SCADA Controller with Zero-Overlap High-Clearance Coordinates
 */

let stationsMeta = {};
let edgesList = [];
let latestTickData = null;
let selectedStationId = "ST06";
let ws = null;
let pollTimer = null;
let currentView = "floor";
let sceneEngine = null;

function getBaselineFactoryCoordinates() {
  return {
    // === ZONE 1: BODY CONSTRUCTION (ST01 - ST14) [Top: 10px, Height: 360px] ===
    "ST01": { x: 100,  y: 130, isParallel: false },
    "ST02": { x: 260,  y: 130, isParallel: false },
    "ST03": { x: 420,  y: 40,  isParallel: true, branch: "FORK: UPPER LH" },
    "ST04": { x: 420,  y: 220, isParallel: true, branch: "FORK: LOWER RH" },
    "ST05": { x: 580,  y: 130, isParallel: false, branch: "MERGE" },
    "ST06": { x: 740,  y: 130, isParallel: false },
    "ST07": { x: 900,  y: 40,  isParallel: true, branch: "FORK: RESPOT A" },
    "ST08": { x: 900,  y: 220, isParallel: true, branch: "FORK: RESPOT B" },
    "ST09": { x: 1060, y: 130, isParallel: false, branch: "MERGE" },
    "ST10": { x: 1220, y: 130, isParallel: false },
    "ST11": { x: 1380, y: 130, isParallel: false },
    "ST12": { x: 1540, y: 130, isParallel: false },
    "ST13": { x: 1700, y: 130, isParallel: false },
    "ST14": { x: 1860, y: 130, isParallel: false },

    // === ZONE 2: PAINT SHOP (ST15 - ST22) [Top: 390px, Height: 190px, Reverse Flow] ===
    "ST15": { x: 1860, y: 420, isParallel: false },
    "ST16": { x: 1610, y: 420, isParallel: false },
    "ST17": { x: 1360, y: 420, isParallel: false },
    "ST18": { x: 1110, y: 420, isParallel: false },
    "ST19": { x: 860,  y: 420, isParallel: false },
    "ST20": { x: 610,  y: 420, isParallel: false },
    "ST21": { x: 360,  y: 420, isParallel: false },
    "ST22": { x: 110,  y: 420, isParallel: false },

    // === ZONE 3: FINAL ASSEMBLY (ST23 - ST40) [Top: 600px, Height: 500px] ===
    // Row 3A (Forward Flow)
    "ST23": { x: 110,  y: 710, isParallel: false },
    "ST24": { x: 270,  y: 710, isParallel: false },
    "ST25": { x: 430,  y: 630, isParallel: true, branch: "FORK: COCKPIT" },
    "ST26": { x: 430,  y: 790, isParallel: true, branch: "FORK: SUSPENSION" },
    "ST27": { x: 590,  y: 710, isParallel: false, branch: "MERGE" },
    "ST28": { x: 750,  y: 710, isParallel: false },
    "ST29": { x: 910,  y: 710, isParallel: false },
    "ST30": { x: 1070, y: 710, isParallel: false },
    "ST31": { x: 1230, y: 710, isParallel: false },
    "ST32": { x: 1390, y: 710, isParallel: false },

    // Row 3B (Reverse Flow)
    "ST33": { x: 1390, y: 940, isParallel: false },
    "ST34": { x: 1210, y: 940, isParallel: false },
    "ST35": { x: 1030, y: 940, isParallel: false },
    "ST36": { x: 850,  y: 940, isParallel: false },
    "ST37": { x: 670,  y: 940, isParallel: false },
    "ST38": { x: 490,  y: 940, isParallel: false },
    "ST39": { x: 310,  y: 940, isParallel: false },
    "ST40": { x: 130,  y: 940, isParallel: false }
  };
}

function resetBaselineCoordinates() {
  window.stationCoords = getBaselineFactoryCoordinates();
}

window.stationCoords = Object.assign(window.stationCoords || {}, getBaselineFactoryCoordinates());

document.addEventListener("DOMContentLoaded", async () => {
  sceneEngine = new TwinSceneEngine("nodes-container", "conveyor-rails-svg");
  await loadStationsTopology();
  initStreaming();
  loadLeadershipData();
  initSchematicInteractivity();
  renderVinTrailGrid();
});

function switchView(viewName) {
  currentView = viewName;
  const dockFloor = document.getElementById("dock-btn-floor");
  const dockLead = document.getElementById("dock-btn-leadership");
  const dockWeekly = document.getElementById("dock-btn-weekly");
  const dockTopology = document.getElementById("dock-btn-topology");
  
  if (dockFloor) dockFloor.classList.toggle("active", viewName === "floor");
  if (dockLead) dockLead.classList.toggle("active", viewName === "leadership");
  if (dockWeekly) dockWeekly.classList.toggle("active", viewName === "weekly");
  if (dockTopology) dockTopology.classList.toggle("active", viewName === "topology");

  const viewFloor = document.getElementById("view-floor");
  const viewLead = document.getElementById("view-leadership");
  const viewWeekly = document.getElementById("view-weekly");
  const viewTopology = document.getElementById("view-topology");

  if (viewFloor) viewFloor.classList.toggle("active", viewName === "floor");
  if (viewLead) viewLead.classList.toggle("active", viewName === "leadership");
  if (viewWeekly) viewWeekly.classList.toggle("active", viewName === "weekly");
  if (viewTopology) viewTopology.classList.toggle("active", viewName === "topology");

  if (viewName === "leadership") loadLeadershipData();
  if (viewName === "topology" && typeof initTopologyEditor === "function") initTopologyEditor();
}

function resetSchematicView() {
  const viewport = document.getElementById("schematic-viewport");
  if (viewport) viewport.scrollTo({ left: 0, top: 0, behavior: "smooth" });
}

async function loadStationsTopology() {
  try {
    const res = await fetch("/api/stations");
    const data = await res.json();
    stationsMeta = data.stations || {};
    edgesList = data.edges || [];
    if (sceneEngine) {
      sceneEngine.renderScene(stationsMeta, edgesList);
    }
    populateFaultStationDropdown();
  } catch (err) {
    console.error("Failed to load stations topology:", err);
  }
}

function initStreaming() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/api/ws/stream`;

  try {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      updateConnectionStatus(true, "● SCADA WS STREAM ACTIVE");
      if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        handleTickUpdate(payload);
      } catch (e) {
        console.error("Error parsing WS payload:", e);
      }
    };

    ws.onerror = () => startPollingFallback("● HTTP POLLING FALLBACK");
    ws.onclose = () => startPollingFallback("● HTTP POLLING FALLBACK");
  } catch (e) {
    startPollingFallback("● HTTP POLLING FALLBACK");
  }
}

function startPollingFallback(statusText) {
  if (pollTimer) return;
  updateConnectionStatus(true, statusText || "● HTTP POLLING ACTIVE");
  pollTickData();
  pollTimer = setInterval(pollTickData, 350);
}

async function pollTickData() {
  try {
    const res = await fetch("/api/risk/current");
    if (res.ok) {
      const payload = await res.json();
      handleTickUpdate(payload);
    }
  } catch (err) {
    console.warn("Polling tick error:", err);
  }
}

function updateConnectionStatus(connected, text) {
  const label = document.getElementById("ws-status-label");
  if (label) {
    label.innerText = text || (connected ? "● SCADA STREAM ACTIVE" : "● OFFLINE");
    label.style.color = connected ? "var(--status-nominal)" : "var(--status-critical)";
  }
}

function handleTickUpdate(payload) {
  latestTickData = payload;

  if (payload.kpis) {
    const k = payload.kpis;
    const confEl = document.getElementById("kpi-confidence");
    if (confEl) confEl.innerText = `${k.fleet_twin_confidence || 94}%`;

    const alertEl = document.getElementById("kpi-alerts");
    if (alertEl) {
      alertEl.innerText = k.active_anomalies_count || 0;
      alertEl.style.color = (k.active_anomalies_count > 0) ? "var(--status-critical)" : "inherit";
    }

    const jphEl = document.getElementById("kpi-jph");
    if (jphEl) jphEl.innerText = k.jobs_per_hour ? k.jobs_per_hour.toFixed(1) : "55.4";

    const savEl = document.getElementById("kpi-savings");
    if (savEl) savEl.innerText = `${(k.total_downtime_avoided_hours || 14.8).toFixed(1)} hrs`;
    const leadSav = document.getElementById("lead-downtime-val");
    if (leadSav) leadSav.innerText = `${(k.total_downtime_avoided_hours || 14.8).toFixed(1)} hrs`;
  }

  const clockEl = document.getElementById("sim-clock");
  if (clockEl && payload.timestamp) {
    clockEl.innerText = payload.timestamp;
  }

  if (payload.stations) {
    let onlineCount = 0;
    Object.keys(payload.stations).forEach((sid) => {
      const st = payload.stations[sid];
      if (!st.is_blackout) onlineCount++;
    });

    const onlineEl = document.getElementById("kpi-machines-online");
    if (onlineEl) onlineEl.innerText = onlineCount;

    if (sceneEngine) {
      sceneEngine.updateTelemetry(payload.stations);
    }
  }

  updateCockpitDrawer(selectedStationId);
}

function selectStation(sid) {
  selectedStationId = sid;
  if (sceneEngine) sceneEngine.selectedId = sid;

  document.querySelectorAll(".station-schematic-node").forEach(n => n.classList.remove("selected"));
  const node = document.getElementById(`station-node-${sid}`);
  if (node) node.classList.add("selected");

  const faultSelect = document.getElementById("fault-target-station");
  if (faultSelect && faultSelect.value !== sid) {
    faultSelect.value = sid;
  }

  updateCockpitDrawer(sid);
}

function updateCockpitDrawer(sid) {
  const meta = stationsMeta[sid];
  if (!meta || !latestTickData || !latestTickData.stations) return;

  const st = latestTickData.stations[sid] || {};

  document.getElementById("focus-sid").innerText = sid;
  document.getElementById("focus-name").innerText = meta.name;
  document.getElementById("focus-zone").innerText = `${meta.zone.toUpperCase()} // ${meta.station_type}`;

  const isBlackout = Boolean(st.is_blackout);
  const isStopped = Boolean(st.is_stopped);

  const tierBadge = document.getElementById("focus-tier");
  if (isBlackout) {
    tierBadge.innerText = "SENSOR BLACKOUT (OFFLINE)";
    tierBadge.className = "node-tier-pill manual";
  } else {
    tierBadge.innerText = `${meta.sensor_tier.toUpperCase()} SENSOR`;
    tierBadge.className = `node-tier-pill ${meta.sensor_tier === 'manual' ? 'manual' : ''}`;
  }

  const ct = st.cycle_time_s || meta.target_cycle_time_s;
  const ctSuffix = isBlackout ? " (VIRTUAL)" : (isStopped ? " (HALT)" : "");
  document.getElementById("focus-ct").innerText = `${ct.toFixed(1)}s${ctSuffix}`;
  const ctFill = document.getElementById("gauge-ct-fill");
  if (ctFill) {
    const pct = Math.min(100, Math.max(10, ((ct - 45) / 35) * 100));
    ctFill.style.width = `${pct}%`;
    ctFill.style.background = isStopped || ct > 72 ? "var(--status-critical)" : (ct > 67 ? "var(--status-warning)" : "var(--status-nominal)");
  }

  const buf = st.buffer_level !== undefined ? st.buffer_level : 4;
  const cap = meta.buffer_capacity_units || 8;
  document.getElementById("focus-buf").innerText = `${buf} / ${cap}`;
  const bufFill = document.getElementById("gauge-buf-fill");
  if (bufFill) {
    const bufPct = Math.min(100, (buf / cap) * 100);
    bufFill.style.width = `${bufPct}%`;
    bufFill.style.background = bufPct >= 90 ? "var(--status-critical)" : (bufPct >= 70 ? "var(--status-warning)" : "var(--status-nominal)");
  }

  const vib = st.vibration !== undefined && st.vibration !== null ? st.vibration : 1.20;
  const isoStatus = isBlackout ? "VIRTUAL" : (st.iso_vibration_status || (vib < 1.12 ? "GOOD" : (vib <= 2.8 ? "SAT" : (vib <= 4.5 ? "WARN" : "CRIT"))));
  document.getElementById("focus-vib").innerText = isBlackout ? "IMPUTED (NO SIGNAL)" : `${vib.toFixed(2)} mm/s (${isoStatus})`;
  const vibFill = document.getElementById("gauge-vib-fill");
  if (vibFill) {
    const vibPct = isBlackout ? 20 : Math.min(100, Math.max(5, (vib / 5.0) * 100));
    vibFill.style.width = `${vibPct}%`;
    vibFill.style.background = isBlackout ? "#94a3b8" : (vib > 4.5 ? "var(--status-critical)" : (vib > 2.8 ? "var(--status-warning)" : "var(--status-nominal)"));
  }

  const temp = st.temperature !== undefined && st.temperature !== null ? st.temperature : 24.0;
  const tempEl = document.getElementById("focus-temp");
  if (tempEl) tempEl.innerText = isBlackout ? "IMPUTED (NO SIGNAL)" : `${temp.toFixed(1)}°C`;
  const tempFill = document.getElementById("gauge-temp-fill");
  if (tempFill) {
    const tempPct = isBlackout ? 15 : Math.min(100, Math.max(8, (temp / 210.0) * 100));
    tempFill.style.width = `${tempPct}%`;
    tempFill.style.background = isBlackout ? "#94a3b8" : (temp > 200.0 ? "var(--status-critical)" : (temp > 65.0 && temp < 180.0 ? "var(--status-warning)" : "var(--status-nominal)"));
  }

  const pwr = st.power_kw || meta.power_base_kw || 30.0;
  document.getElementById("focus-power").innerText = isBlackout ? "IMPUTED" : `${pwr.toFixed(1)} kW`;
  const pwrFill = document.getElementById("gauge-power-fill");
  if (pwrFill) {
    const pwrPct = isBlackout ? 20 : Math.min(100, (pwr / 75.0) * 100);
    pwrFill.style.width = `${pwrPct}%`;
    pwrFill.style.background = isBlackout ? "#94a3b8" : (pwr > (meta.power_base_kw || 30.0) * 1.5 ? "var(--status-warning)" : "var(--status-nominal)");
  }

  const conf = st.twin_confidence !== undefined ? st.twin_confidence : 95.0;
  const spcTrend = isBlackout ? "BLACKOUT" : (st.spc_trend || "STABLE");
  const confEl = document.getElementById("focus-spc-conf");
  if (confEl) confEl.innerText = `${conf.toFixed(0)}% (${spcTrend})`;
  const confFill = document.getElementById("gauge-conf-fill");
  if (confFill) {
    confFill.style.width = `${Math.min(100, Math.max(5, conf))}%`;
    confFill.style.background = conf < 65 ? "var(--status-critical)" : (conf < 80 ? "var(--status-warning)" : "var(--status-nominal)");
  }

  const propList = document.getElementById("focus-prop-list");
  const propCountEl = document.getElementById("prop-count");
  propList.innerHTML = "";

  const propMap = latestTickData.propagation || {};
  const impacted = propMap[sid] || [];

  if (propCountEl) propCountEl.innerText = `${impacted.length} AT RISK`;

  if (impacted.length === 0) {
    propList.innerHTML = `<div style="font-size: 0.76rem; color: var(--text-secondary); font-family: var(--font-mono); padding: 4px 0;">Nominal line flow — zero starvation ripple.</div>`;
  } else {
    impacted.forEach(item => {
      const row = document.createElement("div");
      row.className = "countdown-row";
      row.innerHTML = `
        <span style="font-weight: 700; color: var(--status-warning);">${item.station_id}</span>
        <span style="font-weight: 800; color: var(--status-critical);">${item.time_to_impact_min}m countdown</span>
      `;
      propList.appendChild(row);
    });
  }

  const recs = latestTickData.recommendations || [];
  const stRec = recs.find(r => r.station_id === sid) || recs[0];

  if (stRec) {
    document.getElementById("rec-title").innerText = stRec.title;
    document.getElementById("rec-action").innerText = stRec.recommended_action || stRec.rationale;
    document.getElementById("rec-impact").innerText = `Impact: ${stRec.expected_impact || `${stRec.downtime_avoided_min || 0} min line starvation avoided`}`;
    document.getElementById("rec-conf-tag").innerText = `${Math.round((stRec.confidence || 0.9) * 100)}% CONFIDENCE`;
  }
}

function initSchematicInteractivity() {
  const viewport = document.getElementById("schematic-viewport");
  if (!viewport) return;

  let isDown = false;
  let startX, startY;
  let scrollLeft, scrollTop;

  viewport.addEventListener("mousedown", (e) => {
    if (e.target.closest(".station-schematic-node")) return;
    isDown = true;
    viewport.style.cursor = "grabbing";
    startX = e.pageX - viewport.offsetLeft;
    startY = e.pageY - viewport.offsetTop;
    scrollLeft = viewport.scrollLeft;
    scrollTop = viewport.scrollTop;
  });

  viewport.addEventListener("mouseleave", () => {
    isDown = false;
    viewport.style.cursor = "default";
  });

  viewport.addEventListener("mouseup", () => {
    isDown = false;
    viewport.style.cursor = "default";
  });

  viewport.addEventListener("mousemove", (e) => {
    if (!isDown) return;
    e.preventDefault();
    const x = e.pageX - viewport.offsetLeft;
    const y = e.pageY - viewport.offsetTop;
    viewport.scrollLeft = scrollLeft - (x - startX) * 1.5;
    viewport.scrollTop = scrollTop - (y - startY) * 1.5;
  });
}

async function controlSim(action) {
  try {
    const res = await fetch("/api/simulator/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action })
    });
    const data = await res.json();
    console.log("Sim control:", data);
  } catch (err) {
    console.error("Control error:", err);
  }
}

async function setSpeed(mult, btn) {
  document.querySelectorAll(".speed-tick").forEach(b => b.classList.remove("selected"));
  if (btn) btn.classList.add("selected");
  try {
    await fetch("/api/simulator/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "speed", speed_multiplier: mult })
    });
  } catch (err) {
    console.error("Speed error:", err);
  }
}

async function injectAnomaly(anomalyType, stationId) {
  try {
    const res = await fetch("/api/simulator/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "inject_anomaly",
        anomaly_type: anomalyType,
        station_id: stationId
      })
    });
    const data = await res.json();
    if (data.payload) {
      handleTickUpdate(data.payload);
    }
    selectStation(stationId);
    console.log("Injected anomaly successfully:", data);
  } catch (err) {
    console.error("Injection error:", err);
  }
}

async function clearAllAnomalies() {
  try {
    const res = await fetch("/api/simulator/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "clear_anomalies" })
    });
    const data = await res.json();
    if (data.payload) {
      handleTickUpdate(data.payload);
    }
    selectStation(selectedStationId);
    console.log("Cleared all anomalies:", data);
  } catch (err) {
    console.error("Error clearing anomalies:", err);
  }
}

function populateFaultStationDropdown() {
  const select = document.getElementById("fault-target-station");
  if (!select) return;
  select.innerHTML = "";

  const sids = Object.keys(stationsMeta);
  sids.forEach(sid => {
    const meta = stationsMeta[sid];
    const opt = document.createElement("option");
    opt.value = sid;
    opt.innerText = `${sid}: ${meta.name || sid}`;
    if (sid === selectedStationId) opt.selected = true;
    select.appendChild(opt);
  });
}

function onFaultStationSelectChange(sid) {
  selectStation(sid);
}

function injectCustomFault() {
  const stationSelect = document.getElementById("fault-target-station");
  const typeSelect = document.getElementById("fault-type-select");
  const sid = stationSelect ? stationSelect.value : selectedStationId;
  const atype = typeSelect ? typeSelect.value : "stoppage";
  injectAnomaly(atype, sid);
}

function injectFocusedFault(atype) {
  injectAnomaly(atype, selectedStationId);
}

async function loadLeadershipData() {
  try {
    const res = await fetch("/api/leadership/summary");
    const data = await res.json();
    renderThermalHeatmap(data.heatmap || []);
    renderParetoCauses(data.root_causes || []);
  } catch (err) {
    console.warn("Leadership load error:", err);
  }
}

function renderThermalHeatmap(heatmapData) {
  const container = document.getElementById("thermal-heatmap");
  if (!container) return;
  container.innerHTML = "";

  const sids = Object.keys(stationsMeta);
  sids.forEach(sid => {
    const row = document.createElement("div");
    row.className = "thm-row";

    const lbl = document.createElement("span");
    lbl.className = "thm-sid";
    lbl.innerText = sid;
    row.appendChild(lbl);

    for (let i = 0; i < 20; i++) {
      const cell = document.createElement("div");
      cell.className = "thm-cell";
      const isAnomaly = (sid === "ST06" && i > 11) || (sid === "ST02" && i > 14);
      if (isAnomaly) {
        cell.style.background = "var(--status-critical)";
      } else {
        cell.style.background = "var(--status-nominal-bg)";
        cell.style.border = "1px solid var(--border-subtle)";
      }
      row.appendChild(cell);
    }

    container.appendChild(row);
  });
}

function renderParetoCauses(causes) {
  const container = document.querySelector(".root-cause-list");
  const weeklyContainer = document.querySelector(".root-cause-list-weekly");
  if (!container) return;
  container.innerHTML = "";
  if (weeklyContainer) weeklyContainer.innerHTML = "";

  const defaultCauses = [
    { title: "Servo Drive Over-Current (Framing Line ST06)", pct: "34%", icon: "⚡" },
    { title: "Air Pressure Drop in Adhesive Sealers (ST09)", pct: "22%", icon: "💨" },
    { title: "Nutrunner Calibration Drift (Torquing ST35)", pct: "15%", icon: "🔧" },
    { title: "Blower Fan Bearing Wear (Paint Oven ST17)", pct: "11%", icon: "🌀" }
  ];

  const items = (causes && causes.length) ? causes : defaultCauses;
  items.forEach(c => {
    const div = document.createElement("div");
    div.style.padding = "10px 12px";
    div.style.background = "#f8fafc";
    div.style.border = "1px solid var(--border-subtle)";
    div.style.borderRadius = "var(--radius-sm)";
    div.style.marginBottom = "8px";
    div.innerHTML = `
      <div style="display: flex; justify-content: space-between; font-size: 0.78rem; font-family: var(--font-brand); font-weight: 700; color: var(--text-primary);">
        <span>${c.icon || '⚡'} ${c.title}</span>
        <span style="color: var(--brand-blue); font-family: var(--font-mono); font-weight: 800;">${c.pct}</span>
      </div>
      <div style="width: 100%; background: #e2e8f0; height: 5px; border-radius: 999px; margin-top: 6px; overflow: hidden;">
        <div style="background: var(--brand-blue); height: 100%; width: ${c.pct};"></div>
      </div>
    `;
    container.appendChild(div.cloneNode(true));
    if (weeklyContainer) weeklyContainer.appendChild(div);
  });
}

function renderVinTrailGrid() {
  const container = document.getElementById("vin-trail-container");
  if (!container) return;
  container.innerHTML = "";

  for (let i = 1; i <= 40; i++) {
    const sid = `ST${i.toString().padStart(2, '0')}`;
    const node = document.createElement("div");
    node.className = "vin-tick-node passed";
    node.innerText = sid;
    container.appendChild(node);
  }
}

async function traceGenealogy() {
  const input = document.getElementById("genealogy-input");
  const vin = input ? input.value.trim() : "VIN-2026-01042";
  const resultEl = document.getElementById("genealogy-result");
  if (!resultEl) return;

  try {
    const res = await fetch(`/api/genealogy/${vin}`);
    const data = await res.json();
    resultEl.innerHTML = `
      <span style="color: var(--status-nominal); font-weight: 700;">${data.vin || vin}:</span> 
      ${data.total_stations_visited || 40}/40 Stations Visited • 
      Defects Detected: <strong style="color: var(--status-nominal);">${data.defects_detected || 0}</strong> • 
      Quality Gate: <strong style="color: var(--status-nominal); text-transform: uppercase;">${data.status || 'PASSED BUY-OFF'}</strong>
    `;
  } catch (err) {
    resultEl.innerHTML = `<span style="color: var(--status-critical);">Failed to trace ${vin}.</span>`;
  }
}

function updateLineBalancing(val) {
  const lbl = document.getElementById("slider-target-val");
  if (lbl) lbl.innerText = `Target JPH: ${val} U/hr`;
}
