/**
 * DigitalTwin.ai — TwinSphere SCADA Controller with Zero-Overlap High-Clearance Coordinates
 */

// Auto-route API calls to localhost:8000 if opened directly from filesystem
const originalFetch = window.fetch;
window.fetch = async function(...args) {
  if (typeof args[0] === 'string' && args[0].startsWith('/api/')) {
    if (window.location.protocol === 'file:') {
      args[0] = 'http://localhost:8000' + args[0];
    }
  }
  return originalFetch.apply(this, args);
};

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
    // === ZONE 1: BODY CONSTRUCTION (ST01 - ST14) [Top: 10px, Height: 430px, Forward Flow] ===
    "ST01": { x: 80,   y: 170, isParallel: false },
    "ST02": { x: 310,  y: 170, isParallel: false },
    "ST03": { x: 540,  y: 35,  isParallel: true, branch: "FORK: UPPER LH" },
    "ST04": { x: 540,  y: 305, isParallel: true, branch: "FORK: LOWER RH" },
    "ST05": { x: 770,  y: 170, isParallel: false, branch: "MERGE" },
    "ST06": { x: 1000, y: 170, isParallel: false },
    "ST07": { x: 1230, y: 35,  isParallel: true, branch: "FORK: RESPOT A" },
    "ST08": { x: 1230, y: 305, isParallel: true, branch: "FORK: RESPOT B" },
    "ST09": { x: 1460, y: 170, isParallel: false, branch: "MERGE" },
    "ST10": { x: 1690, y: 170, isParallel: false },
    "ST11": { x: 1920, y: 170, isParallel: false },
    "ST12": { x: 2150, y: 170, isParallel: false },
    "ST13": { x: 2380, y: 170, isParallel: false },
    "ST14": { x: 2610, y: 170, isParallel: false },

    // === ZONE 2: PAINT SHOP (ST15 - ST22) [Top: 450px, Height: 210px, Reverse Flow Right-to-Left] ===
    "ST15": { x: 2610, y: 480, isParallel: false },
    "ST16": { x: 2248, y: 480, isParallel: false },
    "ST17": { x: 1886, y: 480, isParallel: false },
    "ST18": { x: 1524, y: 480, isParallel: false },
    "ST19": { x: 1162, y: 480, isParallel: false },
    "ST20": { x: 800,  y: 480, isParallel: false },
    "ST21": { x: 438,  y: 480, isParallel: false },
    "ST22": { x: 80,   y: 480, isParallel: false },

    // === ZONE 3: FINAL ASSEMBLY (ST23 - ST40) [Top: 670px, Height: 580px] ===
    // Row 3A (Forward Flow Left-to-Right)
    "ST23": { x: 80,   y: 810, isParallel: false },
    "ST24": { x: 310,  y: 810, isParallel: false },
    "ST25": { x: 540,  y: 685, isParallel: true, branch: "FORK: COCKPIT" },
    "ST26": { x: 540,  y: 935, isParallel: true, branch: "FORK: SUSPENSION" },
    "ST27": { x: 770,  y: 810, isParallel: false, branch: "MERGE" },
    "ST28": { x: 1000, y: 810, isParallel: false },
    "ST29": { x: 1230, y: 810, isParallel: false },
    "ST30": { x: 1460, y: 810, isParallel: false },
    "ST31": { x: 1690, y: 810, isParallel: false },
    "ST32": { x: 1920, y: 810, isParallel: false },

    // Row 3B (Reverse Flow Right-to-Left)
    "ST33": { x: 1920, y: 1100, isParallel: false },
    "ST34": { x: 1657, y: 1100, isParallel: false },
    "ST35": { x: 1394, y: 1100, isParallel: false },
    "ST36": { x: 1131, y: 1100, isParallel: false },
    "ST37": { x: 868,  y: 1100, isParallel: false },
    "ST38": { x: 605,  y: 1100, isParallel: false },
    "ST39": { x: 342,  y: 1100, isParallel: false },
    "ST40": { x: 80,   y: 1100, isParallel: false }
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
  updateLineBalancing(55);
});
function switchView(viewName) {
  currentView = viewName;
  const dockFloor = document.getElementById("dock-btn-floor");
  const dockLead = document.getElementById("dock-btn-leadership");
  const dockPlantManager = document.getElementById("dock-btn-plant-manager");
  const dockOperator = document.getElementById("dock-btn-operator");
  const dockWeekly = document.getElementById("dock-btn-weekly");
  const dockTopology = document.getElementById("dock-btn-topology");
  
  if (dockFloor) dockFloor.classList.toggle("active", viewName === "floor");
  if (dockLead) dockLead.classList.toggle("active", viewName === "leadership");
  if (dockPlantManager) dockPlantManager.classList.toggle("active", viewName === "plant-manager");
  if (dockOperator) dockOperator.classList.toggle("active", viewName === "operator");
  if (dockWeekly) dockWeekly.classList.toggle("active", viewName === "weekly");
  if (dockTopology) dockTopology.classList.toggle("active", viewName === "topology");

  const viewFloor = document.getElementById("view-floor");
  const viewLead = document.getElementById("view-leadership");
  const viewPlantManager = document.getElementById("view-plant-manager");
  const viewOperator = document.getElementById("view-operator");
  const viewWeekly = document.getElementById("view-weekly");
  const viewTopology = document.getElementById("view-topology");

  if (viewFloor) viewFloor.classList.toggle("active", viewName === "floor");
  if (viewLead) viewLead.classList.toggle("active", viewName === "leadership");
  if (viewPlantManager) viewPlantManager.classList.toggle("active", viewName === "plant-manager");
  if (viewOperator) viewOperator.classList.toggle("active", viewName === "operator");
  if (viewWeekly) viewWeekly.classList.toggle("active", viewName === "weekly");
  if (viewTopology) viewTopology.classList.toggle("active", viewName === "topology");

  if (viewName === "leadership" || viewName === "plant-manager") {
    if (viewName === "leadership") {
      loadLeadershipData();
    } else {
      loadAssignments();
      renderVinTrailGrid();
    }
    if (!window._leadershipRefreshTimer) {
      window._leadershipRefreshTimer = setInterval(() => {
        if (currentView === "leadership" || currentView === "plant-manager") {
          loadLeadershipData();
        } else {
          clearInterval(window._leadershipRefreshTimer);
          window._leadershipRefreshTimer = null;
        }
      }, 3000);
    }
  } else {
    if (window._leadershipRefreshTimer) {
      clearInterval(window._leadershipRefreshTimer);
      window._leadershipRefreshTimer = null;
    }
  }

  if (viewName === "operator") {
    loadAssignments();
    renderOperatorView();
  }

  if (viewName === "weekly") {
    loadLeadershipData();
    const slider = document.getElementById("whatif-jph-slider");
    updateLineBalancing(slider ? slider.value : 55);
  }

  if (viewName === "topology" && typeof initTopologyEditor === "function") {
    initTopologyEditor();
  }
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
      sceneEngine.renderScene(stationsMeta, edgesList, data.active_vehicles || []);
    }
    populateFaultStationDropdown();
  } catch (err) {
    console.error("Failed to load stations topology:", err);
  }
}

function initStreaming() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  let wsUrl = `${protocol}//${window.location.host}/api/ws/stream`;
  if (window.location.protocol === 'file:') {
    wsUrl = `ws://localhost:8000/api/ws/stream`;
  }

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

    // Option 1: Andon Ingress Lock Indicator
    const andonPill = document.getElementById("andon-status-pill");
    const andonText = document.getElementById("andon-status-text");
    const isAndon = Boolean(k.andon_ingress_locked);
    if (andonPill) {
      if (isAndon) {
        andonPill.style.display = "inline-flex";
        if (andonText) {
          const reason = k.andon_reason ? ` // ${k.andon_reason}` : "";
          andonText.innerText = `🛑 ANDON LOCK: INGRESS HALTED${reason}`;
          andonPill.title = k.andon_reason || "Line ingress halted due to active issue on assembly line";
        }
      } else {
        andonPill.style.display = "none";
      }
    }
  }

  const clockEl = document.getElementById("sim-clock");
  if (clockEl && payload.timestamp) {
    clockEl.innerText = payload.timestamp;
  }

  if (payload.stations) {
    let onlineCount = 0;
    const totalStations = Object.keys(payload.stations).length || 40;
    Object.keys(payload.stations).forEach((sid) => {
      const st = payload.stations[sid];
      if (!st.is_blackout && !st.is_stopped) onlineCount++;
    });

    const onlineEl = document.getElementById("kpi-machines-online");
    if (onlineEl) onlineEl.innerText = `${onlineCount}/${totalStations}`;

    if (sceneEngine) {
      sceneEngine.updateTelemetry(payload.stations, payload.vehicles);
    }
  }

  if (currentView === "operator") {
    renderOperatorView();
  }

  updateCockpitDrawer(selectedStationId);
}

