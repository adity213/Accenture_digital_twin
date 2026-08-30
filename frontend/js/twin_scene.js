/**
 * DigitalTwin.ai — TwinSphere SCADA Connected Conveyor Engine v4.5
 * Strict FIFO Conveyor Queue & Sequential Machine Dwell Engine
 * - Station Cradle Lock: Exactly ONE vehicle can dock & cycle in a machine at a time
 * - Strict FIFO Queueing: Backlogged vehicles queue neatly along the incoming conveyor track (Slot #1, Slot #2)
 * - Cascading Delay Depiction: After a stoppage is cleared, queued cars process sequentially ONE-BY-ONE
 * - 100% Rail-Conforming: All queued and transit vehicles stay perfectly centered on the SVG conveyor curves
 * - 1:1 Live Backend Fleet Sync: Stable colors, real-time VIN telemetry & accurate genealogy
 */

class TwinSceneEngine {
  constructor(canvasContainerId, svgLayerId) {
    this.container = document.getElementById(canvasContainerId);
    this.svgLayer = document.getElementById(svgLayerId);
    this.vehicleLayer = document.getElementById("vehicle-fleet-layer") || this.container;
    this.stations = {};
    this.edges = [];
    this.edgePaths = {};
    this.selectedId = "ST06";
    this.stationsPayload = {};
    this.fleet = [];
    this.activeHudVin = null;
    this.isHudPinned = false;
    this.hudElement = null;
    this.hudCloseTimer = null;
    window._logQueueDiagnostics = true;
    this.animFrameId = null;
    this.initHoverHud();
    this.startMotionLoop();
  }

  static getMachineGlyph(type, sid, statusColor = "#15803d", isManual = false) {
    switch (type) {
      case "RoboticWeld":
      case "RespotWeld":
        return `
          <svg viewBox="0 0 80 40" width="80" height="38">
            <polygon points="40,24 65,32 40,38 15,32" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.2"/>
            <rect x="24" y="26" width="10" height="5" rx="1" fill="#0f172a"/>
            <line x1="29" y1="26" x2="42" y2="14" stroke="#0057ff" stroke-width="3" stroke-linecap="round"/>
            <circle cx="42" cy="14" r="2.5" fill="#0f172a"/>
            <line x1="42" y1="14" x2="56" y2="20" stroke="#0057ff" stroke-width="2.5" stroke-linecap="round"/>
            <circle cx="56" cy="20" r="2.5" fill="#f59e0b"/>
            <circle cx="56" cy="20" r="3.5" fill="#0284c7" opacity="0.6">
              <animate attributeName="r" values="2.5;5;2.5" dur="1s" repeatCount="indefinite"/>
            </circle>
          </svg>
        `;

      case "MainFraming":
      case "LaserBrazing":
        return `
          <svg viewBox="0 0 80 40" width="80" height="38">
            <rect x="8" y="8" width="64" height="5" rx="1" fill="#0f172a"/>
            <line x1="20" y1="13" x2="20" y2="32" stroke="#334155" stroke-width="2.5"/>
            <line x1="60" y1="13" x2="60" y2="32" stroke="#334155" stroke-width="2.5"/>
            <rect x="16" y="24" width="8" height="8" rx="1" fill="#0057ff"/>
            <rect x="56" y="24" width="8" height="8" rx="1" fill="#0057ff"/>
            <line x1="24" y1="28" x2="56" y2="28" stroke="#0284c7" stroke-width="1.5" stroke-dasharray="3 2">
              <animate attributeName="opacity" values="0.4;1;0.4" dur="1.2s" repeatCount="indefinite"/>
            </line>
          </svg>
        `;

      case "Dispensing":
      case "RoboticUrethane":
        return `
          <svg viewBox="0 0 80 40" width="80" height="38">
            <rect x="20" y="8" width="40" height="6" rx="1" fill="#0f172a"/>
            <line x1="40" y1="14" x2="40" y2="26" stroke="#0284c7" stroke-width="3" stroke-linecap="round"/>
            <circle cx="40" cy="28" r="3" fill="#38bdf8"/>
            <path d="M 36 34 Q 40 30 44 34" fill="none" stroke="#0284c7" stroke-width="2"/>
          </svg>
        `;

      case "RoboticSpray":
      case "ThermalOven":
        return `
          <svg viewBox="0 0 80 40" width="80" height="38">
            <rect x="10" y="6" width="60" height="28" rx="2" fill="#fffbeb" stroke="#f59e0b" stroke-width="1.5"/>
            <line x1="16" y1="13" x2="64" y2="13" stroke="#d97706" stroke-width="1.5"/>
            <line x1="16" y1="19" x2="64" y2="19" stroke="#d97706" stroke-width="1.5"/>
            <line x1="28" y1="6" x2="38" y2="24" stroke="#0f172a" stroke-width="2">
              <animate attributeName="x2" values="24;54;24" dur="2s" repeatCount="indefinite"/>
            </line>
          </svg>
        `;

      case "ChemicalBath":
      case "ElectroDeposition":
        return `
          <svg viewBox="0 0 80 40" width="80" height="38">
            <rect x="10" y="14" width="60" height="20" rx="1" fill="#f0f9ff" stroke="#0284c7" stroke-width="1.5"/>
            <path d="M 12 21 Q 25 19 40 21 T 68 21" fill="none" stroke="#0284c7" stroke-width="1.5">
              <animate attributeName="d" values="M 12 21 Q 25 19 40 21 T 68 21; M 12 21 Q 25 23 40 21 T 68 21; M 12 21 Q 25 19 40 21 T 68 21" dur="2.5s" repeatCount="indefinite"/>
            </path>
            <line x1="40" y1="4" x2="40" y2="15" stroke="#0f172a" stroke-width="2"/>
          </svg>
        `;

      case "QualityScan":
      case "VisionQC":
        return `
          <svg viewBox="0 0 80 40" width="80" height="38">
            <circle cx="40" cy="20" r="12" fill="none" stroke="#0284c7" stroke-width="1.8"/>
            <circle cx="40" cy="20" r="5" fill="#38bdf8" opacity="0.8"/>
            <line x1="22" y1="20" x2="58" y2="20" stroke="#0284c7" stroke-width="1" stroke-dasharray="2 2"/>
            <line x1="40" y1="4" x2="40" y2="36" stroke="#0284c7" stroke-width="1" stroke-dasharray="2 2"/>
          </svg>
        `;

      case "BufferStation":
      case "ConveyorBuffer":
      case "TransferBuffer":
        return `
          <svg viewBox="0 0 80 40" width="80" height="38">
            <line x1="8" y1="20" x2="72" y2="20" stroke="#94a3b8" stroke-width="5" stroke-linecap="round"/>
            <rect x="14" y="13" width="12" height="13" rx="1" fill="#10b981"/>
            <rect x="34" y="13" width="12" height="13" rx="1" fill="#10b981"/>
            <rect x="54" y="13" width="12" height="13" rx="1" fill="#ffffff" stroke="#94a3b8" stroke-width="1" stroke-dasharray="2 2"/>
          </svg>
        `;

      case "AutomatedMarriage":
      case "ModuleMarriage":
      case "AutomatedTorque":
      case "MechanicalTorque":
      case "RoboticTorque":
      case "Dynamometer":
      case "DynamicTest":
        return `
          <svg viewBox="0 0 80 40" width="80" height="38">
            <rect x="14" y="26" width="52" height="5" rx="1" fill="#0f172a"/>
            <rect x="22" y="14" width="6" height="12" fill="#0057ff"/>
            <rect x="52" y="14" width="6" height="12" fill="#0057ff"/>
            <circle cx="25" cy="10" r="2.5" fill="#10b981"/>
            <circle cx="55" cy="10" r="2.5" fill="#10b981"/>
          </svg>
        `;

      case "BuyOff":
      case "QualityGate":
      case "FinalInspection":
        return `
          <svg viewBox="0 0 80 40" width="80" height="38">
            <path d="M 16 36 L 16 8 L 64 8 L 64 36" fill="none" stroke="#0f172a" stroke-width="2.5"/>
            <rect x="20" y="10" width="40" height="9" fill="#0f172a" stroke="#0f172a" stroke-width="1"/>
            <rect x="20" y="10" width="10" height="4.5" fill="#ffffff"/>
            <rect x="40" y="10" width="10" height="4.5" fill="#ffffff"/>
            <rect x="30" y="14.5" width="10" height="4.5" fill="#ffffff"/>
            <rect x="50" y="14.5" width="10" height="4.5" fill="#ffffff"/>
            <line x1="40" y1="19" x2="40" y2="34" stroke="#10b981" stroke-width="1.5" stroke-dasharray="2 2"/>
          </svg>
        `;
      default:
        if (isManual) {
          return `
            <svg viewBox="0 0 80 40" width="80" height="38">
              <circle cx="30" cy="12" r="4.5" fill="#0f172a"/>
              <path d="M 20 32 L 22 20 L 38 20 L 40 32" fill="none" stroke="#0f172a" stroke-width="2.5" stroke-linecap="round"/>
              <rect x="42" y="14" width="15" height="18" rx="1.5" fill="#fef3c7" stroke="#d97706" stroke-width="1.5"/>
              <polyline points="46,24 49,27 54,21" fill="none" stroke="#15803d" stroke-width="2"/>
            </svg>
          `;
        } else {
          return `
            <svg viewBox="0 0 80 40" width="80" height="38">
              <rect x="18" y="8" width="44" height="22" rx="2" fill="#f8fafc" stroke="#94a3b8" stroke-width="1.5"/>
              <circle cx="40" cy="19" r="6" fill="#ffffff" stroke="#0057ff" stroke-width="1.5"/>
              <line x1="40" y1="13" x2="40" y2="25" stroke="#0057ff" stroke-width="1"/>
              <line x1="34" y1="19" x2="46" y2="19" stroke="#0057ff" stroke-width="1"/>
            </svg>
          `;
        }
    }
  }

