# GHOST FIVE // VECTIS
# Validates VECTIS declarations, references, functions, and type contracts before compilation.
"""Semantic analysis for VECTIS programs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

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
    ImportStatement,
    NamespaceDeclaration,
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
from vectis.action_contract import (
    ActionValueType,
    ValueSchema,
    standard_action_contract,
)
from vectis.diagnostic import (
    Diagnostic,
    DiagnosticCode,
    DiagnosticError,
    error_diagnostic,
)
from vectis.evaluator import BUILTINS
from vectis.function_identity import (
    ModuleFunctionId,
    ModuleFunctionScope,
)
from vectis.source_span import SourceSpan
from vectis.type_contracts import (
    TypeContract,
    common_type_contract,
    parse_type_contract,
)


FunctionKey = str | ModuleFunctionId


class SemanticError(DiagnosticError):
    """Compatibility exception for callers that require raised semantics."""

    def __init__(
        self,
        message: str,
        *,
        span: SourceSpan,
        code: DiagnosticCode = DiagnosticCode.SEM_TYPE_MISMATCH,
    ) -> None:
        super().__init__(
            error_diagnostic(
                code=code,
                message=message,
                span=span,
            )
        )


class ValueType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    LIST = "list"
    OBJECT = "object"
    UNKNOWN = "unknown"


_FUNCTION_TYPE_NAMES: dict[str, ValueType] = {
    "string": ValueType.STRING,
    "number": ValueType.NUMBER,
    "boolean": ValueType.BOOLEAN,
    "list": ValueType.LIST,
    "object": ValueType.OBJECT,
    "any": ValueType.UNKNOWN,
}


@dataclass(frozen=True, slots=True)
class SemanticResult:
    diagnostics: tuple[Diagnostic, ...]
    declarations: tuple[tuple[str, ValueType], ...]

    @property
    def ok(self) -> bool:
        return not self.diagnostics


_BUILTIN_RESULTS: dict[str, ValueType] = {
    "upper": ValueType.STRING,
    "lower": ValueType.STRING,
    "trim": ValueType.STRING,
    "length": ValueType.NUMBER,
    "concat": ValueType.STRING,
    "contains": ValueType.BOOLEAN,
    "starts_with": ValueType.BOOLEAN,
    "ends_with": ValueType.BOOLEAN,
    "capitalize": ValueType.STRING,
    "title": ValueType.STRING,
    "replace": ValueType.STRING,
    "repeat": ValueType.STRING,
    "clamp": ValueType.NUMBER,
    "between": ValueType.BOOLEAN,
    "if_else": ValueType.UNKNOWN,
    "all_true": ValueType.BOOLEAN,
    "any_true": ValueType.BOOLEAN,
    "count_true": ValueType.NUMBER,
    "average": ValueType.NUMBER,
    "percent": ValueType.NUMBER,
    "coalesce": ValueType.UNKNOWN,
    "abs": ValueType.NUMBER,
    "round": ValueType.NUMBER,
    "min": ValueType.NUMBER,
    "max": ValueType.NUMBER,
    "string": ValueType.STRING,
    "number": ValueType.NUMBER,
    "boolean": ValueType.BOOLEAN,
    "list": ValueType.LIST,
    "object": ValueType.OBJECT,
    "get": ValueType.UNKNOWN,
    "has": ValueType.BOOLEAN,
    "keys": ValueType.LIST,
    "values": ValueType.LIST,
    "size": ValueType.NUMBER,
    "all": ValueType.BOOLEAN,
    "any": ValueType.BOOLEAN,
}


class SemanticAnalyzer:
    def __init__(
        self,
        program: Program,
        *,
        function_scope: ModuleFunctionScope | None = None,
    ) -> None:
        if not isinstance(program, Program):
            raise TypeError("program must be Program")
        if (
            function_scope is not None
            and not isinstance(
                function_scope,
                ModuleFunctionScope,
            )
        ):
            raise TypeError(
                "function_scope must be ModuleFunctionScope or None"
            )
        self.program = program
        self.function_scope = function_scope
        self.declarations: dict[str, ValueType] = {}
        self.declaration_contracts: dict[str, TypeContract | None] = {}
        self.functions: dict[FunctionKey, FunctionDeclaration] = {}

    def _declaration_key(
        self,
        statement: FunctionDeclaration,
    ) -> FunctionKey:
        if self.function_scope is not None:
            identity = self.function_scope.declaration_id(
                statement.span
            )
            if identity is not None:
                return identity
        return statement.name

    def _call_key(
        self,
        expression: CallExpression,
    ) -> FunctionKey:
        if self.function_scope is not None:
            identity = self.function_scope.call_target(
                expression.span
            )
            if identity is not None:
                return identity
        if expression.qualifier is not None:
            return f"{expression.qualifier}.{expression.name}"
        return expression.name

    def _function_label(
        self,
        key: FunctionKey,
    ) -> str:
        if isinstance(key, ModuleFunctionId):
            return key.label
        return key

    def analyze(self) -> list[Diagnostic]:
        return list(self.result().diagnostics)

    def result(self) -> SemanticResult:
        self.declarations = {}
        self.declaration_contracts = {}
        self.functions = {}
        diagnostics = self._namespace_diagnostics()
        diagnostics.extend(
            self._collect_functions()
        )
        diagnostics.extend(
            self._function_cycle_diagnostics()
        )
        for statement in self.program.statements:
            diagnostics.extend(
                self._analyze_statement(
                    statement,
                    top_level=True,
                )
            )
        return SemanticResult(
            diagnostics=tuple(diagnostics),
            declarations=tuple(self.declarations.items()),
        )

    def _diagnostic(
        self,
        code: DiagnosticCode,
        message: str,
        span: SourceSpan,
    ) -> Diagnostic:
        return error_diagnostic(code=code, message=message, span=span)

    def _namespace_diagnostics(self) -> list[Diagnostic]:
        namespaces = tuple(
            statement
            for statement in self.program.statements
            if isinstance(statement, NamespaceDeclaration)
        )
        diagnostics: list[Diagnostic] = []
        if len(namespaces) > 1:
            diagnostics.append(
                self._diagnostic(
                    DiagnosticCode.SEM_IMPORT_RESOLUTION,
                    "duplicate namespace declaration in module",
                    namespaces[1].span,
                )
            )
        if (
            namespaces
            and self.program.statements
            and self.program.statements[0] is not namespaces[0]
        ):
            diagnostics.append(
                self._diagnostic(
                    DiagnosticCode.SEM_IMPORT_RESOLUTION,
                    "namespace declaration must be the first statement",
                    namespaces[0].span,
                )
            )
        return diagnostics

    def _collect_functions(self) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []

        for statement in self.program.statements:
            if not isinstance(
                statement,
                FunctionDeclaration,
            ):
                continue

            if statement.name in BUILTINS:
                diagnostics.append(
                    self._diagnostic(
                        DiagnosticCode.SEM_DUPLICATE_DECLARATION,
                        (
                            "Function name conflicts with built-in: "
                            f"{statement.name}"
                        ),
                        statement.span,
                    )
                )
                continue

            key = self._declaration_key(statement)
            if key in self.functions:
                diagnostics.append(
                    self._diagnostic(
                        DiagnosticCode.SEM_DUPLICATE_DECLARATION,
                        (
                            "Duplicate function declaration: "
                            f"{statement.name}"
                        ),
                        statement.span,
                    )
                )
                continue

            self.functions[key] = statement

            seen: set[str] = set()
            for parameter in statement.parameters:
                if parameter in seen:
                    diagnostics.append(
                        self._diagnostic(
                            DiagnosticCode.SEM_DUPLICATE_DECLARATION,
                            (
                                "Duplicate function parameter: "
                                f"{parameter}"
                            ),
                            statement.span,
                        )
                    )
                seen.add(parameter)

        return diagnostics

    def _called_user_functions(
        self,
        expression: Expression,
    ) -> tuple[FunctionKey, ...]:
        names: list[FunctionKey] = []

        def visit(current: Expression) -> None:
            if isinstance(current, CallExpression):
                key = self._call_key(current)
                if key in self.functions:
                    names.append(key)
                for argument in current.arguments:
                    visit(argument)
                return
            if isinstance(current, BinaryExpression):
                visit(current.left)
                visit(current.right)
                return
            if isinstance(current, UnaryExpression):
                visit(current.operand)
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

    def _function_cycle_diagnostics(
        self,
    ) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        state: dict[FunctionKey, int] = {
            name: 0
            for name in self.functions
        }
        stack: list[FunctionKey] = []
        reported: set[tuple[str, ...]] = set()

        def visit(name: FunctionKey) -> None:
            state[name] = 1
            stack.append(name)

            for target in self._called_user_functions(
                self.functions[name].body
            ):
                if state[target] == 0:
                    visit(target)
                    continue
                if state[target] != 1:
                    continue

                start = stack.index(target)
                cycle = tuple(
                    [
                        *stack[start:],
                        target,
                    ]
                )
                identity = tuple(
                    sorted(
                        {
                            self._function_label(item)
                            for item in cycle
                        }
                    )
                )
                if identity in reported:
                    continue
                reported.add(identity)
                diagnostics.append(
                    self._diagnostic(
                        DiagnosticCode.SEM_TYPE_MISMATCH,
                        (
                            "Recursive function cycle is not allowed: "
                            + " -> ".join(
                                self._function_label(item)
                                for item in cycle
                            )
                        ),
                        self.functions[name].span,
                    )
                )

            stack.pop()
            state[name] = 2

        for name in self.functions:
            if state[name] == 0:
                visit(name)

        return diagnostics

    def _value_type_for_contract(
        self,
        contract: TypeContract | None,
    ) -> ValueType:
        if contract is None or contract.name == "any":
            return ValueType.UNKNOWN
        return _FUNCTION_TYPE_NAMES.get(
            contract.name,
            ValueType.UNKNOWN,
        )

    def _contract_for_value_type(
        self,
        value_type: ValueType,
    ) -> TypeContract | None:
        if value_type is ValueType.UNKNOWN:
            return None
        return parse_type_contract(value_type.value)

    def _contracts_match(
        self,
        expected: TypeContract | None,
        actual: TypeContract | None,
    ) -> bool:
        if expected is None or expected.name == "any":
            return True
        if actual is None or actual.name == "any":
            return True
        if expected.name != actual.name:
            return False

        if expected.name == "list":
            if expected.item is None:
                return True
            if actual.item is None or actual.item.name == "any":
                return True
            return self._contracts_match(expected.item, actual.item)

        if expected.name == "object" and expected.fields:
            if not actual.fields:
                return True
            actual_fields = dict(actual.fields)
            for field_name, field_contract in expected.fields:
                if field_name not in actual_fields:
                    return False
                if not self._contracts_match(
                    field_contract,
                    actual_fields[field_name],
                ):
                    return False

        return True

    def _function_parameter_contracts(
        self,
        statement: FunctionDeclaration,
    ) -> tuple[TypeContract | None, ...]:
        annotations = (
            statement.parameter_types
            if statement.parameter_types
            else tuple(None for _parameter in statement.parameters)
        )
        return tuple(
            (
                None
                if annotation is None
                else parse_type_contract(annotation)
            )
            for annotation in annotations
        )

    def _function_parameter_types(
        self,
        statement: FunctionDeclaration,
    ) -> tuple[ValueType, ...]:
        return tuple(
            self._value_type_for_contract(contract)
            for contract in self._function_parameter_contracts(statement)
        )

    def _function_annotation_diagnostics(
        self,
        statement: FunctionDeclaration,
    ) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        annotations = (
            statement.parameter_types
            if statement.parameter_types
            else tuple(None for _parameter in statement.parameters)
        )

        for parameter, annotation in zip(
            statement.parameters,
            annotations,
            strict=True,
        ):
            if (
                annotation is not None
                and parse_type_contract(annotation) is None
            ):
                diagnostics.append(
                    self._diagnostic(
                        DiagnosticCode.SEM_TYPE_MISMATCH,
                        (
                            f"Unknown function type {annotation!r} "
                            f"for parameter {parameter!r}"
                        ),
                        statement.span,
                    )
                )

        if (
            statement.return_type is not None
            and parse_type_contract(statement.return_type) is None
        ):
            diagnostics.append(
                self._diagnostic(
                    DiagnosticCode.SEM_TYPE_MISMATCH,
                    (
                        "Unknown function return type: "
                        f"{statement.return_type}"
                    ),
                    statement.span,
                )
            )

        return diagnostics

    def _structured_contract_diagnostics(
        self,
        expression: Expression,
        expected: TypeContract,
        *,
        local_types: dict[str, TypeContract | None] | None,
        label: str,
    ) -> list[Diagnostic]:
        if expected.name == "list":
            if expected.item is None or expected.item.name == "any":
                return []

            if isinstance(expression, ListLiteral):
                items = expression.items
            elif (
                isinstance(expression, CallExpression)
                and expression.name == "list"
            ):
                items = expression.arguments
            else:
                return []

            diagnostics: list[Diagnostic] = []
            for index, item in enumerate(items):
                actual = self._infer_contract(
                    item,
                    local_types=local_types,
                )
                if not self._contracts_match(expected.item, actual):
                    diagnostics.append(
                        self._diagnostic(
                            DiagnosticCode.SEM_TYPE_MISMATCH,
                            (
                                f"{label}[{index}] must be "
                                f"{expected.item.render()}, not "
                                f"{actual.render() if actual is not None else 'unknown'}"
                            ),
                            item.span,
                        )
                    )
                    continue
                diagnostics.extend(
                    self._structured_contract_diagnostics(
                        item,
                        expected.item,
                        local_types=local_types,
                        label=f"{label}[{index}]",
                    )
                )
            return diagnostics

        if expected.name == "object" and expected.fields:
            if not isinstance(expression, ObjectLiteral):
                return []

            entries = dict(expression.entries)
            diagnostics: list[Diagnostic] = []
            for field_name, field_contract in expected.fields:
                item = entries.get(field_name)
                if item is None:
                    diagnostics.append(
                        self._diagnostic(
                            DiagnosticCode.SEM_TYPE_MISMATCH,
                            f"{label} requires field {field_name!r}",
                            expression.span,
                        )
                    )
                    continue

                actual = self._infer_contract(
                    item,
                    local_types=local_types,
                )
                field_label = f"{label}.{field_name}"
                if not self._contracts_match(field_contract, actual):
                    diagnostics.append(
                        self._diagnostic(
                            DiagnosticCode.SEM_TYPE_MISMATCH,
                            (
                                f"{field_label} must be "
                                f"{field_contract.render()}, not "
                                f"{actual.render() if actual is not None else 'unknown'}"
                            ),
                            item.span,
                        )
                    )
                    continue
                diagnostics.extend(
                    self._structured_contract_diagnostics(
                        item,
                        field_contract,
                        local_types=local_types,
                        label=field_label,
                    )
                )
            return diagnostics

        return []

    def _analyze_function(
        self,
        statement: FunctionDeclaration,
    ) -> list[Diagnostic]:
        diagnostics = self._function_annotation_diagnostics(statement)
        parameter_contracts = self._function_parameter_contracts(statement)
        local_types = dict(
            zip(
                statement.parameters,
                parameter_contracts,
                strict=True,
            )
        )
        diagnostics.extend(
            self._analyze_expression(
                statement.body,
                local_names=set(statement.parameters),
                local_types=local_types,
            )
        )

        if statement.return_type is not None:
            expected = parse_type_contract(statement.return_type)
            if expected is not None:
                actual = self._infer_contract(
                    statement.body,
                    local_types=local_types,
                    function_stack=(
                        self._declaration_key(statement),
                    ),
                )
                structured = self._structured_contract_diagnostics(
                    statement.body,
                    expected,
                    local_types=local_types,
                    label=f"Function {statement.name}() return value",
                )
                if structured:
                    diagnostics.extend(structured)
                elif not self._contracts_match(expected, actual):
                    diagnostics.append(
                        self._diagnostic(
                            DiagnosticCode.SEM_TYPE_MISMATCH,
                            (
                                f"Function {statement.name}() declares "
                                f"return type {expected.render()} "
                                "but body evaluates to "
                                f"{actual.render() if actual is not None else 'unknown'}"
                            ),
                            statement.body.span,
                        )
                    )

        return diagnostics

    def _declare(
        self,
        name: str,
        value_type: ValueType,
        span: SourceSpan,
        *,
        contract: TypeContract | None = None,
    ) -> list[Diagnostic]:
        if name in self.declarations:
            return [
                self._diagnostic(
                    DiagnosticCode.SEM_DUPLICATE_DECLARATION,
                    f"Duplicate declaration: {name}",
                    span,
                )
            ]
        self.declarations[name] = value_type
        self.declaration_contracts[name] = (
            contract
            if contract is not None
            else self._contract_for_value_type(value_type)
        )
        return []

    def _analyze_statement(
        self,
        statement: Statement,
        *,
        top_level: bool = False,
    ) -> list[Diagnostic]:
        if isinstance(statement, NamespaceDeclaration):
            if not top_level:
                return [
                    self._diagnostic(
                        DiagnosticCode.SEM_TYPE_MISMATCH,
                        (
                            "namespace declarations are only allowed "
                            "at program top level"
                        ),
                        statement.span,
                    )
                ]
            return []

        if isinstance(statement, ImportStatement):
            return [
                self._diagnostic(
                    DiagnosticCode.SEM_IMPORT_RESOLUTION,
                    (
                        "import declarations require module-aware "
                        "file compilation"
                    ),
                    statement.span,
                )
            ]

        if isinstance(statement, FunctionDeclaration):
            if not top_level:
                return [
                    self._diagnostic(
                        DiagnosticCode.SEM_TYPE_MISMATCH,
                        (
                            "function declarations are only allowed "
                            "at program top level"
                        ),
                        statement.span,
                    )
                ]
            return self._analyze_function(statement)

        if isinstance(statement, (Mission, Stage)):
            return self._analyze_block(statement.body)

        if isinstance(statement, (SourceDeclaration, LetDeclaration)):
            diagnostics = self._analyze_expression(statement.value)
            value_contract = self._infer_contract(statement.value)
            value_type = self._value_type_for_contract(value_contract)
            diagnostics.extend(
                self._declare(
                    statement.name,
                    value_type,
                    statement.span,
                    contract=value_contract,
                )
            )
            return diagnostics

        if isinstance(statement, AnalyzeDeclaration):
            diagnostics: list[Diagnostic] = []
            value_contract = None
            value_type = ValueType.UNKNOWN
            if statement.value is not None:
                diagnostics.extend(self._analyze_expression(statement.value))
                value_contract = self._infer_contract(statement.value)
                value_type = self._value_type_for_contract(value_contract)
            diagnostics.extend(
                self._declare(
                    statement.name,
                    value_type,
                    statement.span,
                    contract=value_contract,
                )
            )
            return diagnostics

        if isinstance(statement, ActionStatement):
            diagnostics = self._analyze_expression(
                statement.arguments
            )
            argument_type = self._infer_type(
                statement.arguments
            )
            if argument_type not in (
                ValueType.OBJECT,
                ValueType.UNKNOWN,
            ):
                diagnostics.append(
                    self._diagnostic(
                        DiagnosticCode.SEM_TYPE_MISMATCH,
                        "action input must evaluate to an object",
                        statement.arguments.span,
                    )
                )

            contract = standard_action_contract(
                statement.operation
            )
            result_type = ValueType.UNKNOWN
            if contract is not None:
                if statement.capability != contract.capability:
                    diagnostics.append(
                        self._diagnostic(
                            DiagnosticCode.SEM_ACTION_CONTRACT,
                            (
                                f"action {statement.operation!r} requires "
                                f"capability {contract.capability!r}"
                            ),
                            statement.span,
                        )
                    )
                if isinstance(
                    statement.arguments,
                    ObjectLiteral,
                ):
                    diagnostics.extend(
                        self._validate_action_expression(
                            statement.arguments,
                            contract.input_schema,
                            path=(
                                f"{statement.operation} input"
                            ),
                        )
                    )
                result_type = (
                    self._value_type_for_action_schema(
                        contract.result_schema
                    )
                )

            diagnostics.extend(
                self._declare(
                    statement.name,
                    result_type,
                    statement.span,
                )
            )
            return diagnostics

        if isinstance(statement, RequireStatement):
            return self._analyze_expression(statement.capability)
        if isinstance(statement, RequestStatement):
            return self._analyze_expression(statement.capability)
        if isinstance(statement, AssertStatement):
            diagnostics = self._analyze_expression(statement.condition)
            condition_type = self._infer_type(statement.condition)
            if condition_type not in (ValueType.BOOLEAN, ValueType.UNKNOWN):
                diagnostics.append(
                    self._diagnostic(
                        DiagnosticCode.SEM_TYPE_MISMATCH,
                        "assert condition must evaluate to boolean",
                        statement.condition.span,
                    )
                )
            return diagnostics
        if isinstance(statement, PublishStatement):
            return self._analyze_expression(statement.value)
        if isinstance(statement, ConfidenceStatement):
            diagnostics = self._analyze_expression(statement.value)
            value_type = self._infer_type(statement.value)
            if value_type not in (ValueType.NUMBER, ValueType.UNKNOWN):
                diagnostics.append(
                    self._diagnostic(
                        DiagnosticCode.SEM_TYPE_MISMATCH,
                        "confidence must evaluate to a number",
                        statement.value.span,
                    )
                )
            return diagnostics
        if isinstance(statement, CitationsStatement):
            diagnostics: list[Diagnostic] = []
            for value in statement.values:
                diagnostics.extend(self._analyze_expression(value))
            return diagnostics
        if isinstance(statement, WhenStatement):
            diagnostics = self._analyze_expression(statement.condition)
            condition_type = self._infer_type(statement.condition)
            if condition_type not in (ValueType.BOOLEAN, ValueType.UNKNOWN):
                diagnostics.append(
                    self._diagnostic(
                        DiagnosticCode.SEM_TYPE_MISMATCH,
                        "when condition must evaluate to boolean",
                        statement.condition.span,
                    )
                )
            diagnostics.extend(self._analyze_block(statement.body))
            if statement.otherwise is not None:
                diagnostics.extend(self._analyze_block(statement.otherwise))
            return diagnostics

        return [
            self._diagnostic(
                DiagnosticCode.SEM_TYPE_MISMATCH,
                f"Unhandled statement type: {type(statement).__name__}",
                statement.span,
            )
        ]

    def _analyze_block(self, block: Block) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for statement in block.statements:
            diagnostics.extend(self._analyze_statement(statement))
        return diagnostics

    def _analyze_expression(
        self,
        expression: Expression,
        *,
        local_names: set[str] | None = None,
        local_types: dict[str, TypeContract | None] | None = None,
    ) -> list[Diagnostic]:
        if isinstance(expression, Reference):
            known = (
                expression.name in local_names
                if local_names is not None
                else expression.name in self.declarations
            )
            if not known:
                message = (
                    (
                        "Function body may reference only parameters: "
                        f"{expression.name}"
                    )
                    if local_names is not None
                    else f"Undeclared reference: {expression.name}"
                )
                return [
                    self._diagnostic(
                        DiagnosticCode.SEM_UNDECLARED_REFERENCE,
                        message,
                        expression.span,
                    )
                ]
            return []

        if isinstance(expression, CallExpression):
            diagnostics: list[Diagnostic] = []
            builtin = (
                BUILTINS.get(expression.name)
                if expression.qualifier is None
                else None
            )
            user_function = self.functions.get(
                self._call_key(expression)
            )
            count = len(expression.arguments)

            if builtin is not None:
                if count < builtin.min_args or (
                    builtin.max_args is not None
                    and count > builtin.max_args
                ):
                    diagnostics.append(
                        self._diagnostic(
                            DiagnosticCode.SEM_INVALID_ARITY,
                            (
                                "Invalid argument count for "
                                f"{expression.name}()"
                            ),
                            expression.span,
                        )
                    )
            elif user_function is not None:
                if count != len(
                    user_function.parameters
                ):
                    diagnostics.append(
                        self._diagnostic(
                            DiagnosticCode.SEM_INVALID_ARITY,
                            (
                                "Invalid argument count for "
                                f"{expression.name}()"
                            ),
                            expression.span,
                        )
                    )

                expected_contracts = self._function_parameter_contracts(
                    user_function
                )
                for position, (argument, expected) in enumerate(
                    zip(expression.arguments, expected_contracts),
                    start=1,
                ):
                    if expected is None or expected.name == "any":
                        continue
                    actual = self._infer_contract(
                        argument,
                        local_types=local_types,
                    )
                    label = (
                        f"Argument {position} to {expression.name}()"
                    )
                    structured = self._structured_contract_diagnostics(
                        argument,
                        expected,
                        local_types=local_types,
                        label=label,
                    )
                    if structured:
                        diagnostics.extend(structured)
                    elif not self._contracts_match(expected, actual):
                        diagnostics.append(
                            self._diagnostic(
                                DiagnosticCode.SEM_TYPE_MISMATCH,
                                (
                                    f"{label} must be {expected.render()}, "
                                    "not "
                                    f"{actual.render() if actual is not None else 'unknown'}"
                                ),
                                argument.span,
                            )
                        )
            else:
                diagnostics.append(
                    self._diagnostic(
                        DiagnosticCode.SEM_UNKNOWN_FUNCTION,
                        f"Unknown function: {expression.name}",
                        expression.span,
                    )
                )

            if (
                expression.qualifier is None
                and expression.name == "get"
                and len(expression.arguments) >= 2
                and isinstance(expression.arguments[1], StringLiteral)
            ):
                target = self._infer_contract(
                    expression.arguments[0],
                    local_types=local_types,
                )
                if (
                    target is not None
                    and target.name == "object"
                    and target.fields
                    and target.field(expression.arguments[1].value) is None
                ):
                    diagnostics.append(
                        self._diagnostic(
                            DiagnosticCode.SEM_TYPE_MISMATCH,
                            (
                                "Object contract has no field "
                                f"{expression.arguments[1].value!r}"
                            ),
                            expression.span,
                        )
                    )

            for argument in expression.arguments:
                diagnostics.extend(
                    self._analyze_expression(
                        argument,
                        local_names=local_names,
                        local_types=local_types,
                    )
                )
            return diagnostics

        if isinstance(expression, BinaryExpression):
            return [
                *self._analyze_expression(
                    expression.left,
                    local_names=local_names,
                    local_types=local_types,
                ),
                *self._analyze_expression(
                    expression.right,
                    local_names=local_names,
                    local_types=local_types,
                ),
            ]

        if isinstance(expression, ListLiteral):
            diagnostics: list[Diagnostic] = []
            for item in expression.items:
                diagnostics.extend(
                    self._analyze_expression(
                        item,
                        local_names=local_names,
                        local_types=local_types,
                    )
                )
            return diagnostics

        if isinstance(expression, ObjectLiteral):
            diagnostics: list[Diagnostic] = []
            seen: set[str] = set()
            for key, item in expression.entries:
                if key in seen:
                    diagnostics.append(
                        self._diagnostic(
                            DiagnosticCode.SEM_DUPLICATE_DECLARATION,
                            f"Duplicate object member: {key}",
                            expression.span,
                        )
                    )
                seen.add(key)
                diagnostics.extend(
                    self._analyze_expression(
                        item,
                        local_names=local_names,
                        local_types=local_types,
                    )
                )
            return diagnostics

        if isinstance(expression, MemberAccess):
            diagnostics = self._analyze_expression(
                expression.target,
                local_names=local_names,
                local_types=local_types,
            )
            target = self._infer_contract(
                expression.target,
                local_types=local_types,
            )
            if (
                target is not None
                and target.name == "object"
                and target.fields
                and target.field(expression.member) is None
            ):
                diagnostics.append(
                    self._diagnostic(
                        DiagnosticCode.SEM_TYPE_MISMATCH,
                        (
                            "Object contract has no field "
                            f"{expression.member!r}"
                        ),
                        expression.span,
                    )
                )
            return diagnostics

        if isinstance(expression, IndexAccess):
            diagnostics = [
                *self._analyze_expression(
                    expression.target,
                    local_names=local_names,
                    local_types=local_types,
                ),
                *self._analyze_expression(
                    expression.index,
                    local_names=local_names,
                    local_types=local_types,
                ),
            ]
            target = self._infer_contract(
                expression.target,
                local_types=local_types,
            )
            if (
                target is not None
                and target.name == "object"
                and target.fields
                and isinstance(expression.index, StringLiteral)
                and target.field(expression.index.value) is None
            ):
                diagnostics.append(
                    self._diagnostic(
                        DiagnosticCode.SEM_TYPE_MISMATCH,
                        (
                            "Object contract has no field "
                            f"{expression.index.value!r}"
                        ),
                        expression.span,
                    )
                )
            return diagnostics

        if isinstance(expression, UnaryExpression):
            return self._analyze_expression(
                expression.operand,
                local_names=local_names,
                local_types=local_types,
            )

        if isinstance(
            expression,
            (StringLiteral, NumberLiteral, BooleanLiteral),
        ):
            return []

        return [
            self._diagnostic(
                DiagnosticCode.SEM_TYPE_MISMATCH,
                f"Unhandled expression type: {type(expression).__name__}",
                expression.span,
            )
        ]

    def _value_type_for_action_schema(
        self,
        schema: ValueSchema,
    ) -> ValueType:
        mapping = {
            ActionValueType.STRING: ValueType.STRING,
            ActionValueType.NUMBER: ValueType.NUMBER,
            ActionValueType.BOOLEAN: ValueType.BOOLEAN,
            ActionValueType.LIST: ValueType.LIST,
            ActionValueType.OBJECT: ValueType.OBJECT,
            ActionValueType.ANY: ValueType.UNKNOWN,
        }
        return mapping[schema.value_type]

    def _validate_action_expression(
        self,
        expression: Expression,
        schema: ValueSchema,
        *,
        path: str,
    ) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        expected = self._value_type_for_action_schema(
            schema
        )
        actual = self._infer_type(expression)

        if (
            expected is not ValueType.UNKNOWN
            and actual is not ValueType.UNKNOWN
            and actual is not expected
        ):
            return [
                self._diagnostic(
                    DiagnosticCode.SEM_ACTION_CONTRACT,
                    (
                        f"{path} must be "
                        f"{schema.value_type.value}, "
                        f"not {actual.value}"
                    ),
                    expression.span,
                )
            ]

        if isinstance(expression, ListLiteral):
            if schema.item is not None:
                for index, item in enumerate(
                    expression.items
                ):
                    diagnostics.extend(
                        self._validate_action_expression(
                            item,
                            schema.item,
                            path=f"{path}[{index}]",
                        )
                    )
            return diagnostics

        if isinstance(expression, ObjectLiteral):
            fields = {
                field.name: field
                for field in schema.fields
            }
            entries = dict(expression.entries)

            for field in schema.fields:
                if (
                    field.required
                    and field.name not in entries
                ):
                    diagnostics.append(
                        self._diagnostic(
                            DiagnosticCode.SEM_ACTION_CONTRACT,
                            (
                                f"{path} requires field "
                                f"{field.name!r}"
                            ),
                            expression.span,
                        )
                    )

            if (
                fields
                and not schema.allow_extra_fields
            ):
                for name in sorted(
                    set(entries) - set(fields)
                ):
                    diagnostics.append(
                        self._diagnostic(
                            DiagnosticCode.SEM_ACTION_CONTRACT,
                            (
                                f"{path} contains unsupported "
                                f"field {name!r}"
                            ),
                            expression.span,
                        )
                    )

            for name, item in expression.entries:
                field = fields.get(name)
                if field is not None:
                    diagnostics.extend(
                        self._validate_action_expression(
                            item,
                            field.schema,
                            path=f"{path}.{name}",
                        )
                    )
                elif schema.values is not None:
                    diagnostics.extend(
                        self._validate_action_expression(
                            item,
                            schema.values,
                            path=f"{path}.{name}",
                        )
                    )
            return diagnostics

        return diagnostics

    def _infer_function_contract(
        self,
        name: FunctionKey,
        *,
        stack: tuple[FunctionKey, ...] = (),
    ) -> TypeContract | None:
        if name in stack:
            return None

        function = self.functions.get(name)
        if function is None:
            return None

        if function.return_type is not None:
            return parse_type_contract(function.return_type)

        local_types = dict(
            zip(
                function.parameters,
                self._function_parameter_contracts(function),
                strict=True,
            )
        )
        return self._infer_contract(
            function.body,
            local_types=local_types,
            function_stack=(*stack, name),
        )

    def _infer_function_type(
        self,
        name: FunctionKey,
        *,
        stack: tuple[FunctionKey, ...] = (),
    ) -> ValueType:
        return self._value_type_for_contract(
            self._infer_function_contract(name, stack=stack)
        )

    def _infer_contract(
        self,
        expression: Expression,
        *,
        local_types: dict[str, TypeContract | None] | None = None,
        function_stack: tuple[FunctionKey, ...] = (),
    ) -> TypeContract | None:
        if isinstance(expression, StringLiteral):
            return TypeContract("string")
        if isinstance(expression, NumberLiteral):
            return TypeContract("number")
        if isinstance(expression, BooleanLiteral):
            return TypeContract("boolean")
        if isinstance(expression, Reference):
            if local_types is not None:
                return local_types.get(expression.name)
            return self.declaration_contracts.get(expression.name)
        if isinstance(expression, CallExpression):
            if expression.qualifier is not None:
                return self._infer_function_contract(
                    self._call_key(expression),
                    stack=function_stack,
                )
            if expression.name == "list":
                items = tuple(
                    self._infer_contract(
                        item,
                        local_types=local_types,
                        function_stack=function_stack,
                    )
                    for item in expression.arguments
                )
                common = common_type_contract(items)
                if common is not None:
                    return TypeContract("list", common)
                return TypeContract("list", TypeContract("any"))
            if expression.name == "object":
                if len(expression.arguments) % 2 != 0:
                    return TypeContract("object")
                fields: list[tuple[str, TypeContract]] = []
                seen: set[str] = set()
                for index in range(0, len(expression.arguments), 2):
                    key = expression.arguments[index]
                    if not isinstance(key, StringLiteral):
                        return TypeContract("object")
                    if (
                        not key.value
                        or not (key.value[0].isalpha() or key.value[0] == "_")
                        or not all(
                            char.isalnum() or char == "_"
                            for char in key.value[1:]
                        )
                    ):
                        return TypeContract("object")
                    if key.value in seen:
                        return TypeContract("object")
                    seen.add(key.value)
                    value = self._infer_contract(
                        expression.arguments[index + 1],
                        local_types=local_types,
                        function_stack=function_stack,
                    )
                    fields.append(
                        (
                            key.value,
                            value if value is not None else TypeContract("any"),
                        )
                    )
                if fields:
                    return TypeContract("object", fields=tuple(fields))
                return TypeContract("object")
            if expression.name == "if_else" and len(expression.arguments) == 3:
                condition = expression.arguments[0]
                if isinstance(condition, BooleanLiteral):
                    selected = (
                        expression.arguments[1]
                        if condition.value
                        else expression.arguments[2]
                    )
                    return self._infer_contract(
                        selected,
                        local_types=local_types,
                        function_stack=function_stack,
                    )
                return common_type_contract(
                    tuple(
                        self._infer_contract(
                            item,
                            local_types=local_types,
                            function_stack=function_stack,
                        )
                        for item in expression.arguments[1:]
                    )
                )
            if expression.name == "coalesce" and expression.arguments:
                return common_type_contract(
                    tuple(
                        self._infer_contract(
                            item,
                            local_types=local_types,
                            function_stack=function_stack,
                        )
                        for item in expression.arguments
                    )
                )
            if expression.name == "keys":
                return TypeContract("list", TypeContract("string"))
            if expression.name == "values":
                target = (
                    self._infer_contract(
                        expression.arguments[0],
                        local_types=local_types,
                        function_stack=function_stack,
                    )
                    if expression.arguments
                    else None
                )
                if (
                    target is not None
                    and target.name == "object"
                    and target.fields
                ):
                    contracts = tuple(
                        contract
                        for _name, contract in target.fields
                    )
                    common = common_type_contract(contracts)
                    if common is not None:
                        return TypeContract("list", common)
                return TypeContract("list", TypeContract("any"))
            if expression.name == "get" and len(expression.arguments) >= 2:
                target = self._infer_contract(
                    expression.arguments[0],
                    local_types=local_types,
                    function_stack=function_stack,
                )
                if (
                    target is not None
                    and target.name == "object"
                    and isinstance(expression.arguments[1], StringLiteral)
                ):
                    field = target.field(expression.arguments[1].value)
                    if field is not None:
                        return field
                if (
                    target is not None
                    and target.name == "list"
                    and target.item is not None
                    and target.item.name != "any"
                ):
                    if len(expression.arguments) == 2:
                        return target.item
                    default = self._infer_contract(
                        expression.arguments[2],
                        local_types=local_types,
                        function_stack=function_stack,
                    )
                    return common_type_contract((target.item, default))
            if expression.name in _BUILTIN_RESULTS:
                return self._contract_for_value_type(
                    _BUILTIN_RESULTS[expression.name]
                )
            return self._infer_function_contract(
                self._call_key(expression),
                stack=function_stack,
            )
        if isinstance(expression, ListLiteral):
            items = tuple(
                self._infer_contract(
                    item,
                    local_types=local_types,
                    function_stack=function_stack,
                )
                for item in expression.items
            )
            common = common_type_contract(items)
            if common is not None:
                return TypeContract("list", common)
            return TypeContract("list", TypeContract("any"))
        if isinstance(expression, ObjectLiteral):
            fields: list[tuple[str, TypeContract]] = []
            seen: set[str] = set()
            for field_name, item in expression.entries:
                if field_name in seen:
                    return TypeContract("object")
                seen.add(field_name)
                contract = self._infer_contract(
                    item,
                    local_types=local_types,
                    function_stack=function_stack,
                )
                fields.append(
                    (
                        field_name,
                        contract if contract is not None else TypeContract("any"),
                    )
                )
            if not fields:
                return TypeContract("object")
            return TypeContract("object", fields=tuple(fields))
        if isinstance(expression, MemberAccess):
            target = self._infer_contract(
                expression.target,
                local_types=local_types,
                function_stack=function_stack,
            )
            if target is not None and target.name == "object":
                return target.field(expression.member)
            return None
        if isinstance(expression, IndexAccess):
            target = self._infer_contract(
                expression.target,
                local_types=local_types,
                function_stack=function_stack,
            )
            if (
                target is not None
                and target.name == "list"
                and target.item is not None
                and target.item.name != "any"
            ):
                return target.item
            if (
                target is not None
                and target.name == "object"
                and isinstance(expression.index, StringLiteral)
            ):
                return target.field(expression.index.value)
            return None
        if isinstance(expression, UnaryExpression):
            if expression.operator == "!":
                return TypeContract("boolean")
            return TypeContract("number")
        if isinstance(expression, BinaryExpression):
            if expression.operator in {
                "&&",
                "||",
                "==",
                "!=",
                ">",
                ">=",
                "<",
                "<=",
            }:
                return TypeContract("boolean")
            if expression.operator == "+":
                left = self._infer_contract(
                    expression.left,
                    local_types=local_types,
                    function_stack=function_stack,
                )
                right = self._infer_contract(
                    expression.right,
                    local_types=local_types,
                    function_stack=function_stack,
                )
                if (
                    left is not None
                    and right is not None
                    and left.name == "string"
                    and right.name == "string"
                ):
                    return TypeContract("string")
                if (
                    left is not None
                    and right is not None
                    and left.name == "number"
                    and right.name == "number"
                ):
                    return TypeContract("number")
                return None
            if expression.operator in {
                "-",
                "*",
                "/",
                "%",
            }:
                return TypeContract("number")
        return None

    def _infer_type(
        self,
        expression: Expression,
        *,
        local_types: dict[str, TypeContract | None] | None = None,
        function_stack: tuple[FunctionKey, ...] = (),
    ) -> ValueType:
        return self._value_type_for_contract(
            self._infer_contract(
                expression,
                local_types=local_types,
                function_stack=function_stack,
            )
        )


def analyze_result(
    program: Program,
    *,
    function_scope: ModuleFunctionScope | None = None,
) -> SemanticResult:
    return SemanticAnalyzer(
        program,
        function_scope=function_scope,
    ).result()


def analyze(
    program: Program,
    *,
    function_scope: ModuleFunctionScope | None = None,
) -> list[Diagnostic]:
    return SemanticAnalyzer(
        program,
        function_scope=function_scope,
    ).analyze()
