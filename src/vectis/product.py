# GHOST FIVE // VECTIS
# Provides project scaffolding, graph exports, expression tools, and batch validation.

from __future__ import annotations

from collections import Counter
from pathlib import Path
import hashlib
import html
import json

from vectis.compiler import compile_program
from vectis.evaluator import Scalar, evaluate_expression
from vectis.ir import EdgeKind, ExecutionGraph, GraphNode, NodeKind
from vectis.modules import load_program_file
from vectis.parser import parse_expression
from vectis.runtime import RuntimeResult


BRAND_BLOCK = """<!-- ghost-five-brand:start -->
<div align="center">

**GHOST FIVE // VECTIS**

A language for turning what you intend to happen into a system that can prove how it will happen.

</div>
<!-- ghost-five-brand:end -->
"""


def evaluate_text(expression: str) -> Scalar:
    """Evaluate one pure VECTIS expression without creating a mission."""
    return evaluate_expression(
        parse_expression(expression, file="<cli-expression>"),
        {},
    )


def graph_fingerprint(graph: ExecutionGraph) -> str:
    """Return a stable SHA-256 fingerprint of the canonical graph JSON."""
    return hashlib.sha256(
        graph.to_json().encode("utf-8")
    ).hexdigest()


def node_stage_name(node: GraphNode) -> str | None:
    """Return the organizational stage attached to a graph node, if any."""
    for key, value in node.metadata:
        if key == "stage" and isinstance(value, str) and value:
            return value
    return None


def graph_summary(graph: ExecutionGraph) -> dict[str, object]:
    """Return deterministic structural metrics for an execution graph."""
    kinds = Counter(node.kind.value for node in graph.nodes)
    branch_edges = sum(
        1
        for edge in graph.edges
        if edge.kind in (EdgeKind.TRUE_BRANCH, EdgeKind.FALSE_BRANCH)
    )
    stages = tuple(
        dict.fromkeys(
            stage
            for node in graph.nodes
            if (stage := node_stage_name(node)) is not None
        )
    )
    order = graph.topological_order()

    predecessors: dict[str, list[str]] = {
        node.id: []
        for node in graph.nodes
    }
    successors: dict[str, list[str]] = {
        node.id: []
        for node in graph.nodes
    }

    # Build adjacency once so plan inspection stays linear in graph size.
    for edge in graph.edges:
        predecessors[edge.target].append(edge.source)
        successors[edge.source].append(edge.target)

    depth: dict[str, int] = {}
    for node_id in order:
        incoming = predecessors[node_id]
        depth[node_id] = (
            0
            if not incoming
            else max(depth[parent] for parent in incoming) + 1
        )

    widths = Counter(depth.values())
    max_depth = max(depth.values(), default=0)

    return {
        "nodes": len(graph.nodes),
        "edges": len(graph.edges),
        "branch_edges": branch_edges,
        "stage_count": len(stages),
        "stages": list(stages),
        "depth": max_depth,
        "levels": max_depth + 1 if graph.nodes else 0,
        "max_width": max(widths.values(), default=0),
        "max_fan_in": max(
            (len(predecessors[node.id]) for node in graph.nodes),
            default=0,
        ),
        "max_fan_out": max(
            (len(successors[node.id]) for node in graph.nodes),
            default=0,
        ),
        "sources": [
            node_id for node_id in order if not predecessors[node_id]
        ],
        "sinks": [
            node_id for node_id in order if not successors[node_id]
        ],
        "node_kinds": dict(sorted(kinds.items())),
        "fingerprint": graph_fingerprint(graph),
        "topological_order": list(order),
    }


def stage_manifest(graph: ExecutionGraph) -> tuple[dict[str, object], ...]:
    """Summarize deterministic node distribution across named stages."""
    order: list[str] = []
    buckets: dict[str, list[GraphNode]] = {}

    for node in graph.nodes:
        stage = node_stage_name(node) or "Mission"
        if stage not in buckets:
            order.append(stage)
            buckets[stage] = []
        buckets[stage].append(node)

    return tuple(
        {
            "name": stage,
            "nodes": len(buckets[stage]),
            "node_kinds": dict(
                sorted(
                    Counter(
                        node.kind.value
                        for node in buckets[stage]
                    ).items()
                )
            ),
        }
        for stage in order
    )


