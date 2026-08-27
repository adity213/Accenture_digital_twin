/**
 * DigitalTwin.ai — TwinSphere SCADA Connected Conveyor Engine v3.0
 */

class TwinSceneEngine {
  constructor(canvasContainerId, svgLayerId) {
    this.container = document.getElementById(canvasContainerId);
    this.svgLayer = document.getElementById(svgLayerId);
    this.stations = {};
    this.edges = [];
    this.selectedId = "ST06";
    this.carBodies = [];
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

      case "BufferStation":
      case "ConveyorBuffer":
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
      case "Dynamometer":
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

  calculateFloorCoordinates(stations, edges) {
    if (typeof window.stationCoords === "undefined") {
      window.stationCoords = {};
    }

    // Industrial calibrated floor baseline for standard ST01 - ST40
    const baseline = (typeof getBaselineFactoryCoordinates === "function") 
      ? getBaselineFactoryCoordinates() 
      : {
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

        "ST15": { x: 1860, y: 420, isParallel: false },
        "ST16": { x: 1610, y: 420, isParallel: false },
        "ST17": { x: 1360, y: 420, isParallel: false },
        "ST18": { x: 1110, y: 420, isParallel: false },
        "ST19": { x: 860,  y: 420, isParallel: false },
        "ST20": { x: 610,  y: 420, isParallel: false },
        "ST21": { x: 360,  y: 420, isParallel: false },
        "ST22": { x: 110,  y: 420, isParallel: false },

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

        "ST33": { x: 1390, y: 940, isParallel: false },
        "ST34": { x: 1210, y: 940, isParallel: false },
        "ST35": { x: 1030, y: 940, isParallel: false },
        "ST36": { x: 850,  y: 940, isParallel: false },
        "ST37": { x: 670,  y: 940, isParallel: false },
        "ST38": { x: 490,  y: 940, isParallel: false },
        "ST39": { x: 310,  y: 940, isParallel: false },
        "ST40": { x: 130,  y: 940, isParallel: false }
      };

    // Ensure baseline keys exist in window.stationCoords
    Object.keys(baseline).forEach(sid => {
      if (!window.stationCoords[sid]) {
        window.stationCoords[sid] = Object.assign({}, baseline[sid]);
      }
    });

    // Smart Calibrated Layout Placement for Custom / Added Stations
    Object.keys(stations).forEach(sid => {
      if (baseline[sid] && window.stationCoords[sid]) return;

      const meta = stations[sid] || {};
      const zone = (meta.zone || "Body").toLowerCase();
      let pos = window.stationCoords[sid];

      // Define Zone Y bounds
      let expectedMinY = 20, expectedMaxY = 360, defaultY = 130;
      let flowDirection = "ltr"; // left-to-right

      if (zone.includes("paint")) {
        expectedMinY = 380;
        expectedMaxY = 570;
        defaultY = 420;
        flowDirection = "rtl"; // right-to-left
      } else if (zone.includes("assembly")) {
        expectedMinY = 590;
        expectedMaxY = 1100;
        defaultY = 710;
        flowDirection = "ltr";
      }

      // Check if position needs recalibration to fit proper floor zone bay
      const isOutOfBounds = !pos || pos.y < expectedMinY || pos.y > expectedMaxY;

      if (isOutOfBounds) {
        // Find upstream link in DAG
        const upstreamEdge = edges.find(e => e[1] === sid);
        const upstreamSid = upstreamEdge ? upstreamEdge[0] : null;
        const upstreamPos = upstreamSid ? window.stationCoords[upstreamSid] : null;

        let newX = 110;
        let newY = defaultY;

        if (upstreamPos && upstreamPos.y >= expectedMinY && upstreamPos.y <= expectedMaxY) {
          if (flowDirection === "ltr") {
            newX = upstreamPos.x + 160;
            newY = upstreamPos.y;
          } else {
            // Paint (Reverse Flow)
            if (upstreamPos.x >= 270) {
              newX = upstreamPos.x - 160;
              newY = upstreamPos.y;
            } else {
              // Near left edge of Paint shop, place on lower parallel spur
              newX = upstreamPos.x + 150;
              newY = upstreamPos.y + 70;
            }
          }
        } else {
          // Place after other stations in this zone
          const existingInZone = Object.keys(stations).filter(s => s !== sid && (stations[s].zone || "").toLowerCase().includes(zone));
          if (existingInZone.length > 0) {
            const lastSid = existingInZone[existingInZone.length - 1];
            const lastPos = window.stationCoords[lastSid];
            if (lastPos) {
              newX = flowDirection === "ltr" ? lastPos.x + 160 : Math.max(110, lastPos.x - 160);
              newY = lastPos.y;
            }
          }
        }

        window.stationCoords[sid] = { x: newX, y: newY, branch: pos?.branch || "" };
      }
    });

    // Zero-Overlap Collision Resolver
    const allSids = Object.keys(stations);
    for (let i = 0; i < allSids.length; i++) {
      for (let j = i + 1; j < allSids.length; j++) {
        const s1 = allSids[i];
        const s2 = allSids[j];
        const p1 = window.stationCoords[s1];
        const p2 = window.stationCoords[s2];
        if (p1 && p2) {
          const dist = Math.hypot(p1.x - p2.x, p1.y - p2.y);
          if (dist < 110) {
            p2.x += 160;
            if (p2.x > 2100) {
              p2.x = 110;
              p2.y += 70;
            }
          }
        }
      }
    }
  }

  renderScene(stationsMeta, edges) {
    this.stations = stationsMeta;
    this.edges = edges;
    if (!this.container || !this.svgLayer) return;

    // Recalibrate coordinates for all active stations
    this.calculateFloorCoordinates(this.stations, this.edges);

    this.container.innerHTML = "";
    this.svgLayer.innerHTML = "";

    const NODE_W = 144;
    const NODE_H = 124;

    // Smart Continuous Port-to-Port Conveyor Rail Bezier Calculations
    this.edges.forEach(([u, v]) => {
      const p1 = window.stationCoords[u];
      const p2 = window.stationCoords[v];
      if (!p1 || !p2) return;

      let x1, y1, x2, y2, cx1, cy1, cx2, cy2;
      const dx = p2.x - p1.x;
      const dy = p2.y - p1.y;

      if (dx > 40) {
        // Forward Flow: Left-to-Right
        x1 = p1.x + NODE_W;
        y1 = p1.y + NODE_H * 0.5;
        x2 = p2.x;
        y2 = p2.y + NODE_H * 0.5;
        const midX = x1 + (x2 - x1) * 0.5;
        cx1 = midX;
        cy1 = y1;
        cx2 = midX;
        cy2 = y2;
      } else if (dx < -40) {
        // Reverse Flow: Right-to-Left (Zone 2 Paint & Zone 3B Assembly)
        x1 = p1.x;
        y1 = p1.y + NODE_H * 0.5;
        x2 = p2.x + NODE_W;
        y2 = p2.y + NODE_H * 0.5;
        const midX = x1 + (x2 - x1) * 0.5;
        cx1 = midX;
        cy1 = y1;
        cx2 = midX;
        cy2 = y2;
      } else {
        // Vertical Turnaround Transfers (ST14->ST15, ST22->ST23, ST32->ST33)
        if (p1.x > 900) {
          // Right-side U-Turn Loop (Zone 1->2 and Zone 3A->3B)
          x1 = p1.x + NODE_W;
          y1 = p1.y + NODE_H * 0.5;
          x2 = p2.x + NODE_W;
          y2 = p2.y + NODE_H * 0.5;
          cx1 = Math.min(2220, Math.max(x1, x2) + 75);
          cy1 = y1;
          cx2 = cx1;
          cy2 = y2;
        } else {
          // Left-side U-Turn Loop (Zone 2->3)
          x1 = p1.x;
          y1 = p1.y + NODE_H * 0.5;
          x2 = p2.x;
          y2 = p2.y + NODE_H * 0.5;
          cx1 = Math.max(35, Math.min(x1, x2) - 65);
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
      pathChev.setAttribute("class", "rail-chevrons");
      this.svgLayer.appendChild(pathChev);
    });

    // Render Station Nodes
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
      `;

      this.container.appendChild(node);
    });

    this.initLivingLineVehicles();
  }

  initLivingLineVehicles() {
    const sids = Object.keys(this.stations);
    this.carBodies = [];
    if (sids.length === 0) return;

    const numVehicles = Math.min(8, sids.length);
    const step = Math.max(1, Math.floor(sids.length / numVehicles));

    for (let i = 0; i < numVehicles; i++) {
      const sid = sids[Math.min(i * step, sids.length - 1)];
      this.carBodies.push({ id: `car-${i + 1}`, currentSid: sid });
    }

    this.carBodies.forEach((c) => {
      const el = document.createElement("div");
      el.id = `vehicle-${c.id}`;
      el.className = "car-body-silhouette";
      el.innerHTML = `
        <svg viewBox="0 0 32 18" width="32" height="18">
          <rect x="2" y="2" width="28" height="14" rx="4" fill="#0057ff" stroke="#0046d6" stroke-width="1.5"/>
          <rect x="8" y="4" width="16" height="10" rx="2" fill="#ffffff"/>
        </svg>
      `;
      this.container.appendChild(el);
      this.updateVehiclePosition(c);
    });
  }

  updateVehiclePosition(car) {
    const el = document.getElementById(`vehicle-${car.id}`);
    const pos = window.stationCoords[car.currentSid];
    if (!el || !pos) return;

    el.style.left = `${pos.x + 72}px`;
    el.style.top = `${pos.y + 62}px`;
  }

  updateTelemetry(stationsPayload) {
    if (!stationsPayload) return;

    Object.keys(stationsPayload).forEach((sid) => {
      const st = stationsPayload[sid];
      const node = document.getElementById(`station-node-${sid}`);
      const ctEl = document.getElementById(`s-ct-${sid}`);
      const riskEl = document.getElementById(`s-risk-${sid}`);

      if (ctEl) ctEl.innerText = `${(st.cycle_time_s || 60).toFixed(1)}s`;

      const riskPct = Math.round((st.composite_risk || 0.05) * 100);
      if (riskEl) {
        riskEl.innerText = `${riskPct}%`;
        riskEl.style.color = riskPct >= 80 ? "var(--status-critical)" : (riskPct >= 60 ? "var(--status-warning)" : "var(--status-nominal)");
      }

      if (node) {
        node.classList.remove("status-warning", "status-critical");
        if (riskPct >= 80 || st.is_stopped) {
          node.classList.add("status-critical");
        } else if (riskPct >= 60) {
          node.classList.add("status-warning");
        }
      }
    });
  }
}
