# GHOST FIVE // VECTIS
# Regression coverage for first-class structured value syntax.
from __future__ import annotations

import unittest

from vectis.ast import (
    IndexAccess,
    ListLiteral,
    MemberAccess,
    ObjectLiteral,
)
from vectis.compiler import compile_program
from vectis.evaluator import EvaluationError, evaluate_expression
from vectis.formatter import format_program
from vectis.ir import EdgeKind
from vectis.parser import parse, parse_expression
from vectis.runtime import Runtime


class StructuredSyntaxTests(unittest.TestCase):
    def evaluate(self, source: str, values=None):
        return evaluate_expression(
            parse_expression(
                source,
                file="<structured-syntax-test>",
            ),
            values or {},
        )

    def test_list_literal_evaluates_deterministically(self):
        self.assertEqual(
            self.evaluate('[1, "two", true]'),
            (1, "two", True),
        )

    def test_object_literal_evaluates_deterministically(self):
        self.assertEqual(
            self.evaluate(
                '{ready: true, score: 94, "label": "release"}'
            ),
            {
                "ready": True,
                "score": 94,
                "label": "release",
            },
        )

    def test_member_access_reads_object_value(self):
        self.assertEqual(
            self.evaluate(
                '{build: {coverage: 96}}.build.coverage'
            ),
            96,
        )

    def test_index_access_reads_lists_and_objects(self):
        self.assertEqual(
            self.evaluate('["zero", "one", "two"][1]'),
            "one",
        )
        self.assertEqual(
            self.evaluate(
                '{"release-status": "GO"}["release-status"]'
            ),
            "GO",
        )

    def test_access_errors_are_explicit(self):
        with self.assertRaises(EvaluationError):
            self.evaluate('{ready: true}.missing')
        with self.assertRaises(EvaluationError):
            self.evaluate('[1, 2][4]')
        with self.assertRaises(EvaluationError):
            self.evaluate('[1, 2]["one"]')

    def test_parser_builds_structured_ast(self):
        expression = parse_expression(
            '{build: {coverage: 96, checks: [true, false]}}'
            '.build.checks[0]'
        )
        self.assertIsInstance(expression, IndexAccess)
        self.assertIsInstance(expression.target, MemberAccess)
        self.assertIsInstance(
            expression.target.target,
            MemberAccess,
        )
        root = expression.target.target.target
        self.assertIsInstance(root, ObjectLiteral)

    def test_literal_nodes_are_exposed_directly(self):
        list_expression = parse_expression('[1, 2, 3]')
        object_expression = parse_expression('{a: 1}')
        self.assertIsInstance(list_expression, ListLiteral)
        self.assertIsInstance(object_expression, ObjectLiteral)

    def test_duplicate_object_members_fail_semantics(self):
        program = parse(
            '''
mission "duplicate" {
    source config {ready: true, ready: false};
}
'''
        )
        result = compile_program(program)
        self.assertFalse(result.ok)
        self.assertTrue(
            any(
                "Duplicate object member" in diagnostic.message
                for diagnostic in result.diagnostics
            )
        )

    def test_structured_access_preserves_graph_dependencies(self):
        program = parse(
            '''
mission "structured" {
    source build {passed: true, coverage: 96};
    let approved build.passed && build.coverage >= 90;
    publish approved;
}
'''
        )
        result = compile_program(program)
        self.assertTrue(result.ok)
        self.assertIsNotNone(result.graph)
        dependencies = {
            (edge.source, edge.target, edge.kind)
            for edge in result.graph.edges
        }
        self.assertIn(
            ("build", "approved", EdgeKind.DEPENDENCY),
            dependencies,
        )

    def test_runtime_executes_structured_mission(self):
        program = parse(
            '''
mission "structured" {
    source build {
        passed: true,
        coverage: 96,
        checks: [true, true, true]
    };
    let approved build.passed
        && build.coverage >= 90
        && all(build.checks);
    assert approved, "Build gate failed";
    publish {
        status: if_else(approved, "GO", "HOLD"),
        coverage: build.coverage,
        first_check: build.checks[0]
    };
}
'''
        )
        compiled = compile_program(program)
        self.assertTrue(compiled.ok)
        result = Runtime(compiled.graph).execute()
        self.assertTrue(result.success)
        published = result.value_for("publish:0001")
        self.assertEqual(
            published,
            {
                "status": "GO",
                "coverage": 96,
                "first_check": True,
            },
        )

    def test_pure_function_can_use_structured_syntax(self):
        program = parse(
            '''
function summarize(score, checks) {
    return {
        score: score,
        check_count: size(checks),
        first_check: checks[0]
    };
}

mission "functions" {
    source checks [true, false, true];
    let summary summarize(94, checks);
    publish summary.check_count;
}
'''
        )
        compiled = compile_program(program)
        self.assertTrue(compiled.ok)
        result = Runtime(compiled.graph).execute()
        self.assertTrue(result.success)
        self.assertEqual(
            result.value_for("publish:0001"),
            3,
        )

    def test_formatter_round_trips_structured_syntax(self):
        source = '''
mission "format" {
source build {passed: true, checks: [true, false]};
publish build.checks[0];
}
'''
        first = format_program(parse(source))
        second = format_program(parse(first))
        self.assertEqual(first, second)
        self.assertIn(
            "source build {passed: true, checks: [true, false]};",
            first,
        )
        self.assertIn(
            "publish build.checks[0];",
            first,
        )


if __name__ == "__main__":
    unittest.main()