def capability_manifest(graph: ExecutionGraph) -> dict[str, object]:
    """Describe explicit capability statements and action authority in a plan."""
    required: list[str] = []
    requested: list[str] = []
    unresolved: list[str] = []
    actions: list[dict[str, str]] = []

    for node in graph.nodes:
        if node.kind is NodeKind.ACTION:
            metadata = dict(node.metadata)
            capability = metadata.get("capability")
            operation = metadata.get("operation")
            if (
                isinstance(capability, str)
                and capability.strip()
            ):
                if capability not in required:
                    required.append(capability)
            else:
                unresolved.append(node.id)

            if (
                isinstance(operation, str)
                and operation
                and isinstance(capability, str)
                and capability
            ):
                actions.append(
                    {
                        "node": node.id,
                        "operation": operation,
                        "capability": capability,
                    }
                )
            continue

        if node.kind not in (NodeKind.REQUIRE, NodeKind.REQUEST):
            continue

        target = required if node.kind is NodeKind.REQUIRE else requested
        if isinstance(node.value, str) and node.value.strip():
            if node.value not in target:
                target.append(node.value)
        else:
            unresolved.append(node.id)

    return {
        "required": required,
        "requested": requested,
        "all": sorted(set(required) | set(requested)),
        "actions": actions,
        "unresolved_nodes": unresolved,
    }


def plan_audit(graph: ExecutionGraph) -> dict[str, object]:
    """Return a complete deterministic pre-execution plan audit."""
    summary = graph_summary(graph)
    return {
        "fingerprint": summary["fingerprint"],
        "summary": summary,
        "stages": list(stage_manifest(graph)),
        "capabilities": capability_manifest(graph),
        "determinism": {
            "acyclic": True,
            "topological_nodes": len(summary["topological_order"]),
        },
    }


def execution_timeline(
    graph: ExecutionGraph,
    result: RuntimeResult,
) -> tuple[dict[str, object], ...]:
    """Group runtime state and values by deterministic graph level."""
    states = dict(result.node_states)
    values = dict(result.node_values)
    node_map = {node.id: node for node in graph.nodes}
    predecessors: dict[str, list[str]] = {
        node.id: []
        for node in graph.nodes
    }

    for edge in graph.edges:
        predecessors[edge.target].append(edge.source)

    levels: dict[str, int] = {}
    buckets: dict[int, list[dict[str, object]]] = {}

    for node_id in graph.topological_order():
        incoming = predecessors[node_id]
        level = (
            0
            if not incoming
            else max(levels[parent] for parent in incoming) + 1
        )
        levels[node_id] = level
        node = node_map[node_id]
        buckets.setdefault(level, []).append(
            {
                "id": node.id,
                "kind": node.kind.value,
                "stage": node_stage_name(node) or "Mission",
                "state": states[node_id].value,
                "value": values.get(node_id),
            }
        )

    return tuple(
        {
            "level": level,
            "nodes": tuple(buckets[level]),
        }
        for level in sorted(buckets)
    )


def enforce_graph_limits(
    graph: ExecutionGraph,
    *,
    max_nodes: int | None = None,
    max_edges: int | None = None,
    max_depth: int | None = None,
    max_width: int | None = None,
    max_fan_in: int | None = None,
    max_fan_out: int | None = None,
) -> dict[str, object]:
    """Validate a plan against explicit structural complexity limits."""
    summary = graph_summary(graph)
    limits = {
        "nodes": max_nodes,
        "edges": max_edges,
        "depth": max_depth,
        "max_width": max_width,
        "max_fan_in": max_fan_in,
        "max_fan_out": max_fan_out,
    }
    violations: list[str] = []

    for key, limit in limits.items():
        if limit is None:
            continue
        if limit < 1:
            raise ValueError(
                f"{key} limit must be greater than zero"
            )
        actual = int(summary[key])
        if actual > limit:
            violations.append(
                f"{key} {actual} exceeds configured maximum {limit}"
            )

    return {
        "ok": not violations,
        "summary": summary,
        "limits": limits,
        "violations": violations,
    }


def graph_to_dot(graph: ExecutionGraph) -> str:
    """Render an execution graph as Graphviz DOT without external packages."""
    lines = ["digraph vectis {", "  rankdir=LR;"]
    for node in graph.nodes:
        label = f"{node.id}\\n{node.kind.value}"
        lines.append(
            f"  {json.dumps(node.id)} "
            f"[label={json.dumps(label)}];"
        )
    for edge in graph.edges:
        lines.append(
            f"  {json.dumps(edge.source)} -> "
            f"{json.dumps(edge.target)} "
            f"[label={json.dumps(edge.kind.value)}];"
        )
    lines.append("}")
    return "\n".join(lines) + "\n"


