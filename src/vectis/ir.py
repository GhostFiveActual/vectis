# GHOST FIVE // VECTIS
# Defines the execution graph intermediate representation and serialization contract.
from __future__ import annotations

import heapq
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeAlias


JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = (
    JsonScalar
    | tuple["JsonValue", ...]
    | list["JsonValue"]
    | dict[str, "JsonValue"]
)
GRAPH_FORMAT_VERSION = 1


def _normalize_json_value(value: Any) -> JsonValue:
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, (tuple, list)):
        return tuple(
            _normalize_json_value(item)
            for item in value
        )
    if isinstance(value, dict):
        normalized: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    "serialized object keys must be strings"
                )
            normalized[key] = _normalize_json_value(item)
        return normalized
    raise TypeError(
        "graph values must contain JSON-compatible VECTIS values"
    )


def _json_native_value(value: JsonValue) -> Any:
    if isinstance(value, tuple):
        return [
            _json_native_value(item)
            for item in value
        ]
    if isinstance(value, list):
        return [
            _json_native_value(item)
            for item in value
        ]
    if isinstance(value, dict):
        return {
            key: _json_native_value(item)
            for key, item in value.items()
        }
    return value


class NodeKind(str, Enum):
    MISSION = "mission"
    SOURCE = "source"
    VALUE = "value"
    ANALYZE = "analyze"
    ACTION = "action"
    REQUIRE = "require"
    REQUEST = "request"
    ASSERT = "assert"
    PUBLISH = "publish"
    CITATIONS = "citations"
    CONFIDENCE = "confidence"
    CONDITION = "condition"


class EdgeKind(str, Enum):
    DEPENDENCY = "dependency"
    TRUE_BRANCH = "true"
    FALSE_BRANCH = "false"


