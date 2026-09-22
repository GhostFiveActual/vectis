# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS ast contract.
import unittest
from dataclasses import FrozenInstanceError

from vectis.ast import (
    AnalyzeDeclaration,
    BinaryExpression,
    Block,
    BooleanLiteral,
    CitationsStatement,
    ConfidenceStatement,
    Expression,
    Mission,
    Node,
    NumberLiteral,
    Program,
    PublishStatement,
    Reference,
    RequestStatement,
    RequireStatement,
    SourceDeclaration,
    Statement,
    StringLiteral,
    UnaryExpression,
    WhenStatement,
)
from vectis.source_position import SourcePosition
from vectis.source_span import SourceSpan


def span(
    start_column: int = 1,
    end_column: int = 2,
) -> SourceSpan:
    return SourceSpan(
        start=SourcePosition(
            line=1,
            column=start_column,
            file="test.vectis",
        ),
        end=SourcePosition(
            line=1,
            column=end_column,
            file="test.vectis",
        ),
    )


class ASTTests(unittest.TestCase):
    def test_uses_canonical_source_span(self):
        node = StringLiteral(
            span=span(),
            value="hello",
        )

        self.assertIs(
            type(node.span),
            SourceSpan,
        )

    def test_node_rejects_noncanonical_span(self):
        with self.assertRaises(TypeError):
            Node(
                span=object(),
            )

    def test_ast_is_immutable(self):
        node = Reference(
            span=span(),
            name="input",
        )

        with self.assertRaises(FrozenInstanceError):
            node.name = "other"

    def test_literal_nodes_are_expressions(self):
        values = (
            StringLiteral(
                span=span(),
                value="hello",
            ),
            NumberLiteral(
                span=span(),
                value=42,
            ),
            NumberLiteral(
                span=span(),
                value=0.8,
            ),
            BooleanLiteral(
                span=span(),
                value=True,
            ),
        )

        for value in values:
            self.assertIsInstance(
                value,
                Expression,
            )

    def test_number_rejects_boolean(self):
        with self.assertRaises(TypeError):
            NumberLiteral(
                span=span(),
                value=True,
            )

    def test_reference_requires_name(self):
        with self.assertRaises(ValueError):
            Reference(
                span=span(),
                name="",
            )

    def test_unary_expression(self):
        operand = Reference(
            span=span(),
            name="ready",
        )

        expression = UnaryExpression(
            span=span(),
            operator="!",
            operand=operand,
        )

        self.assertIs(
            expression.operand,
            operand,
        )

    def test_binary_expression(self):
        left = Reference(
            span=span(),
            name="confidence",
        )

        right = NumberLiteral(
            span=span(),
            value=0.8,
        )

        expression = BinaryExpression(
            span=span(),
            left=left,
            operator=">=",
            right=right,
        )

        self.assertIs(
            expression.left,
            left,
        )

        self.assertIs(
            expression.right,
            right,
        )

    def test_block_requires_tuple(self):
        with self.assertRaises(TypeError):
            Block(
                span=span(),
                statements=[],
            )

    def test_block_rejects_expression_as_statement(self):
        with self.assertRaises(TypeError):
            Block(
                span=span(),
                statements=(
                    StringLiteral(
                        span=span(),
                        value="not a statement",
                    ),
                ),
            )

    def test_mission_is_statement(self):
        body = Block(
            span=span(),
            statements=(),
        )

        mission = Mission(
            span=span(),
            name="research",
            body=body,
        )

        self.assertIsInstance(
            mission,
            Statement,
        )

        self.assertIs(
            mission.body,
            body,
        )

    def test_source_declaration(self):
        value = StringLiteral(
            span=span(),
            value="https://example.invalid",
        )

        declaration = SourceDeclaration(
            span=span(),
            name="primary",
            value=value,
        )

        self.assertIs(
            declaration.value,
            value,
        )

    def test_analyze_declaration_may_defer_value(self):
        declaration = AnalyzeDeclaration(
            span=span(),
            name="summary",
        )

        self.assertIsNone(
            declaration.value,
        )

    def test_capability_statements_accept_expressions(self):
        capability = Reference(
            span=span(),
            name="network",
        )

        require = RequireStatement(
            span=span(),
            capability=capability,
        )

        request = RequestStatement(
            span=span(),
            capability=capability,
        )

        self.assertIs(
            require.capability,
            capability,
        )

        self.assertIs(
            request.capability,
            capability,
        )

    def test_publish_statement(self):
        value = Reference(
            span=span(),
            name="report",
        )

        statement = PublishStatement(
            span=span(),
            value=value,
        )

        self.assertIs(
            statement.value,
            value,
        )

    def test_citations_are_immutable_expression_tuple(self):
        first = Reference(
            span=span(),
            name="primary",
        )

        second = Reference(
            span=span(),
            name="secondary",
        )

        statement = CitationsStatement(
            span=span(),
            values=(
                first,
                second,
            ),
        )

        self.assertEqual(
            statement.values,
            (
                first,
                second,
            ),
        )

        with self.assertRaises(TypeError):
            CitationsStatement(
                span=span(),
                values=[first],
            )

    def test_confidence_is_expression_backed(self):
        value = NumberLiteral(
            span=span(),
            value=0.9,
        )

        statement = ConfidenceStatement(
            span=span(),
            value=value,
        )

        self.assertIs(
            statement.value,
            value,
        )

    def test_when_owns_optional_otherwise_block(self):
        condition = BinaryExpression(
            span=span(),
            left=Reference(
                span=span(),
                name="confidence",
            ),
            operator=">=",
            right=NumberLiteral(
                span=span(),
                value=0.8,
            ),
        )

        primary = Block(
            span=span(),
            statements=(),
        )

        alternate = Block(
            span=span(),
            statements=(),
        )

        statement = WhenStatement(
            span=span(),
            condition=condition,
            body=primary,
            otherwise=alternate,
        )

        self.assertIs(
            statement.otherwise,
            alternate,
        )

    def test_program_preserves_statement_order(self):
        first = SourceDeclaration(
            span=span(),
            name="input",
            value=StringLiteral(
                span=span(),
                value="data",
            ),
        )

        second = PublishStatement(
            span=span(),
            value=Reference(
                span=span(),
                name="input",
            ),
        )

        program = Program(
            span=span(),
            statements=(
                first,
                second,
            ),
        )

        self.assertEqual(
            program.statements,
            (
                first,
                second,
            ),
        )


if __name__ == "__main__":
    unittest.main()
