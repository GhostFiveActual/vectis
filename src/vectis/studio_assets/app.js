/* GHOST FIVE // VECTIS
 * Runs the VECTIS Studio browser interface and renders compiler and runtime results.
 */
"use strict";

const state = {
  examples: [],
  graph: null,
  runtime: null,
  ast: null,
  diagnostics: []
};

const $ = (id) => {
  const node = document.getElementById(id);
  if (!node) throw new Error(`Missing VECTIS Studio element: ${id}`);
  return node;
};

function toast(message) {
  const node = $("toast");
  node.textContent = message;
  node.classList.add("show");
  window.setTimeout(() => node.classList.remove("show"), 1800);
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error(`Studio API returned invalid JSON (${response.status}).`);
  }
  if (!response.ok) {
    const error = new Error(payload.error || `Studio API failed (${response.status}).`);
    error.payload = payload;
    throw error;
  }
  return payload;
}

function request(path, source, extra = {}) {
  return api(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source, ...extra })
  });
}

function sourceText() { return $("source").value; }

function updateLineNumbers() {
  const source = $("source");
  const count = Math.max(1, source.value.split("\n").length);
  $("line-numbers").textContent = Array.from({ length: count }, (_, index) => index + 1).join("\n");
  $("line-numbers").scrollTop = source.scrollTop;
}

function updateCursor() {
  const source = $("source");
  const before = source.value.slice(0, source.selectionStart);
  const lines = before.split("\n");
  $("cursor-status").textContent = `Ln ${lines.length}, Col ${lines.at(-1).length + 1}`;
}

function jsonText(value) {
  return value == null ? "" : JSON.stringify(value, null, 2);
}

function setRunState(label, kind = "neutral") {
  const node = $("run-state");
  node.textContent = label;
  node.className = `run-state ${kind}`;
}

function renderMetrics() {
  const graph = state.graph || { nodes: [], edges: [] };
  const runtime = state.runtime || { execution_order: [], failures: [] };
  $("metric-nodes").textContent = String(graph.nodes?.length || 0);
  $("metric-edges").textContent = String(graph.edges?.length || 0);
  $("metric-executed").textContent = String(runtime.execution_order?.length || 0);
  $("metric-failures").textContent = String(runtime.failures?.length || 0);
}

function renderDiagnostics() {
  $("diag-count").textContent = String(state.diagnostics.length);
  $("diagnostics-tab").textContent = state.diagnostics.length
    ? jsonText(state.diagnostics)
    : "No diagnostics.";
}

function renderRuntime() {
  const target = $("runtime-tab");
  target.replaceChildren();
  if (!state.runtime) {
    const empty = document.createElement("div");
    empty.className = "value";
    empty.textContent = "Run a mission to inspect deterministic runtime states and values.";
    target.appendChild(empty);
    return;
  }
  const values = new Map(state.runtime.node_values || []);
  const list = document.createElement("div");
  list.className = "runtime-list";
  for (const [nodeId, nodeState] of state.runtime.node_states || []) {
    const row = document.createElement("div");
    row.className = "runtime-row";
    const id = document.createElement("code");
    id.textContent = nodeId;
    const status = document.createElement("span");
    status.className = `state ${nodeState}`;
    status.textContent = nodeState;
    const value = document.createElement("span");
    value.className = "value";
    value.textContent = values.has(nodeId) ? JSON.stringify(values.get(nodeId)) : "—";
    row.append(id, status, value);
    list.appendChild(row);
  }
  target.appendChild(list);
}

function graphLayout(graph) {
  const nodes = graph?.nodes || [];
  const edges = graph?.edges || [];
  const incoming = new Map(nodes.map((node) => [node.id, 0]));
  const outgoing = new Map(nodes.map((node) => [node.id, []]));
  for (const edge of edges) {
    incoming.set(edge.target, (incoming.get(edge.target) || 0) + 1);
    outgoing.get(edge.source)?.push(edge.target);
  }
  const level = new Map();
  const queue = nodes.filter((node) => (incoming.get(node.id) || 0) === 0).map((node) => node.id);
  for (const id of queue) level.set(id, 0);
  const pending = new Map(incoming);
  while (queue.length) {
    const id = queue.shift();
    const nextLevel = (level.get(id) || 0) + 1;
    for (const target of outgoing.get(id) || []) {
      level.set(target, Math.max(level.get(target) || 0, nextLevel));
      pending.set(target, (pending.get(target) || 1) - 1);
      if (pending.get(target) === 0) queue.push(target);
    }
  }
  const buckets = new Map();
  for (const node of nodes) {
    const depth = level.get(node.id) || 0;
    if (!buckets.has(depth)) buckets.set(depth, []);
    buckets.get(depth).push(node);
  }
  const positions = new Map();
  for (const [depth, bucket] of buckets) {
    bucket.forEach((node, index) => positions.set(node.id, { x: 35 + depth * 210, y: 30 + index * 95 }));
  }
  return positions;
}

