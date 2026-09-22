/* GHOST FIVE // VECTIS
 * Runs the Launch Control interface against the local VECTIS execution API.
 */
"use strict";

const byId = (id) => document.getElementById(id);

let lastPayload = null;

const scenarios = {
  nominal: {
    quality: 96, fuel: 97, weather: 92, risk: 18,
    ready: true, navigation: true, communications: true,
    range: true, payload: true
  },
  weather: {
    quality: 96, fuel: 97, weather: 58, risk: 18,
    ready: true, navigation: true, communications: true,
    range: true, payload: true
  },
  systems: {
    quality: 96, fuel: 97, weather: 92, risk: 18,
    ready: false, navigation: false, communications: true,
    range: true, payload: true
  },
  risk: {
    quality: 96, fuel: 97, weather: 92, risk: 62,
    ready: true, navigation: true, communications: true,
    range: true, payload: true
  }
};

function applyScenario(name) {
  const scenario = scenarios[name];
  if (!scenario) return;

  for (const id of ["quality", "fuel", "weather", "risk"]) {
    byId(id).value = String(scenario[id]);
    byId(id).dispatchEvent(new Event("input"));
  }

  byId("ready").checked = scenario.ready;
  byId("navigation-ready").checked = scenario.navigation;
  byId("communications-ready").checked = scenario.communications;
  byId("range-clear").checked = scenario.range;
  byId("payload-ready").checked = scenario.payload;
  byId("header-status").textContent = "READY";
  byId("launch-orb").dataset.state = "idle";
  byId("decision-label").textContent = "STANDBY";
}

function bindRange(id, outputId) {
  const input = byId(id);
  const output = byId(outputId);
  const sync = () => { output.textContent = input.value; };
  input.addEventListener("input", sync);
  sync();
}

function setGate(id, value) {
  const gate = byId(id);
  const strong = gate.querySelector("strong");
  const passed = value === true;
  gate.dataset.state = passed ? "go" : "hold";
  strong.textContent = passed ? "GO" : "HOLD";
}

function setDecision(authorized, score) {
  const orb = byId("launch-orb");
  orb.dataset.state = authorized ? "go" : "hold";
  byId("decision-label").textContent = authorized ? "GO" : "HOLD";
  byId("readiness-score").textContent = Number(score || 0).toFixed(1);
  byId("header-status").textContent = authorized ? "GO FOR LAUNCH" : "HOLD";
  byId("decision-copy").textContent = authorized
    ? "Every deterministic gate passed. VECTIS selected the launch path."
    : "At least one gate failed. VECTIS selected the hold path and preserved the reason in the trace.";
}

function renderPublished(graph, values, states) {
  const log = byId("mission-log");
  log.replaceChildren();
  let count = 0;

  for (const node of graph.nodes) {
    if (node.kind !== "publish") continue;
    if (states.get(node.id) !== "succeeded") continue;
    if (!values.has(node.id)) continue;

    count += 1;
    const item = document.createElement("div");
    item.className = "log-entry";
    item.textContent = String(values.get(node.id));
    log.appendChild(item);
  }

  if (count === 0) {
    const empty = document.createElement("p");
    empty.textContent = "No publish node completed.";
    log.appendChild(empty);
  }

  byId("published-count").textContent = String(count);
}

function renderTrace(graph, values, states) {
  const trace = byId("trace");
  trace.replaceChildren();

  for (const node of graph.nodes) {
    const state = states.get(node.id) || "pending";
    const row = document.createElement("div");
    row.className = "trace-row";
    row.dataset.state = state;

    const identity = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = node.id;
    const kind = document.createElement("span");
    kind.textContent = node.kind;
    identity.append(name, kind);

    const stateNode = document.createElement("b");
    stateNode.textContent = state.toUpperCase();

    const valueNode = document.createElement("code");
    valueNode.textContent = values.has(node.id)
      ? JSON.stringify(values.get(node.id))
      : "";

    row.append(identity, stateNode, valueNode);
    trace.appendChild(row);
  }
}