  initHoverHud() {
    let hud = document.getElementById("vehicle-hover-hud");
    const parent = document.getElementById("living-line-stage") || this.container;
    if (!hud && parent) {
      hud = document.createElement("div");
      hud.id = "vehicle-hover-hud";
      hud.className = "vehicle-hover-hud";
      hud.style.display = "none";
      parent.appendChild(hud);
    }
    if (hud) {
      hud.onclick = (e) => e.stopPropagation();
      hud.onmouseenter = () => {
        if (this.hudCloseTimer) {
          clearTimeout(this.hudCloseTimer);
          this.hudCloseTimer = null;
        }
      };
      hud.onmouseleave = () => {
        if (!this.isHudPinned) {
          this.scheduleHideHud(200);
        }
      };
    }
    this.hudElement = hud;

    // Dismiss HUD when clicking anywhere outside
    document.addEventListener("pointerdown", (e) => {
      if (this.hudElement && this.hudElement.style.display !== "none") {
        if (!e.target.closest(".vehicle-carrier-node") && !e.target.closest(".vehicle-hover-hud")) {
          this.hideVehicleHud(true);
        }
      }
    });
  }

  calculateFloorCoordinates(stations, edges) {
    if (typeof window.stationCoords === "undefined") {
      window.stationCoords = {};
    }

    const baseline = (typeof getBaselineFactoryCoordinates === "function")
      ? getBaselineFactoryCoordinates()
      : {
        "ST01": { x: 80, y: 170, isParallel: false },
        "ST02": { x: 310, y: 170, isParallel: false },
        "ST03": { x: 540, y: 35, isParallel: true, branch: "FORK: UPPER LH" },
        "ST04": { x: 540, y: 305, isParallel: true, branch: "FORK: LOWER RH" },
        "ST05": { x: 770, y: 170, isParallel: false, branch: "MERGE" },
        "ST06": { x: 1000, y: 170, isParallel: false },
        "ST07": { x: 1230, y: 35, isParallel: true, branch: "FORK: RESPOT A" },
        "ST08": { x: 1230, y: 305, isParallel: true, branch: "FORK: RESPOT B" },
        "ST09": { x: 1460, y: 170, isParallel: false, branch: "MERGE" },
        "ST10": { x: 1690, y: 170, isParallel: false },
        "ST11": { x: 1920, y: 170, isParallel: false },
        "ST12": { x: 2150, y: 170, isParallel: false },
        "ST13": { x: 2380, y: 170, isParallel: false },
        "ST14": { x: 2610, y: 170, isParallel: false },

        "ST15": { x: 2610, y: 480, isParallel: false },
        "ST16": { x: 2248, y: 480, isParallel: false },
        "ST17": { x: 1886, y: 480, isParallel: false },
        "ST18": { x: 1524, y: 480, isParallel: false },
        "ST19": { x: 1162, y: 480, isParallel: false },
        "ST20": { x: 800, y: 480, isParallel: false },
        "ST21": { x: 438, y: 480, isParallel: false },
        "ST22": { x: 80, y: 480, isParallel: false },

        "ST23": { x: 80, y: 810, isParallel: false },
        "ST24": { x: 310, y: 810, isParallel: false },
        "ST25": { x: 540, y: 685, isParallel: true, branch: "FORK: COCKPIT" },
        "ST26": { x: 540, y: 935, isParallel: true, branch: "FORK: SUSPENSION" },
        "ST27": { x: 770, y: 810, isParallel: false, branch: "MERGE" },
        "ST28": { x: 1000, y: 810, isParallel: false },
        "ST29": { x: 1230, y: 810, isParallel: false },
        "ST30": { x: 1460, y: 810, isParallel: false },
        "ST31": { x: 1690, y: 810, isParallel: false },
        "ST32": { x: 1920, y: 810, isParallel: false },

        "ST33": { x: 1920, y: 1100, isParallel: false },
        "ST34": { x: 1657, y: 1100, isParallel: false },
        "ST35": { x: 1394, y: 1100, isParallel: false },
        "ST36": { x: 1131, y: 1100, isParallel: false },
        "ST37": { x: 868, y: 1100, isParallel: false },
        "ST38": { x: 605, y: 1100, isParallel: false },
        "ST39": { x: 342, y: 1100, isParallel: false },
        "ST40": { x: 80, y: 1100, isParallel: false }
      };

    Object.keys(baseline).forEach(sid => {
      if (!window.stationCoords[sid]) {
        window.stationCoords[sid] = Object.assign({}, baseline[sid]);
      }
    });

    // Dynamically support any new custom stations added
    Object.keys(stations).forEach(sid => {
      if (baseline[sid] && window.stationCoords[sid]) return;
      const meta = stations[sid] || {};
      const zone = (meta.zone || "Body").toLowerCase();
      let pos = window.stationCoords[sid];

      let defaultY = 170;
      let flowDirection = "ltr";

      if (zone.includes("paint")) {
        defaultY = 480;
        flowDirection = "rtl";
      } else if (zone.includes("assembly")) {
        defaultY = 810;
        flowDirection = "ltr";
      }

      if (!pos) {
        const upstreamEdge = edges.find(e => e[1] === sid);
        const upstreamSid = upstreamEdge ? upstreamEdge[0] : null;
        const upstreamPos = upstreamSid ? window.stationCoords[upstreamSid] : null;

        let newX = 80;
        let newY = defaultY;

        if (upstreamPos) {
          newX = flowDirection === "ltr" ? upstreamPos.x + 230 : Math.max(80, upstreamPos.x - 230);
          newY = upstreamPos.y;
        }
        window.stationCoords[sid] = { x: newX, y: newY, branch: "" };
      }
    });
  }