window.traceVinFromVehicle = function(vin) {
  if (!vin) return;
  switchView('plant-manager');
  const input = document.getElementById("genealogy-input");
  if (input) input.value = vin;
  setTimeout(() => {
    traceGenealogy();
  }, 120);
};

function selectStation(sid) {
  selectedStationId = sid;
  if (sceneEngine) sceneEngine.selectedId = sid;

  document.querySelectorAll(".station-schematic-node").forEach(n => {
    n.classList.remove("selected");
  });
  const node = document.getElementById(`station-node-${sid}`);
  if (node) node.classList.add("selected");

  const faultSelect = document.getElementById("fault-target-station");
  if (faultSelect && faultSelect.value !== sid) {
    faultSelect.value = sid;
  }

  updateCockpitDrawer(sid);
}

function focusStationOnFloor(sid) {
  if (!sid) return;

  // 1. Switch to floor supervisor view
  switchView("floor");

  // 2. Select station & populate cockpit drawer
  selectStation(sid);

  // 3. Clear previous focus spotlights and enlarge targeted assembly cell
  document.querySelectorAll(".station-schematic-node").forEach(n => {
    n.classList.remove("operator-focus-spotlight");
  });

  setTimeout(() => {
    const node = document.getElementById(`station-node-${sid}`);
    if (node) {
      node.classList.add("operator-focus-spotlight");

      // Smoothly scroll and center the enlarged assembly station in viewport
      const viewport = document.getElementById("schematic-viewport");
      if (viewport) {
        const nodeLeft = node.offsetLeft;
        const nodeTop = node.offsetTop;
        const targetScrollLeft = Math.max(0, nodeLeft - viewport.clientWidth / 2 + node.offsetWidth / 2);
        const targetScrollTop = Math.max(0, nodeTop - viewport.clientHeight / 2 + node.offsetHeight / 2);

        viewport.scrollTo({
          left: targetScrollLeft,
          top: targetScrollTop,
          behavior: "smooth"
        });
      }
    }
  }, 100);
}
window.focusStationOnFloor = focusStationOnFloor;