function renderTimeline(levels) {
  const timeline = byId("timeline");
  timeline.replaceChildren();

  for (const level of levels) {
    const group = document.createElement("section");
    group.className = "timeline-level";

    const heading = document.createElement("div");
    heading.className = "timeline-heading";
    const label = document.createElement("strong");
    label.textContent = `LEVEL ${level.level}`;
    const count = document.createElement("span");
    count.textContent = `${level.nodes.length} node${level.nodes.length === 1 ? "" : "s"}`;
    heading.append(label, count);
    group.appendChild(heading);

    const nodes = document.createElement("div");
    nodes.className = "timeline-nodes";

    for (const node of level.nodes) {
      const item = document.createElement("article");
      item.className = "timeline-node";
      item.dataset.state = node.state;

      const identity = document.createElement("strong");
      identity.textContent = node.id;
      const meta = document.createElement("span");
      meta.textContent = node.stage
        ? `${node.kind} // ${node.stage}`
        : node.kind;
      const state = document.createElement("b");
      state.textContent = node.state.toUpperCase();

      item.append(identity, meta, state);
      nodes.appendChild(item);
    }

    group.appendChild(nodes);
    timeline.appendChild(group);
  }

  if (levels.length === 0) {
    const empty = document.createElement("p");
    empty.textContent = "No execution levels available.";
    timeline.appendChild(empty);
  }
}


async function runMission(event) {
  event.preventDefault();
  byId("header-status").textContent = "EXECUTING";
  byId("launch-orb").dataset.state = "active";
  byId("decision-label").textContent = "RUNNING";

  const payload = {
    mission: byId("mission").value,
    vehicle: byId("vehicle").value,
    operator: byId("operator").value,
    quality: Number(byId("quality").value),
    risk: Number(byId("risk").value),
    fuel_percent: Number(byId("fuel").value),
    weather_score: Number(byId("weather").value),
    ready: byId("ready").checked,
    navigation_ready: byId("navigation-ready").checked,
    communications_ready: byId("communications-ready").checked,
    range_clear: byId("range-clear").checked,
    payload_ready: byId("payload-ready").checked
  };

  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || "VECTIS execution failed");
    }

    lastPayload = payload;
    byId("export-report").disabled = false;

    const values = new Map(result.runtime.node_values || []);
    const states = new Map(result.runtime.node_states || []);

    byId("source").textContent = result.source;
    byId("nodes").textContent = String(result.summary.nodes);
    byId("edges").textContent = String(result.summary.edges);
    byId("levels").textContent = String(result.summary.levels);
    byId("stages").textContent = String(result.summary.stage_count);
    byId("width").textContent = String(result.summary.max_width);
    byId("failures").textContent = String(result.runtime.failures.length);
    byId("fingerprint").textContent = result.summary.fingerprint;

    setGate("gate-systems", values.get("systems_gate"));
    setGate("gate-environment", values.get("environment_gate"));
    setGate("gate-fuel", values.get("fuel_gate"));
    setGate("gate-payload", values.get("payload_gate"));
    setGate("gate-risk", values.get("risk_gate"));

    setDecision(
      values.get("launch_authorized") === true,
      values.get("readiness_score")
    );
    renderPublished(result.graph, values, states);
    renderTrace(result.graph, values, states);
    renderTimeline(result.timeline || []);
  } catch (error) {
    byId("launch-orb").dataset.state = "hold";
    byId("decision-label").textContent = "ERROR";
    byId("header-status").textContent = "ERROR";
    byId("decision-copy").textContent = error.message;
  }
}

async function openProofReport() {
  if (!lastPayload) return;

  const button = byId("export-report");
  button.disabled = true;
  button.textContent = "Building Report";

  try {
    const response = await fetch("/api/report", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(lastPayload)
    });
    const html = await response.text();

    if (!response.ok) {
      throw new Error("Unable to generate execution report");
    }

    const blob = new Blob([html], {type: "text/html"});
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    button.textContent = "Open Proof Report";
  } catch (error) {
    button.textContent = "Report unavailable";
    setTimeout(() => {
      button.textContent = "Open Proof Report";
    }, 1600);
  } finally {
    button.disabled = false;
  }
}

async function copySource() {
  try {
    await navigator.clipboard.writeText(byId("source").textContent);
    byId("copy-source").textContent = "Copied";
    setTimeout(() => { byId("copy-source").textContent = "Copy Source"; }, 1200);
  } catch (_error) {
    byId("copy-source").textContent = "Copy unavailable";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  bindRange("quality", "quality-value");
  bindRange("fuel", "fuel-value");
  bindRange("weather", "weather-value");
  bindRange("risk", "risk-value");
  byId("readiness-form").addEventListener("submit", runMission);
  byId("copy-source").addEventListener("click", copySource);
  byId("export-report").addEventListener("click", openProofReport);
  for (const button of document.querySelectorAll("[data-scenario]")) {
    button.addEventListener(
      "click",
      () => applyScenario(button.dataset.scenario)
    );
  }
});