def graph_to_mermaid(graph: ExecutionGraph) -> str:
    """Render an execution graph as Mermaid flowchart text."""
    lines = ["flowchart LR"]
    for node in graph.nodes:
        safe_id = _mermaid_id(node.id)
        label = f"{node.id} | {node.kind.value}".replace('"', "'")
        lines.append(f'    {safe_id}["{label}"]')
    for edge in graph.edges:
        lines.append(
            f"    {_mermaid_id(edge.source)} "
            f"-->|{edge.kind.value}| "
            f"{_mermaid_id(edge.target)}"
        )
    return "\n".join(lines) + "\n"


def _mermaid_id(value: str) -> str:
    """Convert a graph node identifier into a Mermaid safe identifier."""
    return "n_" + "".join(
        char if char.isalnum() else "_"
        for char in value
    )


def execution_report_html(
    graph: ExecutionGraph,
    result: RuntimeResult,
    *,
    mission_name: str,
    source_name: str,
) -> str:
    """Render a standalone execution report without external dependencies."""
    states = dict(result.node_states)
    values = dict(result.node_values)
    failures = {
        failure.node_id: failure.message
        for failure in result.failures
    }
    summary = graph_summary(graph)

    rows: list[str] = []
    for node in graph.nodes:
        state = states[node.id].value
        value = values.get(node.id, "")
        failure = failures.get(node.id, "")
        stage = node_stage_name(node) or "Mission"
        rows.append(
            "<tr>"
            f"<td>{html.escape(stage)}</td>"
            f"<td><code>{html.escape(node.id)}</code></td>"
            f"<td>{html.escape(node.kind.value)}</td>"
            f"<td><span class=\"state {html.escape(state)}\">"
            f"{html.escape(state.upper())}</span></td>"
            f"<td><code>{html.escape(json.dumps(value, ensure_ascii=False))}</code></td>"
            f"<td>{html.escape(failure)}</td>"
            "</tr>"
        )

    published = [
        values[node.id]
        for node in graph.nodes
        if node.kind.value == "publish"
        and node.id in values
        and states[node.id].value == "succeeded"
    ]
    published_html = "".join(
        f"<li><code>{html.escape(json.dumps(value, ensure_ascii=False))}</code></li>"
        for value in published
    ) or "<li>No published values.</li>"

    status = "COMPLETE" if result.success else "FAILED"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VECTIS Execution Report</title>