  renderScene(stationsMeta, edges, activeVehicles = []) {
    this.stations = stationsMeta;
    this.edges = edges;
    if (!this.container || !this.svgLayer) return;

    this.vehicleLayer = document.getElementById("vehicle-fleet-layer") || this.container;
    this.calculateFloorCoordinates(this.stations, this.edges);

    this.container.innerHTML = "";
    this.svgLayer.innerHTML = "";
    this.edgePaths = {};

    if (this.vehicleLayer && this.vehicleLayer !== this.container) {
      this.vehicleLayer.innerHTML = "";
    }

    const NODE_W = 144;
    const NODE_H = 124;

    // Continuous Port-to-Port Conveyor Rail Bezier SVG
    this.edges.forEach(([u, v]) => {
      const p1 = window.stationCoords[u];
      const p2 = window.stationCoords[v];
      if (!p1 || !p2) return;

      let x1, y1, x2, y2, cx1, cy1, cx2, cy2;
      const dx = p2.x - p1.x;
      let isReverseFlow = false;

      if (dx > 40) {
        // Forward Flow: Left-to-Right (Straight, Forks ST02->ST03, Merges ST07/ST08->ST09)
        x1 = p1.x + NODE_W;
        y1 = p1.y + NODE_H * 0.5;
        x2 = p2.x;
        y2 = p2.y + NODE_H * 0.5;
        const midX = x1 + (x2 - x1) * 0.5;
        cx1 = midX; cy1 = y1;
        cx2 = midX; cy2 = y2;
      } else if (dx < -40) {
        // Reverse Flow: Right-to-Left (Zone 2 Paint Shop, Row 4 Buy-off)
        isReverseFlow = true;
        x1 = p1.x;
        y1 = p1.y + NODE_H * 0.5;
        x2 = p2.x + NODE_W;
        y2 = p2.y + NODE_H * 0.5;
        const midX = x1 + (x2 - x1) * 0.5;
        cx1 = midX; cy1 = y1;
        cx2 = midX; cy2 = y2;
      } else {
        // Vertical Turnaround Transfers (ST14->ST15, ST22->ST23, ST32->ST33)
        if (p1.x > 900) {
          x1 = p1.x + NODE_W;
          y1 = p1.y + NODE_H * 0.5;
          x2 = p2.x + NODE_W;
          y2 = p2.y + NODE_H * 0.5;
          cx1 = Math.min(2850, Math.max(x1, x2) + 95);
          cy1 = y1;
          cx2 = cx1;
          cy2 = y2;
        } else {
          x1 = p1.x;
          y1 = p1.y + NODE_H * 0.5;
          x2 = p2.x;
          y2 = p2.y + NODE_H * 0.5;
          cx1 = Math.max(20, Math.min(x1, x2) - 75);
          cy1 = y1;
          cx2 = cx1;
          cy2 = y2;
        }
      }

      const pathD = `M ${x1} ${y1} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${x2} ${y2}`;

      const pathOuter = document.createElementNS("http://www.w3.org/2000/svg", "path");
      pathOuter.setAttribute("d", pathD);
      pathOuter.setAttribute("class", "rail-track-outer");
      this.svgLayer.appendChild(pathOuter);

      const pathInner = document.createElementNS("http://www.w3.org/2000/svg", "path");
      pathInner.setAttribute("d", pathD);
      pathInner.setAttribute("class", "rail-track-inner");
      this.svgLayer.appendChild(pathInner);

      const pathChev = document.createElementNS("http://www.w3.org/2000/svg", "path");
      pathChev.setAttribute("d", pathD);
      pathChev.setAttribute("class", `rail-chevrons ${isReverseFlow ? 'flow-reverse' : 'flow-forward'}`);
      this.svgLayer.appendChild(pathChev);

      // Store exact mathematical trajectory definition for flawless vehicle tracking
      this.edgePaths[`${u}->${v}`] = {
        x1, y1,
        cx1, cy1,
        cx2, cy2,
        x2, y2
      };
    });

    // Render Station Nodes with Cycle Progress Bar
    Object.keys(this.stations).forEach((sid) => {
      const meta = this.stations[sid];
      const pos = window.stationCoords[sid] || { x: 50, y: 80 };
      const isManual = meta.sensor_tier === "manual";

      const node = document.createElement("div");
      node.id = `station-node-${sid}`;
      node.className = `station-schematic-node ${sid === this.selectedId ? "selected" : ""}`;
      node.style.left = `${pos.x}px`;
      node.style.top = `${pos.y}px`;
      node.tabIndex = 0;
      node.setAttribute("role", "button");
      node.setAttribute("aria-label", `${sid}: ${meta.name}`);
      node.onclick = () => selectStation(sid);
      node.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") selectStation(sid); };

      let forkBadge = "";
      if (pos.branch) {
        forkBadge = `<span class="island-branch-tag">${pos.branch}</span>`;
      }

      node.innerHTML = `
        ${forkBadge}
        <div class="node-hud-top">
          <span class="node-sid">${sid}</span>
          <span class="node-tier-pill ${isManual ? 'manual' : ''}">${(meta.sensor_tier || "RICH").toUpperCase()}</span>
        </div>
        <div class="station-glyph-wrap" id="glyph-${sid}">
          ${TwinSceneEngine.getMachineGlyph(meta.station_type || meta.type, sid, "#15803d", isManual)}
        </div>
        <div class="node-name-label">${meta.name}</div>
        <div class="node-hud-footer">
          <span class="node-val-ct" id="s-ct-${sid}">${(meta.target_cycle_time_s || meta.target_cycle_time || 55.0).toFixed(1)}s</span>
          <span class="node-val-risk" id="s-risk-${sid}">5%</span>
        </div>
        <div class="station-dwell-bar-wrap">
          <div class="station-dwell-bar-fill" id="s-bar-${sid}"></div>
        </div>
      `;

      this.container.appendChild(node);
    });

    this.initHoverHud();
    this.seedCleanFleet(activeVehicles);
  }

  seedCleanFleet(activeVehicles) {
    this.fleet = [];
    if (!this.edges || this.edges.length === 0) return;

    if (Array.isArray(activeVehicles) && activeVehicles.length > 0) {
      const stationOccupancy = {};

      activeVehicles.forEach((vData) => {
        const curSid = vData.current_station || "ST01";
        const prevSid = vData.previous_station || (this.stations[curSid]?.upstream_ids?.[0]) || curSid;

        stationOccupancy[curSid] = (stationOccupancy[curSid] || 0) + 1;
        const occIndex = stationOccupancy[curSid] - 1;
        const isDocked = (occIndex === 0 && vData.is_processing !== false);

        const veh = {
          vin: vData.vin,
          fromStation: prevSid,
          toStation: curSid,
          backendCurrentStation: curSid,
          backendPreviousStation: prevSid,
          progress: isDocked ? 1.0 : 0.0,
          state: isDocked ? "DOCK" : "QUEUE",
          dwellTimer: 0.0,
          dwellTarget: 2.5,
          speed: 0.012,
          defect_count: vData.defect_count || 0,
          route_index: vData.route_index || 1,
          route_length_estimate: vData.route_length_estimate || 37,
          route_length: vData.route_length,
          visited_station_ids: vData.visited_station_ids || [],
          queueSlot: isDocked ? 0 : occIndex,
          element: null
        };
        this.fleet.push(veh);
      });
    }

    this.createFleetDOM();
  }