@dataclass(frozen=True, slots=True, kw_only=True)
class GraphNode:
    id: str
    kind: NodeKind
    label: str | None = None
    value: JsonValue = None
    metadata: tuple[tuple[str, JsonScalar], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("GraphNode.id must be a non-empty string")

        if isinstance(self.kind, str) and not isinstance(
            self.kind,
            NodeKind,
        ):
            object.__setattr__(
                self,
                "kind",
                NodeKind(self.kind),
            )

        if not isinstance(self.kind, NodeKind):
            raise TypeError("GraphNode.kind must be NodeKind")

        if self.label is not None and not isinstance(
            self.label,
            str,
        ):
            raise TypeError(
                "GraphNode.label must be str or None"
            )

        object.__setattr__(
            self,
            "value",
            _normalize_json_value(self.value),
        )

        if not isinstance(self.metadata, tuple):
            raise TypeError(
                "GraphNode.metadata must be a tuple"
            )

        seen: set[str] = set()

        for item in self.metadata:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
                or not isinstance(item[0], str)
                or not item[0]
            ):
                raise TypeError(
                    "GraphNode.metadata entries must be "
                    "(non-empty str, scalar) tuples"
                )

            key, value = item

            if key in seen:
                raise ValueError(
                    f"duplicate metadata key: {key}"
                )

            if not isinstance(
                value,
                (str, int, float, bool, type(None)),
            ):
                raise TypeError(
                    "GraphNode metadata values must be "
                    "JSON scalar values"
                )

            seen.add(key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "label": self.label,
            "value": _json_native_value(self.value),
            "metadata": {
                key: value
                for key, value in self.metadata
            },
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> GraphNode:
        metadata = data.get("metadata", {})

        if not isinstance(metadata, dict):
            raise TypeError(
                "GraphNode metadata must deserialize from object"
            )

        return cls(
            id=data["id"],
            kind=NodeKind(data["kind"]),
            label=data.get("label"),
            value=_normalize_json_value(data.get("value")),
            metadata=tuple(metadata.items()),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class GraphEdge:
    source: str
    target: str
    kind: EdgeKind = EdgeKind.DEPENDENCY

    def __post_init__(self) -> None:
        for name, value in (
            ("source", self.source),
            ("target", self.target),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"GraphEdge.{name} must be a non-empty string"
                )

        if isinstance(self.kind, str) and not isinstance(
            self.kind,
            EdgeKind,
        ):
            object.__setattr__(
                self,
                "kind",
                EdgeKind(self.kind),
            )

        if not isinstance(self.kind, EdgeKind):
            raise TypeError("GraphEdge.kind must be EdgeKind")

    def to_dict(self) -> dict[str, str]:
        return {
            "source": self.source,
            "target": self.target,
            "kind": self.kind.value,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> GraphEdge:
        return cls(
            source=data["source"],
            target=data["target"],
            kind=EdgeKind(
                data.get(
                    "kind",
                    EdgeKind.DEPENDENCY.value,
                )
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionGraph:
    nodes: tuple[GraphNode, ...] = ()
    edges: tuple[GraphEdge, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.nodes, tuple):
            raise TypeError(
                "ExecutionGraph.nodes must be a tuple"
            )

        if not isinstance(self.edges, tuple):
            raise TypeError(
                "ExecutionGraph.edges must be a tuple"
            )

        if not all(
            isinstance(node, GraphNode)
            for node in self.nodes
        ):
            raise TypeError(
                "ExecutionGraph.nodes must contain GraphNode"
            )

        if not all(
            isinstance(edge, GraphEdge)
            for edge in self.edges
        ):
            raise TypeError(
                "ExecutionGraph.edges must contain GraphEdge"
            )

        node_ids = [node.id for node in self.nodes]

        if len(node_ids) != len(set(node_ids)):
            raise ValueError(
                "ExecutionGraph node ids must be unique"
            )

        known = set(node_ids)
        edge_keys: set[
            tuple[str, str, EdgeKind]
        ] = set()

        for edge in self.edges:
            if edge.source not in known:
                raise ValueError(
                    f"edge source does not exist: {edge.source}"
                )

            if edge.target not in known:
                raise ValueError(
                    f"edge target does not exist: {edge.target}"
                )

            key = (
                edge.source,
                edge.target,
                edge.kind,
            )

            if key in edge_keys:
                raise ValueError(
                    "ExecutionGraph edges must be unique"
                )

            edge_keys.add(key)

        self.topological_order()

    def node(
        self,
        node_id: str,
    ) -> GraphNode:
        for node in self.nodes:
            if node.id == node_id:
                return node

        raise KeyError(node_id)

    def dependencies_of(
        self,
        node_id: str,
    ) -> tuple[str, ...]:
        self.node(node_id)

        return tuple(
            edge.source
            for edge in self.edges
            if (
                edge.target == node_id
                and edge.kind is EdgeKind.DEPENDENCY
            )
        )

    def successors_of(
        self,
        node_id: str,
    ) -> tuple[str, ...]:
        self.node(node_id)

        return tuple(
            edge.target
            for edge in self.edges
            if edge.source == node_id
        )

    def topological_order(
        self,
    ) -> tuple[str, ...]:
        """Return a deterministic topological order that scales to large graphs."""
        order = {
            node.id: index
            for index, node in enumerate(self.nodes)
        }

        indegree = {
            node.id: 0
            for node in self.nodes
        }

        outgoing: dict[str, list[str]] = {
            node.id: []
            for node in self.nodes
        }

        for edge in self.edges:
            indegree[edge.target] += 1
            outgoing[edge.source].append(edge.target)

        ready = [
            (order[node.id], node.id)
            for node in self.nodes
            if indegree[node.id] == 0
        ]
        heapq.heapify(ready)

        result: list[str] = []

        while ready:
            _position, current = heapq.heappop(ready)
            result.append(current)

            for target in outgoing[current]:
                indegree[target] -= 1
                if indegree[target] == 0:
                    heapq.heappush(
                        ready,
                        (order[target], target),
                    )

        if len(result) != len(self.nodes):
            raise ValueError(
                "ExecutionGraph must be acyclic"
            )

        return tuple(result)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": GRAPH_FORMAT_VERSION,
            "nodes": [
                node.to_dict()
                for node in self.nodes
            ],
            "edges": [
                edge.to_dict()
                for edge in self.edges
            ],
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> ExecutionGraph:
        if data.get("version") != GRAPH_FORMAT_VERSION:
            raise ValueError(
                "unsupported execution graph version"
            )

        raw_nodes = data.get("nodes")
        raw_edges = data.get("edges")

        if not isinstance(raw_nodes, list):
            raise TypeError(
                "serialized nodes must be a list"
            )

        if not isinstance(raw_edges, list):
            raise TypeError(
                "serialized edges must be a list"
            )

        return cls(
            nodes=tuple(
                GraphNode.from_dict(node)
                for node in raw_nodes
            ),
            edges=tuple(
                GraphEdge.from_dict(edge)
                for edge in raw_edges
            ),
        )

    @classmethod
    def from_json(
        cls,
        payload: str,
    ) -> ExecutionGraph:
        data = json.loads(payload)

        if not isinstance(data, dict):
            raise TypeError(
                "execution graph JSON must contain an object"
            )

        return cls.from_dict(data)