function updateCockpitDrawer(sid) {
  const meta = stationsMeta[sid];
  if (!meta || !latestTickData || !latestTickData.stations) return;

  const st = latestTickData.stations[sid] || {};

  document.getElementById("focus-sid").innerText = sid;
  document.getElementById("focus-name").innerText = meta.name;
  document.getElementById("focus-zone").innerText = `${meta.zone.toUpperCase()} // ${meta.station_type}`;

  const isBlackout = Boolean(st.is_blackout);
  const isStopped = Boolean(st.is_stopped);
  const isManual = meta.sensor_tier === 'manual';
  const isVirtual = isBlackout || isManual;

  const alertBox = document.getElementById("sensor-coverage-alert");
  if (alertBox) {
    alertBox.style.display = isVirtual ? "block" : "none";
    if (isVirtual) {
      const vData = st.virtual_sensor_imputed_data;
      if (vData) {
        // Disagreement variance is mapped 0-1, lower is higher confidence.
        const confPct = Math.max(0, 100 - (vData.imputation_disagreement * 100)).toFixed(0);
        document.getElementById("sensor-coverage-title").innerText = `⚠️ VIRTUAL SENSOR IMPUTATION (CONFIDENCE ${confPct}%)`;
        document.getElementById("sensor-coverage-details").innerHTML = `
          Missing: Physical Vibration, Temp, Power.<br/>
          Est (Neighbor/Flow/Shift): ${vData.imputation_components.neighbor_estimate}s / ${vData.imputation_components.flow_estimate}s / ${vData.imputation_components.shift_baseline}s
        `;
      } else {
         document.getElementById("sensor-coverage-title").innerText = `⚠️ VIRTUAL SENSOR IMPUTATION`;
         document.getElementById("sensor-coverage-details").innerText = `Missing: Physical Vibration, Temp, Power. Below telemetry is Virtual / Imputed.`;
      }
    }
  }

  const tierBadge = document.getElementById("focus-tier");
  if (isBlackout) {
    tierBadge.innerText = "SENSOR BLACKOUT (OFFLINE)";
    tierBadge.className = "node-tier-pill manual";
  } else {
    tierBadge.innerText = `${meta.sensor_tier.toUpperCase()} SENSOR`;
    tierBadge.className = `node-tier-pill ${isManual ? 'manual' : ''}`;
  }

  const ct = st.cycle_time_s || meta.target_cycle_time_s;
  const ctSuffix = isVirtual ? " (ESTIMATED)" : (isStopped ? " (HALT)" : "");
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
  const isoStatus = isVirtual ? "VIRTUAL" : (st.iso_vibration_status || (vib < 1.12 ? "GOOD" : (vib <= 2.8 ? "SAT" : (vib <= 4.5 ? "WARN" : "CRIT"))));
  document.getElementById("focus-vib").innerText = isVirtual ? "IMPUTED (NO SIGNAL)" : `${vib.toFixed(2)} mm/s (${isoStatus})`;
  const vibFill = document.getElementById("gauge-vib-fill");
  if (vibFill) {
    const vibPct = isVirtual ? 20 : Math.min(100, Math.max(5, (vib / 5.0) * 100));
    vibFill.style.width = `${vibPct}%`;
    vibFill.style.background = isVirtual ? "#94a3b8" : (vib > 4.5 ? "var(--status-critical)" : (vib > 2.8 ? "var(--status-warning)" : "var(--status-nominal)"));
  }

  const temp = st.temperature !== undefined && st.temperature !== null ? st.temperature : 24.0;
  const tempEl = document.getElementById("focus-temp");
  if (tempEl) tempEl.innerText = isVirtual ? "IMPUTED (NO SIGNAL)" : `${temp.toFixed(1)}°C`;
  const tempFill = document.getElementById("gauge-temp-fill");
  if (tempFill) {
    const tempPct = isVirtual ? 15 : Math.min(100, Math.max(8, (temp / 210.0) * 100));
    tempFill.style.width = `${tempPct}%`;
    tempFill.style.background = isVirtual ? "#94a3b8" : (temp > 200.0 ? "var(--status-critical)" : (temp > 65.0 && temp < 180.0 ? "var(--status-warning)" : "var(--status-nominal)"));
  }

  const pwr = st.power_kw || meta.power_base_kw || 30.0;
  document.getElementById("focus-power").innerText = isVirtual ? "IMPUTED" : `${pwr.toFixed(1)} kW`;
  const pwrFill = document.getElementById("gauge-power-fill");
  if (pwrFill) {
    const pwrPct = isVirtual ? 20 : Math.min(100, (pwr / 75.0) * 100);
    pwrFill.style.width = `${pwrPct}%`;
    pwrFill.style.background = isVirtual ? "#94a3b8" : (pwr > (meta.power_base_kw || 30.0) * 1.5 ? "var(--status-warning)" : "var(--status-nominal)");
  }

  const conf = st.twin_confidence !== undefined ? st.twin_confidence : 95.0;
  const spcTrend = isVirtual ? "IMPUTED" : (st.spc_trend || "STABLE");
  const confEl = document.getElementById("focus-spc-conf");
  if (confEl) confEl.innerText = `${conf.toFixed(0)}% (${spcTrend})`;
  const confFill = document.getElementById("gauge-conf-fill");
  if (confFill) {
    confFill.style.width = `${Math.min(100, Math.max(5, conf))}%`;
    confFill.style.background = conf < 65 ? "var(--status-critical)" : (conf < 80 ? "var(--status-warning)" : "var(--status-nominal)");
  }

  // 7. Update Predictive Maintenance & Service Schedule Card
  const maintStatusEl = document.getElementById("focus-maint-status");
  const maintDateEl = document.getElementById("focus-maint-date");
  const maintCountdownEl = document.getElementById("focus-maint-countdown");
  const maintWearValEl = document.getElementById("focus-maint-wear-val");
  const maintWearBarEl = document.getElementById("focus-maint-wear-bar");

  if (maintStatusEl || maintDateEl) {
    const defaultOffset = (((parseInt(sid.replace('ST', ''), 10) || 1) * 3) % 18 + 5).toString().padStart(2, '0');
    const rawMaintDate = meta.next_maintenance_date || `2026-03-${defaultOffset}T08:00`;
    
    // Parse target date
    const targetDate = new Date(rawMaintDate.includes('T') ? rawMaintDate : `${rawMaintDate}T08:00`);
    
    // Simulation baseline time
    let simDate = new Date();
    if (latestTickData.timestamp) {
      const parsedSim = new Date(latestTickData.timestamp.replace(' ', 'T'));
      if (!isNaN(parsedSim.getTime())) simDate = parsedSim;
    }
    
    const diffMs = targetDate - simDate;
    const diffHours = diffMs / (1000 * 60 * 60);
    const diffDays = Math.floor(diffHours / 24);
    const remHours = Math.max(0, Math.floor(diffHours % 24));
    const estTicks = Math.max(0, Math.floor(diffHours * 60)); // 60 ticks/hour

    const formattedDate = isNaN(targetDate.getTime()) 
      ? rawMaintDate.replace('T', ' ') 
      : targetDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) + ' ' + targetDate.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

    if (maintDateEl) maintDateEl.innerText = formattedDate;

    if (diffMs > 0) {
      if (diffDays >= 3) {
        if (maintStatusEl) {
          maintStatusEl.innerText = "🟢 ON SCHEDULE";
          maintStatusEl.style.color = "#15803d";
          maintStatusEl.style.background = "#dcfce7";
        }
      } else {
        if (maintStatusEl) {
          maintStatusEl.innerText = "🟡 SERVICE DUE SOON";
          maintStatusEl.style.color = "#b45309";
          maintStatusEl.style.background = "#fef3c7";
        }
      }
      if (maintCountdownEl) {
        maintCountdownEl.innerText = diffDays > 0 
          ? `${diffDays}d ${remHours}h (~${estTicks.toLocaleString()} Ticks)` 
          : `${remHours}h remaining (~${estTicks.toLocaleString()} Ticks)`;
        maintCountdownEl.style.color = diffDays >= 3 ? "#0284c7" : "#d97706";
      }
    } else {
      if (maintStatusEl) {
        maintStatusEl.innerText = "🔴 SERVICE OVERDUE";
        maintStatusEl.style.color = "#b91c1c";
        maintStatusEl.style.background = "#fee2e2";
      }
      if (maintCountdownEl) {
        maintCountdownEl.innerText = `Overdue by ${Math.abs(diffDays)}d (${Math.abs(remHours)}h)`;
        maintCountdownEl.style.color = "#dc2626";
      }
    }

    // Dynamic Tool Wear / Degradation progress
    const wearRaw = st.wear !== undefined ? st.wear : (st.tool_wear !== undefined ? st.tool_wear : (((parseInt(sid.replace('ST',''), 10) * 11 + (latestTickData.tick || 0)) % 100) / 100));
    const wearPct = Math.min(100, Math.max(0, Math.round(wearRaw * 100)));
    
    if (maintWearValEl) maintWearValEl.innerText = `${wearPct}% Degraded`;
    if (maintWearBarEl) {
      maintWearBarEl.style.width = `${wearPct}%`;
      maintWearBarEl.style.background = wearPct > 80 ? "#ef4444" : (wearPct > 50 ? "#f59e0b" : "#10b981");
    }
  }

  const propList = document.getElementById("focus-prop-list");
  const propCountEl = document.getElementById("prop-count");
  propList.innerHTML = "";

  const propMap = latestTickData.propagation || {};
  const propData = propMap[sid] || null;
  const impactedList = propData ? (propData.downstream_impact_tree || []) : [];
  const totalImpacted = propData ? (propData.total_downstream_impacted !== undefined ? propData.total_downstream_impacted : impactedList.length) : 0;

  if (propCountEl) propCountEl.innerText = `${totalImpacted} AT RISK`;

  if (totalImpacted === 0 || impactedList.length === 0) {
    propList.innerHTML = `<div style="font-size: 0.76rem; color: var(--text-secondary); font-family: var(--font-mono); padding: 4px 0;">Nominal line flow — zero starvation ripple.</div>`;
  } else {
    impactedList.slice(0, 8).forEach(item => {
      const row = document.createElement("div");
      row.className = "countdown-row";
      const impactMin = typeof item.time_to_impact_min === 'number' ? item.time_to_impact_min.toFixed(1) : item.time_to_impact_min;
      row.innerHTML = `
        <span style="font-weight: 700; color: var(--status-warning);">${item.station_id} (${item.station_name || item.zone})</span>
        <span style="font-weight: 800; color: var(--status-critical);">${impactMin}m countdown (Risk: ${(item.propagated_risk * 100).toFixed(0)}%)</span>
      `;
      propList.appendChild(row);
    });
    if (impactedList.length > 8) {
      const moreRow = document.createElement("div");
      moreRow.style.cssText = "font-size: 0.72rem; color: var(--text-secondary); text-align: center; padding-top: 4px;";
      moreRow.innerText = `+${impactedList.length - 8} additional downstream stations in ripple path`;
      propList.appendChild(moreRow);
    }
  }

  const recs = latestTickData.recommendations || [];
  const stRec = recs.find(r => r.station_id === sid) || recs[0];

  const riskDriversList = document.getElementById("risk-drivers-list");
  if (riskDriversList && st.risk_drivers && st.risk_drivers.length > 0) {
    riskDriversList.innerHTML = "";
    document.getElementById("risk-drivers-container").style.display = "block";
    
    // Calculate total impact to show percentage influence
    const totalImpact = st.risk_drivers.reduce((sum, d) => sum + d.impact_score, 0) || 1.0;
    
    const chainContainer = document.createElement("div");
    chainContainer.style.display = "flex";
    chainContainer.style.flexDirection = "column";
    chainContainer.style.gap = "0px";
    
    st.risk_drivers.forEach((d, index) => {
      const pct = Math.round((d.impact_score / totalImpact) * 100);
      const isLast = index === st.risk_drivers.length - 1;
      
      const row = document.createElement("div");
      row.style.cssText = `display: flex; flex-direction: column;`;
      
      const badgeColor = pct >= 50 
        ? "background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5;" 
        : (pct >= 25 ? "background: #fef3c7; color: #b45309; border: 1px solid #fde68a;" : "background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd;");

      const borderAccent = (d.z_score >= 2.5) ? "border-left: 3.5px solid #ef4444;" : ((d.z_score >= 1.5) ? "border-left: 3.5px solid #f59e0b;" : "");

      const node = document.createElement("div");
      node.style.cssText = `padding: 8px 10px; border-radius: 6px; background: #ffffff; border: 1px solid var(--border-subtle); ${borderAccent} position: relative; z-index: 2; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);`;
      
      const zScoreText = (d.z_score !== undefined && d.z_score > 0) ? ` (${d.z_score}σ deviation)` : "";
      const unitText = d.unit ? ` ${d.unit}` : "";

      node.innerHTML = `
        <div style="font-weight: 800; color: #0f172a; margin-bottom: 3px; display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem;">
          <span>${d.feature.toUpperCase()}</span>
          <span style="font-size: 0.68rem; font-weight: 800; font-family: var(--font-mono); padding: 1px 6px; border-radius: 4px; ${badgeColor}">${pct}% Risk Weight</span>
        </div>
        <div style="color: #475569; line-height: 1.3; font-size: 0.70rem;">
          ${d.explanation}
        </div>
        <div style="margin-top: 4px; font-size: 0.65rem; color: #64748b; font-family: var(--font-mono);">
          Evidence: Observed ${d.value}${unitText}${zScoreText} vs Baseline ${d.baseline}${unitText}
        </div>
      `;
      
      row.appendChild(node);
      
      if (!isLast) {
        const arrow = document.createElement("div");
        arrow.style.cssText = `height: 14px; width: 2px; background: #e2e8f0; margin: 0 auto; position: relative; z-index: 1;`;
        const arrowhead = document.createElement("div");
        arrowhead.style.cssText = `position: absolute; bottom: -2px; left: -3px; width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #e2e8f0;`;
        arrow.appendChild(arrowhead);
        row.appendChild(arrow);
      }
      
      chainContainer.appendChild(row);
    });
    
    // Final prediction node
    const finalArrow = document.createElement("div");
    finalArrow.style.cssText = `height: 14px; width: 2px; background: #fca5a5; margin: 0 auto; position: relative; z-index: 1;`;
    const finalArrowhead = document.createElement("div");
    finalArrowhead.style.cssText = `position: absolute; bottom: -2px; left: -3px; width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #fca5a5;`;
    finalArrow.appendChild(finalArrowhead);
    
    const predictionNode = document.createElement("div");
    predictionNode.style.cssText = `padding: 8px 10px; border-radius: 6px; background: #fee2e2; border: 1px solid #fca5a5; text-align: center; font-weight: 800; color: #b91c1c; font-size: 0.75rem; text-transform: uppercase;`;
    predictionNode.innerText = "🚨 RISK PREDICTED";
    
    chainContainer.appendChild(finalArrow);
    chainContainer.appendChild(predictionNode);
    
    riskDriversList.appendChild(chainContainer);
  } else if (riskDriversList) {
    document.getElementById("risk-drivers-container").style.display = "none";
  }

  if (stRec) {
    document.getElementById("rec-title").innerText = stRec.title;
    document.getElementById("rec-action").innerText = stRec.recommended_action || stRec.rationale;
    document.getElementById("rec-impact").innerText = `Impact: ${stRec.expected_impact || `${stRec.downtime_avoided_min || 0} min line starvation avoided`}`;
    document.getElementById("rec-conf-tag").innerText = `${Math.round((stRec.confidence || 0.9) * 100)}% CONFIDENCE`;

    const btnApply = document.getElementById("btn-apply-intervention");
    const badge = document.getElementById("intervention-badge");
    
    // Check if an intervention is already active for this station
    const activeInterventions = latestTickData.interventions || {};
    if (activeInterventions[sid] && activeInterventions[sid].active) {
      if (btnApply) btnApply.style.display = "none";
      if (badge) {
        badge.style.display = "block";
        badge.innerText = `⚡ ${activeInterventions[sid].type.replace(/_/g, ' ')} ACTIVE`;
      }
    } else {
      if (badge) badge.style.display = "none";
      // Show Apply button if recommendation is actionable (e.g. has SOP steps or a specific title)
      if (btnApply && stRec.sop && stRec.sop.steps.length > 0) {
        btnApply.style.display = "block";
        btnApply.onclick = () => applyIntervention(sid, "INCREASE_CONVEYOR_SPEED"); // example
      } else if (btnApply) {
        btnApply.style.display = "none";
      }
    }

    const sopStepsList = document.getElementById("sop-steps-list");
    const sopBadge = document.getElementById("sop-badge");
    if (sopStepsList && stRec.sop && Array.isArray(stRec.sop.steps)) {
      const sop = stRec.sop;
      const activeStepNum = sop.active_step_number || 1;
      if (sopBadge) {
        const activeStepObj = sop.steps.find(s => s.step === activeStepNum) || sop.steps[0];
        sopBadge.innerText = `STEP ${activeStepNum}: ${(activeStepObj.role || 'OPERATOR').toUpperCase()}`;
        sopBadge.style.color = activeStepNum > 1 ? "#ef4444" : "#38bdf8";
        sopBadge.style.background = activeStepNum > 1 ? "rgba(239, 68, 68, 0.2)" : "rgba(56, 189, 248, 0.15)";
      }
      sopStepsList.innerHTML = "";
      sop.steps.forEach(s => {
        const isActive = s.step === activeStepNum;
        const stepRow = document.createElement("div");
        stepRow.style.cssText = `padding: 6px 8px; border-radius: 4px; border-left: 3px solid ${isActive ? '#38bdf8' : '#334155'}; background: ${isActive ? 'rgba(56, 189, 248, 0.12)' : 'rgba(15, 23, 42, 0.4)'}; margin-bottom: 2px;`;
        const escTxt = s.escalate_after_ticks ? ` <span style="color: #94a3b8;">(Escalates after ${s.escalate_after_ticks} ticks)</span>` : "";
        stepRow.innerHTML = `
          <div style="font-weight: 800; color: ${isActive ? '#38bdf8' : '#94a3b8'}; margin-bottom: 2px;">
            Step ${s.step} [${s.role}]${escTxt} ${isActive ? '⚡ ACTIVE' : ''}
          </div>
          <div style="color: ${isActive ? '#f8fafc' : '#94a3b8'}; line-height: 1.3;">${s.action}</div>
        `;
        sopStepsList.appendChild(stepRow);
      });
    }
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

async function applyIntervention(stationId, interventionType = "INCREASE_CONVEYOR_SPEED") {
  if (!stationId) stationId = selectedStationId;
  if (!stationId) return;
  
  try {
    const res = await fetch("http://localhost:8000/api/interventions/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        station_id: stationId,
        intervention_type: interventionType,
        duration_ticks: 30
      })
    });
    if (!res.ok) {
      console.error("Failed to apply intervention");
    }
  } catch(e) {
    console.error("API error", e);
  }
}

