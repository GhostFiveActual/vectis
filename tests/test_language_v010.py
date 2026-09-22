# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS language v010 contract.
from __future__ import annotations

import unittest

from vectis.compiler import compile_program
from vectis.ir import EdgeKind, NodeKind
from vectis.parser import parse
from vectis.runtime import NodeState, Runtime


class LanguageV010Tests(unittest.TestCase):
    SOURCE = '''mission "VECTIS 0.1" {
    source ready true;
    source score 91;
    let product upper("vectis");
    let passing score >= 80;
    let message concat(product, " READY");

    when ready && passing {
        publish message;
        publish length(message);
    } otherwise {
        publish "review";
        publish "blocked";
    }
}
'''

    def compile(self):
        result = compile_program(parse(self.SOURCE, file="<v010-test>"))
        self.assertTrue(result.ok, result.diagnostics)
        self.assertIsNotNone(result.graph)
        return result.graph

    def test_let_nodes_are_first_class_values(self):
        graph = self.compile()
        self.assertEqual(graph.node("product").kind, NodeKind.VALUE)
        self.assertEqual(graph.node("product").value, "VECTIS")
        self.assertEqual(graph.node("passing").value, True)
        self.assertEqual(graph.node("message").value, "VECTIS READY")

    def test_general_condition_expression_executes(self):
        graph = self.compile()
        result = Runtime(graph).execute()
        self.assertTrue(result.success, result.failures)
        self.assertEqual(result.value_for("condition:0001"), True)
        self.assertEqual(result.value_for("publish:0001"), "VECTIS READY")
        self.assertEqual(result.value_for("publish:0002"), 12)
        self.assertIs(result.state_for("publish:0003"), NodeState.SKIPPED)
        self.assertIs(result.state_for("publish:0004"), NodeState.SKIPPED)

    def test_every_branch_node_is_explicitly_gated(self):
        graph = self.compile()
        true_targets = {
            edge.target
            for edge in graph.edges
            if edge.source == "condition:0001"
            and edge.kind is EdgeKind.TRUE_BRANCH
        }
        false_targets = {
            edge.target
            for edge in graph.edges
            if edge.source == "condition:0001"
            and edge.kind is EdgeKind.FALSE_BRANCH
        }
        self.assertEqual(true_targets, {"publish:0001", "publish:0002"})
        self.assertEqual(false_targets, {"publish:0003", "publish:0004"})

    def test_unknown_function_is_semantic_error(self):
        result = compile_program(
            parse('mission "bad" { let x unknown(1); }')
        )
        self.assertFalse(result.ok)
        self.assertIn("SEM003", {item.code.value for item in result.diagnostics})

    def test_invalid_function_arity_is_semantic_error(self):
        result = compile_program(
            parse('mission "bad" { let x upper("a", "b"); }')
        )
        self.assertFalse(result.ok)
        self.assertIn("SEM004", {item.code.value for item in result.diagnostics})


if __name__ == "__main__":
    unittest.main()