  createFleetDOM() {
    const parent = document.getElementById("vehicle-fleet-layer") || this.container;
    if (!parent) return;

    this.fleet.forEach((veh) => {
      if (!veh.element) {
        const el = document.createElement("div");
        el.id = `veh-carrier-${veh.vin}`;
        el.className = "vehicle-carrier-node";

        el.innerHTML = `
          <span class="vehicle-carrier-badge">${veh.vin.replace("VIN-2026-", "#")}</span>
          <svg class="veh-body-svg" viewBox="0 0 54 28" width="54" height="28">
            <rect x="2" y="21" width="50" height="4.5" rx="1.5" fill="#1e293b" stroke="#0f172a" stroke-width="1"/>
            <circle cx="10" cy="23.5" r="2" fill="#94a3b8"/>
            <circle cx="44" cy="23.5" r="2" fill="#94a3b8"/>
            <path class="veh-chassis-path" d="M 6,19 L 8,13 L 17,10 L 25,5 L 39,5 L 47,11 L 50,14 L 50,19 Z" 
                  fill="#0284c7" stroke="#0369a1" stroke-width="1.6"/>
            <polygon points="18,10 25,6 38,6 45,11 38,11 25,11" fill="#ffffff" opacity="0.85"/>
            <rect x="48" y="14" width="2" height="3" fill="#38bdf8" rx="0.5"/>
            <rect x="5" y="14" width="2" height="3" fill="#f87171" rx="0.5"/>
          </svg>
        `;

        // Click to Open & Lock HUD
        el.onclick = (e) => {
          e.stopPropagation();
          this.showVehicleHud(veh, el, true);
        };

        // Hover preview
        el.onmouseenter = () => {
          if (this.hudCloseTimer) {
            clearTimeout(this.hudCloseTimer);
            this.hudCloseTimer = null;
          }
          if (!this.isHudPinned) {
            this.showVehicleHud(veh, el, false);
          }
        };

        el.onmouseleave = () => {
          if (!this.isHudPinned) {
            this.scheduleHideHud(220);
          }
        };

        parent.appendChild(el);
        veh.element = el;
      }
    });
  }

  /**
   * 100% Rail-Conforming Trajectory Calculation
   * Evaluates the EXACT cubic bezier curve of the SVG rail track between fromSid and toSid.
   * Smoothly connects station center -> exit port -> SVG curve -> entrance port -> station center.
   */
  getConveyorTrackPosition(fromSid, toSid, t) {
    const p1 = window.stationCoords[fromSid] || { x: 80, y: 170 };
    const p2 = window.stationCoords[toSid] || p1;
    const edgeKey = `${fromSid}->${toSid}`;
    const edgeData = this.edgePaths ? this.edgePaths[edgeKey] : null;

    const c1 = { x: p1.x + 72, y: p1.y + 60 };
    const c2 = { x: p2.x + 72, y: p2.y + 60 };

    if (!edgeData) {
      return {
        x: c1.x + (c2.x - c1.x) * t,
        y: c1.y + (c2.y - c1.y) * t
      };
    }

    // Origin Station Exit Port
    const port1 = { x: edgeData.x1, y: edgeData.y1 };
    // Destination Station Entrance Port
    const port2 = { x: edgeData.x2, y: edgeData.y2 };

    if (t <= 0.12) {
      // Smooth linear roll from center of station into exit port
      const subT = t / 0.12;
      return {
        x: c1.x + (port1.x - c1.x) * subT,
        y: c1.y + (port1.y - c1.y) * subT
      };
    } else if (t >= 0.88) {
      // Smooth linear roll from entrance port into center of destination station
      const subT = (t - 0.88) / 0.12;
      return {
        x: port2.x + (c2.x - port2.x) * subT,
        y: port2.y + (c2.y - port2.y) * subT
      };
    } else {
      // In transit along the exact SVG conveyor track curve (S-Curves, Merges, Forks, U-Turns)
      const normT = (t - 0.12) / 0.76;

      const mt = 1 - normT;
      const mt2 = mt * mt;
      const mt3 = mt2 * mt;
      const t2 = normT * normT;
      const t3 = t2 * normT;

      const x = mt3 * edgeData.x1 + 3 * mt2 * normT * edgeData.cx1 + 3 * mt * t2 * edgeData.cx2 + t3 * edgeData.x2;
      const y = mt3 * edgeData.y1 + 3 * mt2 * normT * edgeData.cy1 + 3 * mt * t2 * edgeData.cy2 + t3 * edgeData.y2;
      return { x, y };
    }
  }

  /**
   * Returns the physical pixel track length between two stations.
   */
  getTrackLength(fromSid, toSid) {
    const p1 = window.stationCoords ? window.stationCoords[fromSid] : null;
    const p2 = window.stationCoords ? window.stationCoords[toSid] : null;
    if (!p1 || !p2) return 220;
    const edgeKey = `${fromSid}->${toSid}`;
    const edgeData = this.edgePaths ? this.edgePaths[edgeKey] : null;
    if (edgeData) {
      return Math.round(Math.hypot(edgeData.x2 - edgeData.x1, edgeData.y2 - edgeData.y1) + 144);
    }
    return Math.round(Math.hypot(p2.x - p1.x, p2.y - p1.y));
  }

