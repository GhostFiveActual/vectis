# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS assert statement contract.
from __future__ import annotations

import unittest

from vectis.compiler import compile_program
from vectis.ir import NodeKind
from vectis.parser import parse
from vectis.runtime import NodeState, Runtime


class AssertStatementTests(unittest.TestCase):
    def compile(self, source: str):
        result = compile_program(parse(source, file="<assert-test>"))
        self.assertTrue(result.ok, result.diagnostics)
        return result.graph

    def test_true_assert_succeeds(self):
        graph = self.compile(
            'mission "assert" { source score 90; assert score >= 80; publish "ok"; }'
        )
        node = graph.node("assert:0001")
        self.assertEqual(node.kind, NodeKind.ASSERT)
        result = Runtime(graph).execute()
        self.assertTrue(result.success)
        self.assertIs(result.state_for("assert:0001"), NodeState.SUCCEEDED)

    def test_false_assert_fails(self):
        graph = self.compile(
            'mission "assert" { source score 70; assert score >= 80; publish "never"; }'
        )
        result = Runtime(graph).execute()
        self.assertFalse(result.success)
        self.assertIs(result.state_for("assert:0001"), NodeState.FAILED)
        self.assertIsNotNone(result.failure_for("assert:0001"))
        self.assertIs(result.state_for("publish:0001"), NodeState.BLOCKED)

    def test_non_boolean_assert_is_semantic_error(self):
        result = compile_program(parse('mission "assert" { assert 1; }'))
        self.assertFalse(result.ok)
        self.assertIn("SEM005", {item.code.value for item in result.diagnostics})


if __name__ == "__main__":
    unittest.main()
