# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS runtime contract.
import unittest

from vectis.actions import ActionRegistry
from vectis.capabilities import Capability, CapabilityRegistry
from vectis.ir import (
    EdgeKind,
    ExecutionGraph,
    GraphEdge,
    GraphNode,
    NodeKind,
)
from vectis.runtime import (
    NodeState,
    Runtime,
    RuntimeResult,
)


class RuntimeTests(unittest.TestCase):
    def linear_graph(self) -> ExecutionGraph:
        return ExecutionGraph(
            nodes=(
                GraphNode(
                    id="source",
                    kind=NodeKind.SOURCE,
                    value="records",
                ),
                GraphNode(
                    id="analyze",
                    kind=NodeKind.ANALYZE,
                    value="analysis",
                ),
                GraphNode(
                    id="publish",
                    kind=NodeKind.PUBLISH,
                    value="result",
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

    def test_runtime_returns_public_result_contract(self):
        result = Runtime(
            ExecutionGraph()
        ).execute()

        self.assertIsInstance(
            result,
            RuntimeResult,
        )
        self.assertTrue(result.success)
        self.assertEqual(
            result.status,
            "success",
        )

    def test_deterministic_scheduling_uses_graph_order(self):
        graph = self.linear_graph()
        seen = []

        runtime = Runtime(
            graph,
            handlers={
                NodeKind.SOURCE:
                    lambda node: seen.append(node.id),
                NodeKind.ANALYZE:
                    lambda node: seen.append(node.id),
                NodeKind.PUBLISH:
                    lambda node: seen.append(node.id),
            },
        )

        result = runtime.execute()

        self.assertTrue(result.success)
        self.assertEqual(
            result.execution_order,
            graph.topological_order(),
        )
        self.assertEqual(
            seen,
            [
                "source",
                "analyze",
                "publish",
            ],
        )

    def test_node_state_tracking_records_success(self):
        result = Runtime(
            self.linear_graph()
        ).execute()

        self.assertIs(
            result.state_for("source"),
            NodeState.SUCCEEDED,
        )
        self.assertIs(
            result.state_for("analyze"),
            NodeState.SUCCEEDED,
        )
        self.assertIs(
            result.state_for("publish"),
            NodeState.SUCCEEDED,
        )

    def test_failure_propagates_to_dependents(self):
        graph = self.linear_graph()

        def fail(_node):
            raise ValueError(
                "intentional failure"
            )

        result = Runtime(
            graph,
            handlers={
                NodeKind.ANALYZE: fail,
            },
        ).execute()

        self.assertFalse(result.success)

        self.assertIs(
            result.state_for("source"),
            NodeState.SUCCEEDED,
        )
        self.assertIs(
            result.state_for("analyze"),
            NodeState.FAILED,
        )
        self.assertIs(
            result.state_for("publish"),
            NodeState.BLOCKED,
        )

        self.assertIsNotNone(
            result.failure_for("analyze")
        )
        self.assertIsNotNone(
            result.failure_for("publish")
        )

    def test_dry_run_invokes_no_handlers(self):
        graph = self.linear_graph()
        called = []

        def handler(node):
            called.append(node.id)

        result = Runtime(
            graph,
            handlers={
                NodeKind.SOURCE: handler,
                NodeKind.ANALYZE: handler,
                NodeKind.PUBLISH: handler,
            },
            dry_run=True,
        ).execute()

        self.assertTrue(result.success)
        self.assertTrue(result.dry_run)
        self.assertEqual(called, [])

        self.assertEqual(
            result.execution_order,
            graph.topological_order(),
        )

        for node_id in graph.topological_order():
            self.assertIs(
                result.state_for(node_id),
                NodeState.DRY_RUN,
            )

    def test_true_condition_skips_false_branch(self):
        graph = ExecutionGraph(
            nodes=(
                GraphNode(
                    id="condition",
                    kind=NodeKind.CONDITION,
                    value=True,
                ),
                GraphNode(
                    id="true",
                    kind=NodeKind.PUBLISH,
                    value="selected",
                ),
                GraphNode(
                    id="false",
                    kind=NodeKind.PUBLISH,
                    value="not-selected",
                ),
            ),
            edges=(
                GraphEdge(
                    source="condition",
                    target="true",
                    kind=EdgeKind.TRUE_BRANCH,
                ),
                GraphEdge(
                    source="condition",
                    target="false",
                    kind=EdgeKind.FALSE_BRANCH,
                ),
            ),
        )

        result = Runtime(graph).execute()

        self.assertTrue(result.success)
        self.assertIs(
            result.state_for("condition"),
            NodeState.SUCCEEDED,
        )
        self.assertIs(
            result.state_for("true"),
            NodeState.SUCCEEDED,
        )
        self.assertIs(
            result.state_for("false"),
            NodeState.SKIPPED,
        )

    def test_false_condition_skips_true_branch(self):
        graph = ExecutionGraph(
            nodes=(
                GraphNode(
                    id="condition",
                    kind=NodeKind.CONDITION,
                    value=False,
                ),
                GraphNode(
                    id="true",
                    kind=NodeKind.PUBLISH,
                    value="not-selected",
                ),
                GraphNode(
                    id="false",
                    kind=NodeKind.PUBLISH,
                    value="selected",
                ),
            ),
            edges=(
                GraphEdge(
                    source="condition",
                    target="true",
                    kind=EdgeKind.TRUE_BRANCH,
                ),
                GraphEdge(
                    source="condition",
                    target="false",
                    kind=EdgeKind.FALSE_BRANCH,
                ),
            ),
        )

        result = Runtime(graph).execute()

        self.assertTrue(result.success)
        self.assertIs(
            result.state_for("true"),
            NodeState.SKIPPED,
        )
        self.assertIs(
            result.state_for("false"),
            NodeState.SUCCEEDED,
        )

    def test_unavailable_capability_is_denied(self):
        graph = ExecutionGraph(
            nodes=(
                GraphNode(
                    id="require",
                    kind=NodeKind.REQUIRE,
                    value="filesystem",
                ),
            ),
        )

        result = Runtime(graph).execute()

        self.assertFalse(result.success)
        self.assertIs(
            result.state_for("require"),
            NodeState.FAILED,
        )

        failure = result.failure_for(
            "require"
        )

        self.assertIsNotNone(failure)
        self.assertIn(
            "unavailable",
            failure.message,
        )

    def test_available_capability_is_accepted(self):
        registry = CapabilityRegistry()

        registry.declare_capability(
            Capability(
                name="filesystem",
                description=(
                    "Explicit test capability"
                ),
            )
        )

        graph = ExecutionGraph(
            nodes=(
                GraphNode(
                    id="require",
                    kind=NodeKind.REQUIRE,
                    value="filesystem",
                ),
            ),
        )

        result = Runtime(
            graph,
            capabilities=registry,
        ).execute()

        self.assertTrue(result.success)
        self.assertIs(
            result.state_for("require"),
            NodeState.SUCCEEDED,
        )

    def test_action_requires_capability_and_registered_handler(self):
        graph = ExecutionGraph(
            nodes=(
                GraphNode(
                    id="read",
                    kind=NodeKind.ACTION,
                    metadata=(
                        ("operation", "filesystem.read_text"),
                        ("capability", "filesystem"),
                        ("expression", '{path: "input.txt"}'),
                    ),
                ),
            ),
        )

        action_registry = ActionRegistry()
        action_registry.register(
            "filesystem.read_text",
            "filesystem",
            lambda arguments: "content",
        )

        denied = Runtime(
            graph,
            actions=action_registry,
        ).execute()
        self.assertFalse(denied.success)
        self.assertIn(
            "unavailable",
            denied.failure_for("read").message,
        )

        registry = CapabilityRegistry()
        registry.declare_capability(
            Capability(
                name="filesystem",
                description="Explicit test filesystem authority",
            )
        )

        unavailable = Runtime(
            graph,
            capabilities=registry,
        ).execute()
        self.assertFalse(unavailable.success)
        self.assertIn(
            "operation",
            unavailable.failure_for("read").message,
        )

        seen = []
        allowed_actions = ActionRegistry()
        allowed_actions.register(
            "filesystem.read_text",
            "filesystem",
            lambda arguments: (
                seen.append(arguments)
                or "content"
            ),
        )
        allowed = Runtime(
            graph,
            capabilities=registry,
            actions=allowed_actions,
        ).execute()
        self.assertTrue(allowed.success)
        self.assertEqual(
            seen,
            [{"path": "input.txt"}],
        )
        self.assertEqual(
            allowed.value_for("read"),
            "content",
        )

    def test_action_result_flows_to_dependents(self):
        registry = CapabilityRegistry()
        registry.declare_capability(
            Capability(
                name="test",
                description="Explicit test action authority",
            )
        )
        graph = ExecutionGraph(
            nodes=(
                GraphNode(
                    id="action_result",
                    kind=NodeKind.ACTION,
                    metadata=(
                        ("operation", "test.value"),
                        ("capability", "test"),
                        ("expression", "{}"),
                    ),
                ),
                GraphNode(
                    id="publish",
                    kind=NodeKind.PUBLISH,
                    metadata=(
                        ("expression", "action_result"),
                    ),
                ),
            ),
            edges=(
                GraphEdge(
                    source="action_result",
                    target="publish",
                ),
            ),
        )

        actions = ActionRegistry()
        actions.register(
            "test.value",
            "test",
            lambda _arguments: {"status": "ok"},
        )

        result = Runtime(
            graph,
            capabilities=registry,
            actions=actions,
        ).execute()

        self.assertTrue(result.success)
        self.assertEqual(
            result.value_for("publish"),
            {"status": "ok"},
        )

    def test_repeated_execution_is_deterministic(self):
        graph = self.linear_graph()

        first = Runtime(graph).execute()
        second = Runtime(graph).execute()

        self.assertEqual(
            first,
            second,
        )

    def test_unknown_result_node_raises_key_error(self):
        result = Runtime(
            ExecutionGraph()
        ).execute()

        with self.assertRaises(KeyError):
            result.state_for(
                "missing"
            )


    def test_assertion_failure_surfaces_explanation(self):
        graph = ExecutionGraph(
            nodes=(
                GraphNode(
                    id="assert:0001",
                    kind=NodeKind.ASSERT,
                    value=False,
                    metadata=(
                        (
                            "assertion_message",
                            "Readiness gate failed",
                        ),
                    ),
                ),
            ),
        )

        result = Runtime(graph).execute()

        self.assertFalse(result.success)
        failure = result.failure_for("assert:0001")
        self.assertIsNotNone(failure)
        self.assertIn(
            "Readiness gate failed",
            failure.message,
        )


if __name__ == "__main__":
    unittest.main()