  /**
   * Calculates distinct, offset queue positions along the upstream conveyor curve
   * feeding into a station, guaranteeing at least 58px of center-to-center physical
   * spacing regardless of segment length.
   */
  getStationQueuePosition(toSid, queueIndex = 0, preferredFromSid = null) {
    const pTo = window.stationCoords[toSid] || { x: 100, y: 170 };
    const cradlePos = { x: pTo.x + 72, y: pTo.y + 60 };

    let fromSid = preferredFromSid;
    const stMeta = this.stations ? this.stations[toSid] : null;
    const upstreams = (stMeta && Array.isArray(stMeta.upstream_ids)) ? stMeta.upstream_ids : [];

    if (!fromSid || fromSid === toSid) {
      if (upstreams.length > 1) {
        // Multi-branch merge: alternate queue positions by upstream parent
        fromSid = upstreams[queueIndex % upstreams.length];
      } else if (upstreams.length === 1) {
        fromSid = upstreams[0];
      }
    }

    if (!fromSid || fromSid === toSid) {
      // For ST01 infeed buffer, queue line extends horizontally to the left along infeed conveyor
      const offset = 70 + (Math.min(queueIndex, 3) * 58);
      return { x: cradlePos.x - offset, y: cradlePos.y };
    }

    const pFrom = window.stationCoords[fromSid];
    const edgeKey = `${fromSid}->${toSid}`;
    const edgeData = this.edgePaths ? this.edgePaths[edgeKey] : null;

    // Per-branch queue index when merging
    const effectiveBranchIndex = (upstreams.length > 1 && !preferredFromSid) 
      ? Math.floor(queueIndex / upstreams.length) 
      : queueIndex;

    const MIN_CAR_SPACING = 58; // px center-to-center clearance (car width: 54px)

    if (edgeData) {
      // Physical bezier chord distance between ports
      const bezierLength = Math.max(20, Math.hypot(edgeData.x2 - edgeData.x1, edgeData.y2 - edgeData.y1));
      const maxFitCars = Math.max(1, Math.floor((bezierLength - 16) / MIN_CAR_SPACING) + 1);
      // Clamp to visible rail segment so overflow vehicles do not run through upstream station card
      const clampedIndex = Math.min(effectiveBranchIndex, maxFitCars - 1);
      const targetDist = Math.min(bezierLength - 6, 18 + (clampedIndex * MIN_CAR_SPACING));

      const normT = Math.max(0.0, Math.min(1.0, 1.0 - (targetDist / bezierLength)));
      const mt = 1 - normT;
      const mt2 = mt * mt;
      const mt3 = mt2 * mt;
      const t2 = normT * normT;
      const t3 = t2 * normT;

      const x = mt3 * edgeData.x1 + 3 * mt2 * normT * edgeData.cx1 + 3 * mt * t2 * edgeData.cx2 + t3 * edgeData.x2;
      const y = mt3 * edgeData.y1 + 3 * mt2 * normT * edgeData.cy1 + 3 * mt * t2 * edgeData.cy2 + t3 * edgeData.y2;
      return { x, y };
    }

    // Straight-line fallback when edgeData is not present
    const c1 = pFrom ? { x: pFrom.x + 72, y: pFrom.y + 60 } : { x: cradlePos.x - 220, y: cradlePos.y };
    const totalDist = Math.max(MIN_CAR_SPACING, Math.hypot(cradlePos.x - c1.x, cradlePos.y - c1.y));
    const dirX = (c1.x - cradlePos.x) / totalDist;
    const dirY = (c1.y - cradlePos.y) / totalDist;
    const clampedIndex = Math.min(effectiveBranchIndex, 3);
    return {
      x: cradlePos.x + dirX * (20 + clampedIndex * MIN_CAR_SPACING),
      y: cradlePos.y + dirY * (20 + clampedIndex * MIN_CAR_SPACING)
    };
  }

  startMotionLoop() {
    if (this.animFrameId) cancelAnimationFrame(this.animFrameId);

    const tick = () => {
      this.stepFleetMotion();
      this.animFrameId = requestAnimationFrame(tick);
    };
    this.animFrameId = requestAnimationFrame(tick);
  }

