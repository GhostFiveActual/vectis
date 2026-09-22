# GHOST FIVE // VECTIS
# Regression coverage for named stage syntax and graph metadata.

from __future__ import annotations

import unittest

from vectis.compiler import compile_program
from vectis.formatter import format_program
from vectis.parser import parse
from vectis.product import graph_summary, node_stage_name
from vectis.runtime import Runtime


class StageTests(unittest.TestCase):
    """Protect stage organization without hidden runtime behavior."""

    SOURCE = """mission "Staged mission" {
    stage "Inputs" {
        source ready true;
        source score 94;
    }

    stage "Decision" {
        let approved ready && score >= 80;
        when approved {
            publish "AUTHORIZED";
        } otherwise {
            publish "REVIEW";
        }
    }
}
"""

    def test_stage_parses_and_formats_deterministically(self):
        program = parse(self.SOURCE, file="<stage-test>")
        formatted = format_program(program)
        reparsed = parse(formatted, file="<stage-test>")

        self.assertEqual(format_program(reparsed), formatted)
        self.assertIn('stage "Inputs" {', formatted)
        self.assertIn('stage "Decision" {', formatted)

    def test_stage_metadata_is_attached_to_nodes(self):
        result = compile_program(
            parse(self.SOURCE, file="<stage-test>")
        )
        self.assertTrue(result.ok)

        metadata = {
            node.id: dict(node.metadata)
            for node in result.graph.nodes
        }
        self.assertEqual(metadata["ready"]["stage"], "Inputs")
        self.assertEqual(metadata["score"]["stage"], "Inputs")
        self.assertEqual(metadata["approved"]["stage"], "Decision")
        self.assertEqual(
            metadata["condition:0001"]["stage"],
            "Decision",
        )

    def test_graph_summary_reports_stage_structure(self):
        result = compile_program(
            parse(self.SOURCE, file="<stage-test>")
        )
        summary = graph_summary(result.graph)

        self.assertEqual(summary["stage_count"], 2)
        self.assertEqual(
            summary["stages"],
            ["Inputs", "Decision"],
        )
        self.assertEqual(
            node_stage_name(result.graph.node("ready")),
            "Inputs",
        )

    def test_stage_preserves_cross_stage_dependencies(self):
        result = compile_program(
            parse(self.SOURCE, file="<stage-test>")
        )
        runtime = Runtime(result.graph).execute()

        self.assertTrue(runtime.success)
        self.assertEqual(runtime.value_for("approved"), True)
        self.assertEqual(
            runtime.value_for("publish:0001"),
            "AUTHORIZED",
        )

    def test_nested_stage_records_full_path(self):
        source = """mission "Nested" {
    stage "Outer" {
        stage "Inner" {
            source ready true;
        }
    }
}
"""
        result = compile_program(
            parse(source, file="<stage-test>")
        )
        self.assertTrue(result.ok)
        self.assertEqual(
            dict(result.graph.node("ready").metadata)["stage"],
            "Outer / Inner",
        )


if __name__ == "__main__":
    unittest.main()