async function controlSim(action) {
  const btnRun = document.getElementById("btn-run");
  const btnHold = document.getElementById("btn-hold");
  const btnStep = document.getElementById("btn-step");

  if (action === "run" || action === "play") {
    if (btnRun) btnRun.classList.add("active-play");
    if (btnHold) btnHold.classList.remove("active-play");
  } else if (action === "pause" || action === "hold") {
    if (btnRun) btnRun.classList.remove("active-play");
    if (btnHold) btnHold.classList.add("active-play");
  } else if (action === "step") {
    if (btnRun) btnRun.classList.remove("active-play");
    if (btnHold) btnHold.classList.add("active-play");
  }

  try {
    const res = await fetch("/api/simulator/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action })
    });
    const data = await res.json();
    if (data.payload) {
      handleTickUpdate(data.payload);
      if (currentView === "leadership" || currentView === "weekly") {
        loadLeadershipData();
      }
    }
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
      body: JSON.stringify({ action: "set_speed", speed_multiplier: mult })
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
    if (currentView === "leadership" || currentView === "weekly") {
      loadLeadershipData();
    }
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
    if (currentView === "leadership" || currentView === "weekly") {
      loadLeadershipData();
    }
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

window.currentRoiMode = "takt";
window.cachedStationRois = [];

function setRoiMode(mode) {
  window.currentRoiMode = mode;
  const btnTakt = document.getElementById("roi-mode-btn-takt");
  const btnGross = document.getElementById("roi-mode-btn-gross");
  const btnTaktTop = document.getElementById("roi-mode-btn-takt-top");
  const btnGrossTop = document.getElementById("roi-mode-btn-gross-top");

  if (btnTakt) btnTakt.classList.toggle("active-play", mode === "takt");
  if (btnGross) btnGross.classList.toggle("active-play", mode === "gross");
  if (btnTaktTop) btnTaktTop.classList.toggle("active-play", mode === "takt");
  if (btnGrossTop) btnGrossTop.classList.toggle("active-play", mode === "gross");

  renderStationRoiTable(window.cachedStationRois);
}

async function loadLeadershipData() {
  try {
    const res = await fetch("/api/leadership/summary");
    const data = await res.json();
    
    // 1. Render Senior Leadership Financial Intelligence KPIs
    if (data.financials) {
      const f = data.financials;
      const sqftEl = document.getElementById("lead-cost-sqft");
      if (sqftEl) sqftEl.innerText = `$${(f.cost_per_sqft_usd || 1800).toLocaleString('en-US', { minimumFractionDigits: 2 })} / sq ft`;

      const tonEl = document.getElementById("lead-cost-ton");
      if (tonEl) tonEl.innerText = `$${(f.cost_per_ton_usd || 1727.27).toLocaleString('en-US', { minimumFractionDigits: 2 })} / ton`;

      const savVal = data.summary?.cost_saved_usd || 0;
      const savEl = document.getElementById("lead-savings-usd");
      if (savEl) savEl.innerText = `$${(savVal / 1000000.0).toFixed(2)} M`;

      // First-Principles Takt Value Shield
      const tvlEl = document.getElementById("lead-tvl-usd");
      const tvlSub = document.getElementById("lead-tvl-sub");
      if (f.takt_economics) {
        const tvlVal = f.takt_economics.total_tvl_avoided_usd || 0;
        const units = f.takt_economics.total_units_protected || 0;
        if (tvlEl) tvlEl.innerText = `$${(tvlVal / 1000000.0).toFixed(2)} M`;
        if (tvlSub) tvlSub.innerText = `${units.toFixed(1)} Units Protected ($9.2k Margin)`;
      }

      const jphEl = document.getElementById("lead-jph-comp");
      if (jphEl && f.jph_targets) {
        const act = f.jph_targets.line_jph_actual || 55.4;
        const tgt = f.jph_targets.line_jph_target || 55.0;
        jphEl.innerText = `${act.toFixed(1)} / ${tgt.toFixed(1)} JPH`;
      }

      window.cachedStationRois = f.station_roi || [];
      renderStationRoiTable(window.cachedStationRois);
    }

    renderThermalHeatmap(data.heatmap || []);
    renderParetoCauses(data.top_root_causes || []);
    
    // Render Dynamic Zone OEE
    if (data.zone_oee) {
      const zo = data.zone_oee;
      const setOee = (zone, key) => {
        if (!zo[key]) return;
        const valEl = document.getElementById(`oee-val-${zone}`);
        const barEl = document.getElementById(`oee-bar-${zone}`);
        const availEl = document.getElementById(`oee-avail-${zone}`);
        const perfEl = document.getElementById(`oee-perf-${zone}`);
        const qualEl = document.getElementById(`oee-qual-${zone}`);

        if (valEl) valEl.innerText = `${zo[key].oee.toFixed(1)}% OEE`;
        if (barEl) barEl.style.width = `${zo[key].oee}%`;
        if (availEl) availEl.innerText = `Availability: ${zo[key].availability.toFixed(1)}%`;
        if (perfEl) perfEl.innerText = `Performance: ${zo[key].performance.toFixed(1)}%`;
        if (qualEl) qualEl.innerText = `Quality: ${zo[key].quality.toFixed(1)}%`;
      };
      
      setOee('body', 'body');
      setOee('paint', 'paint');
      setOee('assy', 'assy');
    }
  } catch (err) {
    console.warn("Leadership load error:", err);
    renderThermalHeatmap([]);
    renderParetoCauses([]);
  }
}

function renderStationRoiTable(stationRois) {
  const thead = document.getElementById("lead-station-roi-thead");
  const tbody = document.getElementById("lead-station-roi-tbody");
  if (!tbody) return;
  tbody.innerHTML = "";

  const isTaktMode = (window.currentRoiMode === "takt");

  if (thead) {
    if (isTaktMode) {
      thead.innerHTML = `
        <tr style="background: #f0fdf4; color: #166534; position: sticky; top: 0; z-index: 1; border-bottom: 2px solid #bbf7d0;">
          <th style="padding: 8px 10px;">Station</th>
          <th style="padding: 8px 10px;">Station Capex</th>
          <th style="padding: 8px 10px;">Takt Delay Saved</th>
          <th style="padding: 8px 10px;">Units Protected</th>
          <th style="padding: 8px 10px;">Takt Value ($9.2k/u)</th>
          <th style="padding: 8px 10px;">Quality Shield</th>
          <th style="padding: 8px 10px;">Takt Payback</th>
          <th style="padding: 8px 10px;">⚡ Takt ROI</th>
        </tr>
      `;
    } else {
      thead.innerHTML = `
        <tr style="background: #f1f5f9; color: #475569; position: sticky; top: 0; z-index: 1; border-bottom: 2px solid #cbd5e1;">
          <th style="padding: 8px 10px;">Station</th>
          <th style="padding: 8px 10px;">Category</th>
          <th style="padding: 8px 10px;">Station Capex</th>
          <th style="padding: 8px 10px;">Downtime Avoided</th>
          <th style="padding: 8px 10px;">Attributed Savings</th>
          <th style="padding: 8px 10px;">Payback Period</th>
          <th style="padding: 8px 10px;">CapEx ROI</th>
        </tr>
      `;
    }
  }

  if (!stationRois || stationRois.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="padding: 12px; text-align: center; color: #94a3b8;">No station financial telemetry logged yet.</td></tr>`;
    return;
  }

  // Sort: active savings stations first
  const sorted = [...stationRois].sort((a, b) => {
    const valB = isTaktMode ? (b.net_value_created_usd || 0) : (b.attributed_savings_usd || 0);
    const valA = isTaktMode ? (a.net_value_created_usd || 0) : (a.attributed_savings_usd || 0);
    return valB - valA;
  });

  sorted.forEach(s => {
    const tr = document.createElement("tr");
    const hasSavings = (s.attributed_savings_usd || 0) > 0 || (s.net_value_created_usd || 0) > 0;
    tr.style.cssText = `border-bottom: 1px solid #f1f5f9; background: ${hasSavings ? (isTaktMode ? '#f0fdf4' : '#f8fafc') : 'transparent'}; transition: background 0.2s ease;`;

    if (isTaktMode) {
      const roiBadge = hasSavings 
        ? `<span style="font-weight: 800; color: #15803d; background: #dcfce7; padding: 2px 6px; border-radius: 4px;">+${(s.first_principles_roi_pct || 0).toFixed(1)}%</span>`
        : `<span style="color: #94a3b8; font-weight: 500;">0.0%</span>`;

      const paybackBadge = hasSavings && s.takt_payback_days
        ? `<span style="color: #0284c7; font-weight: 700;">${s.takt_payback_days} shift-days</span>`
        : `<span style="color: #94a3b8; font-weight: 400;">In-Spec Baseline</span>`;

      tr.innerHTML = `
        <td style="padding: 7px 10px; font-weight: 700; color: #0f172a;">${s.station_id} <span style="font-weight: 400; color: #64748b; font-size: 0.68rem;">(${s.station_name})</span></td>
        <td style="padding: 7px 10px; color: #0f172a;">$${(s.capex_usd || 0).toLocaleString()}</td>
        <td style="padding: 7px 10px; font-weight: ${hasSavings ? '700' : '400'}; color: ${hasSavings ? '#b91c1c' : '#64748b'};">${s.downtime_avoided_min || 0} min</td>
        <td style="padding: 7px 10px; font-weight: 700; color: ${hasSavings ? '#0284c7' : '#64748b'};">${(s.units_protected_count || 0).toFixed(1)} units</td>
        <td style="padding: 7px 10px; font-weight: 700; color: ${hasSavings ? '#15803d' : '#64748b'};">$${Math.round(s.tvl_avoided_usd || 0).toLocaleString()}</td>
        <td style="padding: 7px 10px; color: #64748b;">$${Math.round(s.quality_savings_usd || 0).toLocaleString()}</td>
        <td style="padding: 7px 10px;">${paybackBadge}</td>
        <td style="padding: 7px 10px;">${roiBadge}</td>
      `;
    } else {
      const roiBadge = hasSavings 
        ? `<span style="font-weight: 800; color: #15803d; background: #dcfce7; padding: 2px 6px; border-radius: 4px;">+${(s.roi_pct || 0).toFixed(1)}%</span>`
        : `<span style="color: #94a3b8; font-weight: 500;">0.0%</span>`;

      const paybackBadge = hasSavings && s.payback_period_days
        ? `<span style="color: #0284c7; font-weight: 700;">${s.payback_period_days} shift-days</span>`
        : `<span style="color: #94a3b8; font-weight: 400;">In-Spec Baseline</span>`;

      tr.innerHTML = `
        <td style="padding: 7px 10px; font-weight: 700; color: #0f172a;">${s.station_id} <span style="font-weight: 400; color: #64748b;">(${s.station_name})</span></td>
        <td style="padding: 7px 10px; color: #475569;">${s.station_type}</td>
        <td style="padding: 7px 10px; color: #0f172a;">$${(s.capex_usd || 0).toLocaleString()}</td>
        <td style="padding: 7px 10px; font-weight: ${hasSavings ? '700' : '400'}; color: ${hasSavings ? '#b91c1c' : '#64748b'};">${s.downtime_avoided_min || 0} min</td>
        <td style="padding: 7px 10px; font-weight: 700; color: ${hasSavings ? '#15803d' : '#64748b'};">$${(s.attributed_savings_usd || 0).toLocaleString()}</td>
        <td style="padding: 7px 10px;">${paybackBadge}</td>
        <td style="padding: 7px 10px;">${roiBadge}</td>
      `;
    }
    tbody.appendChild(tr);
  });
}

