/**
 * DigitalTwin.ai — Industrial DAG Topology Drag-and-Drop Editor
 * Allows plant engineers to add/delete stations, connect/disconnect flow edges,
 * re-route parallel tracks, auto-align layout, and reboot the Digital Twin in real-time.
 * Features full Undo (Ctrl+Z) and Redo (Ctrl+Y) history state management.
 */

let editorStations = {};
let editorEdges = [];
let isDraggingNode = false;
let dragContext = null;
let activeConnectingPort = null; // Used for click-to-connect mode
let isDraggingEdge = false;
let tempEdgeStart = null;

// Undo / Redo History Stacks (Snapshots of { stations, edges, coords })
const undoStack = [];
const redoStack = [];
const MAX_HISTORY = 50;

// Ensure stationCoords global exists
if (typeof window.stationCoords === "undefined") {
  window.stationCoords = {};
}

/**
 * Capture current topology snapshot for Undo/Redo history
 */
function pushHistorySnapshot() {
  const snapshot = {
    stations: JSON.parse(JSON.stringify(editorStations)),
    edges: JSON.parse(JSON.stringify(editorEdges)),
    coords: JSON.parse(JSON.stringify(window.stationCoords))
  };

  undoStack.push(snapshot);
  if (undoStack.length > MAX_HISTORY) {
    undoStack.shift();
  }

  // Clear redo stack on new action
  redoStack.length = 0;
  updateUndoRedoUI();
}

/**
 * Update Undo / Redo button disabled states
 */
function updateUndoRedoUI() {
  const btnUndo = document.getElementById("btn-undo");
  const btnRedo = document.getElementById("btn-redo");

  if (btnUndo) {
    btnUndo.disabled = undoStack.length === 0;
  }
  if (btnRedo) {
    btnRedo.disabled = redoStack.length === 0;
  }
}

/**
 * Undo Last Action (Ctrl + Z)
 */
function undo() {
  if (undoStack.length === 0) {
    showToast("ℹ️ Nothing to undo", 1500);
    return;
  }

  // Save current state to Redo stack
  const currentState = {
    stations: JSON.parse(JSON.stringify(editorStations)),
    edges: JSON.parse(JSON.stringify(editorEdges)),
    coords: JSON.parse(JSON.stringify(window.stationCoords))
  };
  redoStack.push(currentState);
  if (redoStack.length > MAX_HISTORY) redoStack.shift();

  // Restore previous state from Undo stack
  const prevState = undoStack.pop();
  editorStations = JSON.parse(JSON.stringify(prevState.stations));
  editorEdges = JSON.parse(JSON.stringify(prevState.edges));
  window.stationCoords = JSON.parse(JSON.stringify(prevState.coords));

  cancelConnectingMode();
  renderEditorCanvas();
  updateUndoRedoUI();
  showToast("↩️ Undo: Reverted action", 1800);
}

/**
 * Redo Last Undone Action (Ctrl + Y or Ctrl + Shift + Z)
 */
function redo() {
  if (redoStack.length === 0) {
    showToast("ℹ️ Nothing to redo", 1500);
    return;
  }

  // Save current state to Undo stack
  const currentState = {
    stations: JSON.parse(JSON.stringify(editorStations)),
    edges: JSON.parse(JSON.stringify(editorEdges)),
    coords: JSON.parse(JSON.stringify(window.stationCoords))
  };
  undoStack.push(currentState);
  if (undoStack.length > MAX_HISTORY) undoStack.shift();

  // Restore next state from Redo stack
  const nextState = redoStack.pop();
  editorStations = JSON.parse(JSON.stringify(nextState.stations));
  editorEdges = JSON.parse(JSON.stringify(nextState.edges));
  window.stationCoords = JSON.parse(JSON.stringify(nextState.coords));

  cancelConnectingMode();
  renderEditorCanvas();
  updateUndoRedoUI();
  showToast("↪️ Redo: Reapplied action", 1800);
}

/**
 * Initialize Topology Editor from API or existing runtime state
 */
async function initTopologyEditor() {
  try {
    const res = await fetch("/api/stations");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    editorStations = JSON.parse(JSON.stringify(data.stations || {}));
    editorEdges = JSON.parse(JSON.stringify(data.edges || []));
    
    // Ensure all stations have coordinates
    Object.keys(editorStations).forEach((sid, idx) => {
      if (!window.stationCoords[sid]) {
        const zone = (editorStations[sid].zone || "Body").toLowerCase();
        let yOffset = 80;
        if (zone.includes("paint")) yOffset = 360;
        else if (zone.includes("assembly")) yOffset = 620;

        window.stationCoords[sid] = {
          x: 40 + (idx % 8) * 190,
          y: yOffset + Math.floor((idx % 24) / 8) * 140
        };
      }
    });

    // Reset undo/redo history on fresh load
    undoStack.length = 0;
    redoStack.length = 0;
    updateUndoRedoUI();

    renderEditorCanvas();
    showToast("🛠️ DAG Topology Editor active. Drag cards or connect IN/OUT ports.", 2500);
  } catch (err) {
    console.error("Failed to load topology for editor:", err);
    showToast("⚠️ Could not load topology: " + err.message, 3500);
  }
}

/**
 * Updates the editor toolbar counters
 */
function updateEditorCounter() {
  const countEl = document.getElementById("editor-station-count");
  if (countEl) {
    const sCount = Object.keys(editorStations).length;
    const eCount = editorEdges.length;
    countEl.innerText = `${sCount} STATIONS // ${eCount} FLOW EDGES`;
  }
}

