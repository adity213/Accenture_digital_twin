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

  static getMachineGlyph(type, sid, statusColor = "var(--status-nominal)", isManual = false) {
    switch (type) {
      case "RoboticWeld":
      case "RespotWeld":
        return `
          <svg viewBox="0 0 80 40" width="80" height="38">
            <polygon points="40,24 65,32 40,38 15,32" fill="var(--surface-panel-raised)" stroke="var(--border-strong)" stroke-width="1.2"/>
            <rect x="24" y="26" width="10" height="5" rx="1" fill="var(--steel)"/>
            <line x1="29" y1="26" x2="42" y2="14" stroke="var(--brand-blue)" stroke-width="3" stroke-linecap="round"/>
            <circle cx="42" cy="14" r="2.5" fill="var(--steel)"/>
            <line x1="42" y1="14" x2="56" y2="20" stroke="var(--brand-blue)" stroke-width="2.5" stroke-linecap="round"/>
            <circle cx="56" cy="20" r="2.5" fill="var(--status-warning)"/>
            <circle cx="56" cy="20" r="3.5" fill="var(--accent-weld)" opacity="0.6">
              <animate attributeName="r" values="2.5;5;2.5" dur="1s" repeatCount="indefinite"/>
            </circle>
          </svg>
        `;

      case "MainFraming":
      case "LaserBrazing":
        return `
          <svg viewBox="0 0 80 40" width="80" height="38">
            <rect x="8" y="8" width="64" height="5" rx="1" fill="var(--steel)"/>
            <line x1="20" y1="13" x2="20" y2="32" stroke="var(--steel)" stroke-width="2.5"/>
            <line x1="60" y1="13" x2="60" y2="32" stroke="var(--steel)" stroke-width="2.5"/>
            <rect x="16" y="24" width="8" height="8" rx="1" fill="var(--brand-blue)"/>
            <rect x="56" y="24" width="8" height="8" rx="1" fill="var(--brand-blue)"/>
            <line x1="24" y1="28" x2="56" y2="28" stroke="var(--accent-weld)" stroke-width="1.5" stroke-dasharray="3 2">
              <animate attributeName="opacity" values="0.4;1;0.4" dur="1.2s" repeatCount="indefinite"/>
            </line>
          </svg>
        `;

      case "RoboticSpray":
      case "ThermalOven":
        return `
          <svg viewBox="0 0 80 40" width="80" height="38">
            <rect x="10" y="6" width="60" height="28" rx="2" fill="var(--status-warning-bg)" stroke="var(--status-warning)" stroke-width="1.5"/>
            <line x1="16" y1="13" x2="64" y2="13" stroke="var(--status-warning)" stroke-width="1.5"/>
            <line x1="16" y1="19" x2="64" y2="19" stroke="var(--status-warning)" stroke-width="1.5"/>
            <line x1="28" y1="6" x2="38" y2="24" stroke="var(--steel)" stroke-width="2">
              <animate attributeName="x2" values="24;54;24" dur="2s" repeatCount="indefinite"/>
            </line>
          </svg>
        `;

      case "ChemicalBath":
      case "ElectroDeposition":
        return `
          <svg viewBox="0 0 80 40" width="80" height="38">
            <rect x="10" y="14" width="60" height="20" rx="1" fill="var(--surface-panel-raised)" stroke="var(--accent-weld)" stroke-width="1.5"/>
            <path d="M 12 21 Q 25 19 40 21 T 68 21" fill="none" stroke="var(--accent-weld)" stroke-width="1.5">
              <animate attributeName="d" values="M 12 21 Q 25 19 40 21 T 68 21; M 12 21 Q 25 23 40 21 T 68 21; M 12 21 Q 25 19 40 21 T 68 21" dur="2.5s" repeatCount="indefinite"/>
            </path>
            <line x1="40" y1="4" x2="40" y2="15" stroke="var(--steel)" stroke-width="2"/>
          </svg>
        `;

      case "BufferStation":
      case "ConveyorBuffer":
        return `
          <svg viewBox="0 0 80 40" width="80" height="38">
            <line x1="8" y1="20" x2="72" y2="20" stroke="var(--border-strong)" stroke-width="5" stroke-linecap="round"/>
            <rect x="14" y="13" width="12" height="13" rx="1" fill="var(--status-nominal)"/>
            <rect x="34" y="13" width="12" height="13" rx="1" fill="var(--status-nominal)"/>
            <rect x="54" y="13" width="12" height="13" rx="1" fill="var(--bg-panel)" stroke="var(--border-strong)" stroke-width="1" stroke-dasharray="2 2"/>
          </svg>
        `;

      case "AutomatedMarriage":
      case "ModuleMarriage":
      case "AutomatedTorque":
      case "Dynamometer":
        return `
          <svg viewBox="0 0 80 40" width="80" height="38">
            <rect x="14" y="26" width="52" height="5" rx="1" fill="var(--steel)"/>
            <rect x="22" y="14" width="6" height="12" fill="var(--brand-blue)"/>
            <rect x="52" y="14" width="6" height="12" fill="var(--brand-blue)"/>
            <circle cx="25" cy="10" r="2.5" fill="var(--status-nominal)"/>
            <circle cx="55" cy="10" r="2.5" fill="var(--status-nominal)"/>
          </svg>
        `;

      case "BuyOff":
      case "QualityGate":
        return `
          <svg viewBox="0 0 80 40" width="80" height="38">
            <path d="M 16 36 L 16 8 L 64 8 L 64 36" fill="none" stroke="var(--steel)" stroke-width="2.5"/>
            <rect x="20" y="10" width="40" height="9" fill="var(--steel)" stroke="var(--steel)" stroke-width="1"/>
            <rect x="20" y="10" width="10" height="4.5" fill="var(--bg-panel)"/>
            <rect x="40" y="10" width="10" height="4.5" fill="var(--bg-panel)"/>
            <rect x="30" y="14.5" width="10" height="4.5" fill="var(--bg-panel)"/>
            <rect x="50" y="14.5" width="10" height="4.5" fill="var(--bg-panel)"/>
            <line x1="40" y1="19" x2="40" y2="34" stroke="var(--status-nominal)" stroke-width="1.5" stroke-dasharray="2 2"/>
          </svg>
        `;

      default:
        if (isManual) {
          return `
            <svg viewBox="0 0 80 40" width="80" height="38">
              <circle cx="30" cy="12" r="4.5" fill="var(--steel)"/>
              <path d="M 20 32 L 22 20 L 38 20 L 40 32" fill="none" stroke="var(--steel)" stroke-width="2.5" stroke-linecap="round"/>
              <rect x="42" y="14" width="15" height="18" rx="1.5" fill="var(--status-warning-bg)" stroke="var(--status-warning)" stroke-width="1.5"/>
              <polyline points="46,24 49,27 54,21" fill="none" stroke="var(--status-nominal)" stroke-width="2"/>
            </svg>
          `;
        } else {
          return `
            <svg viewBox="0 0 80 40" width="80" height="38">
              <rect x="18" y="8" width="44" height="22" rx="2" fill="var(--surface-panel-raised)" stroke="var(--border-strong)" stroke-width="1.5"/>
              <circle cx="40" cy="19" r="6" fill="var(--bg-panel)" stroke="var(--brand-blue)" stroke-width="1.5"/>
              <line x1="40" y1="13" x2="40" y2="25" stroke="var(--brand-blue)" stroke-width="1"/>
              <line x1="34" y1="19" x2="46" y2="19" stroke="var(--brand-blue)" stroke-width="1"/>
            </svg>
          `;
        }
    }
  }

  renderScene(stationsMeta, edges) {
    this.stations = stationsMeta;
    this.edges = edges;
    if (!this.container || !this.svgLayer) return;

    this.container.innerHTML = "";
    this.svgLayer.innerHTML = "";

    const NODE_W = 144;
    const NODE_H = 124;

    // Smart Continuous Port-to-Port Conveyor Rail Bezier Calculations
    this.edges.forEach(([u, v]) => {
      const p1 = stationCoords[u];
      const p2 = stationCoords[v];
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
        if (p1.x > 1000) {
          // Right-side U-Turn Loop (Zone 1->2 and Zone 3A->3B)
          x1 = p1.x + NODE_W;
          y1 = p1.y + NODE_H * 0.5;
          x2 = p2.x + NODE_W;
          y2 = p2.y + NODE_H * 0.5;
          cx1 = x1 + 90;
          cy1 = y1;
          cx2 = x2 + 90;
          cy2 = y2;
        } else {
          // Left-side U-Turn Loop (Zone 2->3)
          x1 = p1.x;
          y1 = p1.y + NODE_H * 0.5;
          x2 = p2.x;
          y2 = p2.y + NODE_H * 0.5;
          cx1 = x1 - 90;
          cy1 = y1;
          cx2 = x2 - 90;
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

    // Render 40 Station Nodes
    Object.keys(this.stations).forEach((sid) => {
      const meta = this.stations[sid];
      const pos = stationCoords[sid] || { x: 50, y: 80 };
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
          <span class="node-tier-pill ${isManual ? 'manual' : ''}">${meta.sensor_tier.toUpperCase()}</span>
        </div>
        <div class="station-glyph-wrap" id="glyph-${sid}">
          ${TwinSceneEngine.getMachineGlyph(meta.station_type, sid, "var(--status-nominal)", isManual)}
        </div>
        <div class="node-name-label">${meta.name}</div>
        <div class="node-hud-footer">
          <span class="node-val-ct" id="s-ct-${sid}">${meta.target_cycle_time_s.toFixed(1)}s</span>
          <span class="node-val-risk" id="s-risk-${sid}">5%</span>
        </div>
      `;

      this.container.appendChild(node);
    });

    this.initLivingLineVehicles();
  }

  initLivingLineVehicles() {
    this.carBodies = [
      { id: "car-1", currentSid: "ST02" },
      { id: "car-2", currentSid: "ST06" },
      { id: "car-3", currentSid: "ST10" },
      { id: "car-4", currentSid: "ST17" },
      { id: "car-5", currentSid: "ST20" },
      { id: "car-6", currentSid: "ST25" },
      { id: "car-7", currentSid: "ST30" },
      { id: "car-8", currentSid: "ST36" }
    ];

    this.carBodies.forEach((c) => {
      const el = document.createElement("div");
      el.id = `vehicle-${c.id}`;
      el.className = "car-body-silhouette";
      el.innerHTML = `
        <svg viewBox="0 0 32 18" width="32" height="18">
          <rect x="2" y="2" width="28" height="14" rx="4" fill="var(--brand-blue)" stroke="var(--accent-signal)" stroke-width="1.5"/>
          <rect x="8" y="4" width="16" height="10" rx="2" fill="var(--bg-panel)"/>
        </svg>
      `;
      this.container.appendChild(el);
      this.updateVehiclePosition(c);
    });
  }

  updateVehiclePosition(car) {
    const el = document.getElementById(`vehicle-${car.id}`);
    const pos = stationCoords[car.currentSid];
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

      
      // CONFIDENCE OPACITY
      if (st.twin_confidence !== undefined) {
          node.style.opacity = Math.max(0.3, st.twin_confidence);
          node.style.filter = `saturate(${Math.max(30, st.twin_confidence * 100)}%)`;
      }
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