function renderThermalHeatmap(heatmapData) {
  const container = document.getElementById("thermal-heatmap");
  if (!container) return;
  container.innerHTML = "";

  // Ensure 40 stations list
  let sids = Object.keys(stationsMeta);
  if (!sids || sids.length === 0) {
    sids = Array.from({ length: 40 }, (_, i) => `ST${(i + 1).toString().padStart(2, '0')}`);
  }

  const heatMapLookup = {};
  if (Array.isArray(heatmapData)) {
    heatmapData.forEach(item => {
      if (item && item.station_id) {
        heatMapLookup[item.station_id] = item.readings || [];
      }
    });
  }

  const count = 20;

  // Render X-axis header row for Shift Ticks
  const headerRow = document.createElement("div");
  headerRow.className = "thm-row";
  headerRow.style.marginBottom = "6px";
  headerRow.style.position = "sticky";
  headerRow.style.top = "0";
  headerRow.style.zIndex = "10";
  headerRow.style.backgroundColor = "var(--panel-bg, #ffffff)";
  
  const emptyCorner = document.createElement("span");
  emptyCorner.className = "thm-sid";
  headerRow.appendChild(emptyCorner);
  
  for (let i = 0; i < count; i++) {
    const tickLbl = document.createElement("div");
    tickLbl.className = "thm-cell";
    tickLbl.style.background = "transparent";
    tickLbl.style.fontSize = "0.55rem";
    tickLbl.style.color = "var(--text-muted)";
    tickLbl.style.display = "flex";
    tickLbl.style.alignItems = "flex-end";
    tickLbl.style.justifyContent = "center";
    tickLbl.style.fontFamily = "var(--font-mono)";
    tickLbl.innerText = `-${count - i}`;
    headerRow.appendChild(tickLbl);
  }
  container.appendChild(headerRow);

  sids.forEach(sid => {
    const row = document.createElement("div");
    row.className = "thm-row";

    const lbl = document.createElement("span");
    lbl.className = "thm-sid";
    lbl.innerText = sid;
    row.appendChild(lbl);

    const readings = heatMapLookup[sid] || [];

    for (let i = 0; i < count; i++) {
      const cell = document.createElement("div");
      cell.className = "thm-cell";
      
      const rVal = (readings[i] !== undefined && readings[i] !== null) ? readings[i] : 1.0;
      let cellBg = "#10b981"; // Nominal green
      let statusText = "Nominal (1.0x Target)";

      if (rVal > 1.30) {
        cellBg = "#ef4444"; // Red Critical
        statusText = `Critical Slowdown (${(rVal * 100).toFixed(0)}% Target)`;
      } else if (rVal > 1.15) {
        cellBg = "#f59e0b"; // Amber Warning
        statusText = `Warning Drift (${(rVal * 100).toFixed(0)}% Target)`;
      } else if (rVal < 0.85) {
        cellBg = "#38bdf8"; // Blue Under-cycle
        statusText = `Starved/Under-cycle (${(rVal * 100).toFixed(0)}% Target)`;
      }

      cell.style.background = cellBg;
      cell.title = `${sid} [Tick -${count - i}]: ${statusText}`;
      row.appendChild(cell);
    }

    container.appendChild(row);
  });
}

