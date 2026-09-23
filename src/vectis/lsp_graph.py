# GHOST FIVE // VECTIS
# Builds deterministic read-only execution graph inspection payloads for editor clients.
"""Deterministic structural inspection for compiled VECTIS execution graphs."""

from __future__ import annotations

from vectis.ir import ExecutionGraph
from vectis.product import (
    capability_manifest,
    graph_summary,
    node_stage_name,
    stage_manifest,
)


GRAPH_INSPECTION_VERSION = 1


def graph_inspection(
    graph: ExecutionGraph,
) -> dict[str, object]:
    """Return a deterministic structural inspection without runtime values."""
    if not isinstance(graph, ExecutionGraph):
        raise TypeError("graph must be an ExecutionGraph")

    summary = graph_summary(graph)
    node_map = {node.id: node for node in graph.nodes}
    incoming: dict[str, list[dict[str, str]]] = {
        node.id: [] for node in graph.nodes
    }
    outgoing: dict[str, list[dict[str, str]]] = {
        node.id: [] for node in graph.nodes
    }

    for edge in graph.edges:
        incoming[edge.target].append(
            {"source": edge.source, "kind": edge.kind.value}
        )
        outgoing[edge.source].append(
            {"target": edge.target, "kind": edge.kind.value}
        )

    nodes: list[dict[str, object]] = []
    for node_id in graph.topological_order():
        node = node_map[node_id]
        nodes.append(
            {
                "id": node.id,
                "kind": node.kind.value,
                "label": node.label,
                "stage": node_stage_name(node) or "Mission",
                "dependencies": list(graph.dependencies_of(node.id)),
                "successors": list(graph.successors_of(node.id)),
                "incoming": list(incoming[node.id]),
                "outgoing": list(outgoing[node.id]),
                "metadata": {key: value for key, value in node.metadata},
            }
        )

    return {
        "version": GRAPH_INSPECTION_VERSION,
        "fingerprint": summary["fingerprint"],
        "summary": summary,
        "stages": list(stage_manifest(graph)),
        "capabilities": capability_manifest(graph),
        "nodes": nodes,
    }


__all__ = ["GRAPH_INSPECTION_VERSION", "graph_inspection"]