// Industrial Manufacturing Asset Symbol Catalog (30 Machine Categories)
const ASSET_SYMBOLS = [
  { type: "RoboticWeld", label: "Robotic Weld", icon: "🦾", zone: "Body", desc: "Robotic Spot & Arc Welder" },
  { type: "LaserBrazing", label: "Laser Brazing", icon: "⚡", zone: "Body", desc: "Precision Roof Laser Brazing" },
  { type: "MainFraming", label: "Main Framing", icon: "🏗️", zone: "Body", desc: "Body Framing Geometry Rig" },
  { type: "RespotWeld", label: "Respot Weld", icon: "⚡", zone: "Body", desc: "Respot Resistance Welder" },
  { type: "Dispensing", label: "Sealer Dispense", icon: "💧", zone: "Body", desc: "Structural Adhesive Dispenser" },
  { type: "Fitting", label: "Door & Panel Fit", icon: "🚪", zone: "Body", desc: "Door/Hood Alignment Rig" },
  { type: "QualityScan", label: "CMM Laser Scan", icon: "🔍", zone: "Body", desc: "3D Geometry Optical Scan" },
  { type: "ManualFinishing", label: "Metal Polish", icon: "🪚", zone: "Body", desc: "Manual Metal Finishing" },
  { type: "SubAssembly", label: "Sub-Assembly", icon: "⚙️", zone: "Body", desc: "Underbody Press & Jigs" },
  { type: "ChemicalBath", label: "Chemical Bath", icon: "🧪", zone: "Paint", desc: "Degreasing & Pre-Treatment" },
  { type: "ElectroDeposition", label: "E-Coat Dip", icon: "⚡", zone: "Paint", desc: "Cathodic E-Coat Immersion" },
  { type: "ThermalOven", label: "Thermal Oven", icon: "🔥", zone: "Paint", desc: "E-Coat Curing Thermal Oven" },
  { type: "ManualSealing", label: "PVC Sealing", icon: "🪛", zone: "Paint", desc: "Underbody PVC Manual Seal" },
  { type: "RoboticSpray", label: "Paint Spray", icon: "🎨", zone: "Paint", desc: "Automated Spray Booth" },
  { type: "VisionQC", label: "Vision QC", icon: "👁️", zone: "Paint", desc: "Surface & Paint Vision Check" },
  { type: "TransferBuffer", label: "Transfer Buffer", icon: "📦", zone: "Transfer", desc: "Conveyor Buffer / Lift Table" },
  { type: "ManualWiring", label: "Wire Harness", icon: "🔌", zone: "Assembly", desc: "Wiring Harness Routing" },
  { type: "ModuleMarriage", label: "Module Marriage", icon: "🧩", zone: "Assembly", desc: "Cockpit / IP Marriage" },
  { type: "MechanicalTorque", label: "Chassis Torque", icon: "🔧", zone: "Assembly", desc: "Suspension Mechanical Torque" },
  { type: "AutomatedMarriage", label: "Battery Marriage", icon: "🔋", zone: "Assembly", desc: "Drivetrain & Battery Marriage" },
  { type: "RoboticTorque", label: "Robotic Torque", icon: "⚙️", zone: "Assembly", desc: "Undercarriage Nutrunner" },
  { type: "RoboticUrethane", label: "Robotic Glazing", icon: "🪟", zone: "Assembly", desc: "Windshield Robotic Glazing" },
  { type: "ManualTrim", label: "Interior Trim", icon: "✂️", zone: "Assembly", desc: "Headliner & Pillars Trim" },
  { type: "SafetyCalibration", label: "Safety / ADAS", icon: "🎯", zone: "Assembly", desc: "Steering & Safety Calibration" },
  { type: "AutomatedTorque", label: "Wheel Torquing", icon: "🔩", zone: "Assembly", desc: "Automated 5-Spindle Torque" },
  { type: "FluidFill", label: "Fluid Vacuum Fill", icon: "🛢️", zone: "Assembly", desc: "Brake/Coolant Vacuum Fill" },
  { type: "ManualFitting", label: "Weatherstrip Fit", icon: "🧤", zone: "Assembly", desc: "Door Weatherstrip Manual Fit" },
  { type: "ElectronicFlash", label: "ECU Flash", icon: "💻", zone: "Assembly", desc: "EOL ECU Flash & Sync" },
  { type: "DynamicTest", label: "Dynamometer", icon: "🏎️", zone: "Assembly", desc: "Dynamometer & Roll Bench" },
  { type: "FinalInspection", label: "Final Buy-off", icon: "🏁", zone: "Assembly", desc: "Final ADAS Buy-Off Tunnel" }
];

function getAssetSymbolInfo(type) {
  if (!type) return { icon: "⚙️", label: "Station", desc: "Standard Station" };
  const lower = String(type).toLowerCase();
  const match = ASSET_SYMBOLS.find(s => s.type.toLowerCase() === lower);
  return match || { icon: "⚙️", label: type, desc: type };
}

/**
 * Main Render Function for Canvas & Stations
 */