<style>
:root {{
  color-scheme: dark;
  font-family: Inter, ui-sans-serif, system-ui, sans-serif;
  background: #05090b;
  color: #e8f3f1;
  --teal: #4cc9c0;
  --line: rgba(76, 201, 192, .22);
  --panel: #0a1417;
  --muted: #8ca3a0;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: #05090b; }}
main {{ width: min(1320px, calc(100% - 32px)); margin: 0 auto; padding: 40px 0 64px; }}
header {{ border-bottom: 1px solid var(--line); padding-bottom: 24px; }}
.brand {{ color: var(--teal); font: 800 12px ui-monospace, monospace; letter-spacing: .14em; }}
h1 {{ margin: 8px 0; font-size: clamp(32px, 5vw, 58px); }}
.slogan, .muted {{ color: var(--muted); }}
.metrics {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 10px; margin: 24px 0; }}
.metric, section {{ border: 1px solid var(--line); background: var(--panel); border-radius: 12px; padding: 18px; }}
.metric span {{ display: block; color: var(--muted); font-size: 11px; }}
.metric strong {{ display: block; margin-top: 6px; font: 750 24px ui-monospace, monospace; }}
table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid var(--line); vertical-align: top; }}
th {{ color: var(--muted); }}
code {{ font-family: ui-monospace, Consolas, monospace; }}
.state {{ font: 800 10px ui-monospace, monospace; letter-spacing: .08em; }}
.state.succeeded {{ color: #63dba6; }}
.state.failed, .state.blocked {{ color: #ef7e7e; }}
.state.skipped {{ color: #d6b86e; }}
.state.dry_run {{ color: var(--teal); }}
@media (max-width: 760px) {{ .metrics {{ grid-template-columns: 1fr 1fr; }} }}
</style>
</head>
<body>
<main>
<header>
<div class="brand">GHOST FIVE // VECTIS</div>
<h1>Execution Report</h1>
<p class="slogan">A language for turning what you intend to happen into a system that can prove how it will happen.</p>
<p><strong>{html.escape(mission_name)}</strong><br><span class="muted">{html.escape(source_name)}</span></p>
</header>
<div class="metrics">
<div class="metric"><span>STATUS</span><strong>{status}</strong></div>
<div class="metric"><span>NODES</span><strong>{summary["nodes"]}</strong></div>
<div class="metric"><span>EDGES</span><strong>{summary["edges"]}</strong></div>
<div class="metric"><span>STAGES</span><strong>{summary["stage_count"]}</strong></div>
<div class="metric"><span>DEPTH</span><strong>{summary["depth"]}</strong></div>
<div class="metric"><span>FAILURES</span><strong>{len(result.failures)}</strong></div>
</div>
<section>
<h2>Plan Fingerprint</h2>
<code>{summary["fingerprint"]}</code>
</section>
<section>
<h2>Published Results</h2>
<ul>{published_html}</ul>
</section>
<section>
<h2>Execution Trace</h2>
<table>
<thead><tr><th>Stage</th><th>Node</th><th>Kind</th><th>State</th><th>Value</th><th>Failure</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
</section>
</main>
</body>
</html>
"""


def initialize_project(root: Path, *, force: bool = False) -> tuple[Path, ...]:
    """Create a small Ghost Five branded VECTIS project scaffold."""
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)

    files = {
        root / "README.md": (
            BRAND_BLOCK
            + "\n# VECTIS Project\n\n"
            + "## Purpose\n\n"
            + "This project was created with vectis init. "
            + "Put executable missions in the missions directory and "
            + "validate them with vectis test.\n"
        ),
        root / "vectis.toml": (
            "# GHOST FIVE // VECTIS\n"
            "# Project metadata for a VECTIS mission collection.\n"
            "[project]\n"
            'name = "vectis-project"\n'
            'mission_root = "missions"\n'
            "\n"
            "[packages.readiness]\n"
            'entry = "lib/readiness.vectis"\n'
        ),
        root / "actions.example.toml": (
            "# GHOST FIVE // VECTIS\n"
            "# Explicit action authority example. This file is never loaded automatically.\n"
            "[actions.filesystem]\n"
            'roots = ["."]\n'
        ),
        root / "lib" / "readiness.vectis": (
            "// GHOST FIVE // VECTIS\n"
            "// Reusable pure readiness functions for this project.\n"
            "function readiness_status(ready) {\n"
            '    return if_else(ready, "READY", "REVIEW");\n'
            "}\n"
        ),
        root / "missions" / "main.vectis": (
            "// GHOST FIVE // VECTIS\n"
            "// Primary mission created by vectis init.\n"
            'import package "readiness";\n'
            "\n"
            'mission "Primary mission" {\n'
            "    source ready true;\n"
            "    let status readiness.readiness_status(ready);\n"
            "\n"
            "    when ready {\n"
            "        publish status;\n"
            "    } otherwise {\n"
            '        request "manual-review";\n'
            "    }\n"
            "}\n"
        ),
    }

    created: list[Path] = []
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not force:
            raise FileExistsError(
                f"{path} already exists; use --force to replace scaffold files"
            )
        path.write_text(content, encoding="utf-8")
        created.append(path)

    return tuple(created)


def test_project(root: Path) -> dict[str, object]:
    """Compile every VECTIS file below a path and return deterministic results."""
    root = root.resolve()
    paths = (
        [root]
        if root.is_file()
        else sorted(root.rglob("*.vectis"))
    )

    records: list[dict[str, object]] = []
    passed = 0

    for path in paths:
        try:
            loaded = load_program_file(
                path,
                root=(
                    root
                    if root.is_dir()
                    else root.parent
                ),
            )
            result = compile_program(
                loaded.program,
                function_scope=loaded.function_scope,
            )
            ok = result.ok
            diagnostics = [
                diagnostic.to_dict()
                for diagnostic in result.diagnostics
            ]
        except Exception as exc:
            ok = False
            diagnostic = getattr(exc, "diagnostic", None)
            diagnostics = (
                [diagnostic.to_dict()]
                if diagnostic is not None
                else [{"message": f"{type(exc).__name__}: {exc}"}]
            )

        if ok:
            passed += 1

        records.append(
            {
                "file": str(path),
                "ok": ok,
                "diagnostics": diagnostics,
            }
        )

    return {
        "root": str(root),
        "files": len(records),
        "passed": passed,
        "failed": len(records) - passed,
        "results": records,
    }