function renderParetoCauses(causes) {
  const container = document.querySelector(".root-cause-list");
  const weeklyContainer = document.querySelector(".root-cause-list-weekly");
  if (!container && !weeklyContainer) return;
  if (container) container.innerHTML = "";
  if (weeklyContainer) weeklyContainer.innerHTML = "";

  const defaultCauses = [
    { title: "Tooling Wear & Friction Drift (Framing ST06)", pct: "34%", icon: "⚡" },
    { title: "Air Pressure Drop in Adhesive Sealers (ST09)", pct: "24%", icon: "💨" },
    { title: "Torque Calibration Outlier (ST35)", pct: "18%", icon: "🔧" },
    { title: "Thermal Oven Blower Harmonic (ST17)", pct: "14%", icon: "🌀" },
    { title: "Optic Vision QC Camera Occlusion (ST22)", pct: "10%", icon: "👁️" }
  ];

  let items = defaultCauses;
  if (Array.isArray(causes) && causes.length > 0) {
    const totalCount = causes.reduce((sum, c) => sum + (c.count || 1), 0) || 1;
    items = causes.map(c => ({
      title: c.cause || "Unspecified Anomaly",
      pct: `${Math.round((c.count / totalCount) * 100)}%`,
      icon: "⚡"
    }));
  }

  items.forEach(c => {
    const div = document.createElement("div");
    div.style.padding = "8px 12px";
    div.style.background = "#f8fafc";
    div.style.border = "1px solid var(--border-subtle)";
    div.style.borderRadius = "var(--radius-sm)";
    div.style.marginBottom = "6px";
    div.innerHTML = `
      <div style="display: flex; justify-content: space-between; font-size: 0.76rem; font-family: var(--font-brand); font-weight: 700; color: var(--text-primary);">
        <span>${c.icon} ${c.title}</span>
        <span style="color: var(--brand-blue); font-family: var(--font-mono); font-weight: 800;">${c.pct}</span>
      </div>
      <div style="width: 100%; background: #e2e8f0; height: 4px; border-radius: 999px; margin-top: 5px; overflow: hidden;">
        <div style="background: var(--brand-blue); height: 100%; width: ${c.pct};"></div>
      </div>
    `;
    if (container) container.appendChild(div.cloneNode(true));
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
    node.id = `vin-node-${sid}`;
    node.innerText = sid;
    container.appendChild(node);
  }
}

async function traceGenealogy() {
  const input = document.getElementById("genealogy-input");
  let vin = input ? input.value.trim() : "";
  const resultEl = document.getElementById("genealogy-result");
  if (!resultEl) return;

  if (!vin) {
    try {
      const vRes = await fetch("/api/vehicles/recent?limit=1");
      const vData = await vRes.json();
      if (vData.recent_completed && vData.recent_completed.length > 0) {
        vin = vData.recent_completed[vData.recent_completed.length - 1].vehicle_id;
      } else if (vData.active_in_line && vData.active_in_line.length > 0) {
        vin = vData.active_in_line[vData.active_in_line.length - 1].vehicle_id;
      }
      if (input && vin) input.value = vin;
    } catch (e) {}
  }
  if (!vin) vin = "VIN-2026-01001";

  try {
    const res = await fetch(`/api/vehicles/${vin}/genealogy`);
    const data = await res.json();
    
    if (data.status === "NOT_FOUND") {
      try {
        const vRes = await fetch("/api/vehicles/recent?limit=1");
        const vData = await vRes.json();
        let fallbackVin = null;
        if (vData.recent_completed && vData.recent_completed.length > 0) {
          fallbackVin = vData.recent_completed[vData.recent_completed.length - 1].vehicle_id;
        } else if (vData.active_in_line && vData.active_in_line.length > 0) {
          fallbackVin = vData.active_in_line[vData.active_in_line.length - 1].vehicle_id;
        }
        if (fallbackVin && fallbackVin !== vin) {
          if (input) input.value = fallbackVin;
          return traceGenealogy();
        }
      } catch (e) {}
    }

    // Reset all nodes
    renderVinTrailGrid();
    
    const trace = data.station_trace || [];
    const visitedSids = new Set();
    const defectSids = new Set();

    trace.forEach(t => {
      visitedSids.add(t.station_id);
      if (t.defect_flag) defectSids.add(t.station_id);
    });

    for (let i = 1; i <= 40; i++) {
      const sid = `ST${i.toString().padStart(2, '0')}`;
      const node = document.getElementById(`vin-node-${sid}`);
      if (node) {
        if (defectSids.has(sid)) {
          node.className = "vin-tick-node failed";
        } else if (visitedSids.has(sid)) {
          node.className = "vin-tick-node passed";
        } else {
          node.className = "vin-tick-node";
          node.style.background = "#f1f5f9";
          node.style.color = "#94a3b8";
        }
      }
    }

    const visitedCount = visitedSids.size || data.total_stations_visited || (trace ? trace.length : 0);
    const defectCount = defectSids.size || (data.defect_count !== undefined ? data.defect_count : (data.defect_flags ? data.defect_flags.length : 0));
    const isPassed = defectCount === 0;
    const routeTotal = data.route_length || data.route_length_estimate || visitedCount;

    resultEl.innerHTML = `
      <span style="color: ${isPassed ? 'var(--status-nominal)' : 'var(--status-critical)'}; font-weight: 800;">${data.vin || vin}:</span> 
      ${visitedCount}/${routeTotal} Stations Traversed • 
      Defects Flagged: <strong style="color: ${isPassed ? 'var(--status-nominal)' : 'var(--status-critical)'};">${defectCount}</strong> • 
      Quality Status: <strong style="color: ${isPassed ? 'var(--status-nominal)' : 'var(--status-critical)'}; text-transform: uppercase;">${data.status || (isPassed ? 'PASSED FINAL BUY-OFF' : 'FLAGGED_REWORK')}</strong>
    `;
  } catch (err) {
    resultEl.innerHTML = `<span style="color: var(--status-critical);">Failed to trace ${vin}: ${err.message}</span>`;
  }
}

function updateLineBalancing(jphVal) {
  const jph = parseInt(jphVal, 10) || 55;
  const taktSec = (3600.0 / jph);

  const jphLbl = document.getElementById("slider-target-val");
  const taktLbl = document.getElementById("slider-takt-val");
  if (jphLbl) jphLbl.innerText = `Target Output: ${jph} JPH`;
  if (taktLbl) taktLbl.innerText = `Required Takt: ${taktSec.toFixed(1)}s`;

  // Send JPH update to backend simulator
  if (window._jphDebounceTimer) clearTimeout(window._jphDebounceTimer);
  window._jphDebounceTimer = setTimeout(() => {
    fetch("/api/simulator/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "set_jph", jph: jph })
    }).catch(e => console.warn("Failed to sync JPH to simulator:", e));
  }, 250);

  // Calculate bottlenecks from stationsMeta
  const sids = Object.keys(stationsMeta).length > 0 
    ? Object.keys(stationsMeta) 
    : Array.from({ length: 40 }, (_, i) => `ST${(i + 1).toString().padStart(2, '0')}`);

  const bottlenecks = [];
  let totalCycleOverloadSec = 0;

  sids.forEach(sid => {
    const meta = stationsMeta[sid] || {};
    const targetCt = meta.target_cycle_time_s || 60.0;
    if (targetCt > taktSec) {
      const overloadSec = targetCt - taktSec;
      totalCycleOverloadSec += overloadSec;
      bottlenecks.push({
        sid: sid,
        name: meta.name || `Station ${sid}`,
        zone: meta.zone || "Body",
        targetCt: targetCt,
        overloadSec: overloadSec,
        overloadPct: Math.round((overloadSec / taktSec) * 100)
      });
    }
  });

  bottlenecks.sort((a, b) => b.overloadSec - a.overloadSec);

  // Render KPI Grid
  const kpiGrid = document.getElementById("whatif-kpi-grid");
  if (kpiGrid) {
    const starvationIndex = bottlenecks.length > 5 ? "HIGH" : (bottlenecks.length > 2 ? "MEDIUM" : "LOW");
    const laborNeeded = bottlenecks.length > 0 ? `+${Math.ceil(bottlenecks.length * 1.5)} FTE / Robots` : "0 (Balanced)";

    kpiGrid.innerHTML = `
      <div class="whatif-kpi-card">
        <span class="whatif-kpi-title">Bottlenecks</span>
        <span class="whatif-kpi-val" style="color: ${bottlenecks.length > 4 ? '#ef4444' : (bottlenecks.length > 0 ? '#f59e0b' : '#10b981')}">${bottlenecks.length} / 40</span>
      </div>
      <div class="whatif-kpi-card">
        <span class="whatif-kpi-title">Starvation Risk</span>
        <span class="whatif-kpi-val" style="color: ${starvationIndex === 'HIGH' ? '#ef4444' : (starvationIndex === 'MEDIUM' ? '#f59e0b' : '#10b981')}">${starvationIndex}</span>
      </div>
      <div class="whatif-kpi-card">
        <span class="whatif-kpi-title">Line Balancing</span>
        <span class="whatif-kpi-val" style="font-size: 0.85rem; color: var(--brand-blue);">${laborNeeded}</span>
      </div>
    `;
  }

  // Render Bottlenecks List
  const bnList = document.getElementById("whatif-bottlenecks-list");
  if (bnList) {
    bnList.innerHTML = "";
    if (bottlenecks.length === 0) {
      bnList.innerHTML = `
        <div style="padding: 12px; background: #dcfce7; color: #15803d; border-radius: var(--radius-sm); font-size: 0.78rem; font-weight: 700; text-align: center;">
          ✅ Line is 100% balanced at ${jph} JPH! No stations exceed the ${taktSec.toFixed(1)}s takt threshold.
        </div>
      `;
    } else {
      bottlenecks.forEach(b => {
        const isCrit = b.overloadPct > 20;
        const row = document.createElement("div");
        row.className = `whatif-bottleneck-row ${isCrit ? 'critical' : 'warning'}`;
        row.innerHTML = `
          <div>
            <span style="font-weight: 800; font-family: var(--font-mono); color: #0f172a;">${b.sid}</span>
            <span style="color: var(--text-secondary); margin-left: 6px;">${b.name} (${b.zone})</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-secondary);">${b.targetCt.toFixed(0)}s vs ${taktSec.toFixed(1)}s takt</span>
            <span class="whatif-tag ${isCrit ? 'critical' : 'warning'}">+${b.overloadSec.toFixed(1)}s (${b.overloadPct}%)</span>
          </div>
        `;
        bnList.appendChild(row);
      });
    }
  }
}