function renderEditorCanvas() {
  const canvas = document.getElementById("editor-canvas");
  if (!canvas) return;

  canvas.innerHTML = "";
  updateEditorCounter();

  // Create SVG Layer for Flow Conveyor Edges
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.id = "editor-edges-svg";
  svg.style.position = "absolute";
  svg.style.top = "0";
  svg.style.left = "0";
  svg.style.width = "3200px";
  svg.style.height = "2000px";
  svg.style.pointerEvents = "none";

  // Arrow marker definition
  const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
  defs.innerHTML = `
    <marker id="ed-arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#0284c7" />
    </marker>
    <marker id="ed-arrow-hover" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#ef4444" />
    </marker>
  `;
  svg.appendChild(defs);
  canvas.appendChild(svg);

  // Render Station Nodes
  const sids = Object.keys(editorStations);
  sids.forEach((sid, idx) => {
    const meta = editorStations[sid];
    const zoneLabel = (meta.zone || "BODY").toUpperCase();
    let zoneClass = "zone-body";
    if (zoneLabel.includes("PAINT")) {
      zoneClass = "zone-paint";
    } else if (zoneLabel.includes("ASSEMBLY")) {
      zoneClass = "zone-assembly";
    }

    // Coordinates fallback
    let coords = window.stationCoords[sid];
    if (!coords) {
      coords = {
        x: 50 + (idx % 8) * 190,
        y: 80 + Math.floor(idx / 8) * 150
      };
      window.stationCoords[sid] = coords;
    }

    const node = document.createElement("div");
    node.className = `editor-node ${zoneClass}`;
    node.id = `ed-node-${sid}`;
    node.style.left = `${coords.x}px`;
    node.style.top = `${coords.y}px`;

    const taktTime = meta.target_cycle_time_s || meta.target_cycle_time || 55.0;
    const bufCap = meta.buffer_capacity_units || 8;
    const tier = (meta.sensor_tier || "RICH").toUpperCase();
    const stName = meta.name || sid;
    const assetInfo = getAssetSymbolInfo(meta.station_type || meta.type);

    node.innerHTML = `
      <div class="ed-node-header">
        <span class="ed-node-title"><span class="ed-node-glyph-icon">${assetInfo.icon}</span>${sid}</span>
        <span class="ed-node-zone-pill">${zoneLabel.split(" ")[0]}</span>
      </div>
      <div class="ed-node-desc" title="${stName} (${assetInfo.label})">${stName}</div>
      <div class="ed-node-meta">
        <span>Takt: <strong>${taktTime}s</strong></span>
        <span>Cap: <strong>${bufCap}</strong></span>
        <span><strong>${tier}</strong></span>
      </div>
      
      <!-- Flow Ports -->
      <div class="ed-port ed-port-in" id="port-in-${sid}" data-sid="${sid}" data-type="in" title="Input Port (Drop or click here to connect incoming conveyor)">IN</div>
      <div class="ed-port ed-port-out" id="port-out-${sid}" data-sid="${sid}" data-type="out" title="Output Port (Drag or click to connect outgoing conveyor)">OUT</div>
      
      <!-- Action Buttons -->
      <button class="ed-node-edit" title="Edit station parameters & symbol (or double-click)" onclick="openEditStationModal('${sid}')">✏️</button>
      <button class="ed-node-del" title="Delete station from line" onclick="deleteEditorNode('${sid}')">✕</button>
    `;

    // Double click to open Edit Modal directly
    node.addEventListener("dblclick", (e) => {
      e.stopPropagation();
      openEditStationModal(sid);
    });

    // Port Mouse & Click Listeners
    const portIn = node.querySelector(".ed-port-in");
    const portOut = node.querySelector(".ed-port-out");

    portOut.addEventListener("mousedown", (e) => onPortMouseDown(e, sid, "out"));
    portOut.addEventListener("click", (e) => onPortClick(e, sid, "out"));

    portIn.addEventListener("mouseup", (e) => onPortMouseUp(e, sid, "in"));
    portIn.addEventListener("click", (e) => onPortClick(e, sid, "in"));

    // Node Drag Handler
    node.addEventListener("mousedown", (e) => {
      if (e.target.classList.contains("ed-port") || e.target.classList.contains("ed-node-del") || e.target.classList.contains("ed-node-edit")) return;
      isDraggingNode = true;
      dragContext = {
        sid: sid,
        el: node,
        startMouseX: e.clientX,
        startMouseY: e.clientY,
        startNodeX: parseInt(node.style.left, 10) || coords.x,
        startNodeY: parseInt(node.style.top, 10) || coords.y,
        hasMoved: false,
        preDragSnapshot: {
          stations: JSON.parse(JSON.stringify(editorStations)),
          edges: JSON.parse(JSON.stringify(editorEdges)),
          coords: JSON.parse(JSON.stringify(window.stationCoords))
        }
      };
      node.style.zIndex = "100";
    });

    canvas.appendChild(node);
  });

  drawEditorEdges();
}

/**
 * Handle Port Mousedown (Start Dragging Edge)
 */
function onPortMouseDown(e, sid, type) {
  e.stopPropagation();
  if (type !== "out") return;

  isDraggingEdge = true;
  const portEl = document.getElementById(`port-out-${sid}`);
  const canvas = document.getElementById("editor-canvas");
  if (!portEl || !canvas) return;

  const portRect = portEl.getBoundingClientRect();
  const canvasRect = canvas.getBoundingClientRect();

  tempEdgeStart = {
    sid: sid,
    x: portRect.left + portRect.width / 2 - canvasRect.left + canvas.scrollLeft,
    y: portRect.top + portRect.height / 2 - canvasRect.top + canvas.scrollTop
  };
}

/**
 * Handle Port Click (Click-to-Connect Mode)
 */
function onPortClick(e, sid, type) {
  e.stopPropagation();

  if (type === "out") {
    // Select source station
    if (activeConnectingPort && activeConnectingPort.sid === sid) {
      // Cancel selection
      cancelConnectingMode();
      return;
    }

    cancelConnectingMode();
    activeConnectingPort = { sid: sid, type: "out" };
    
    const portEl = document.getElementById(`port-out-${sid}`);
    if (portEl) portEl.classList.add("port-selected-active");

    const modePill = document.getElementById("editor-mode-indicator");
    if (modePill) {
      modePill.style.display = "inline-flex";
      modePill.innerText = `🔗 Connecting from ${sid} → Click target [IN] port`;
    }
    showToast(`🔗 Connecting from ${sid}: Click target station's [IN] port (or press ESC to cancel)`, 3000);
  } else if (type === "in") {
    if (activeConnectingPort && activeConnectingPort.type === "out") {
      const sourceSid = activeConnectingPort.sid;
      const targetSid = sid;
      cancelConnectingMode();
      createConveyorLink(sourceSid, targetSid);
    }
  }
}

/**
 * Handle Port MouseUp (Complete Dragged Edge)
 */
function onPortMouseUp(e, sid, type) {
  if (isDraggingEdge && tempEdgeStart && type === "in") {
    e.stopPropagation();
    const sourceSid = tempEdgeStart.sid;
    const targetSid = sid;
    isDraggingEdge = false;
    tempEdgeStart = null;
    clearTempEdge();
    createConveyorLink(sourceSid, targetSid);
  }
}

/**
 * Cancels active click-to-connect mode
 */
