# GHOST FIVE // VECTIS
# Compiles validated VECTIS syntax into a deterministic execution graph.
from __future__ import annotations

from dataclasses import dataclass, replace

from vectis.ast import (
    ActionStatement,
    AnalyzeDeclaration,
    AssertStatement,
    BinaryExpression,
    Block,
    BooleanLiteral,
    CallExpression,
    CitationsStatement,
    ConfidenceStatement,
    Expression,
    FunctionDeclaration,
    IndexAccess,
    LetDeclaration,
    ListLiteral,
    MemberAccess,
    Mission,
    NumberLiteral,
    ObjectLiteral,
    Program,
    PublishStatement,
    Reference,
    RequestStatement,
    RequireStatement,
    SourceDeclaration,
    Stage,
    Statement,
    StringLiteral,
    UnaryExpression,
    WhenStatement,
)
from vectis.diagnostic import Diagnostic
from vectis.evaluator import EvaluationError, Value, evaluate_expression
from vectis.formatter import format_expression
from vectis.ir import (
    EdgeKind,
    ExecutionGraph,
    GraphEdge,
    GraphNode,
    NodeKind,
)
from vectis.semantic import analyze as analyze_semantics


@dataclass(frozen=True, slots=True)
class CompileResult:
    graph: ExecutionGraph | None
    diagnostics: tuple[Diagnostic, ...] = ()

    @property
    def ok(self) -> bool:
        return self.graph is not None and not self.diagnostics


class CompilationError(ValueError):
    def __init__(self, diagnostics: tuple[Diagnostic, ...]) -> None:
        self.diagnostics = diagnostics
        message = "VECTIS compilation failed"
        if diagnostics:
            rendered = "; ".join(
                diagnostic.render()
                if hasattr(diagnostic, "render")
                else str(diagnostic)
                for diagnostic in diagnostics
            )
            message = f"{message}: {rendered}"
        super().__init__(message)


def _semantic_diagnostics(program: Program) -> tuple[Diagnostic, ...]:
    result = analyze_semantics(program)
    if result is None:
        return ()
    if isinstance(result, (list, tuple)):
        return tuple(result)
    diagnostics = getattr(result, "diagnostics", None)
    if diagnostics is not None:
        return tuple(diagnostics)
    raise TypeError(
        "vectis.semantic.analyze returned an unsupported result type"
    )


def _reference_names(expression: Expression) -> tuple[str, ...]:
    names: list[str] = []

    def visit(current: Expression) -> None:
        if isinstance(current, Reference):
            names.append(current.name)
            return
        if isinstance(current, UnaryExpression):
            visit(current.operand)
            return
        if isinstance(current, BinaryExpression):
            visit(current.left)
            visit(current.right)
            return
        if isinstance(current, CallExpression):
            for argument in current.arguments:
                visit(argument)
            return
        if isinstance(current, ListLiteral):
            for item in current.items:
                visit(item)
            return
        if isinstance(current, ObjectLiteral):
            for _key, item in current.entries:
                visit(item)
            return
        if isinstance(current, MemberAccess):
            visit(current.target)
            return
        if isinstance(current, IndexAccess):
            visit(current.target)
            visit(current.index)

    visit(expression)
    return tuple(dict.fromkeys(names))