  stepFleetMotion() {
    if (!this.fleet || this.fleet.length === 0) return;

    // Read Ground Truth Machine Cradle Occupancy and Queue Buffers directly from telemetry
    const processingVinMap = {}; // sid -> vin occupying cradle
    const queuedVinsMap = {};    // sid -> array of waiting vins
    const stationPayload = this.stationsPayload || {};

    Object.keys(stationPayload).forEach(sid => {
      const st = stationPayload[sid];
      if (st.processing_vin) {
        processingVinMap[sid] = st.processing_vin;
      }
      if (Array.isArray(st.queued_vins) && st.queued_vins.length > 0) {
        queuedVinsMap[sid] = st.queued_vins;
      }
    });

    // Auto-admit lead vehicle into unoccupied cradles so all stations with active vehicles cycle properly
    this.fleet.forEach(v => {
      const sid = v.backendCurrentStation;
      if (sid && !processingVinMap[sid]) {
        const qList = queuedVinsMap[sid] || [];
        if (qList.length === 0 || qList[0] === v.vin) {
          processingVinMap[sid] = v.vin;
        }
      }
    });

    // Reset station dwell progress bars and in-cycle glow for stations with no processing vehicle
    if (this.stations) {
      Object.keys(this.stations).forEach(sid => {
        if (!processingVinMap[sid]) {
          const barEl = document.getElementById(`s-bar-${sid}`);
          if (barEl && barEl.style.width !== "0%") {
            barEl.style.width = "0%";
          }
          const nodeEl = document.getElementById(`station-node-${sid}`);
          if (nodeEl && nodeEl.classList.contains("in-cycle")) {
            nodeEl.classList.remove("in-cycle");
          }
        }
      });
    }

    const now = performance.now();

    this.fleet.forEach((veh) => {
      let targetSid = veh.backendCurrentStation || "ST01";
      let fromSid = veh.backendPreviousStation || (this.stations[targetSid]?.upstream_ids?.[0]) || targetSid;
      let currentHop = null;
      let u = 0.0;
      let localU = 0.0;

      if (veh.animHops && veh.animHops.length > 0) {
        const numHops = veh.animHops.length;
        const elapsed = now - (veh.animStartTime || now);
        const duration = Math.max(150, veh.animDuration || this.measuredBackendInterval || 3200);
        u = Math.max(0.0, Math.min(1.0, elapsed / duration));

        const hopFraction = 1.0 / numHops;
        const currentHopIndex = Math.min(numHops - 1, Math.floor(u / hopFraction));
        currentHop = veh.animHops[currentHopIndex];
        localU = (u - (currentHopIndex * hopFraction)) / hopFraction;

        fromSid = currentHop.from;
        targetSid = currentHop.to;
      }

      veh.fromStation = fromSid;
      veh.toStation = targetSid;

      const fromState = stationPayload[fromSid] || {};
      const toState = stationPayload[targetSid] || {};

      // Dynamic station-proportional transit vs dwell allocation
      // Conveyor transit is smooth and continuous (40-50% of interval), remaining 50-60% is in-station dwell
      const stMeta = this.stations ? this.stations[targetSid] : null;
      const liveCt = toState.is_stopped
        ? (stMeta?.target_cycle_time_s || 55.0) * 4.5
        : (toState.cycle_time_s || stMeta?.target_cycle_time_s || 55.0);
      const transitAlpha = Math.max(0.28, Math.min(0.50, 24.0 / Math.max(20.0, liveCt)));

      const isDestStopped = Boolean(toState.is_stopped);
      const isOriginStopped = Boolean(fromState.is_stopped);

      let isHalted = false;
      let pos = veh.lastPos ? { ...veh.lastPos } : { x: 100, y: 100 };

      const pTo = window.stationCoords[targetSid] || { x: 100, y: 170 };
      const cradlePos = { x: pTo.x + 72, y: pTo.y + 60 };
      const barEl = document.getElementById(`s-bar-${targetSid}`);
      const nodeEl = document.getElementById(`station-node-${targetSid}`);

      // Check Ground Truth Backend Status for this vehicle at targetSid
      const isCradleOccupant = (processingVinMap[targetSid] === veh.vin);
      const queueList = queuedVinsMap[targetSid] || [];
      const queueIndex = queueList.indexOf(veh.vin);
      const isStationProcessing = isCradleOccupant;
      const isVehicleQueued = !isCradleOccupant && (queueIndex !== -1 || (queueList.length > 0 && veh.backendCurrentStation === targetSid));
      const effectiveQueueIndex = isVehicleQueued ? Math.max(0, queueIndex) : 0;

      if (veh.animHops && veh.animHops.length > 0) {
        const rawProg = Math.max(0.0, Math.min(1.0, localU / transitAlpha));
        // Smooth Cubic Ease-Out Deceleration
        const easedProg = 1 - Math.pow(1 - rawProg, 3);

        if (localU <= transitAlpha) {
          // 1. Smooth Conveyor Transit Phase along bezier track
          veh.state = "TRANSIT";
          veh.progress = rawProg;
          veh.queueSlot = -1;

          if (isStationProcessing) {
            // Glides continuously from origin exit port all the way into machine cradle
            pos = this.getConveyorTrackPosition(fromSid, targetSid, easedProg);
          } else if (isVehicleQueued) {
            // Target endpoint is the buffer queue slot outside the station
            // Glides along the bezier rail and gently coasts to a stop at the queue slot (never entering cradle)
            const targetDist = 18 + (effectiveQueueIndex * 58);
            const edgeKey = `${fromSid}->${targetSid}`;
            const edgeData = this.edgePaths ? this.edgePaths[edgeKey] : null;
            const bezierLength = edgeData ? Math.max(20, Math.hypot(edgeData.x2 - edgeData.x1, edgeData.y2 - edgeData.y1)) : 220;
            const maxT = Math.max(0.05, Math.min(0.85, 1.0 - (targetDist / (bezierLength + 144))));
            pos = this.getConveyorTrackPosition(fromSid, targetSid, easedProg * maxT);
          } else {
            pos = this.getConveyorTrackPosition(fromSid, targetSid, easedProg * 0.85);
          }

          if (barEl && !isStationProcessing) {
            barEl.style.width = "0%";
          }
          if (nodeEl && !nodeEl.classList.contains("status-critical") && !isStationProcessing) {
            nodeEl.classList.remove("in-cycle");
          }
        } else {
          // 2. Station Arrival / Machine Dwell Phase
          if (isStationProcessing) {
            const dwellProg = Math.max(0.0, Math.min(1.0, (localU - transitAlpha) / (1.0 - transitAlpha)));
            veh.state = "DOCK";
            veh.progress = 1.0;
            veh.queueSlot = 0;
            pos = cradlePos;

            if (barEl) {
              barEl.style.width = `${Math.min(100, Math.round(dwellProg * 100))}%`;
              barEl.style.backgroundColor = (veh.defect_count > 0) ? "#ef4444" : "#10b981";
            }
            if (nodeEl && !nodeEl.classList.contains("status-critical")) {
              nodeEl.classList.add("in-cycle");
            }
          } else if (isVehicleQueued) {
            // Vehicle is waiting in the station queue buffer -> Render at distinct offset queue coordinate
            veh.state = "QUEUE";
            veh.queueSlot = effectiveQueueIndex;
            pos = this.getStationQueuePosition(targetSid, effectiveQueueIndex, fromSid);
            isHalted = true;
          } else {
            veh.state = "TRANSIT";
            veh.queueSlot = -1;
            pos = veh.lastPos || this.getConveyorTrackPosition(fromSid, targetSid, 0.85);
          }
        }

        if (u >= 1.0) {
          // Finished hops timeline for this interval
          veh.animHops = [];
          veh.fromStation = veh.backendCurrentStation;
          veh.toStation = veh.backendCurrentStation;
          if (isStationProcessing) {
            veh.state = "DOCK";
            veh.progress = 1.0;
            veh.queueSlot = 0;
            pos = cradlePos;
          } else if (isVehicleQueued) {
            veh.state = "QUEUE";
            veh.queueSlot = effectiveQueueIndex;
            pos = this.getStationQueuePosition(veh.backendCurrentStation, effectiveQueueIndex, veh.backendPreviousStation);
            isHalted = true;
          } else {
            veh.state = "TRANSIT";
            veh.queueSlot = -1;
            pos = veh.lastPos || this.getConveyorTrackPosition(veh.fromStation, veh.toStation, 0.85);
          }
        }
      } else {
        // Vehicle not in active hop interpolation
        if (isStationProcessing) {
          // Sole occupant of machine cradle
          pos = cradlePos;
          veh.state = "DOCK";
          veh.progress = 1.0;
          veh.queueSlot = 0;

          const elapsed = now - (veh.animStartTime || now);
          const duration = Math.max(150, veh.animDuration || this.measuredBackendInterval || 3200);
          const dwellFraction = Math.max(0.0, Math.min(1.0, elapsed / duration));

          if (!isDestStopped) {
            if (barEl) {
              barEl.style.width = `${Math.min(100, Math.round(dwellFraction * 100))}%`;
              barEl.style.backgroundColor = (veh.defect_count > 0) ? "#ef4444" : "#10b981";
            }
            if (nodeEl && !nodeEl.classList.contains("status-critical")) {
              nodeEl.classList.add("in-cycle");
            }
          }
        } else if (isVehicleQueued) {
          // Waiting in queue buffer -> distinct offset position
          veh.state = "QUEUE";
          veh.queueSlot = effectiveQueueIndex;
          pos = this.getStationQueuePosition(targetSid, effectiveQueueIndex, fromSid);
          isHalted = true;
        } else {
          veh.state = "TRANSIT";
          veh.queueSlot = -1;
          pos = veh.lastPos || this.getConveyorTrackPosition(fromSid, targetSid, 0.85);
        }
      }

      // Smooth position interpolation for queue and station slot transitions
      if (!veh.renderPos) {
        veh.renderPos = { x: pos.x, y: pos.y };
      } else if (veh.state === "TRANSIT" && veh.animHops && veh.animHops.length > 0) {
        // Direct tracking during continuous bezier transit
        veh.renderPos.x = pos.x;
        veh.renderPos.y = pos.y;
      } else {
        // Smooth easing towards target position for queue advances and docking (prevents visual snapping/crossing)
        const dx = pos.x - veh.renderPos.x;
        const dy = pos.y - veh.renderPos.y;
        const dist = Math.hypot(dx, dy);
        if (dist > 0.5) {
          const easeFactor = 0.18; // smooth ~200-250ms convergence at 60fps
          veh.renderPos.x += dx * easeFactor;
          veh.renderPos.y += dy * easeFactor;
        } else {
          veh.renderPos.x = pos.x;
          veh.renderPos.y = pos.y;
        }
      }

      veh.is_stopped = isHalted;
      veh.lastPos = { ...pos };

      // Calculate track segment capacity and overflow state for queued vehicles
      const edgeKey = `${fromSid}->${targetSid}`;
      const edgeData = this.edgePaths ? this.edgePaths[edgeKey] : null;
      let bezierLength = 220;
      if (edgeData) {
        bezierLength = Math.max(30, Math.hypot(edgeData.x2 - edgeData.x1, edgeData.y2 - edgeData.y1));
      } else if (!fromSid || fromSid === targetSid) {
        bezierLength = 232;
      }
      const maxFitCars = Math.max(1, Math.floor((bezierLength - 16) / 58) + 1);
      const overflowCount = Math.max(0, queueList.length - maxFitCars);
      const isOverflowCar = isVehicleQueued && (queueIndex >= maxFitCars);
      const isTailVisibleCar = isVehicleQueued && (queueIndex === maxFitCars - 1 || (queueIndex === queueList.length - 1 && queueList.length <= maxFitCars));

      const el = veh.element;
      if (el) {
        // Hide individual overflow vehicle sprites that exceed the rail segment capacity
        if (isOverflowCar) {
          el.style.display = "none";
        } else {
          el.style.display = "";
        }

        el.style.left = `${veh.renderPos.x}px`;
        el.style.top = `${veh.renderPos.y}px`;

        const isDocked = (veh.state === "DOCK" && isStationProcessing);
        const isQueued = (veh.state === "QUEUE" || isVehicleQueued);
        const isBlocked = Boolean(veh.is_blocked);
        const isTrueHalted = Boolean(isDestStopped && isHalted);
        
        el.classList.toggle("in-station", isDocked);
        el.classList.toggle("queued", isQueued && !isDocked);
        el.classList.toggle("halted", isTrueHalted || isBlocked);

        const badgeEl = el.querySelector(".vehicle-carrier-badge");
        if (badgeEl) {
          badgeEl.classList.remove("overflow-pill");
          if (isDocked) {
            badgeEl.innerText = `⚙️ ${targetSid}`;
          } else if (isQueued && isTailVisibleCar && overflowCount > 0) {
            badgeEl.classList.add("overflow-pill");
            badgeEl.innerText = `+${overflowCount + 1} wait`;
          } else if (isTrueHalted) {
            badgeEl.innerText = (veh.queueSlot === 0) ? `🛑 ${targetSid}` : `🛑 #${veh.queueSlot + 1}`;
          } else if (isBlocked) {
            badgeEl.innerText = (veh.queueSlot === 0) ? `⏸️ ${targetSid}` : `⏸️ #${veh.queueSlot + 1}`;
          } else if (isQueued && veh.queueSlot >= 0) {
            badgeEl.innerText = (veh.queueSlot === 0) ? `BUF #1` : `#${veh.queueSlot + 1}`;
          } else if (isQueued) {
            badgeEl.innerText = veh.vin.replace("VIN-2026-", "#"); // position pending confirmation
          } else {
            badgeEl.innerText = veh.vin.replace("VIN-2026-", "#");
          }
        }

        const pathEl = el.querySelector(".veh-chassis-path");
        if (pathEl) {
          const hasDefect = (veh.defect_count || 0) > 0;
          const isRed = Boolean((isDestStopped && isHalted) || isBlocked);
          pathEl.setAttribute("fill", isRed ? "#ef4444" : (hasDefect ? "#f59e0b" : "#0284c7"));
          pathEl.setAttribute("stroke", isRed ? "#b91c1c" : (hasDefect ? "#b45309" : "#0369a1"));
        }

        // Keep HUD pinned above vehicle
        if (this.activeHudVin === veh.vin && this.hudElement && this.hudElement.style.display !== "none") {
          this.hudElement.style.left = `${veh.renderPos.x}px`;
          this.hudElement.style.top = `${veh.renderPos.y}px`;
        }
      }
    });

    // Debug Instrumentation Logging for Queue Verification
    if (typeof window !== "undefined" && window._logQueueDiagnostics) {
      const queuedVehs = this.fleet.filter(v => v.state === "QUEUE" || v.queueSlot >= 0);
      if (queuedVehs.length > 0) {
        const nowMs = performance.now();
        if (!this._lastDiagLogTime || nowMs - this._lastDiagLogTime > 1000) {
          this._lastDiagLogTime = nowMs;
          const logTable = queuedVehs.map(v => ({
            vin: v.vin,
            targetStation: v.toStation,
            fromStation: v.fromStation,
            state: v.state,
            queueSlot: v.queueSlot,
            posX: Math.round(v.renderPos?.x ?? v.lastPos?.x ?? 0),
            posY: Math.round(v.renderPos?.y ?? v.lastPos?.y ?? 0),
            trackLength: this.getTrackLength(v.fromStation, v.toStation)
          }));
          console.table(logTable);
          window._lastQueueDiagnostics = logTable;
        }
      }
    }

    // Cleanly prune vehicles that completed the line
    this.fleet = this.fleet.filter(veh => !veh.isCompleted);
  }