function cancelConnectingMode() {
  if (activeConnectingPort) {
    const portEl = document.getElementById(`port-out-${activeConnectingPort.sid}`);
    if (portEl) portEl.classList.remove("port-selected-active");
  }
  activeConnectingPort = null;
  const modePill = document.getElementById("editor-mode-indicator");
  if (modePill) modePill.style.display = "none";
}

/**
 * Connect Two Stations with validation (Records history snapshot)
 */
function createConveyorLink(sourceSid, targetSid) {
  if (sourceSid === targetSid) {
    showToast("⚠️ Cannot connect a station to itself!", 2500);
    return;
  }

  // Check if edge already exists
  const alreadyExists = editorEdges.some(e => e[0] === sourceSid && e[1] === targetSid);
  if (alreadyExists) {
    showToast(`⚠️ Conveyor link ${sourceSid} ➔ ${targetSid} already exists!`, 2500);
    return;
  }

  // Record snapshot before modifying
  pushHistorySnapshot();

  // Add Edge
  editorEdges.push([sourceSid, targetSid]);
  drawEditorEdges();
  updateEditorCounter();
  showToast(`✅ Connected conveyor: ${sourceSid} ➔ ${targetSid}`, 2500);
}

/**
 * Draw all conveyor bezier curves on SVG layer
 */
function drawEditorEdges() {
  const svg = document.getElementById("editor-edges-svg");
  const canvas = document.getElementById("editor-canvas");
  if (!svg || !canvas) return;

  // Clear existing paths (preserve defs)
  const paths = svg.querySelectorAll("g.edge-group");
  paths.forEach(p => p.remove());

  const canvasRect = canvas.getBoundingClientRect();

  editorEdges.forEach((edge, idx) => {
    const [u, v] = edge;
    const node1 = document.getElementById(`ed-node-${u}`);
    const node2 = document.getElementById(`ed-node-${v}`);
    if (!node1 || !node2) return;

    const p1 = node1.querySelector(".ed-port-out");
    const p2 = node2.querySelector(".ed-port-in");
    if (!p1 || !p2) return;

    const r1 = p1.getBoundingClientRect();
    const r2 = p2.getBoundingClientRect();

    const x1 = r1.left + r1.width / 2 - canvasRect.left + canvas.scrollLeft;
    const y1 = r1.top + r1.height / 2 - canvasRect.top + canvas.scrollTop;
    const x2 = r2.left + r2.width / 2 - canvasRect.left + canvas.scrollLeft;
    const y2 = r2.top + r2.height / 2 - canvasRect.top + canvas.scrollTop;

    const dx = Math.abs(x2 - x1);
    let cx1, cy1, cx2, cy2;

    if (x2 >= x1) {
      // Forward Left-to-Right curve
      const ctrlDx = Math.max(30, (x2 - x1) * 0.5);
      cx1 = x1 + ctrlDx;
      cy1 = y1;
      cx2 = x2 - ctrlDx;
      cy2 = y2;
    } else {
      // Reverse / Row-Wrap S-curve: clamp control points cleanly so they don't clip off borders
      const loopOffset = Math.min(75, Math.max(35, Math.abs(y2 - y1) * 0.35));
      cx1 = x1 + loopOffset;
      cy1 = y1 + (y2 > y1 ? 25 : -25);
      cx2 = Math.max(25, x2 - loopOffset);
      cy2 = y2 - (y2 > y1 ? 25 : -25);
    }

    const pathD = `M ${x1} ${y1} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${x2} ${y2}`;

    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("class", "edge-group");
    g.style.pointerEvents = "all";
    g.style.cursor = "pointer";

    // Hit-testing transparent broad stroke
    const hitPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    hitPath.setAttribute("d", pathD);
    hitPath.setAttribute("stroke", "transparent");
    hitPath.setAttribute("stroke-width", "20");
    hitPath.setAttribute("fill", "none");

    // Visible styled conveyor path
    const visiblePath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    visiblePath.setAttribute("d", pathD);
    visiblePath.setAttribute("stroke", "#0284c7");
    visiblePath.setAttribute("stroke-width", "2.8");
    visiblePath.setAttribute("fill", "none");
    visiblePath.setAttribute("marker-end", "url(#ed-arrow)");

    // Hover & Click handlers to Disconnect
    g.addEventListener("mouseenter", () => {
      visiblePath.setAttribute("stroke", "#ef4444");
      visiblePath.setAttribute("stroke-width", "4.5");
      visiblePath.setAttribute("marker-end", "url(#ed-arrow-hover)");
    });

    g.addEventListener("mouseleave", () => {
      visiblePath.setAttribute("stroke", "#0284c7");
      visiblePath.setAttribute("stroke-width", "2.8");
      visiblePath.setAttribute("marker-end", "url(#ed-arrow)");
    });

    g.addEventListener("click", () => {
      deleteEdge(u, v);
    });

    g.appendChild(hitPath);
    g.appendChild(visiblePath);
    svg.appendChild(g);
  });
}

/**
 * Remove an edge connection (Records history snapshot)
 */
function deleteEdge(u, v) {
  const idx = editorEdges.findIndex(e => e[0] === u && e[1] === v);
  if (idx !== -1) {
    pushHistorySnapshot();
    editorEdges.splice(idx, 1);
    drawEditorEdges();
    updateEditorCounter();
    showToast(`✂️ Disconnected conveyor: ${u} ➔ ${v}`, 2500);
  }
}

/**
 * Draw Temporary Dragging Edge
 */
function drawTempEdge(x1, y1, x2, y2) {
  const svg = document.getElementById("editor-edges-svg");
  if (!svg) return;

  clearTempEdge();

  const dx = Math.abs(x2 - x1) * 0.5;
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.id = "temp-edge-path";
  path.setAttribute("d", `M ${x1} ${y1} C ${x1 + Math.max(40, dx)} ${y1}, ${x2 - Math.max(40, dx)} ${y2}, ${x2} ${y2}`);
  path.setAttribute("stroke", "#f59e0b");
  path.setAttribute("stroke-width", "3.2");
  path.setAttribute("stroke-dasharray", "6 4");
  path.setAttribute("fill", "none");
  path.style.pointerEvents = "none";
  svg.appendChild(path);
}

