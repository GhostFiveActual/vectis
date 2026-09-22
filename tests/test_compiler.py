# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS compiler contract.
import dataclasses
import unittest

from vectis.compiler import (
    CompilationError,
    CompileResult,
    compile_ast_to_execution_graph,
    compile_program,
)
from vectis.ir import (
    EdgeKind,
    ExecutionGraph,
    NodeKind,
)
from vectis.parser import parse


class CompilerTests(unittest.TestCase):
    def compile_source(
        self,
        source: str,
    ) -> CompileResult:
        program = parse(
            source,
            file="<compiler-test>",
        )
        return compile_program(program)

    def test_empty_program_compiles_to_empty_graph(self):
        result = self.compile_source("")

        self.assertTrue(result.ok)
        self.assertIsInstance(
            result.graph,
            ExecutionGraph,
        )
        self.assertEqual(
            result.graph.nodes,
            (),
        )
        self.assertEqual(
            result.graph.edges,
            (),
        )

    def test_declaration_references_become_dependencies(self):
        result = self.compile_source(
            """
mission "demo" {
    source x 5;
    source y 3;
    source z x + y;
}
"""
        )

        self.assertTrue(result.ok)
        graph = result.graph
        self.assertIsNotNone(graph)

        self.assertEqual(
            tuple(
                node.id
                for node in graph.nodes
            ),
            (
                "x",
                "y",
                "z",
            ),
        )

        dependencies = {
            (
                edge.source,
                edge.target,
                edge.kind,
            )
            for edge in graph.edges
        }

        self.assertEqual(
            dependencies,
            {
                (
                    "x",
                    "z",
                    EdgeKind.DEPENDENCY,
                ),
                (
                    "y",
                    "z",
                    EdgeKind.DEPENDENCY,
                ),
            },
        )

    def test_source_nodes_are_typed(self):
        result = self.compile_source(
            """
mission "demo" {
    source input 42;
}
"""
        )

        node = result.graph.node("input")

        self.assertEqual(
            node.kind,
            NodeKind.SOURCE,
        )
        self.assertEqual(
            node.value,
            42,
        )

    def test_assertion_message_is_preserved_in_plan_metadata(self):
        result = self.compile_source(
            '''
mission "assertion" {
    source ready false;
    assert ready, "Readiness gate failed";
}
'''
        )

        self.assertTrue(result.ok)
        graph = result.graph
        self.assertIsNotNone(graph)
        node = next(
            item
            for item in graph.nodes
            if item.kind is NodeKind.ASSERT
        )
        self.assertEqual(
            dict(node.metadata)["assertion_message"],
            "Readiness gate failed",
        )

    def test_action_rejects_non_object_input(self):
        result = self.compile_source(
            '''
mission "action" {
    action content "filesystem.read_text" using "filesystem" "input.txt";
}
'''
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.graph)
        self.assertTrue(
            any(
                "action input must evaluate to an object"
                in diagnostic.message
                for diagnostic in result.diagnostics
            )
        )

    def test_explicit_action_lowers_with_dependencies_and_authority(self):
        result = self.compile_source(
            '''
mission "action" {
    source path "input.txt";
    action content "filesystem.read_text" using "filesystem" {
        path: path
    };
    publish content;
}
'''
        )

        self.assertTrue(result.ok)
        graph = result.graph
        self.assertIsNotNone(graph)
        action = graph.node("content")
        self.assertIs(action.kind, NodeKind.ACTION)
        metadata = dict(action.metadata)
        self.assertEqual(
            metadata["operation"],
            "filesystem.read_text",
        )
        self.assertEqual(
            metadata["capability"],
            "filesystem",
        )
        self.assertIn(
            ("path", "content"),
            {
                (edge.source, edge.target)
                for edge in graph.edges
            },
        )
        self.assertIn(
            ("content", "publish:0001"),
            {
                (edge.source, edge.target)
                for edge in graph.edges
            },
        )

    def test_action_statements_lower_deterministically(self):
        result = self.compile_source(
            """
mission "demo" {
    require "filesystem";
    request "network";
    publish "done";
}
"""
        )

        self.assertTrue(result.ok)

        self.assertEqual(
            tuple(
                node.kind
                for node in result.graph.nodes
            ),
            (
                NodeKind.REQUIRE,
                NodeKind.REQUEST,
                NodeKind.PUBLISH,
            ),
        )

        self.assertEqual(
            tuple(
                node.id
                for node in result.graph.nodes
            ),
            (
                "require:0001",
                "request:0001",
                "publish:0001",
            ),
        )

    def test_when_has_explicit_true_and_false_edges(self):
        result = self.compile_source(
            """
mission "demo" {
    source ready true;
    when ready {
        publish "yes";
    } otherwise {
        publish "no";
    }
}
"""
        )

        self.assertTrue(result.ok)

        branch_kinds = {
            edge.kind
            for edge in result.graph.edges
            if edge.source == "condition:0001"
        }

        self.assertIn(
            EdgeKind.TRUE_BRANCH,
            branch_kinds,
        )
        self.assertIn(
            EdgeKind.FALSE_BRANCH,
            branch_kinds,
        )

    def test_semantic_failure_blocks_graph_generation(self):
        result = self.compile_source(
            """
mission "demo" {
    publish missing;
}
"""
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.graph)
        self.assertGreater(
            len(result.diagnostics),
            0,
        )

    def test_compilation_is_deterministic(self):
        source = """
mission "demo" {
    source x 5;
    source y x + 1;
    publish y;
}
"""

        first = self.compile_source(source)
        second = self.compile_source(source)

        self.assertTrue(first.ok)
        self.assertTrue(second.ok)

        self.assertEqual(
            first.graph.to_json(),
            second.graph.to_json(),
        )

    def test_compile_result_is_immutable(self):
        result = self.compile_source("")

        with self.assertRaises(
            dataclasses.FrozenInstanceError
        ):
            result.graph = None

    def test_compatibility_wrapper_returns_graph(self):
        program = parse(
            """
mission "demo" {
    source x 1;
}
""",
            file="<compiler-test>",
        )

        graph = compile_ast_to_execution_graph(
            program
        )

        self.assertIsInstance(
            graph,
            ExecutionGraph,
        )
        self.assertEqual(
            graph.node("x").kind,
            NodeKind.SOURCE,
        )

    def test_compatibility_wrapper_rejects_semantic_failure(self):
        program = parse(
            """
mission "demo" {
    publish missing;
}
""",
            file="<compiler-test>",
        )

        with self.assertRaises(
            CompilationError
        ):
            compile_ast_to_execution_graph(
                program
            )


if __name__ == "__main__":
    unittest.main()