function svgElement(name, attrs = {}) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
  return node;
}

function renderGraph() {
  const target = $("graph-canvas");
  target.replaceChildren();
  const graph = state.graph;
  if (!graph?.nodes?.length) {
    $("graph-caption").textContent = "Compile a mission to visualize the plan.";
    return;
  }
  $("graph-caption").textContent = `${graph.nodes.length} nodes // ${graph.edges.length} edges`;
  const positions = graphLayout(graph);
  let width = 600;
  let height = 380;
  for (const pos of positions.values()) {
    width = Math.max(width, pos.x + 190);
    height = Math.max(height, pos.y + 85);
  }
  const svg = svgElement("svg", { viewBox: `0 0 ${width} ${height}`, width, height, role: "img", "aria-label": "VECTIS execution graph" });
  const defs = svgElement("defs");
  const marker = svgElement("marker", { id: "arrow", markerWidth: 8, markerHeight: 8, refX: 7, refY: 3, orient: "auto", markerUnits: "strokeWidth" });
  marker.appendChild(svgElement("path", { d: "M0,0 L0,6 L7,3 z", fill: "rgba(111,152,149,.55)" }));
  defs.appendChild(marker);
  svg.appendChild(defs);

  for (const edge of graph.edges || []) {
    const from = positions.get(edge.source);
    const to = positions.get(edge.target);
    if (!from || !to) continue;
    const path = svgElement("path", {
      d: `M${from.x + 160},${from.y + 30} C${from.x + 185},${from.y + 30} ${to.x - 25},${to.y + 30} ${to.x},${to.y + 30}`,
      class: `graph-edge ${edge.kind}`,
      "marker-end": "url(#arrow)"
    });
    svg.appendChild(path);
    if (edge.kind !== "dependency") {
      const label = svgElement("text", { x: (from.x + to.x + 160) / 2, y: (from.y + to.y + 60) / 2 - 5, class: "graph-label" });
      label.textContent = edge.kind;
      svg.appendChild(label);
    }
  }

  const runtimeStates = new Map(state.runtime?.node_states || []);

  for (const node of graph.nodes) {
    const pos = positions.get(node.id);
    const runtimeState = runtimeStates.get(node.id) || "pending";
    const group = svgElement("g", {
      class: `graph-node ${runtimeState}`,
      transform: `translate(${pos.x},${pos.y})`
    });
    group.appendChild(svgElement("rect", { width: 160, height: 60 }));
    const title = svgElement("text", { x: 12, y: 25 });
    title.textContent = node.id;
    const kind = svgElement("text", { x: 12, y: 44, class: "kind" });
    kind.textContent = node.kind.toUpperCase();
    group.append(title, kind);
    svg.appendChild(group);
  }
  target.appendChild(svg);
}

function renderAll() {
  renderMetrics();
  renderDiagnostics();
  renderRuntime();
  renderGraph();
  $("plan-tab").textContent = jsonText(state.graph);
  $("ast-tab").textContent = jsonText(state.ast);
}

function applyPayload(payload) {
  state.graph = payload.executionGraph || null;
  state.runtime = payload.runtime || null;
  state.ast = payload.ast || null;
  state.diagnostics = payload.diagnostics || [];
  renderAll();
}