function clearTempEdge() {
  const svg = document.getElementById("editor-edges-svg");
  if (svg) {
    const existing = svg.querySelector("#temp-edge-path");
    if (existing) existing.remove();
  }
}

/**
 * Global Window Event Listeners for Smooth Dragging & Undo/Redo Keys
 */
window.addEventListener("mousemove", (e) => {
  const canvas = document.getElementById("editor-canvas");
  if (!canvas) return;

  // Node Dragging
  if (isDraggingNode && dragContext) {
    const deltaX = e.clientX - dragContext.startMouseX;
    const deltaY = e.clientY - dragContext.startMouseY;
    
    if (Math.abs(deltaX) > 2 || Math.abs(deltaY) > 2) {
      dragContext.hasMoved = true;
    }

    const newX = Math.max(20, dragContext.startNodeX + deltaX);
    const newY = Math.max(20, dragContext.startNodeY + deltaY);

    dragContext.el.style.left = `${newX}px`;
    dragContext.el.style.top = `${newY}px`;
    window.stationCoords[dragContext.sid] = { x: newX, y: newY };

    drawEditorEdges();
  }

  // Edge Dragging
  if (isDraggingEdge && tempEdgeStart) {
    const canvasRect = canvas.getBoundingClientRect();
    const curX = e.clientX - canvasRect.left + canvas.scrollLeft;
    const curY = e.clientY - canvasRect.top + canvas.scrollTop;
    drawTempEdge(tempEdgeStart.x, tempEdgeStart.y, curX, curY);
  }
});

window.addEventListener("mouseup", (e) => {
  if (isDraggingNode && dragContext) {
    dragContext.el.style.zIndex = "10";
    if (dragContext.hasMoved && dragContext.preDragSnapshot) {
      // Push history state from before drag started
      undoStack.push(dragContext.preDragSnapshot);
      if (undoStack.length > MAX_HISTORY) undoStack.shift();
      redoStack.length = 0;
      updateUndoRedoUI();
    }
    isDraggingNode = false;
    dragContext = null;
  }

  if (isDraggingEdge) {
    // Check if mouseup happened on an IN port
    const elem = document.elementFromPoint(e.clientX, e.clientY);
    if (elem && elem.classList.contains("ed-port") && elem.dataset.type === "in") {
      const targetSid = elem.dataset.sid;
      if (tempEdgeStart && targetSid) {
        createConveyorLink(tempEdgeStart.sid, targetSid);
      }
    }
    isDraggingEdge = false;
    tempEdgeStart = null;
    clearTempEdge();
  }
});

// Keyboard Shortcuts (Ctrl+Z for Undo, Ctrl+Y or Ctrl+Shift+Z for Redo, ESC for cancel)
window.addEventListener("keydown", (e) => {
  // Ignore inside inputs/textareas
  const targetTag = e.target ? e.target.tagName.toLowerCase() : "";
  if (targetTag === "input" || targetTag === "textarea" || targetTag === "select") {
    return;
  }

  if (e.key === "Escape") {
    cancelConnectingMode();
    isDraggingEdge = false;
    tempEdgeStart = null;
    clearTempEdge();
    return;
  }

  // Only apply when topology editor is active view
  if (typeof window.currentView !== "undefined" && window.currentView !== "topology") {
    return;
  }

  if (e.ctrlKey || e.metaKey) {
    if (e.key === "z" || e.key === "Z") {
      e.preventDefault();
      if (e.shiftKey) {
        redo();
      } else {
        undo();
      }
    } else if (e.key === "y" || e.key === "Y") {
      e.preventDefault();
      redo();
    }
  }
});

/**
 * Delete a Station from DAG (Records history snapshot)
 */
function deleteEditorNode(sid) {
  const name = editorStations[sid]?.name || sid;
  if (!confirm(`Are you sure you want to remove station ${sid} (${name}) and its conveyor links from the layout?`)) {
    return;
  }

  pushHistorySnapshot();

  delete editorStations[sid];
  delete window.stationCoords[sid];
  editorEdges = editorEdges.filter(e => e[0] !== sid && e[1] !== sid);

  renderEditorCanvas();
  showToast(`🗑️ Station ${sid} removed from line. (Ctrl+Z to undo)`, 2500);
}

/**
 * Auto-Arrange Layout across 3 Manufacturing Zones (Records history snapshot)
 */
function autoArrangeLayout() {
  const sids = Object.keys(editorStations);
  if (sids.length === 0) return;

  pushHistorySnapshot();

  const bodySids = [];
  const paintSids = [];
  const assemblySids = [];
  const otherSids = [];

  sids.forEach(sid => {
    const zone = (editorStations[sid].zone || "").toLowerCase();
    if (zone.includes("body")) bodySids.push(sid);
    else if (zone.includes("paint")) paintSids.push(sid);
    else if (zone.includes("assembly")) assemblySids.push(sid);
    else otherSids.push(sid);
  });

  const arrangeRow = (list, startY, rowSpacing = 160) => {
    list.forEach((sid, i) => {
      const col = i % 8;
      const row = Math.floor(i / 8);
      window.stationCoords[sid] = {
        x: 80 + col * 190,
        y: startY + row * rowSpacing
      };
    });
  };

  arrangeRow(bodySids, 60);
  const bodyRows = Math.ceil(bodySids.length / 8) || 1;
  const paintStartY = 60 + bodyRows * 160 + 50;

  arrangeRow(paintSids, paintStartY);
  const paintRows = Math.ceil(paintSids.length / 8) || 1;
  const assemblyStartY = paintStartY + paintRows * 160 + 50;

  arrangeRow(assemblySids, assemblyStartY);
  const assemblyRows = Math.ceil(assemblySids.length / 8) || 1;
  const otherStartY = assemblyStartY + assemblyRows * 160 + 50;

  arrangeRow(otherSids, otherStartY);

  renderEditorCanvas();
  showToast("📐 Layout auto-arranged across manufacturing zone tracks.", 3000);
}

