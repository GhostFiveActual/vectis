# GHOST FIVE // VECTIS
# Parses the VECTIS token stream into the canonical typed syntax tree.
from __future__ import annotations

from dataclasses import replace

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
    IndexAccess,
    LetDeclaration,
    ListLiteral,
    MemberAccess,
    Mission,
    Stage,
    NumberLiteral,
    ObjectLiteral,
    Program,
    PublishStatement,
    Reference,
    RequestStatement,
    RequireStatement,
    SourceDeclaration,
    StringLiteral,
    UnaryExpression,
    WhenStatement,
)
from vectis.diagnostic import (
    DiagnosticCode,
    DiagnosticError,
    error_diagnostic,
    point_span,
)
from vectis.lexer import Lexer
from vectis.source_position import SourcePosition
from vectis.source_span import SourceSpan
from vectis.token import Token


class ParserError(DiagnosticError):
    pass


class Parser:
    _BINARY_LEVELS = (
        ("||",),
        ("&&",),
        ("==", "!="),
        (">", ">=", "<", "<="),
        ("+", "-"),
        ("*", "/", "%"),
    )
    _UNARY_OPERATORS = frozenset({"!", "+", "-"})

    def __init__(self, tokens: list[Token], *, file: str = "<memory>") -> None:
        if not isinstance(tokens, list):
            raise TypeError("tokens must be list[Token]")
        if not all(isinstance(token, Token) for token in tokens):
            raise TypeError("tokens must contain only Token instances")
        if not isinstance(file, str) or not file:
            raise ValueError("file must be a non-empty string")

        self.tokens = tokens
        self.file = file
        self.index = 0

    def parse_program(self) -> Program:
        statements = []

        while not self._at_end():
            statements.append(self._parse_statement())

        if statements:
            span = self._cover(statements[0].span, statements[-1].span)
        else:
            position = SourcePosition(line=1, column=1, file=self.file)
            span = SourceSpan(start=position, end=position)

        return Program(span=span, statements=tuple(statements))

    def parse_expression_only(self) -> Expression:
        expression = self._parse_expression()
        if not self._at_end():
            token = self._current()
            self._error(
                f"unexpected token after expression: {token.value!r}",
                token=token,
                code=DiagnosticCode.SYN_EXPECTED_TOKEN,
            )
        return expression

    def _parse_statement(self):
        token = self._current()

        if token is None:
            self._error(
                "expected statement",
                code=DiagnosticCode.SYN_EXPECTED_STATEMENT,
            )

        if (
            token.type == "identifier"
            and token.value == "private"
            and self.index + 1 < len(self.tokens)
            and self.tokens[self.index + 1].type == "keyword"
            and self.tokens[self.index + 1].value == "function"
        ):
            return self._parse_private_function()

        if token.type != "keyword":
            self._error(
                f"expected statement keyword, found {token.value!r}",
                token=token,
                code=DiagnosticCode.SYN_EXPECTED_STATEMENT,
            )

        if token.value == "otherwise":
            self._error(
                "'otherwise' may only follow a 'when' block",
                token=token,
                code=DiagnosticCode.SYN_STANDALONE_OTHERWISE,
            )

        dispatch = {
            "import": self._parse_import,
            "function": self._parse_function,
            "mission": self._parse_mission,
            "stage": self._parse_stage,
            "source": self._parse_source,
            "let": self._parse_let,
            "analyze": self._parse_analyze,
            "action": self._parse_action,
            "require": self._parse_require,
            "request": self._parse_request,
            "assert": self._parse_assert,
            "publish": self._parse_publish,
            "citations": self._parse_citations,
            "confidence": self._parse_confidence,
            "when": self._parse_when,
        }

        parser = dispatch.get(token.value)

        if parser is None:
            self._error(
                f"keyword {token.value!r} cannot begin a statement",
                token=token,
                code=DiagnosticCode.SYN_INVALID_STATEMENT_KEYWORD,
            )

        return parser()

    def _parse_import(self) -> ImportStatement:
        start = self._expect("keyword", "import")
        path = self._expect(
            "string",
            description="module path string",
        )
        names: tuple[str, ...] | None = None
        alias: str | None = None

        if self._match("punctuation", "{") is not None:
            selected: list[str] = []
            while True:
                name = self._expect(
                    "identifier",
                    description="imported function name",
                )
                if name.value in selected:
                    self._error(
                        (
                            "duplicate imported function name: "
                            f"{name.value}"
                        ),
                        token=name,
                        code=DiagnosticCode.SYN_EXPECTED_TOKEN,
                    )
                selected.append(name.value)

                if self._match("punctuation", "}") is not None:
                    break
                self._expect("punctuation", ",")

            names = tuple(selected)

        if self._match("identifier", "as") is not None:
            alias_token = self._expect(
                "identifier",
                description="module alias",
            )
            if alias_token.value in {"true", "false"}:
                self._error(
                    "module alias cannot use a boolean literal name",
                    token=alias_token,
                    code=DiagnosticCode.SYN_EXPECTED_TOKEN,
                )
            alias = alias_token.value

        end = self._expect("punctuation", ";")
        return ImportStatement(
            span=self._cover(start.span, end.span),
            path=path.value,
            names=names,
            alias=alias,
        )

    def _parse_type_annotation(self, *, description: str) -> str:
        name = self._expect(
            "identifier",
            description=description,
        ).value

        if self._match("punctuation", "[") is not None:
            item = self._parse_type_annotation(
                description="list item type",
            )
            self._expect("punctuation", "]")
            return f"{name}[{item}]"

        if (
            name == "object"
            and self._check("punctuation", "{")
            and self.index + 1 < len(self.tokens)
            and self.tokens[self.index + 1].type == "identifier"
        ):
            self._advance()
            fields: list[str] = []
            if not self._check("punctuation", "}"):
                while True:
                    field_name = self._expect(
                        "identifier",
                        description="object contract field",
                    ).value
                    self._expect("punctuation", ":")
                    field_type = self._parse_type_annotation(
                        description="object contract field type",
                    )
                    fields.append(f"{field_name}:{field_type}")
                    if self._match("punctuation", ",") is None:
                        break
            self._expect("punctuation", "}")
            return f"{name}{{{','.join(fields)}}}"

        return name

    def _parse_private_function(self) -> FunctionDeclaration:
        start = self._expect("identifier", "private")
        return self._parse_function(
            visibility="private",
            start=start,
        )

    def _parse_function(
        self,
        *,
        visibility: str = "public",
        start: Token | None = None,
    ) -> FunctionDeclaration:
        function_token = self._expect("keyword", "function")
        if start is None:
            start = function_token
        name = self._expect(
            "identifier",
            description="function name",
        )
        self._expect("punctuation", "(")
        parameters: list[str] = []
        parameter_types: list[str | None] = []

        if not self._check("punctuation", ")"):
            while True:
                parameter = self._expect(
                    "identifier",
                    description="function parameter",
                )
                parameters.append(parameter.value)

                annotation = None
                if self._match("punctuation", ":") is not None:
                    annotation = self._parse_type_annotation(
                        description="function parameter type",
                    )
                parameter_types.append(annotation)

                if self._match("punctuation", ",") is None:
                    break

        self._expect("punctuation", ")")

        return_type = None
        if self._match("punctuation", ":") is not None:
            return_type = self._parse_type_annotation(
                description="function return type",
            )

        self._expect("punctuation", "{")
        self._expect("keyword", "return")
        body = self._parse_expression()
        self._expect("punctuation", ";")
        closing = self._expect("punctuation", "}")

        parsed_parameter_types = tuple(parameter_types)
        if all(item is None for item in parsed_parameter_types):
            parsed_parameter_types = ()

        return FunctionDeclaration(
            span=self._cover(start.span, closing.span),
            name=name.value,
            parameters=tuple(parameters),
            body=body,
            parameter_types=parsed_parameter_types,
            return_type=return_type,
            visibility=visibility,
        )

    def _parse_mission(self) -> Mission:
        start = self._expect("keyword", "mission")
        name = self._expect("string", description="mission name string")
        body = self._parse_block()
        return Mission(
            span=self._cover(start.span, body.span),
            name=name.value,
            body=body,
        )

    def _parse_stage(self) -> Stage:
        start = self._expect("keyword", "stage")
        name = self._expect("string", description="stage name string")
        body = self._parse_block()
        return Stage(
            span=self._cover(start.span, body.span),
            name=name.value,
            body=body,
        )

    def _parse_source(self) -> SourceDeclaration:
        start = self._expect("keyword", "source")
        name = self._expect("identifier", description="source name")
        value = self._parse_expression()
        end = self._expect("punctuation", ";")
        return SourceDeclaration(
            span=self._cover(start.span, end.span),
            name=name.value,
            value=value,
        )

    def _parse_let(self) -> LetDeclaration:
        start = self._expect("keyword", "let")
        name = self._expect("identifier", description="value name")
        value = self._parse_expression()
        end = self._expect("punctuation", ";")
        return LetDeclaration(
            span=self._cover(start.span, end.span),
            name=name.value,
            value=value,
        )

    def _parse_analyze(self) -> AnalyzeDeclaration:
        start = self._expect("keyword", "analyze")
        name = self._expect("identifier", description="analysis name")
        value = None if self._check("punctuation", ";") else self._parse_expression()
        end = self._expect("punctuation", ";")
        return AnalyzeDeclaration(
            span=self._cover(start.span, end.span),
            name=name.value,
            value=value,
        )

    def _parse_action(self) -> ActionStatement:
        start = self._expect("keyword", "action")
        name = self._expect(
            "identifier",
            description="action result name",
        )
        operation = self._expect(
            "string",
            description="action operation string",
        )
        self._expect("keyword", "using")
        capability = self._expect(
            "string",
            description="action capability string",
        )
        arguments = self._parse_expression()
        end = self._expect("punctuation", ";")
        return ActionStatement(
            span=self._cover(start.span, end.span),
            name=name.value,
            operation=operation.value,
            capability=capability.value,
            arguments=arguments,
        )

    def _parse_require(self) -> RequireStatement:
        start = self._expect("keyword", "require")
        capability = self._parse_expression()
        end = self._expect("punctuation", ";")
        return RequireStatement(
            span=self._cover(start.span, end.span),
            capability=capability,
        )

    def _parse_request(self) -> RequestStatement:
        start = self._expect("keyword", "request")
        capability = self._parse_expression()
        end = self._expect("punctuation", ";")
        return RequestStatement(
            span=self._cover(start.span, end.span),
            capability=capability,
        )

    def _parse_assert(self) -> AssertStatement:
        start = self._expect("keyword", "assert")
        condition = self._parse_expression()
        message = None

        if self._match("punctuation", ",") is not None:
            message_token = self._expect(
                "string",
                description="assertion message string",
            )
            message = message_token.value

        end = self._expect("punctuation", ";")
        return AssertStatement(
            span=self._cover(start.span, end.span),
            condition=condition,
            message=message,
        )

    def _parse_publish(self) -> PublishStatement:
        start = self._expect("keyword", "publish")
        value = self._parse_expression()
        end = self._expect("punctuation", ";")
        return PublishStatement(
            span=self._cover(start.span, end.span),
            value=value,
        )

    def _parse_confidence(self) -> ConfidenceStatement:
        start = self._expect("keyword", "confidence")
        value = self._parse_expression()
        end = self._expect("punctuation", ";")
        return ConfidenceStatement(
            span=self._cover(start.span, end.span),
            value=value,
        )

    def _parse_citations(self) -> CitationsStatement:
        start = self._expect("keyword", "citations")
        self._expect("punctuation", "[")
        values = []

        if not self._check("punctuation", "]"):
            values.append(self._parse_expression())

            while self._match("punctuation", ",") is not None:
                if self._check("punctuation", "]"):
                    self._error(
                        "expected expression after ','",
                        code=DiagnosticCode.SYN_MALFORMED_CITATIONS,
                    )
                values.append(self._parse_expression())

        self._expect("punctuation", "]")
        end = self._expect("punctuation", ";")
        return CitationsStatement(
            span=self._cover(start.span, end.span),
            values=tuple(values),
        )

    def _parse_when(self) -> WhenStatement:
        start = self._expect("keyword", "when")
        condition = self._parse_expression()
        body = self._parse_block()
        otherwise = None
        end_span = body.span

        if self._match("keyword", "otherwise") is not None:
            otherwise = self._parse_block()
            end_span = otherwise.span

        return WhenStatement(
            span=self._cover(start.span, end_span),
            condition=condition,
            body=body,
            otherwise=otherwise,
        )

    def _parse_block(self) -> Block:
        opening = self._expect("punctuation", "{")
        statements = []

        while not self._check("punctuation", "}"):
            if self._at_end():
                self._error(
                    "expected '}' to close block",
                    token=opening,
                    code=DiagnosticCode.SYN_UNCLOSED_BLOCK,
                )
            statements.append(self._parse_statement())

        closing = self._expect("punctuation", "}")
        return Block(
            span=self._cover(opening.span, closing.span),
            statements=tuple(statements),
        )

    def _parse_expression(self) -> Expression:
        return self._parse_binary_level(0)

    def _parse_binary_level(self, level: int) -> Expression:
        if level >= len(self._BINARY_LEVELS):
            return self._parse_unary()

        left = self._parse_binary_level(level + 1)
        operators = self._BINARY_LEVELS[level]

        while (
            self._current() is not None
            and self._current().type == "operator"
            and self._current().value in operators
        ):
            operator = self._advance()
            right = self._parse_binary_level(level + 1)
            left = BinaryExpression(
                span=self._cover(left.span, right.span),
                left=left,
                operator=operator.value,
                right=right,
            )

        return left

    def _parse_unary(self) -> Expression:
        token = self._current()

        if (
            token is not None
            and token.type == "operator"
            and token.value in self._UNARY_OPERATORS
        ):
            operator = self._advance()
            operand = self._parse_unary()
            return UnaryExpression(
                span=self._cover(operator.span, operand.span),
                operator=operator.value,
                operand=operand,
            )

        return self._parse_postfix()

    def _parse_postfix(self) -> Expression:
        expression = self._parse_primary()

        while True:
            if self._match("punctuation", ".") is not None:
                member = self._expect(
                    "identifier",
                    description="member name",
                )
                expression = MemberAccess(
                    span=self._cover(
                        expression.span,
                        member.span,
                    ),
                    target=expression,
                    member=member.value,
                )
                continue

            opening = self._match("punctuation", "[")
            if opening is not None:
                index = self._parse_expression()
                closing = self._expect("punctuation", "]")
                expression = IndexAccess(
                    span=self._cover(
                        expression.span,
                        closing.span,
                    ),
                    target=expression,
                    index=index,
                )
                continue

            return expression

    def _parse_primary(self) -> Expression:
        token = self._current()

        if token is None:
            self._error(
                "expected expression",
                code=DiagnosticCode.SYN_EXPECTED_EXPRESSION,
            )

        if token.type == "string":
            self._advance()
            return StringLiteral(span=token.span, value=token.value)

        if token.type == "number":
            self._advance()
            value = float(token.value) if "." in token.value else int(token.value)
            return NumberLiteral(span=token.span, value=value)

        if token.type == "identifier":
            self._advance()

            if token.value == "true":
                return BooleanLiteral(span=token.span, value=True)

            if token.value == "false":
                return BooleanLiteral(span=token.span, value=False)

            if (
                self._check("punctuation", ".")
                and self.index + 2 < len(self.tokens)
                and self.tokens[self.index + 1].type == "identifier"
                and self.tokens[self.index + 2].type == "punctuation"
                and self.tokens[self.index + 2].value == "("
            ):
                self._advance()
                function = self._advance()
                self._advance()
                arguments: list[Expression] = []

                if not self._check("punctuation", ")"):
                    arguments.append(self._parse_expression())
                    while self._match("punctuation", ",") is not None:
                        arguments.append(self._parse_expression())

                closing = self._expect("punctuation", ")")
                return CallExpression(
                    span=self._cover(token.span, closing.span),
                    name=function.value,
                    arguments=tuple(arguments),
                    qualifier=token.value,
                )

            if self._match("punctuation", "(") is not None:
                arguments: list[Expression] = []

                if not self._check("punctuation", ")"):
                    arguments.append(self._parse_expression())
                    while self._match("punctuation", ",") is not None:
                        arguments.append(self._parse_expression())

                closing = self._expect("punctuation", ")")
                return CallExpression(
                    span=self._cover(token.span, closing.span),
                    name=token.value,
                    arguments=tuple(arguments),
                )

            return Reference(span=token.span, name=token.value)

        list_opening = self._match("punctuation", "[")
        if list_opening is not None:
            items: list[Expression] = []

            if not self._check("punctuation", "]"):
                items.append(self._parse_expression())
                while self._match("punctuation", ",") is not None:
                    items.append(self._parse_expression())

            closing = self._expect("punctuation", "]")
            return ListLiteral(
                span=self._cover(list_opening.span, closing.span),
                items=tuple(items),
            )

        object_opening = self._match("punctuation", "{")
        if object_opening is not None:
            entries: list[tuple[str, Expression]] = []

            if not self._check("punctuation", "}"):
                while True:
                    key = self._current()
                    if key is None or key.type not in {
                        "identifier",
                        "string",
                    }:
                        self._error(
                            "expected object member name",
                            token=key,
                            code=DiagnosticCode.SYN_EXPECTED_TOKEN,
                        )
                    self._advance()
                    self._expect("punctuation", ":")
                    entries.append(
                        (
                            key.value,
                            self._parse_expression(),
                        )
                    )
                    if self._match("punctuation", ",") is None:
                        break

            closing = self._expect("punctuation", "}")
            return ObjectLiteral(
                span=self._cover(
                    object_opening.span,
                    closing.span,
                ),
                entries=tuple(entries),
            )

        opening = self._match("punctuation", "(")

        if opening is not None:
            expression = self._parse_expression()
            closing = self._expect("punctuation", ")")
            return replace(
                expression,
                span=self._cover(opening.span, closing.span),
            )

        self._error(
            f"expected expression, found {token.value!r}",
            token=token,
            code=DiagnosticCode.SYN_EXPECTED_EXPRESSION,
        )

    def _at_end(self) -> bool:
        return self.index >= len(self.tokens)

    def _current(self) -> Token | None:
        return None if self._at_end() else self.tokens[self.index]

    def _advance(self) -> Token:
        token = self._current()

        if token is None:
            self._error(
                "unexpected end of input",
                code=DiagnosticCode.SYN_EXPECTED_TOKEN,
            )

        self.index += 1
        return token

    def _check(self, token_type: str, value: str | None = None) -> bool:
        token = self._current()

        if token is None or token.type != token_type:
            return False

        return value is None or token.value == value

    def _match(self, token_type: str, value: str | None = None) -> Token | None:
        if not self._check(token_type, value):
            return None
        return self._advance()

    def _expect(
        self,
        token_type: str,
        value: str | None = None,
        *,
        description: str | None = None,
    ) -> Token:
        if self._check(token_type, value):
            return self._advance()

        token = self._current()
        expected = description or (
            repr(value) if value is not None else token_type
        )

        if token is None:
            self._error(
                f"expected {expected}, found end of input",
                code=DiagnosticCode.SYN_EXPECTED_TOKEN,
            )

        self._error(
            f"expected {expected}, found {token.value!r}",
            token=token,
            code=DiagnosticCode.SYN_EXPECTED_TOKEN,
        )

    def _error(
        self,
        message: str,
        *,
        code: DiagnosticCode,
        token: Token | None = None,
    ) -> None:
        location = token if token is not None else self._current()

        if location is not None:
            span = location.span
        elif self.tokens:
            end = self.tokens[-1].span.end
            span = point_span(
                file=end.file,
                line=end.line,
                column=end.column + 1,
            )
        else:
            span = point_span(
                file=self.file,
                line=1,
                column=1,
            )

        raise ParserError(
            error_diagnostic(
                code=code,
                message=message,
                span=span,
            )
        )

    @staticmethod
    def _cover(first: SourceSpan, last: SourceSpan) -> SourceSpan:
        return SourceSpan(start=first.start, end=last.end)


def parse(source: str, file: str = "<memory>") -> Program:
    tokens = Lexer(source, file=file).tokenize()
    return Parser(tokens, file=file).parse_program()


def parse_expression(source: str, file: str = "<expression>") -> Expression:
    tokens = Lexer(source, file=file).tokenize()
    return Parser(tokens, file=file).parse_expression_only()