// ============================================================================
// PHASE 6 & 7: OPERATOR AREA ASSIGNMENTS & CURRENT-VS-IDEAL TELEMETRY CARDS
// ============================================================================

let operatorAssignments = [];
let activeOperatorWorkerId = "W01";

async function loadAssignments() {
  try {
    const res = await fetch("/api/assignments");
    const data = await res.json();
    operatorAssignments = data.assignments || [];

    // Populate multi-select options in Admin form if empty
    const assignSelect = document.getElementById("assign-stations-select");
    if (assignSelect && assignSelect.options.length === 0) {
      Object.keys(stationsMeta).forEach(sid => {
        const meta = stationsMeta[sid];
        const opt = document.createElement("option");
        opt.value = sid;
        opt.innerText = `${sid}: ${meta.name} (${meta.zone})`;
        assignSelect.appendChild(opt);
      });
    }

    // Update assignment count tag
    const tag = document.getElementById("assignment-count-tag");
    if (tag) tag.innerText = `${operatorAssignments.length} WORKERS CONFIGURED`;

    // Render Admin List
    const adminList = document.getElementById("operator-assignments-list");
    if (adminList) {
      adminList.innerHTML = "";
      if (operatorAssignments.length === 0) {
        adminList.innerHTML = `<div style="font-size: 0.76rem; color: #94a3b8; padding: 8px;">No workers configured. Create an assignment using the form.</div>`;
      } else {
        operatorAssignments.forEach(w => {
          const row = document.createElement("div");
          row.style.cssText = "display: flex; justify-content: space-between; align-items: center; background: #ffffff; border: 1px solid var(--border-subtle); padding: 8px 12px; border-radius: var(--radius-sm);";
          const stBadges = (w.assigned_station_ids || []).map(s => `<span style="font-size: 0.68rem; font-family: var(--font-mono); background: #f1f5f9; color: #0f172a; padding: 1px 4px; border-radius: 3px; margin-right: 2px;">${s}</span>`).join("");
          row.innerHTML = `
            <div>
              <div style="font-weight: 800; font-size: 0.8rem; color: #0f172a;">${w.worker_name} <span style="font-family: var(--font-mono); font-size: 0.72rem; color: #0284c7;">(${w.worker_id})</span></div>
              <div style="margin-top: 4px; display: flex; flex-wrap: wrap; gap: 2px;">${stBadges}</div>
            </div>
            <button class="fault-btn" style="color: #ef4444; border-color: #fca5a5; font-size: 0.68rem; height: 24px;" onclick="deleteOperatorAssignment('${w.worker_id}')">🗑️ REMOVE</button>
          `;
          adminList.appendChild(row);
        });
      }
    }

    // Populate Worker Dropdown in Operator Dock View
    const workerSelect = document.getElementById("operator-worker-select");
    if (workerSelect) {
      workerSelect.innerHTML = "";
      if (operatorAssignments.length === 0) {
        const opt = document.createElement("option");
        opt.value = "";
        opt.innerText = "No workers configured (Showing All 40 Stations)";
        workerSelect.appendChild(opt);
      } else {
        operatorAssignments.forEach(w => {
          const opt = document.createElement("option");
          opt.value = w.worker_id;
          opt.innerText = `${w.worker_name} (${(w.assigned_station_ids || []).length} stations)`;
          workerSelect.appendChild(opt);
        });
        if (!operatorAssignments.some(w => w.worker_id === activeOperatorWorkerId)) {
          activeOperatorWorkerId = operatorAssignments[0].worker_id;
        }
        workerSelect.value = activeOperatorWorkerId;
      }
    }

    renderOperatorView();
  } catch (err) {
    console.error("Failed to load operator assignments:", err);
  }
}

async function submitOperatorAssignment() {
  const wid = document.getElementById("assign-worker-id").value.trim();
  const wname = document.getElementById("assign-worker-name").value.trim();
  const select = document.getElementById("assign-stations-select");
  const assigned = Array.from(select.selectedOptions).map(o => o.value);

  if (!wid || !wname || assigned.length === 0) {
    alert("Please provide Worker ID, Name, and select at least one assigned station.");
    return;
  }

  try {
    const res = await fetch("/api/assignments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        worker_id: wid,
        worker_name: wname,
        assigned_station_ids: assigned
      })
    });
    if (!res.ok) {
      const err = await res.json();
      alert("Error saving assignment: " + (err.detail || res.statusText));
      return;
    }
    clearAssignmentForm();
    await loadAssignments();
  } catch (err) {
    alert("Network error saving assignment: " + err.message);
  }
}