/**
 * Modal Handling for Adding a Station
 */
function showAddStationModal() {
  const sids = Object.keys(editorStations);
  let maxNum = 0;
  sids.forEach(sid => {
    const num = parseInt(sid.replace("ST", ""), 10);
    if (!isNaN(num) && num > maxNum) maxNum = num;
  });

  const nextSid = `ST${(maxNum + 1).toString().padStart(2, "0")}`;
  const sidInput = document.getElementById("new-sid");
  if (sidInput) sidInput.value = nextSid;

  const maintDateInput = document.getElementById("new-maint-date");
  if (maintDateInput) {
    const now = new Date();
    now.setDate(now.getDate() + 7);
    now.setHours(8, 0, 0, 0);
    const isoStr = now.toISOString().slice(0, 16);
    maintDateInput.value = isoStr;
  }

  const modal = document.getElementById("add-station-modal");
  if (modal) modal.style.display = "flex";
}

function closeAddStationModal() {
  const modal = document.getElementById("add-station-modal");
  if (modal) modal.style.display = "none";
}

function toggleSensorFields() {
  const tier = document.getElementById("new-tier")?.value;
  const powerBox = document.getElementById("sensor-specific-fields");
  if (powerBox) {
    powerBox.style.display = (tier === "rich") ? "block" : "none";
  }
}

/**
 * Submit New Station from Modal (Records history snapshot)
 */
function submitAddStation() {
  const sid = document.getElementById("new-sid")?.value.trim().toUpperCase();
  const name = document.getElementById("new-name")?.value.trim();
  const zone = document.getElementById("new-zone")?.value || "Body";
  const type = document.getElementById("new-type")?.value || "RoboticWeld";
  const ct = parseFloat(document.getElementById("new-ct")?.value || 55.0);
  const tier = document.getElementById("new-tier")?.value || "rich";
  const buffer = parseInt(document.getElementById("new-buffer")?.value || 8, 10);
  const power = parseFloat(document.getElementById("new-power")?.value || 28.0);
  const maintDate = document.getElementById("new-maint-date")?.value || "2026-03-15T08:00";
  const maintInterval = parseInt(document.getElementById("new-maint-interval")?.value || 168, 10);

  if (!sid || !name) {
    alert("Please provide both Station ID and Station Name.");
    return;
  }

  if (editorStations[sid]) {
    alert(`Station ID ${sid} already exists! Please use a unique ID.`);
    return;
  }

  // Record snapshot before adding
  pushHistorySnapshot();

  // Register Station Object
  editorStations[sid] = {
    id: sid,
    station_id: sid,
    name: name,
    zone: zone,
    station_type: type,
    type: type,
    target_cycle_time: ct,
    target_cycle_time_s: ct,
    buffer_capacity_units: buffer,
    sensor_tier: tier,
    power_base_kw: tier === "rich" ? power : null,
    next_maintenance_date: maintDate,
    maintenance_interval_hours: maintInterval,
    upstream_ids: [],
    downstream_ids: [],
    metadata: { manufacturer: "Custom Industrial Station" }
  };

  // Smart Zone-aware initial position
  const zoneKey = zone.toLowerCase();
  let defaultY = 80;
  if (zoneKey.includes("paint")) defaultY = 360;
  else if (zoneKey.includes("assembly")) defaultY = 620;

  const existingInZone = Object.keys(editorStations).filter(s => s !== sid && (editorStations[s].zone || "").toLowerCase().includes(zoneKey));
  const zoneIndex = existingInZone.length;

  window.stationCoords[sid] = {
    x: 80 + (zoneIndex % 8) * 190,
    y: defaultY + Math.floor(zoneIndex / 8) * 140
  };

  closeAddStationModal();
  renderEditorCanvas();
  showToast(`✨ Added station ${sid} (${name}) to ${zone}! Drag into place and link ports.`, 3500);
}

/**
 * Render Asset Symbol Grid for Modal
 */
function renderAssetSymbolGrid(selectedType = "RoboticWeld") {
  const grid = document.getElementById("edit-symbol-grid");
  if (!grid) return;

  grid.innerHTML = "";
  ASSET_SYMBOLS.forEach(item => {
    const isSelected = item.type.toLowerCase() === selectedType.toLowerCase();
    const chip = document.createElement("div");
    chip.className = `asset-symbol-chip ${isSelected ? "active" : ""}`;
    chip.id = `symbol-chip-${item.type}`;
    chip.onclick = () => selectAssetSymbol(item.type);

    chip.innerHTML = `
      <span class="asset-chip-icon">${item.icon}</span>
      <div style="overflow: hidden; flex: 1;">
        <div class="asset-chip-label" title="${item.desc}">${item.label}</div>
        <div class="asset-chip-zone">${item.zone}</div>
      </div>
    `;
    grid.appendChild(chip);
  });
}

function selectAssetSymbol(type) {
  const hiddenInput = document.getElementById("edit-type");
  if (hiddenInput) hiddenInput.value = type;

  const labelEl = document.getElementById("edit-selected-type-label");
  const assetInfo = getAssetSymbolInfo(type);
  if (labelEl) labelEl.innerText = `${assetInfo.icon} ${assetInfo.label} (${type})`;

  // Update chip active classes
  const chips = document.querySelectorAll(".asset-symbol-chip");
  chips.forEach(c => c.classList.remove("active"));
  const activeChip = document.getElementById(`symbol-chip-${type}`);
  if (activeChip) activeChip.classList.add("active");

  updateEditPreview();
}

function toggleEditSensorFields() {
  const tier = document.getElementById("edit-tier")?.value;
  const powerBox = document.getElementById("edit-power-group");
  if (powerBox) {
    powerBox.style.display = (tier === "rich") ? "block" : "none";
  }
}

