# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS parser contract.
from pathlib import Path
import unittest

from vectis.ast import (
    ActionStatement,
    AnalyzeDeclaration,
    AssertStatement,
    BinaryExpression,
    BooleanLiteral,
    CitationsStatement,
    ConfidenceStatement,
    Mission,
    NumberLiteral,
    Program,
    PublishStatement,
    Reference,
    RequestStatement,
    RequireStatement,
    SourceDeclaration,
    UnaryExpression,
    WhenStatement,
)
from vectis.parser import ParserError, parse


class ParserTests(unittest.TestCase):
    def test_empty_program(self):
        program = parse("", file="empty.vectis")
        self.assertIsInstance(program, Program)
        self.assertEqual(program.statements, ())
        self.assertEqual(program.span.file, "empty.vectis")
        self.assertEqual(
            (program.span.start.line, program.span.start.column),
            (1, 1),
        )

    def test_all_statement_forms(self):
        source = (
            'mission "Demo" {\n'
            '    source web "query";\n'
            '    analyze findings;\n'
            '    require web;\n'
            '    request human_reviewer;\n'
            '    publish findings;\n'
            '    citations [primary, secondary];\n'
            '    confidence 0.90;\n'
            '}\n'
        )
        program = parse(source, file="statements.vectis")
        mission = program.statements[0]
        self.assertIsInstance(mission, Mission)
        self.assertEqual(
            tuple(type(statement) for statement in mission.body.statements),
            (
                SourceDeclaration,
                AnalyzeDeclaration,
                RequireStatement,
                RequestStatement,
                PublishStatement,
                CitationsStatement,
                ConfidenceStatement,
            ),
        )

    def test_analyze_optional_value(self):
        first, second = parse(
            "analyze first; analyze second evidence;",
            file="analyze.vectis",
        ).statements
        self.assertIsNone(first.value)
        self.assertIsInstance(second.value, Reference)
        self.assertEqual(second.value.name, "evidence")

    def test_action_statement_preserves_explicit_authority(self):
        node = parse(
            (
                'action response "http.request" using "http" '
                '{method: "GET", url: endpoint};'
            ),
            file="action.vectis",
        ).statements[0]
        self.assertIsInstance(node, ActionStatement)
        self.assertEqual(node.name, "response")
        self.assertEqual(node.operation, "http.request")
        self.assertEqual(node.capability, "http")
        self.assertEqual(
            type(node.arguments).__name__,
            "ObjectLiteral",
        )

    def test_assertion_message_is_optional_and_preserved(self):
        first, second = parse(
            'assert ready; assert score >= 90, "Quality must be at least 90";',
            file="assertions.vectis",
        ).statements
        self.assertIsInstance(first, AssertStatement)
        self.assertIsNone(first.message)
        self.assertIsInstance(second, AssertStatement)
        self.assertEqual(
            second.message,
            "Quality must be at least 90",
        )

    def test_assertion_message_requires_string(self):
        with self.assertRaises(ParserError):
            parse(
                "assert ready, reason;",
                file="assertion-message.vectis",
            )

    def test_when_owns_otherwise(self):
        node = parse(
            "when ready { publish result; } otherwise { request reviewer; }",
            file="when.vectis",
        ).statements[0]
        self.assertIsInstance(node, WhenStatement)
        self.assertIsNotNone(node.otherwise)

    def test_contextual_boolean_literals(self):
        condition = parse(
            "when true && false { publish result; }",
            file="booleans.vectis",
        ).statements[0].condition
        self.assertIsInstance(condition, BinaryExpression)
        self.assertIsInstance(condition.left, BooleanLiteral)
        self.assertTrue(condition.left.value)
        self.assertIsInstance(condition.right, BooleanLiteral)
        self.assertFalse(condition.right.value)

    def test_boolean_matching_is_case_sensitive(self):
        condition = parse(
            "when True { publish result; }",
            file="case.vectis",
        ).statements[0].condition
        self.assertIsInstance(condition, Reference)
        self.assertEqual(condition.name, "True")

    def test_multiplication_precedes_addition(self):
        expression = parse(
            "confidence 1 + 2 * 3;",
            file="precedence.vectis",
        ).statements[0].value
        self.assertEqual(expression.operator, "+")
        self.assertIsInstance(expression.right, BinaryExpression)
        self.assertEqual(expression.right.operator, "*")

    def test_and_precedes_or(self):
        condition = parse(
            "when a && b || c { publish result; }",
            file="logic.vectis",
        ).statements[0].condition
        self.assertEqual(condition.operator, "||")
        self.assertIsInstance(condition.left, BinaryExpression)
        self.assertEqual(condition.left.operator, "&&")

    def test_binary_operators_are_left_associative(self):
        expression = parse(
            "confidence a - b - c;",
            file="assoc.vectis",
        ).statements[0].value
        self.assertEqual(expression.operator, "-")
        self.assertIsInstance(expression.left, BinaryExpression)
        self.assertEqual(expression.left.operator, "-")

    def test_unary_operators_are_right_associative(self):
        expression = parse(
            "confidence ! ! ready;",
            file="unary.vectis",
        ).statements[0].value
        self.assertIsInstance(expression, UnaryExpression)
        self.assertIsInstance(expression.operand, UnaryExpression)

    def test_signed_number_is_literal(self):
        expression = parse(
            "confidence -42;",
            file="number.vectis",
        ).statements[0].value
        self.assertIsInstance(expression, NumberLiteral)
        self.assertEqual(expression.value, -42)

    def test_unary_minus_reference(self):
        expression = parse(
            "confidence - ready;",
            file="unary-minus.vectis",
        ).statements[0].value
        self.assertIsInstance(expression, UnaryExpression)
        self.assertEqual(expression.operator, "-")

    def test_parentheses_override_precedence(self):
        expression = parse(
            "confidence (1 + 2) * 3;",
            file="paren.vectis",
        ).statements[0].value
        self.assertEqual(expression.operator, "*")
        self.assertIsInstance(expression.left, BinaryExpression)
        self.assertEqual(expression.left.operator, "+")

    def test_empty_citations(self):
        node = parse(
            "citations [];",
            file="citations.vectis",
        ).statements[0]
        self.assertEqual(node.values, ())

    def test_citations_preserve_order(self):
        node = parse(
            "citations [a, b, c];",
            file="citations.vectis",
        ).statements[0]
        self.assertEqual(
            tuple(value.name for value in node.values),
            ("a", "b", "c"),
        )

    def test_all_official_valid_examples_parse(self):
        for path in sorted(Path("examples/valid").glob("*.vectis")):
            with self.subTest(path=path):
                program = parse(
                    path.read_text(encoding="utf-8"),
                    file=str(path),
                )
                self.assertIsInstance(program, Program)

    def test_all_official_invalid_examples_fail_with_location(self):
        for path in sorted(Path("examples/invalid").glob("*.vectis")):
            with self.subTest(path=path):
                with self.assertRaises(ParserError) as caught:
                    parse(
                        path.read_text(encoding="utf-8"),
                        file=str(path),
                    )
                message = str(caught.exception)
                self.assertIn(str(path), message)
                self.assertRegex(message, r":\d+:\d+:")

    def test_standalone_otherwise_is_rejected(self):
        with self.assertRaisesRegex(ParserError, "may only follow"):
            parse(
                "otherwise { publish result; }",
                file="standalone.vectis",
            )

    def test_missing_semicolon_is_rejected(self):
        with self.assertRaises(ParserError):
            parse(
                "publish result",
                file="missing-semicolon.vectis",
            )

    def test_missing_expression_is_rejected(self):
        with self.assertRaises(ParserError):
            parse(
                "confidence;",
                file="missing-expression.vectis",
            )

    def test_unclosed_block_is_rejected(self):
        with self.assertRaises(ParserError):
            parse(
                'mission "x" { publish result;',
                file="unclosed.vectis",
            )

    def test_trailing_citation_comma_is_rejected(self):
        with self.assertRaises(ParserError):
            parse(
                "citations [a,];",
                file="citation-comma.vectis",
            )

    def test_statement_and_program_spans(self):
        program = parse(
            "publish result;\nconfidence 1;",
            file="span.vectis",
        )
        first, second = program.statements
        self.assertEqual(
            (first.span.start.line, first.span.start.column),
            (1, 1),
        )
        self.assertEqual(
            (first.span.end.line, first.span.end.column),
            (1, 15),
        )
        self.assertEqual(
            (second.span.start.line, second.span.start.column),
            (2, 1),
        )
        self.assertEqual(
            (second.span.end.line, second.span.end.column),
            (2, 13),
        )
        self.assertEqual(program.span.start, first.span.start)
        self.assertEqual(program.span.end, second.span.end)

    def test_diagnostic_uses_supplied_file(self):
        with self.assertRaises(ParserError) as caught:
            parse(
                "publish ;",
                file="diagnostic.vectis",
            )
        self.assertIn(
            "diagnostic.vectis:1:",
            str(caught.exception),
        )


if __name__ == "__main__":
    unittest.main()
