# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS ir contract.
import unittest

from vectis.ir import (
    GRAPH_FORMAT_VERSION,
    EdgeKind,
    ExecutionGraph,
    GraphEdge,
    GraphNode,
    NodeKind,
)


class ExecutionGraphTests(unittest.TestCase):
    def test_graph_node_is_typed(self):
        node = GraphNode(
            id="source-1",
            kind=NodeKind.SOURCE,
        )

        self.assertEqual(
            node.kind,
            NodeKind.SOURCE,
        )

    def test_graph_node_accepts_stable_string_kind(self):
        node = GraphNode(
            id="publish-1",
            kind="publish",
        )

        self.assertIs(
            node.kind,
            NodeKind.PUBLISH,
        )

    def test_graph_edge_is_typed_dependency(self):
        edge = GraphEdge(
            source="a",
            target="b",
        )

        self.assertIs(
            edge.kind,
            EdgeKind.DEPENDENCY,
        )

    def test_unknown_edge_endpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            ExecutionGraph(
                nodes=(
                    GraphNode(
                        id="a",
                        kind=NodeKind.SOURCE,
                    ),
                ),
                edges=(
                    GraphEdge(
                        source="a",
                        target="missing",
                    ),
                ),
            )

    def test_duplicate_node_id_is_rejected(self):
        with self.assertRaises(ValueError):
            ExecutionGraph(
                nodes=(
                    GraphNode(
                        id="a",
                        kind=NodeKind.SOURCE,
                    ),
                    GraphNode(
                        id="a",
                        kind=NodeKind.ANALYZE,
                    ),
                ),
            )

    def test_cycle_is_rejected(self):
        with self.assertRaises(ValueError):
            ExecutionGraph(
                nodes=(
                    GraphNode(
                        id="a",
                        kind=NodeKind.SOURCE,
                    ),
                    GraphNode(
                        id="b",
                        kind=NodeKind.ANALYZE,
                    ),
                ),
                edges=(
                    GraphEdge(
                        source="a",
                        target="b",
                    ),
                    GraphEdge(
                        source="b",
                        target="a",
                    ),
                ),
            )

    def test_topological_order_is_deterministic(self):
        graph = ExecutionGraph(
            nodes=(
                GraphNode(
                    id="source",
                    kind=NodeKind.SOURCE,
                ),
                GraphNode(
                    id="analyze",
                    kind=NodeKind.ANALYZE,
                ),
                GraphNode(
                    id="publish",
                    kind=NodeKind.PUBLISH,
                ),
            ),
            edges=(
                GraphEdge(
                    source="source",
                    target="analyze",
                ),
                GraphEdge(
                    source="analyze",
                    target="publish",
                ),
            ),
        )

        self.assertEqual(
            graph.topological_order(),
            (
                "source",
                "analyze",
                "publish",
            ),
        )

    def test_dependency_query_is_explicit(self):
        graph = ExecutionGraph(
            nodes=(
                GraphNode(
                    id="source",
                    kind=NodeKind.SOURCE,
                ),
                GraphNode(
                    id="analyze",
                    kind=NodeKind.ANALYZE,
                ),
            ),
            edges=(
                GraphEdge(
                    source="source",
                    target="analyze",
                ),
            ),
        )

        self.assertEqual(
            graph.dependencies_of("analyze"),
            ("source",),
        )

    def test_conditional_edges_are_explicit(self):
        graph = ExecutionGraph(
            nodes=(
                GraphNode(
                    id="condition",
                    kind=NodeKind.CONDITION,
                ),
                GraphNode(
                    id="true-path",
                    kind=NodeKind.PUBLISH,
                ),
                GraphNode(
                    id="false-path",
                    kind=NodeKind.PUBLISH,
                ),
            ),
            edges=(
                GraphEdge(
                    source="condition",
                    target="true-path",
                    kind=EdgeKind.TRUE_BRANCH,
                ),
                GraphEdge(
                    source="condition",
                    target="false-path",
                    kind=EdgeKind.FALSE_BRANCH,
                ),
            ),
        )

        self.assertEqual(
            graph.successors_of("condition"),
            (
                "true-path",
                "false-path",
            ),
        )

    def test_serialization_round_trip(self):
        original = ExecutionGraph(
            nodes=(
                GraphNode(
                    id="source",
                    kind=NodeKind.SOURCE,
                    label="input",
                    value="example",
                    metadata=(
                        ("name", "records"),
                    ),
                ),
                GraphNode(
                    id="publish",
                    kind=NodeKind.PUBLISH,
                ),
            ),
            edges=(
                GraphEdge(
                    source="source",
                    target="publish",
                ),
            ),
        )

        restored = ExecutionGraph.from_json(
            original.to_json()
        )

        self.assertEqual(
            restored,
            original,
        )

    def test_structured_serialization_round_trip_preserves_value_model(self):
        original = ExecutionGraph(
            nodes=(
                GraphNode(
                    id="state",
                    kind=NodeKind.SOURCE,
                    value={
                        "checks": (True, False, True),
                        "metrics": {
                            "coverage": 94,
                        },
                    },
                ),
            ),
        )

        payload = original.to_dict()

        self.assertEqual(
            payload["version"],
            GRAPH_FORMAT_VERSION,
        )
        self.assertEqual(
            payload["nodes"][0]["value"]["checks"],
            [True, False, True],
        )

        restored = ExecutionGraph.from_json(
            original.to_json()
        )

        self.assertEqual(
            restored,
            original,
        )
        self.assertIsInstance(
            restored.node("state").value["checks"],
            tuple,
        )

    def test_unsupported_graph_version_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "unsupported execution graph version",
        ):
            ExecutionGraph.from_dict(
                {
                    "version": GRAPH_FORMAT_VERSION + 1,
                    "nodes": [],
                    "edges": [],
                }
            )

    def test_serialization_is_deterministic(self):
        graph = ExecutionGraph(
            nodes=(
                GraphNode(
                    id="a",
                    kind=NodeKind.SOURCE,
                ),
            ),
        )

        self.assertEqual(
            graph.to_json(),
            graph.to_json(),
        )


if __name__ == "__main__":
    unittest.main()