function updateEditPreview() {
  const sid = document.getElementById("edit-sid")?.value || "ST01";
  const name = document.getElementById("edit-name")?.value.trim() || `Station ${sid}`;
  const zone = document.getElementById("edit-zone")?.value || "Body";
  const tier = document.getElementById("edit-tier")?.value || "rich";
  const type = document.getElementById("edit-type")?.value || "RoboticWeld";
  const ct = document.getElementById("edit-ct")?.value || "55.0";

  const assetInfo = getAssetSymbolInfo(type);

  const glyphEl = document.getElementById("edit-preview-glyph");
  const nameEl = document.getElementById("edit-preview-name");
  const zoneEl = document.getElementById("edit-preview-zone");
  const tierEl = document.getElementById("edit-preview-tier");
  const taktEl = document.getElementById("edit-preview-takt");

  if (glyphEl) glyphEl.innerHTML = `<span style="font-size: 1.25rem;">${assetInfo.icon}</span>`;
  if (nameEl) nameEl.innerText = name;
  if (zoneEl) zoneEl.innerText = `${zone} Zone`;
  if (tierEl) tierEl.innerText = tier === "rich" ? "RICH PLC SENSOR" : "MANUAL SENSOR";
  if (taktEl) taktEl.innerText = `${ct}s Takt`;
}

/**
 * Open Edit Station Modal with pre-populated values
 */
function openEditStationModal(sid) {
  const meta = editorStations[sid];
  if (!meta) {
    showToast(`⚠️ Station ${sid} not found in editor layout.`, 2500);
    return;
  }

  const sidInput = document.getElementById("edit-sid");
  const sidBadge = document.getElementById("edit-sid-badge");
  const nameInput = document.getElementById("edit-name");
  const zoneSelect = document.getElementById("edit-zone");
  const tierSelect = document.getElementById("edit-tier");
  const typeInput = document.getElementById("edit-type");
  const ctInput = document.getElementById("edit-ct");
  const bufferInput = document.getElementById("edit-buffer");
  const powerInput = document.getElementById("edit-power");

  if (sidInput) sidInput.value = sid;
  if (sidBadge) sidBadge.innerText = sid;
  if (nameInput) nameInput.value = meta.name || sid;
  if (zoneSelect) zoneSelect.value = meta.zone || "Body";
  if (tierSelect) tierSelect.value = meta.sensor_tier || "rich";

  const currentType = meta.station_type || meta.type || "RoboticWeld";
  if (typeInput) typeInput.value = currentType;

  if (ctInput) ctInput.value = meta.target_cycle_time_s || meta.target_cycle_time || 55.0;
  if (bufferInput) bufferInput.value = meta.buffer_capacity_units || 8;
  if (powerInput) powerInput.value = meta.power_base_kw || 28.0;

  // Maintenance Schedule & Calendar Population
  const maintDateInput = document.getElementById("edit-maint-date");
  const maintIntervalInput = document.getElementById("edit-maint-interval");
  if (maintDateInput) {
    const dayOffset = (((parseInt(sid.replace('ST',''), 10) || 1) * 3) % 18 + 5).toString().padStart(2, '0');
    maintDateInput.value = meta.next_maintenance_date || `2026-03-${dayOffset}T08:00`;
  }
  if (maintIntervalInput) {
    maintIntervalInput.value = meta.maintenance_interval_hours || (meta.sensor_tier === "rich" ? 168 : 336);
  }

  // Render symbol picker
  renderAssetSymbolGrid(currentType);

  // Set type label
  const assetInfo = getAssetSymbolInfo(currentType);
  const labelEl = document.getElementById("edit-selected-type-label");
  if (labelEl) labelEl.innerText = `${assetInfo.icon} ${assetInfo.label} (${currentType})`;

  toggleEditSensorFields();
  updateEditPreview();

  const modal = document.getElementById("edit-station-modal");
  if (modal) modal.style.display = "flex";
}

function closeEditStationModal() {
  const modal = document.getElementById("edit-station-modal");
  if (modal) modal.style.display = "none";
}

/**
 * Save Modified Station Parameters
 */
function saveEditStation() {
  const sid = document.getElementById("edit-sid")?.value;
  if (!sid || !editorStations[sid]) {
    alert("Invalid station ID.");
    return;
  }

  const name = document.getElementById("edit-name")?.value.trim();
  const zone = document.getElementById("edit-zone")?.value || "Body";
  const type = document.getElementById("edit-type")?.value || "RoboticWeld";
  const ct = parseFloat(document.getElementById("edit-ct")?.value || 55.0);
  const tier = document.getElementById("edit-tier")?.value || "rich";
  const buffer = parseInt(document.getElementById("edit-buffer")?.value || 8, 10);
  const power = parseFloat(document.getElementById("edit-power")?.value || 28.0);
  const maintDate = document.getElementById("edit-maint-date")?.value || "2026-03-15T08:00";
  const maintInterval = parseInt(document.getElementById("edit-maint-interval")?.value || 168, 10);

  if (!name) {
    alert("Please provide a valid Station Name.");
    return;
  }

  if (isNaN(ct) || ct <= 0) {
    alert("Please enter a valid positive cycle time.");
    return;
  }

  // Push snapshot for Undo/Redo
  pushHistorySnapshot();

  // Update Station Definition
  editorStations[sid].name = name;
  editorStations[sid].zone = zone;
  editorStations[sid].station_type = type;
  editorStations[sid].type = type;
  editorStations[sid].sensor_tier = tier;
  editorStations[sid].target_cycle_time = ct;
  editorStations[sid].target_cycle_time_s = ct;
  editorStations[sid].buffer_capacity_units = buffer;
  editorStations[sid].power_base_kw = (tier === "rich") ? power : null;
  editorStations[sid].next_maintenance_date = maintDate;
  editorStations[sid].maintenance_interval_hours = maintInterval;

  closeEditStationModal();
  renderEditorCanvas();

  const assetInfo = getAssetSymbolInfo(type);
  showToast(`✅ Updated ${sid} (${name}) with scheduled service: ${maintDate.replace('T', ' ')}!`, 3500);
}

/**
 * Connections List Modal
 */
