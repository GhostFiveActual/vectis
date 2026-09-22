# GHOST FIVE // VECTIS
# Regression coverage for deterministic user-defined pure functions.
from __future__ import annotations

import unittest

from vectis.ast import FunctionDeclaration
from vectis.compiler import compile_program
from vectis.formatter import format_program
from vectis.ir import EdgeKind
from vectis.parser import parse
from vectis.runtime import Runtime


class PureFunctionTests(unittest.TestCase):
    def compile(self, source: str):
        program = parse(
            source,
            file="<pure-function-test>",
        )
        return program, compile_program(program)

    def test_parser_preserves_function_contract(self):
        program = parse(
            """
function release_ready(score, risk) {
    return score >= 90 && risk <= 25;
}
"""
        )

        function = program.statements[0]
        self.assertIsInstance(
            function,
            FunctionDeclaration,
        )
        self.assertEqual(
            function.name,
            "release_ready",
        )
        self.assertEqual(
            function.parameters,
            ("score", "risk"),
        )

    def test_formatter_round_trip_is_stable(self):
        source = """
function release_ready(score, risk) {
return score >= 90 && risk <= 25;
}

mission "release" {
source quality 94;
source risk 12;
let approved release_ready(quality, risk);
publish approved;
}
"""
        first = format_program(parse(source))
        second = format_program(parse(first))

        self.assertEqual(first, second)
        self.assertIn(
            "function release_ready(score, risk) {",
            first,
        )
        self.assertIn(
            "    return ((score >= 90) && (risk <= 25));",
            first,
        )

    def test_function_expands_into_existing_execution_model(self):
        _program, compiled = self.compile(
            """
function release_ready(score, risk) {
    return score >= 90 && risk <= 25;
}

mission "release" {
    source quality 94;
    source risk 12;
    let approved release_ready(quality, risk);
    publish approved;
}
"""
        )

        self.assertTrue(
            compiled.ok,
            compiled.diagnostics,
        )
        graph = compiled.graph
        self.assertIsNotNone(graph)
        self.assertEqual(
            tuple(node.id for node in graph.nodes),
            (
                "quality",
                "risk",
                "approved",
                "publish:0001",
            ),
        )

        approved = graph.node("approved")
        metadata = dict(approved.metadata)
        self.assertEqual(
            metadata["source_expression"],
            "release_ready(quality, risk)",
        )
        self.assertNotIn(
            "release_ready",
            metadata["expression"],
        )

        dependencies = {
            (
                edge.source,
                edge.target,
                edge.kind,
            )
            for edge in graph.edges
        }
        self.assertIn(
            (
                "quality",
                "approved",
                EdgeKind.DEPENDENCY,
            ),
            dependencies,
        )
        self.assertIn(
            (
                "risk",
                "approved",
                EdgeKind.DEPENDENCY,
            ),
            dependencies,
        )

        result = Runtime(graph).execute()
        self.assertTrue(
            result.success,
            result.failures,
        )
        self.assertIs(
            result.value_for("approved"),
            True,
        )
        self.assertIs(
            result.value_for("publish:0001"),
            True,
        )

    def test_functions_support_forward_calls_and_structured_values(self):
        _program, compiled = self.compile(
            """
function release_summary(score, risk) {
    return object(
        "approved", release_ready(score, risk),
        "score", score,
        "risk", risk
    );
}

function release_ready(score, risk) {
    return score >= 90 && risk <= 25;
}

mission "release" {
    source quality 96;
    source risk 15;
    let summary release_summary(quality, risk);
    assert get(summary, "approved"), "Release gate failed";
    publish summary;
}
"""
        )

        self.assertTrue(
            compiled.ok,
            compiled.diagnostics,
        )
        result = Runtime(compiled.graph).execute()
        self.assertTrue(
            result.success,
            result.failures,
        )
        self.assertEqual(
            result.value_for("summary"),
            {
                "approved": True,
                "score": 96,
                "risk": 15,
            },
        )

    def test_function_result_type_participates_in_semantics(self):
        _program, compiled = self.compile(
            """
function label(value) {
    return upper(value);
}

mission "bad" {
    when label("vectis") {
        publish "invalid";
    }
}
"""
        )

        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "when condition must evaluate to boolean"
                in diagnostic.message
                for diagnostic in compiled.diagnostics
            )
        )

    def test_wrong_arity_is_rejected(self):
        _program, compiled = self.compile(
            """
function gate(score, risk) {
    return score >= 90 && risk <= 25;
}

mission "bad" {
    let approved gate(90);
}
"""
        )

        self.assertFalse(compiled.ok)
        self.assertIn(
            "SEM004",
            {
                diagnostic.code.value
                for diagnostic in compiled.diagnostics
            },
        )

    def test_duplicate_parameters_are_rejected(self):
        _program, compiled = self.compile(
            """
function gate(score, score) {
    return score >= 90;
}

mission "bad" {
    publish "blocked";
}
"""
        )

        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "Duplicate function parameter"
                in diagnostic.message
                for diagnostic in compiled.diagnostics
            )
        )

    def test_builtin_name_collision_is_rejected(self):
        _program, compiled = self.compile(
            """
function upper(value) {
    return value;
}

mission "bad" {
    publish "blocked";
}
"""
        )

        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "conflicts with built-in"
                in diagnostic.message
                for diagnostic in compiled.diagnostics
            )
        )

    def test_function_cannot_capture_mission_or_global_values(self):
        _program, compiled = self.compile(
            """
source minimum 90;

function gate(score) {
    return score >= minimum;
}

mission "bad" {
    source score 95;
    publish gate(score);
}
"""
        )

        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "Function body may reference only parameters"
                in diagnostic.message
                for diagnostic in compiled.diagnostics
            )
        )

    def test_recursive_function_cycle_is_rejected(self):
        _program, compiled = self.compile(
            """
function first(value) {
    return second(value);
}

function second(value) {
    return first(value);
}

mission "bad" {
    publish first(1);
}
"""
        )

        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "Recursive function cycle is not allowed"
                in diagnostic.message
                for diagnostic in compiled.diagnostics
            )
        )

    def test_function_declaration_inside_mission_is_rejected(self):
        _program, compiled = self.compile(
            """
mission "bad" {
    function gate(score) {
        return score >= 90;
    }

    source score 95;
    publish gate(score);
}
"""
        )

        self.assertFalse(compiled.ok)
        self.assertTrue(
            any(
                "only allowed at program top level"
                in diagnostic.message
                for diagnostic in compiled.diagnostics
            )
        )


if __name__ == "__main__":
    unittest.main()