async function deleteOperatorAssignment(workerId) {
  if (!confirm(`Delete operator assignment for ${workerId}?`)) return;
  try {
    await fetch(`/api/assignments/${workerId}`, { method: "DELETE" });
    await loadAssignments();
  } catch (err) {
    console.error("Error deleting assignment:", err);
  }
}

function clearAssignmentForm() {
  document.getElementById("assign-worker-id").value = "";
  document.getElementById("assign-worker-name").value = "";
  const select = document.getElementById("assign-stations-select");
  if (select) Array.from(select.options).forEach(o => o.selected = false);
}

function onOperatorWorkerChange(workerId) {
  activeOperatorWorkerId = workerId;
  renderOperatorView();
}

function renderOperatorView() {
  const container = document.getElementById("operator-stations-container");
  const summaryEl = document.getElementById("operator-coverage-summary");
  if (!container) return;

  const currentWorker = operatorAssignments.find(w => w.worker_id === activeOperatorWorkerId);
  const targetStationIds = currentWorker ? currentWorker.assigned_station_ids : Object.keys(stationsMeta);

  if (summaryEl) {
    if (currentWorker) {
      summaryEl.innerText = `Coverage: ${targetStationIds.length} Stations Allocated (${currentWorker.worker_name})`;
    } else {
      summaryEl.innerText = `Coverage: Showing all ${targetStationIds.length} stations (Unfiltered)`;
    }
  }

  if (targetStationIds.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; padding: 24px; background: #f8fafc; border: 1px dashed var(--border-subtle); border-radius: var(--radius-md); text-align: center;">
        <div style="font-weight: 800; font-size: 0.9rem; color: #0f172a; margin-bottom: 6px;">No Operator Assignments Configured</div>
        <div style="font-size: 0.78rem; color: var(--text-secondary);">Configure operator stations in the Leadership panel to enable filtered line views.</div>
      </div>
    `;
    return;
  }

  container.innerHTML = "";
  const stationsData = (latestTickData && latestTickData.stations) ? latestTickData.stations : {};

  targetStationIds.forEach(sid => {
    const meta = stationsMeta[sid] || {};
    const st = stationsData[sid] || {};

    const ct = st.cycle_time_s || meta.target_cycle_time_s || 60.0;
    const targetCt = meta.target_cycle_time_s || 60.0;
    const buf = st.buffer_level !== undefined ? st.buffer_level : 4;
    const cap = meta.buffer_capacity_units || 8;
    const vib = st.vibration !== undefined && st.vibration !== null ? st.vibration : 1.10;
    const temp = st.temperature !== undefined && st.temperature !== null ? st.temperature : 24.0;
    const pwr = st.power_kw || meta.power_base_kw || 30.0;
    const basePwr = meta.power_base_kw || 30.0;
    const risk = st.composite_risk || 0.05;
    const isBlackout = Boolean(st.is_blackout);
    const isStopped = Boolean(st.is_stopped);

    // Ideal reference baselines (Phase 7)
    let idealTemp = 24.0;
    if (meta.station_type === "ThermalOven") idealTemp = 190.0;
    else if (meta.station_type === "ChemicalBath" || meta.station_type === "ElectroDeposition") idealTemp = 55.0;

    let statusText = "NOMINAL";
    let statusClass = "status-nominal";
    if (isStopped) {
      statusText = "STOPPED";
      statusClass = "status-critical";
    } else if (isBlackout) {
      statusText = "POWER TRIP / DEGRADED";
      statusClass = "status-warning";
    } else if (risk >= 0.80) {
      statusText = "CRITICAL RISK";
      statusClass = "status-critical";
    } else if (risk >= 0.60) {
      statusText = "ELEVATED RISK";
      statusClass = "status-warning";
    }

    const card = document.createElement("div");
    card.style.cssText = `background: #ffffff; border: 1px solid ${risk >= 0.8 || isStopped ? 'var(--status-critical)' : 'var(--border-subtle)'}; border-radius: var(--radius-md); padding: 14px; box-shadow: var(--shadow-sm); display: flex; flex-direction: column; gap: 10px; cursor: pointer; transition: all 0.2s ease;`;
    card.onclick = () => focusStationOnFloor(sid);

    card.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-family: var(--font-mono); font-weight: 800; font-size: 0.95rem; color: #0f172a;">${sid}</span>
            <span class="node-tier-pill ${meta.sensor_tier === 'manual' ? 'manual' : ''}">${(meta.sensor_tier || 'rich').toUpperCase()}</span>
          </div>
          <div style="font-weight: 700; font-size: 0.82rem; color: #334155; margin-top: 2px;">${meta.name || sid}</div>
          <div style="font-size: 0.70rem; color: #64748b; font-family: var(--font-mono);">${meta.zone} // ${meta.station_type}</div>
        </div>
        <div style="text-align: right;">
          <span style="font-size: 0.68rem; font-weight: 800; font-family: var(--font-mono); padding: 3px 8px; border-radius: 4px; background: ${isStopped || risk >= 0.8 ? '#fee2e2' : (risk >= 0.6 ? '#fef3c7' : '#dcfce7')}; color: ${isStopped || risk >= 0.8 ? '#b91c1c' : (risk >= 0.6 ? '#b45309' : '#15803d')};">
            ${statusText}
          </span>
          <div style="font-size: 0.74rem; font-family: var(--font-mono); font-weight: 800; margin-top: 4px; color: ${risk >= 0.8 ? 'var(--status-critical)' : 'inherit'};">
            ${st.serving_mode && st.serving_mode.includes('fallback') ? '<span style="font-size: 0.65rem; background-color: #f59e0b; color: white; padding: 2px 4px; border-radius: 4px; margin-right: 4px; vertical-align: middle;" title="Model disconnected or diverging. Hard fallback to deterministic heuristic.">⚠ FALLBACK MODE</span>' : ''}Risk: ${(risk * 100).toFixed(0)}%
          </div>
        </div>
      </div>

      <!-- CURRENT VS IDEAL PARAMETERS TABLE (PHASE 7) -->
      <div style="background: #f8fafc; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 8px 10px; font-size: 0.72rem; font-family: var(--font-mono);">
        <div style="display: grid; grid-template-columns: 100px 1fr 1fr; font-weight: 800; color: #64748b; margin-bottom: 4px; border-bottom: 1px solid #e2e8f0; padding-bottom: 3px;">
          <span>PARAMETER</span>
          <span>CURRENT</span>
          <span>IDEAL (TARGET)</span>
        </div>
        <div style="display: grid; grid-template-columns: 100px 1fr 1fr; padding: 2px 0; color: ${ct > targetCt * 1.15 ? '#b91c1c' : '#0f172a'}; font-weight: ${ct > targetCt * 1.15 ? '700' : 'normal'};">
          <span>Job Time:</span>
          <span>${ct.toFixed(1)}s</span>
          <span style="color: #64748b;">${targetCt.toFixed(1)}s (Takt)</span>
        </div>
        <div style="display: grid; grid-template-columns: 100px 1fr 1fr; padding: 2px 0; color: ${vib > 4.5 ? '#b91c1c' : (vib > 2.8 ? '#b45309' : '#0f172a')}; font-weight: ${vib > 2.8 ? '700' : 'normal'};">
          <span>Vibration:</span>
          <span>${vib.toFixed(2)} mm/s</span>
          <span style="color: #64748b;">0.80 mm/s (≤4.5)</span>
        </div>
        <div style="display: grid; grid-template-columns: 100px 1fr 1fr; padding: 2px 0; color: #0f172a;">
          <span>Temperature:</span>
          <span>${temp.toFixed(1)}°C</span>
          <span style="color: #64748b;">${idealTemp.toFixed(1)}°C</span>
        </div>
        <div style="display: grid; grid-template-columns: 100px 1fr 1fr; padding: 2px 0; color: #0f172a;">
          <span>Power Draw:</span>
          <span>${pwr.toFixed(1)} kW</span>
          <span style="color: #64748b;">${basePwr.toFixed(1)} kW</span>
        </div>
      </div>

      <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.72rem; color: #64748b; font-family: var(--font-mono); padding-top: 2px;">
        <span>Buffer: ${buf}/${cap} units</span>
        <span style="color: var(--brand-blue); font-weight: 700;">Click to focus cell ➔</span>
      </div>
    `;

    container.appendChild(card);
  });
}