function showConnectionsModal() {
  const container = document.getElementById("connections-list-container");
  if (!container) return;

  container.innerHTML = "";

  if (editorEdges.length === 0) {
    container.innerHTML = `<div style="text-align: center; color: var(--text-muted); font-size: 0.8rem; padding: 20px;">No active conveyor links configured.</div>`;
  } else {
    editorEdges.forEach(([u, v], idx) => {
      const uName = editorStations[u]?.name || u;
      const vName = editorStations[v]?.name || v;

      const item = document.createElement("div");
      item.className = "connection-row-item";
      item.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px; font-family: var(--font-mono); font-size: 0.78rem;">
          <strong style="color: var(--brand-blue);">${u}</strong>
          <span style="color: var(--text-muted); font-size: 0.7rem;">(${uName})</span>
          <span style="color: #64748b;">➔</span>
          <strong style="color: var(--brand-blue);">${v}</strong>
          <span style="color: var(--text-muted); font-size: 0.7rem;">(${vName})</span>
        </div>
        <button class="fault-btn" style="height: 24px; padding: 0 8px; font-size: 0.68rem; color: #dc2626;" onclick="deleteEdge('${u}', '${v}'); showConnectionsModal();">
          Disconnect
        </button>
      `;
      container.appendChild(item);
    });
  }

  const modal = document.getElementById("connections-modal");
  if (modal) modal.style.display = "flex";
}

function closeConnectionsModal() {
  const modal = document.getElementById("connections-modal");
  if (modal) modal.style.display = "none";
}

/**
 * Reset Layout to Factory Defaults (Records history snapshot & resets backend simulation)
 */
async function resetEditorToDefault() {
  if (!confirm("Reset plant layout back to standard 40-station industrial baseline?")) return;
  pushHistorySnapshot();
  try {
    showToast("🔄 Resetting plant layout to standard 40-station baseline...", 2500);
    const res = await fetch("/api/topology/reset", { method: "POST" });
    if (!res.ok) throw new Error("Failed to reset topology on server");
    const data = await res.json();

    // Reset coordinates registry to factory baseline
    if (typeof resetBaselineCoordinates === "function") {
      resetBaselineCoordinates();
    }

    // Re-initialize editor
    await initTopologyEditor();

    // Refresh floor scene & fault injector
    if (typeof loadStationsTopology === "function") {
      await loadStationsTopology();
    }

    const plantTag = document.getElementById("plant-station-count-tag");
    if (plantTag) {
      plantTag.innerText = `ASSEMBLY PLANT 04 // 40 STATIONS`;
    }

    showToast(`✅ Plant layout restored to standard 40-station baseline!`, 3500);
  } catch (err) {
    console.error("Reset failed:", err);
    showToast(`⚠️ Reset error: ${err.message}`, 3500);
  }
}

/**
 * Apply Topology to Backend & Reboot Digital Twin Simulation
 */
async function applyTopology() {
  showToast("⚡ Re-initializing physics simulator and retraining risk model...", 4000);

  const req = {
    stations: editorStations,
    edges: editorEdges,
    metadata: {
      name: "Custom Plant Layout",
      created_by: "Plant Manager SCADA Editor",
      applied_at: new Date().toISOString()
    }
  };

  try {
    const res = await fetch("/api/topology/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req)
    });

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`Server error: ${errText}`);
    }

    const data = await res.json();

    if (data.status === "TOPOLOGY_APPLIED") {
      let msg = `✅ Topology applied! Digital Twin rebooted with ${data.station_count} stations & ${data.edges_count || editorEdges.length} conveyor links.`;
      
      if (data.model_status === "retraining_required") {
        msg += `<br><br><span style="color: #ef4444; font-weight: bold;">⚠️ MODEL INCOMPATIBILITY DETECTED:</span><br>The new topology station set materially differs from the trained risk model features. ML fallback to deterministic baseline is active until the model is retrained.`;
      }
      if (data.warnings && data.warnings.length > 0) {
        msg += `<br><br><span style="color: #f59e0b; font-weight: bold;">⚠️ ROUTING WARNING:</span><br>` + data.warnings.join('<br>');
      }
      
      showToast(msg, 10000);

      // Refresh Floor Supervisor View
      if (typeof loadStationsTopology === "function") {
        await loadStationsTopology();
      }

      // Update plant title badge
      const plantTag = document.getElementById("plant-station-count-tag");
      if (plantTag) {
        plantTag.innerText = `ASSEMBLY PLANT 04 // ${data.station_count} STATIONS`;
      }

      // Switch to floor view
      if (typeof switchView === "function") {
        switchView("floor");
      }
    } else {
      alert("Error applying topology: " + JSON.stringify(data));
    }
  } catch (err) {
    console.error("Apply topology failed:", err);
    alert("Network error applying topology: " + err.message);
  }
}

/**
 * Toast Notification Utility
 */
function showToast(msg, duration = 3000) {
  let toast = document.getElementById("editor-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "editor-toast";
    toast.className = "editor-toast";
    document.body.appendChild(toast);
  }

  toast.innerHTML = msg;
  toast.classList.add("show");

  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    toast.classList.remove("show");
  }, duration);
}

// Global Window Bindings
window.openEditStationModal = openEditStationModal;
window.closeEditStationModal = closeEditStationModal;
window.saveEditStation = saveEditStation;
window.selectAssetSymbol = selectAssetSymbol;
window.toggleEditSensorFields = toggleEditSensorFields;
window.updateEditPreview = updateEditPreview;
window.showAddStationModal = showAddStationModal;
window.closeAddStationModal = closeAddStationModal;
window.submitAddStation = submitAddStation;
window.deleteEditorNode = deleteEditorNode;
window.autoArrangeLayout = autoArrangeLayout;
window.showConnectionsModal = showConnectionsModal;
window.closeConnectionsModal = closeConnectionsModal;
window.resetEditorToDefault = resetEditorToDefault;
window.applyTopology = applyTopology;
window.undo = undo;
window.redo = redo;