class _GraphBuilder:
    def __init__(
        self,
        functions: dict[str, FunctionDeclaration],
    ) -> None:
        self.functions = dict(functions)
        self.nodes: list[GraphNode] = []
        self.edges: list[GraphEdge] = []
        self.node_ids: set[str] = set()
        self.edge_keys: set[tuple[str, str, EdgeKind]] = set()
        self.counters: dict[str, int] = {}
        self.known_values: dict[str, Value] = {}
        self.stage_stack: list[str] = []

    def build(self, program: Program) -> ExecutionGraph:
        for statement in program.statements:
            self._compile_statement(statement)
        return ExecutionGraph(
            nodes=tuple(self.nodes),
            edges=tuple(self.edges),
        )

    def _fresh_id(self, prefix: str) -> str:
        counter = self.counters.get(prefix, 0)
        while True:
            counter += 1
            candidate = f"{prefix}:{counter:04d}"
            if candidate not in self.node_ids:
                self.counters[prefix] = counter
                return candidate

    def _add_node(self, node: GraphNode) -> None:
        if node.id in self.node_ids:
            raise ValueError(f"duplicate compiler node id: {node.id}")
        self.node_ids.add(node.id)
        self.nodes.append(node)

    def _add_edge(
        self,
        source: str,
        target: str,
        kind: EdgeKind = EdgeKind.DEPENDENCY,
    ) -> None:
        key = (source, target, kind)
        if key in self.edge_keys:
            return
        self.edge_keys.add(key)
        self.edges.append(GraphEdge(source=source, target=target, kind=kind))

    def _substitute_expression(
        self,
        expression: Expression,
        bindings: dict[str, Expression],
    ) -> Expression:
        if isinstance(expression, Reference):
            return bindings.get(
                expression.name,
                expression,
            )
        if isinstance(expression, UnaryExpression):
            return replace(
                expression,
                operand=self._substitute_expression(
                    expression.operand,
                    bindings,
                ),
            )
        if isinstance(expression, BinaryExpression):
            return replace(
                expression,
                left=self._substitute_expression(
                    expression.left,
                    bindings,
                ),
                right=self._substitute_expression(
                    expression.right,
                    bindings,
                ),
            )
        if isinstance(expression, CallExpression):
            return replace(
                expression,
                arguments=tuple(
                    self._substitute_expression(
                        argument,
                        bindings,
                    )
                    for argument in expression.arguments
                ),
            )
        if isinstance(expression, ListLiteral):
            return replace(
                expression,
                items=tuple(
                    self._substitute_expression(
                        item,
                        bindings,
                    )
                    for item in expression.items
                ),
            )
        if isinstance(expression, ObjectLiteral):
            return replace(
                expression,
                entries=tuple(
                    (
                        key,
                        self._substitute_expression(
                            item,
                            bindings,
                        ),
                    )
                    for key, item in expression.entries
                ),
            )
        if isinstance(expression, MemberAccess):
            return replace(
                expression,
                target=self._substitute_expression(
                    expression.target,
                    bindings,
                ),
            )
        if isinstance(expression, IndexAccess):
            return replace(
                expression,
                target=self._substitute_expression(
                    expression.target,
                    bindings,
                ),
                index=self._substitute_expression(
                    expression.index,
                    bindings,
                ),
            )
        return expression

    def _expand_expression(
        self,
        expression: Expression,
        *,
        stack: tuple[str, ...] = (),
    ) -> Expression:
        if isinstance(expression, UnaryExpression):
            return replace(
                expression,
                operand=self._expand_expression(
                    expression.operand,
                    stack=stack,
                ),
            )

        if isinstance(expression, BinaryExpression):
            return replace(
                expression,
                left=self._expand_expression(
                    expression.left,
                    stack=stack,
                ),
                right=self._expand_expression(
                    expression.right,
                    stack=stack,
                ),
            )

        if isinstance(expression, ListLiteral):
            return replace(
                expression,
                items=tuple(
                    self._expand_expression(
                        item,
                        stack=stack,
                    )
                    for item in expression.items
                ),
            )

        if isinstance(expression, ObjectLiteral):
            return replace(
                expression,
                entries=tuple(
                    (
                        key,
                        self._expand_expression(
                            item,
                            stack=stack,
                        ),
                    )
                    for key, item in expression.entries
                ),
            )

        if isinstance(expression, MemberAccess):
            return replace(
                expression,
                target=self._expand_expression(
                    expression.target,
                    stack=stack,
                ),
            )

        if isinstance(expression, IndexAccess):
            return replace(
                expression,
                target=self._expand_expression(
                    expression.target,
                    stack=stack,
                ),
                index=self._expand_expression(
                    expression.index,
                    stack=stack,
                ),
            )

        if not isinstance(expression, CallExpression):
            return expression

        arguments = tuple(
            self._expand_expression(
                argument,
                stack=stack,
            )
            for argument in expression.arguments
        )
        function = self.functions.get(
            expression.name
        )

        if function is None:
            return replace(
                expression,
                arguments=arguments,
            )

        if expression.name in stack:
            raise ValueError(
                "recursive function expansion reached compiler"
            )

        bindings = dict(
            zip(
                function.parameters,
                arguments,
                strict=True,
            )
        )
        substituted = self._substitute_expression(
            function.body,
            bindings,
        )
        return self._expand_expression(
            substituted,
            stack=(*stack, expression.name),
        )

    def _add_expression_dependencies(
        self,
        expression: Expression,
        target: str,
    ) -> None:
        for name in _reference_names(expression):
            if name in self.node_ids:
                self._add_edge(name, target, EdgeKind.DEPENDENCY)

    def _try_value(self, expression: Expression) -> Value:
        try:
            return evaluate_expression(expression, self.known_values)
        except EvaluationError:
            return None

    def _stage_metadata(self) -> tuple[tuple[str, str], ...]:
        if not self.stage_stack:
            return ()
        return (("stage", " / ".join(self.stage_stack)),)

    def _expression_metadata(
        self,
        expression: Expression,
        *,
        source_expression: Expression | None = None,
    ):
        executable = format_expression(expression)
        metadata: list[
            tuple[str, str]
        ] = [
            ("expression", executable),
        ]

        if source_expression is not None:
            source = format_expression(
                source_expression
            )
            if source != executable:
                metadata.append(
                    ("source_expression", source)
                )

        metadata.extend(
            self._stage_metadata()
        )
        return tuple(metadata)

    def _compile_block(self, block: Block) -> tuple[str, ...]:
        created: list[str] = []
        assertion_guards: list[str] = []

        for statement in block.statements:
            statement_nodes = self._compile_statement(statement)

            for guard_id in assertion_guards:
                for node_id in statement_nodes:
                    if node_id != guard_id:
                        self._add_edge(
                            guard_id,
                            node_id,
                            EdgeKind.DEPENDENCY,
                        )

            created.extend(statement_nodes)

            if isinstance(statement, AssertStatement):
                assertion_guards.extend(statement_nodes)

        return tuple(created)

    def _compile_named_value(
        self,
        *,
        node_id: str,
        kind: NodeKind,
        expression: Expression,
    ) -> tuple[str, ...]:
        expanded = self._expand_expression(
            expression
        )
        value = self._try_value(expanded)
        self._add_node(
            GraphNode(
                id=node_id,
                kind=kind,
                label=node_id,
                value=value,
                metadata=self._expression_metadata(
                    expanded,
                    source_expression=expression,
                ),
            )
        )
        self._add_expression_dependencies(
            expanded,
            node_id,
        )
        if value is not None:
            self.known_values[node_id] = value
        return (node_id,)

    def _compile_statement(self, statement: Statement) -> tuple[str, ...]:
        if isinstance(statement, FunctionDeclaration):
            return ()

        if isinstance(statement, Mission):
            return self._compile_block(statement.body)

        if isinstance(statement, Stage):
            self.stage_stack.append(statement.name)
            try:
                return self._compile_block(statement.body)
            finally:
                self.stage_stack.pop()

        if isinstance(statement, SourceDeclaration):
            return self._compile_named_value(
                node_id=statement.name,
                kind=NodeKind.SOURCE,
                expression=statement.value,
            )

        if isinstance(statement, LetDeclaration):
            return self._compile_named_value(
                node_id=statement.name,
                kind=NodeKind.VALUE,
                expression=statement.value,
            )

        if isinstance(statement, AnalyzeDeclaration):
            node_id = statement.name
            metadata = self._stage_metadata()
            value = None
            expanded = None
            if statement.value is not None:
                expanded = self._expand_expression(
                    statement.value
                )
                value = self._try_value(expanded)
                metadata = self._expression_metadata(
                    expanded,
                    source_expression=statement.value,
                )
            self._add_node(
                GraphNode(
                    id=node_id,
                    kind=NodeKind.ANALYZE,
                    label=statement.name,
                    value=value,
                    metadata=metadata,
                )
            )
            if expanded is not None:
                self._add_expression_dependencies(
                    expanded,
                    node_id,
                )
            if value is not None:
                self.known_values[node_id] = value
            return (node_id,)

        if isinstance(statement, ActionStatement):
            expanded = self._expand_expression(
                statement.arguments
            )
            self._add_node(
                GraphNode(
                    id=statement.name,
                    kind=NodeKind.ACTION,
                    label=statement.operation,
                    value=None,
                    metadata=(
                        ("operation", statement.operation),
                        ("capability", statement.capability),
                        *self._expression_metadata(
                            expanded,
                            source_expression=statement.arguments,
                        ),
                    ),
                )
            )
            self._add_expression_dependencies(
                expanded,
                statement.name,
            )
            return (statement.name,)

        if isinstance(statement, RequireStatement):
            return self._compile_action(
                prefix="require",
                kind=NodeKind.REQUIRE,
                expression=statement.capability,
            )

        if isinstance(statement, RequestStatement):
            return self._compile_action(
                prefix="request",
                kind=NodeKind.REQUEST,
                expression=statement.capability,
            )

        if isinstance(statement, AssertStatement):
            assertion_metadata = (
                (("assertion_message", statement.message),)
                if statement.message is not None
                else ()
            )
            return self._compile_action(
                prefix="assert",
                kind=NodeKind.ASSERT,
                expression=statement.condition,
                metadata=assertion_metadata,
            )

        if isinstance(statement, PublishStatement):
            return self._compile_action(
                prefix="publish",
                kind=NodeKind.PUBLISH,
                expression=statement.value,
            )

        if isinstance(statement, ConfidenceStatement):
            return self._compile_action(
                prefix="confidence",
                kind=NodeKind.CONFIDENCE,
                expression=statement.value,
            )

        if isinstance(statement, CitationsStatement):
            node_id = self._fresh_id("citations")
            expanded_values = tuple(
                self._expand_expression(value)
                for value in statement.values
            )
            self._add_node(
                GraphNode(
                    id=node_id,
                    kind=NodeKind.CITATIONS,
                    label="citations",
                    metadata=(
                        ("count", len(statement.values)),
                        (
                            "values",
                            ", ".join(
                                format_expression(value)
                                for value in expanded_values
                            ),
                        ),
                        *self._stage_metadata(),
                    ),
                )
            )
            for value in expanded_values:
                self._add_expression_dependencies(
                    value,
                    node_id,
                )
            return (node_id,)

        if isinstance(statement, WhenStatement):
            condition_id = self._fresh_id("condition")
            condition = self._expand_expression(
                statement.condition
            )
            condition_value = self._try_value(
                condition
            )
            self._add_node(
                GraphNode(
                    id=condition_id,
                    kind=NodeKind.CONDITION,
                    label="when",
                    value=condition_value,
                    metadata=self._expression_metadata(
                        condition,
                        source_expression=statement.condition,
                    ),
                )
            )
            self._add_expression_dependencies(
                condition,
                condition_id,
            )

            true_nodes = self._compile_block(statement.body)
            false_nodes: tuple[str, ...] = ()
            if statement.otherwise is not None:
                false_nodes = self._compile_block(statement.otherwise)

            for node_id in true_nodes:
                self._add_edge(
                    condition_id,
                    node_id,
                    EdgeKind.TRUE_BRANCH,
                )
            for node_id in false_nodes:
                self._add_edge(
                    condition_id,
                    node_id,
                    EdgeKind.FALSE_BRANCH,
                )

            return (condition_id, *true_nodes, *false_nodes)

        raise TypeError(
            "unsupported VECTIS statement: "
            f"{type(statement).__name__}"
        )

    def _compile_action(
        self,
        *,
        prefix: str,
        kind: NodeKind,
        expression: Expression,
        metadata: tuple[tuple[str, str | int | float | bool | None], ...] = (),
    ) -> tuple[str, ...]:
        node_id = self._fresh_id(prefix)
        expanded = self._expand_expression(
            expression
        )
        value = self._try_value(expanded)
        self._add_node(
            GraphNode(
                id=node_id,
                kind=kind,
                label=prefix,
                value=value,
                metadata=(
                    *self._expression_metadata(
                        expanded,
                        source_expression=expression,
                    ),
                    *metadata,
                ),
            )
        )
        self._add_expression_dependencies(
            expanded,
            node_id,
        )
        return (node_id,)


def compile_program(program: Program) -> CompileResult:
    if not isinstance(program, Program):
        raise TypeError("compile_program requires a Program")

    diagnostics = _semantic_diagnostics(program)
    if diagnostics:
        return CompileResult(graph=None, diagnostics=diagnostics)

    functions = {
        statement.name: statement
        for statement in program.statements
        if isinstance(
            statement,
            FunctionDeclaration,
        )
    }
    graph = _GraphBuilder(
        functions
    ).build(program)
    return CompileResult(graph=graph, diagnostics=())


def compile_ast_to_execution_graph(program: Program) -> ExecutionGraph:
    result = compile_program(program)
    if not result.ok or result.graph is None:
        raise CompilationError(result.diagnostics)
    return result.graph