  updateTelemetry(stationsPayload, vehiclesPayload) {
    if (!stationsPayload) return;
    this.stationsPayload = stationsPayload;

    const now = performance.now();
    const measuredInterval = this.lastBackendUpdateAt ? Math.max(150, now - this.lastBackendUpdateAt) : 1500;
    this.measuredBackendInterval = measuredInterval;
    this.lastBackendUpdateAt = now;

    // Update station node visual states
    Object.keys(stationsPayload).forEach(sid => {
      const st = stationsPayload[sid];
      const node = document.getElementById(`station-node-${sid}`);
      if (node) {
        node.classList.remove("status-nominal", "status-warning", "status-critical", "in-cycle");
        const riskPct = st.risk_score ? (st.risk_score * 100) : (st.risk_level === 'CRITICAL' ? 95 : (st.risk_level === 'WARNING' ? 65 : 20));
        if (riskPct < 60 && !st.is_stopped) {
          node.classList.add("status-nominal");
        } else if (riskPct >= 80 || st.is_stopped) {
          node.classList.add("status-critical");
        } else if (riskPct >= 60) {
          node.classList.add("status-warning");
        }
      }
    });

    // 1:1 Synchronize Fleet by VIN using measured backend cadence interpolation
    if (Array.isArray(vehiclesPayload) && vehiclesPayload.length > 0) {
      const activeVinMap = {};
      vehiclesPayload.forEach(v => { activeVinMap[v.vin] = v; });

      // Update existing fleet items by their exact VIN
      this.fleet.forEach(veh => {
        const vBackend = activeVinMap[veh.vin];
        if (vBackend) {
          const prevBackendStation = veh.backendCurrentStation || veh.toStation || "ST01";
          const newBackendStation = vBackend.current_station || "ST01";
          const prevVisited = veh.backendVisitedStationIds || [];
          const newVisited = vBackend.visited_station_ids || [];

          veh.backendCurrentStation = newBackendStation;
          veh.backendPreviousStation = vBackend.previous_station;
          veh.backendRouteIndex = vBackend.route_index || 1;
          veh.backendRouteLengthEstimate = vBackend.route_length_estimate || 37;
          veh.backendRouteLength = vBackend.route_length;
          veh.backendVisitedStationIds = newVisited;
          veh.backendDefectCount = vBackend.defect_count || 0;
          veh.defect_count = vBackend.defect_count || 0;
          veh.route_index = vBackend.route_index || 1;
          veh.route_length_estimate = vBackend.route_length_estimate || 37;
          veh.route_length = vBackend.route_length;
          veh.visited_station_ids = newVisited;

          // Determine station hops advanced during this measured backend interval
          if (newBackendStation !== prevBackendStation || newVisited.length > prevVisited.length) {
            let hops = [];
            // If full visited trace is available, extract sequential station hops
            if (newVisited.length > 0 && prevBackendStation) {
              const startIdx = newVisited.indexOf(prevBackendStation);
              const endIdx = newVisited.indexOf(newBackendStation);
              if (startIdx !== -1 && endIdx !== -1 && endIdx > startIdx) {
                for (let i = startIdx; i < endIdx; i++) {
                  hops.push({ from: newVisited[i], to: newVisited[i + 1] });
                }
              } else if (startIdx === -1) {
                // Record and log unmatched history fallback
                window._unmatchedStationFallbackCount = (window._unmatchedStationFallbackCount || 0) + 1;
                console.warn(`[twin_scene] Unmatched prevBackendStation hop fallback (#${window._unmatchedStationFallbackCount}):`, {
                  vin: veh.vin,
                  prevBackendStation,
                  newBackendStation,
                  newVisitedLength: newVisited.length
                });
              }
            }
            if (hops.length === 0) {
              const fromSid = veh.state === "DOCK" ? veh.toStation : (veh.fromStation || veh.toStation);
              const prevSid = vBackend.previous_station || fromSid;
              hops = [{ from: prevSid, to: newBackendStation }];
            }

            // Ensure legibility floor (at least 150ms per hop, compressed within measured interval)
            const minHopDuration = 150; // ms
            const effectiveInterval = Math.max(measuredInterval, hops.length * minHopDuration);

            veh.animHops = hops;
            veh.animStartTime = now;
            veh.animDuration = effectiveInterval;
            veh.fromStation = hops[0].from;
            veh.toStation = hops[0].to;
            veh.progress = 0.0;
            veh.state = "TRANSIT";
          } else {
            // Vehicle remained at current station (docked/in-cycle/blocked/halted)
            veh.animHops = [];
            veh.animStartTime = now;
            veh.animDuration = measuredInterval;
            veh.fromStation = newBackendStation;
            veh.toStation = newBackendStation;
            veh.progress = 1.0;
            veh.state = "DOCK";
          }

          if (this.activeHudVin === veh.vin && this.hudElement && this.hudElement.style.display !== "none") {
            this.showVehicleHud(veh, veh.element, this.isHudPinned);
          }
        }
      });

      // Prune vehicles no longer active in the backend
      const missingVins = this.fleet.filter(veh => !activeVinMap[veh.vin]);
      missingVins.forEach(veh => {
        if (veh.element) veh.element.remove();
      });
      this.fleet = this.fleet.filter(veh => activeVinMap[veh.vin]);

      // If fleet has room, introduce new backend vehicles
      const MAX_FLEET_RENDER = 150;
      if (this.fleet.length < Math.min(MAX_FLEET_RENDER, vehiclesPayload.length)) {
        const isInitialHydration = (this.fleet.length === 0);
        const currentFleetVins = new Set(this.fleet.map(f => f.vin));
        vehiclesPayload.forEach(vBackend => {
          if (!currentFleetVins.has(vBackend.vin) && this.fleet.length < MAX_FLEET_RENDER) {
            const curSid = vBackend.current_station || "ST01";
            const prevSid = vBackend.previous_station || (this.stations[curSid]?.upstream_ids?.[0]) || curSid;
            const hasConveyorEdge = Boolean(prevSid && prevSid !== curSid && this.edgePaths && this.edgePaths[`${prevSid}->${curSid}`]);
            const shouldAnimate = !isInitialHydration && hasConveyorEdge && (curSid === "ST01" || curSid === "ST02");

            const newVeh = {
              vin: vBackend.vin,
              fromStation: prevSid,
              toStation: curSid,
              backendCurrentStation: curSid,
              backendPreviousStation: prevSid,
              backendRouteIndex: vBackend.route_index || 1,
              backendRouteLengthEstimate: vBackend.route_length_estimate || 37,
              backendRouteLength: vBackend.route_length,
              backendVisitedStationIds: vBackend.visited_station_ids || [],
              backendDefectCount: vBackend.defect_count || 0,
              animHops: shouldAnimate ? [{ from: prevSid, to: curSid }] : [],
              animStartTime: now,
              animDuration: measuredInterval,
              progress: shouldAnimate ? 0.1 : 1.0,
              state: shouldAnimate ? "TRANSIT" : "DOCK",
              dwellTimer: 0.0,
              dwellTarget: 2.5,
              speed: 0.012,
              defect_count: vBackend.defect_count || 0,
              route_index: vBackend.route_index || 1,
              route_length_estimate: vBackend.route_length_estimate || 37,
              route_length: vBackend.route_length,
              visited_station_ids: vBackend.visited_station_ids || [],
              queueSlot: -1,
              element: null
            };
            this.fleet.push(newVeh);
            currentFleetVins.add(vBackend.vin);
          }
        });
        this.createFleetDOM();
      }
    }
  }

