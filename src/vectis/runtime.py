# GHOST FIVE // VECTIS
# Executes validated VECTIS execution graphs in deterministic order.
"""Deterministic execution runtime for VECTIS execution graphs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping

from vectis.actions import ActionRegistry
from vectis.capabilities import CapabilityRegistry
from vectis.evaluator import (
    EvaluationError,
    Value,
    evaluate_expression,
    is_value,
)
from vectis.ir import EdgeKind, ExecutionGraph, GraphNode, NodeKind
from vectis.parser import ParserError, parse_expression


class NodeState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    DRY_RUN = "dry_run"


class RuntimeExecutionError(RuntimeError):
    """Raised when deterministic node execution cannot continue."""


@dataclass(frozen=True, slots=True)
class RuntimeFailure:
    node_id: str
    message: str


@dataclass(frozen=True, slots=True)
class RuntimeResult:
    success: bool
    dry_run: bool
    execution_order: tuple[str, ...]
    node_states: tuple[tuple[str, NodeState], ...]
    failures: tuple[RuntimeFailure, ...] = ()
    node_values: tuple[tuple[str, object], ...] = ()

    @property
    def status(self) -> str:
        return "success" if self.success else "failure"

    @property
    def states(self) -> dict[str, NodeState]:
        return dict(self.node_states)

    @property
    def values(self) -> dict[str, object]:
        return dict(self.node_values)

    def state_for(self, node_id: str) -> NodeState:
        for current_id, state in self.node_states:
            if current_id == node_id:
                return state
        raise KeyError(node_id)

    def value_for(self, node_id: str) -> object:
        for current_id, value in self.node_values:
            if current_id == node_id:
                return value
        raise KeyError(node_id)

    def failure_for(self, node_id: str) -> RuntimeFailure | None:
        for failure in self.failures:
            if failure.node_id == node_id:
                return failure
        return None


NodeHandler = Callable[[GraphNode], object]


class Runtime:
    """Execute an immutable VECTIS graph in canonical topological order."""

    def __init__(
        self,
        graph: ExecutionGraph,
        *,
        capabilities: CapabilityRegistry | None = None,
        handlers: Mapping[NodeKind, NodeHandler] | None = None,
        actions: ActionRegistry | None = None,
        dry_run: bool = False,
    ) -> None:
        if not isinstance(graph, ExecutionGraph):
            raise TypeError("Runtime.graph must be an ExecutionGraph")
        if capabilities is not None and not isinstance(
            capabilities,
            CapabilityRegistry,
        ):
            raise TypeError(
                "Runtime.capabilities must be a CapabilityRegistry or None"
            )
        if not isinstance(dry_run, bool):
            raise TypeError("Runtime.dry_run must be a bool")

        normalized_handlers: dict[NodeKind, NodeHandler] = {}
        if handlers is not None:
            for kind, handler in handlers.items():
                if not isinstance(kind, NodeKind):
                    raise TypeError(
                        "Runtime handler keys must be NodeKind values"
                    )
                if not callable(handler):
                    raise TypeError(
                        f"Runtime handler for {kind.value!r} must be callable"
                    )
                normalized_handlers[kind] = handler

        if actions is not None and not isinstance(
            actions,
            ActionRegistry,
        ):
            raise TypeError(
                "Runtime.actions must be an ActionRegistry or None"
            )

        self.graph = graph
        self.capabilities = capabilities
        self.handlers = normalized_handlers
        self.actions = actions
        self.dry_run = dry_run
        self._states: dict[str, NodeState] = {}
        self._values: dict[str, object] = {}
        self._expression_values: dict[str, Value] = {}
        self._failures: list[RuntimeFailure] = []
        self._execution_order: list[str] = []
        self._branch_edges: dict[str, tuple[object, ...]] = {}

    def execute(self) -> RuntimeResult:
        schedule = self.graph.topological_order()
        self._states = {node_id: NodeState.PENDING for node_id in schedule}
        self._values = {}
        self._expression_values = {}
        self._failures = []
        self._execution_order = []

        node_map = {
            node.id: node
            for node in self.graph.nodes
        }
        branch_lists: dict[str, list[object]] = {}
        for edge in self.graph.edges:
            if edge.kind in (
                EdgeKind.TRUE_BRANCH,
                EdgeKind.FALSE_BRANCH,
            ):
                branch_lists.setdefault(
                    edge.source,
                    [],
                ).append(edge)
        self._branch_edges = {
            node_id: tuple(edges)
            for node_id, edges in branch_lists.items()
        }

        if self.dry_run:
            for node_id in schedule:
                node = node_map[node_id]
                self._states[node_id] = NodeState.DRY_RUN
                self._values[node_id] = node.value
                self._execution_order.append(node_id)
            return self._result()

        if not self._check_graph_capabilities():
            for node_id in schedule:
                if self._states[node_id] is NodeState.PENDING:
                    self._states[node_id] = NodeState.BLOCKED
            return self._result()

        dependencies: dict[str, tuple[str, ...]] = {
            node_id: ()
            for node_id in schedule
        }
        dependency_lists: dict[str, list[str]] = {
            node_id: []
            for node_id in schedule
        }
        for edge in self.graph.edges:
            if edge.kind is EdgeKind.DEPENDENCY:
                dependency_lists[edge.target].append(edge.source)
        dependencies = {
            node_id: tuple(items)
            for node_id, items in dependency_lists.items()
        }

        for node_id in schedule:
            state = self._states[node_id]
            if state is not NodeState.PENDING:
                continue

            dependency_states = tuple(
                self._states[dependency_id]
                for dependency_id in dependencies[node_id]
            )

            if any(
                dependency_state in (NodeState.FAILED, NodeState.BLOCKED)
                for dependency_state in dependency_states
            ):
                self._states[node_id] = NodeState.BLOCKED
                self._failures.append(
                    RuntimeFailure(
                        node_id=node_id,
                        message="Blocked by failed dependency",
                    )
                )
                continue

            if any(
                dependency_state is NodeState.SKIPPED
                for dependency_state in dependency_states
            ):
                self._states[node_id] = NodeState.SKIPPED
                continue

            node = node_map[node_id]
            self._states[node_id] = NodeState.RUNNING
            self._execution_order.append(node_id)

            try:
                resolved_value = self._resolve_node_value(node)
                self._check_node_capability(node, resolved_value)
                if node.kind is NodeKind.ASSERT:
                    if not isinstance(resolved_value, bool):
                        raise RuntimeExecutionError(
                            f"Assert node {node.id!r} did not produce a boolean value"
                        )
                    if not resolved_value:
                        assertion_message = self._metadata(
                            node,
                            "assertion_message",
                        )
                        detail = (
                            f": {assertion_message}"
                            if isinstance(assertion_message, str)
                            and assertion_message
                            else ""
                        )
                        raise RuntimeExecutionError(
                            f"Assertion failed at node {node.id!r}{detail}"
                        )
                value = self._execute_node(node, resolved_value)
                self._values[node_id] = value
                if is_value(value):
                    self._expression_values[node_id] = value
                self._states[node_id] = NodeState.SUCCEEDED

                if node.kind is NodeKind.CONDITION:
                    self._select_condition_branch(node, value)

            except Exception as exc:
                self._states[node_id] = NodeState.FAILED
                self._failures.append(
                    RuntimeFailure(
                        node_id=node_id,
                        message=f"{type(exc).__name__}: {exc}",
                    )
                )

        return self._result()

    def _check_graph_capabilities(self) -> bool:
        if self.capabilities is None:
            return True
        diagnostics = self.capabilities.check_capabilities(self.graph)
        if not diagnostics:
            return True
        for diagnostic in diagnostics:
            self._failures.append(
                RuntimeFailure(
                    node_id="<capability>",
                    message=str(diagnostic),
                )
            )
        return False

    def _metadata(self, node: GraphNode, key: str) -> object | None:
        for current_key, value in node.metadata:
            if current_key == key:
                return value
        return None

    def _resolve_node_value(self, node: GraphNode) -> object:
        expression_text = self._metadata(node, "expression")
        if not isinstance(expression_text, str) or not expression_text:
            return node.value

        try:
            expression = parse_expression(
                expression_text,
                file=f"<graph:{node.id}>",
            )
            return evaluate_expression(
                expression,
                self._expression_values,
            )
        except (EvaluationError, ParserError) as exc:
            if node.value is not None:
                return node.value
            raise RuntimeExecutionError(
                f"Unable to evaluate {node.id!r}: {exc}"
            ) from exc

    def _check_node_capability(
        self,
        node: GraphNode,
        resolved_value: object,
    ) -> None:
        if node.kind is NodeKind.ACTION:
            capability_name = self._metadata(
                node,
                "capability",
            )
        elif node.kind in (NodeKind.REQUIRE, NodeKind.REQUEST):
            capability_name = resolved_value
        else:
            return

        if not isinstance(capability_name, str) or not capability_name.strip():
            raise RuntimeExecutionError(
                f"{node.kind.value} node {node.id!r} "
                "does not identify a capability"
            )
        if (
            self.capabilities is None
            or not self.capabilities.has_capability(capability_name)
        ):
            raise RuntimeExecutionError(
                f"Capability {capability_name!r} is unavailable"
            )

    def _execute_node(
        self,
        node: GraphNode,
        resolved_value: object,
    ) -> object:
        if node.kind is NodeKind.ACTION:
            operation = self._metadata(
                node,
                "operation",
            )
            if not isinstance(operation, str) or not operation:
                raise RuntimeExecutionError(
                    f"Action node {node.id!r} does not identify an operation"
                )
            capability = self._metadata(
                node,
                "capability",
            )
            if not isinstance(capability, str) or not capability:
                raise RuntimeExecutionError(
                    f"Action node {node.id!r} does not identify a capability"
                )
            if self.actions is None:
                raise RuntimeExecutionError(
                    f"Action operation {operation!r} is unavailable"
                )
            return self.actions.execute(
                operation,
                capability,
                resolved_value,
            )

        handler = self.handlers.get(node.kind)
        if handler is None:
            return resolved_value
        return handler(node)

    def _select_condition_branch(
        self,
        node: GraphNode,
        value: object,
    ) -> None:
        if not isinstance(value, bool):
            raise RuntimeExecutionError(
                f"Condition node {node.id!r} did not produce a boolean value"
            )

        selected_kind = (
            EdgeKind.TRUE_BRANCH if value else EdgeKind.FALSE_BRANCH
        )

        for edge in self._branch_edges.get(node.id, ()):
            if edge.kind is selected_kind:
                continue
            if self._states.get(edge.target) is NodeState.PENDING:
                self._states[edge.target] = NodeState.SKIPPED

    def _result(self) -> RuntimeResult:
        schedule = self.graph.topological_order()
        failure_states = {NodeState.FAILED, NodeState.BLOCKED}
        success = not self._failures and not any(
            self._states[node_id] in failure_states
            for node_id in schedule
        )
        return RuntimeResult(
            success=success,
            dry_run=self.dry_run,
            execution_order=tuple(self._execution_order),
            node_states=tuple(
                (node_id, self._states[node_id])
                for node_id in schedule
            ),
            failures=tuple(self._failures),
            node_values=tuple(
                (node_id, self._values.get(node_id))
                for node_id in schedule
                if node_id in self._values
            ),
        )


DeterministicRuntime = Runtime
ExecutionResult = RuntimeResult