async function action(kind) {
  setRunState(kind.toUpperCase(), "neutral");
  try {
    const endpoint = kind === "run" ? "/api/run" : kind === "plan" ? "/api/plan" : "/api/check";
    const payload = await request(endpoint, sourceText());
    applyPayload(payload);
    if (kind === "run") {
      const ok = payload.runtime?.success === true;
      setRunState(ok ? "SUCCESS" : "FAILED", ok ? "success" : "failure");
      activateTab("runtime");
    } else {
      setRunState("VALID", "success");
      activateTab(kind === "plan" ? "plan" : "diagnostics");
    }
  } catch (error) {
    const payload = error.payload || {};
    state.diagnostics = payload.diagnostics || [{ severity: "error", message: error.message }];
    if (payload.executionGraph) state.graph = payload.executionGraph;
    renderAll();
    setRunState("ERROR", "failure");
    activateTab("diagnostics");
  }
}

async function formatSource() {
  try {
    const payload = await request("/api/format", sourceText());
    $("source").value = payload.source;
    updateLineNumbers();
    updateCursor();
    toast("Mission formatted");
  } catch (error) {
    toast(error.message);
  }
}

function activateTab(name) {
  document.querySelectorAll(".tab").forEach((node) => node.classList.toggle("active", node.dataset.tab === name));
  document.querySelectorAll(".tab-content").forEach((node) => node.classList.toggle("active", node.id === `${name}-tab`));
}

async function loadBootstrap() {
  try {
    const [health, examples, builtins] = await Promise.all([
      api("/api/health"), api("/api/examples"), api("/api/builtins")
    ]);
    $("server-dot").classList.add("online");
    $("server-status").textContent = "Local runtime online";
    $("version-pill").textContent = health.version;
    state.examples = examples.examples || [];
    const select = $("example-select");
    select.replaceChildren();
    for (const example of state.examples) {
      const option = document.createElement("option");
      option.value = example.id;
      option.textContent = example.title;
      select.appendChild(option);
    }
    if (state.examples.length) {
      $("source").value = state.examples[0].source;
      updateLineNumbers();
    }
    renderFunctions(builtins.builtins || []);
    await action("plan");
  } catch (error) {
    $("server-status").textContent = "Runtime unavailable";
    toast(error.message);
  }
}

function renderFunctions(functions) {
  const target = $("function-grid");
  target.replaceChildren();
  for (const item of functions) {
    const card = document.createElement("article");
    card.className = "function-card";
    const name = document.createElement("code");
    name.textContent = `${item.name}(…)`;
    const description = document.createElement("p");
    description.textContent = item.description;
    const arity = document.createElement("div");
    arity.className = "arity";
    arity.textContent = item.max_args == null ? `${item.min_args}+ args` : item.min_args === item.max_args ? `${item.min_args} arg${item.min_args === 1 ? "" : "s"}` : `${item.min_args}–${item.max_args} args`;
    card.append(name, description, arity);
    target.appendChild(card);
  }
}

function switchView(view) {
  $("workspace-view").classList.toggle("hidden", view !== "workspace");
  $("functions-view").classList.toggle("hidden", view !== "functions");
  document.querySelectorAll(".rail-button").forEach((node) => node.classList.toggle("active", node.dataset.view === view));
}

document.addEventListener("DOMContentLoaded", () => {
  const source = $("source");
  source.addEventListener("input", () => { updateLineNumbers(); updateCursor(); });
  source.addEventListener("scroll", updateLineNumbers);
  source.addEventListener("click", updateCursor);
  source.addEventListener("keyup", updateCursor);
  source.addEventListener("keydown", (event) => {
    if (event.key === "Tab") {
      event.preventDefault();
      const start = source.selectionStart;
      const end = source.selectionEnd;
      source.setRangeText("    ", start, end, "end");
      updateLineNumbers();
    }
    if (event.ctrlKey && event.key === "Enter") {
      event.preventDefault();
      action("run");
    }
    if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === "f") {
      event.preventDefault();
      formatSource();
    }
  });

  $("run-button").addEventListener("click", () => action("run"));
  $("check-button").addEventListener("click", () => action("check"));
  $("plan-button").addEventListener("click", () => action("plan"));
  $("format-button").addEventListener("click", formatSource);
  $("example-select").addEventListener("change", (event) => {
    const example = state.examples.find((item) => item.id === event.target.value);
    if (example) {
      source.value = example.source;
      updateLineNumbers();
      action("plan");
    }
  });
  document.querySelectorAll(".tab").forEach((node) => node.addEventListener("click", () => activateTab(node.dataset.tab)));
  document.querySelectorAll(".rail-button").forEach((node) => node.addEventListener("click", () => switchView(node.dataset.view)));
  renderAll();
  loadBootstrap();
});