  showVehicleHud(veh, el, isClick = false) {
    if (this.hudCloseTimer) {
      clearTimeout(this.hudCloseTimer);
      this.hudCloseTimer = null;
    }

    if (!this.hudElement) this.initHoverHud();
    const hud = this.hudElement;
    if (!hud || !el) return;

    if (isClick) {
      this.isHudPinned = true;
    }

    this.activeHudVin = veh.vin;
    
    // Explicitly read telemetry from true backend fields
    const backendSid = veh.backendCurrentStation || veh.toStation || "ST01";
    const backendPrevSid = veh.backendPreviousStation;
    const stMeta = this.stations[backendSid] || {};
    const defectCount = veh.backendDefectCount !== undefined ? veh.backendDefectCount : (veh.defect_count || 0);
    const routeIndex = veh.backendRouteIndex || veh.route_index || 1;
    const routeEstimate = veh.backendRouteLengthEstimate || veh.route_length_estimate || 37;
    const routeLength = veh.backendRouteLength || veh.route_length; // Only set by backend when vehicle reaches terminal station

    const currentLoc = backendPrevSid && backendPrevSid !== backendSid
      ? `${backendPrevSid} ➔ ${backendSid}`
      : `${backendSid} (Station Operation)`;

    const routeDisplay = routeLength
      ? `${routeIndex}/${routeLength} Stations Traversed`
      : `${routeIndex}/${routeEstimate} Stations Traversed`;

    const isHalted = Boolean(veh.is_stopped);
    let statusTag = '🟢 CONVEYOR TRANSIT';
    if (isHalted && this.stationsPayload[veh.toStation]?.is_stopped) statusTag = '🛑 HALTED AT STATION';
    else if (isHalted && veh.queueSlot >= 0) statusTag = `⏱️ QUEUED (#${veh.queueSlot + 1})`;
    else if (veh.state === 'DOCK') statusTag = `⚙️ IN-CYCLE (${veh.toStation})`;

    hud.innerHTML = `
      <div class="hud-vin-title">
        <span class="hud-vin-text">${veh.vin}</span>
        <div style="display: flex; align-items: center; gap: 6px;">
          <span class="hud-status-tag ${isHalted ? 'halted' : ''}">${statusTag}</span>
          <button style="background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 14px; font-weight: bold; line-height: 1; padding: 2px 4px;" onclick="event.stopPropagation(); if (window.sceneEngine) window.sceneEngine.hideVehicleHud(true);">✕</button>
        </div>
      </div>
      <div class="hud-detail-row">
        <span>Current Location:</span>
        <strong>${currentLoc}</strong>
      </div>
      <div class="hud-detail-row">
        <span>Station Description:</span>
        <strong>${stMeta.name || backendSid}</strong>
      </div>
      <div class="hud-detail-row">
        <span>Manufacturing Zone:</span>
        <strong>${stMeta.zone || "Body Construction"}</strong>
      </div>
      <div class="hud-detail-row">
        <span>Quality Buy-Off:</span>
        <strong style="color: ${defectCount > 0 ? '#f59e0b' : '#34d399'};">${defectCount === 0 ? '✓ 0 Defects (Pass)' : `⚠️ ${defectCount} Defect(s) Flagged`}</strong>
      </div>
      <div class="hud-detail-row">
        <span>Line Traversal:</span>
        <strong>${routeDisplay}</strong>
      </div>
      <button class="hud-action-btn" onclick="event.stopPropagation(); window.traceVinFromVehicle('${veh.vin}')">
        <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
        Trace VIN in Genealogy
      </button>
    `;

    hud.style.left = el.style.left;
    hud.style.top = el.style.top;
    hud.style.display = "block";
  }

  scheduleHideHud(delay = 200) {
    if (this.isHudPinned) return;
    if (this.hudCloseTimer) clearTimeout(this.hudCloseTimer);
    this.hudCloseTimer = setTimeout(() => {
      this.hideVehicleHud(false);
    }, delay);
  }

  hideVehicleHud(force = false) {
    if (this.hudCloseTimer) {
      clearTimeout(this.hudCloseTimer);
      this.hudCloseTimer = null;
    }
    if (force || !this.isHudPinned) {
      if (this.hudElement) {
        this.hudElement.style.display = "none";
      }
      this.activeHudVin = null;
      this.isHudPinned = false;
    }
  }
}
